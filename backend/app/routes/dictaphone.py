import traceback
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from pydub import AudioSegment
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user, require_consent
from app.models.recording import Recording
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.recording import DiarizeStatusResponse, SegmentOut
from app.services.post_meeting_processing_service import run_post_meeting_processing
from app.services.speaker_assignment_service import SpeakerAssignmentService
from app.services.whisper_service import WhisperService

router = APIRouter(
    prefix="/meetings",
    tags=["dictaphone"],
)


UPLOAD_DIR = Path("uploads")


ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".webm",
    ".ogg",
}


@router.post("")
def create_dictaphone_recording(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consent),
):
    recording = Recording(
        user_id=current_user.id,
        platform="dictaphone",
        native_meeting_id="local",
        bot_name="Scribe",
        status="pending",
    )

    db.add(recording)
    db.commit()
    db.refresh(recording)

    return {
        "recording_id": recording.id,
        "status": recording.status,
    }


@router.post("/{recording_id}/upload-audio")
async def upload_audio(
    recording_id: int,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(
            Recording.id == recording_id,
            Recording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(
            status_code=404,
            detail="Enregistrement introuvable.",
        )

    if not audio.filename:
        raise HTTPException(
            status_code=400,
            detail="Aucun fichier audio fourni.",
        )

    extension = Path(audio.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Format audio non supporté.",
        )

    recording_dir = UPLOAD_DIR / str(recording_id)
    recording_dir.mkdir(parents=True, exist_ok=True)

    audio_path = recording_dir / f"audio{extension}"

    try:
        content = await audio.read()
        audio_path.write_bytes(content)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de sauvegarder le fichier audio : {exc}",
        ) from exc

    try:
        segment = AudioSegment.from_file(str(audio_path))
        duration_seconds = len(segment) / 1000
        recording.stopped_at = recording.started_at + timedelta(seconds=duration_seconds)
        db.commit()
    except Exception:
        pass

    return {
        "recording_id": recording.id,
        "filename": audio.filename,
        "path": str(audio_path),
        "message": "Fichier audio reçu avec succès.",
    }


@router.post("/{recording_id}/transcribe")
def transcribe_audio(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(
            Recording.id == recording_id,
            Recording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(
            status_code=404,
            detail="Enregistrement introuvable.",
        )

    recording_dir = UPLOAD_DIR / str(recording_id)

    if not recording_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Aucun fichier audio trouvé pour cet enregistrement.",
        )

    audio_files = [
        file
        for file in recording_dir.iterdir()
        if file.is_file()
        and file.suffix.lower() in ALLOWED_EXTENSIONS
    ]

    if not audio_files:
        raise HTTPException(
            status_code=404,
            detail="Aucun fichier audio trouvé pour cet enregistrement.",
        )

    audio_path = audio_files[0]

    try:
        service = WhisperService()
        transcript = service.transcribe(str(audio_path))

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur lors de la transcription : {exc}",
        ) from exc

    recording.transcript = transcript

    db.commit()
    db.refresh(recording)

    return {
        "recording_id": recording.id,
        "transcript": recording.transcript,
    }


def run_diarization(app: FastAPI, recording_id: int, audio_path: str) -> None:
    """
    Transcrit avec horodatage puis diarise avec Pyannote, en tâche de
    fond : ce traitement est purement CPU (pas de GPU sur l'hébergement) et
    peut prendre plusieurs minutes sur un enregistrement de plusieurs
    dizaines de minutes, largement au-delà du délai qu'accepte une requête
    HTTP synchrone (le proxy coupe la connexion avant la fin, sans que rien
    ne soit jamais enregistré). Ouvre sa propre session DB (utilisé depuis
    BackgroundTasks, où la session de la requête d'origine est déjà
    fermée).
    """
    db = SessionLocal()
    try:
        recording = db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            return

        try:
            # 1. Transcription avec les timestamps de chaque segment
            whisper_service = WhisperService()
            transcription_segments = whisper_service.transcribe_segments(audio_path)

            # 2. Diarisation avec Pyannote
            # Import différé : évite de charger torch/pyannote au démarrage
            # de l'application, seulement lors de la première diarisation.
            from app.services.pyannote_service import get_pyannote_service

            pyannote_service = get_pyannote_service(app)
            diarization_segments = pyannote_service.diarize(audio_path)

            # 3. Association des segments Whisper avec les speakers Pyannote
            assignment_service = SpeakerAssignmentService()
            assigned_segments = assignment_service.assign_speakers(
                transcription_segments,
                diarization_segments,
            )

            # 4. Suppression des anciens segments du recording
            db.query(TranscriptSegment).filter(
                TranscriptSegment.recording_id == recording.id
            ).delete(synchronize_session=False)

            # 5. Enregistrement des nouveaux segments en base
            for segment in assigned_segments:
                db.add(TranscriptSegment(
                    recording_id=recording.id,
                    start=segment["start"],
                    end=segment["end"],
                    text=segment["text"],
                    speaker=segment["speaker"],
                ))

            recording.diarization_status = "done"
            db.commit()

        except Exception:
            db.rollback()

            # Affiche le traceback complet dans le terminal Uvicorn
            # pendant la phase de diagnostic.
            traceback.print_exc()

            recording = db.query(Recording).filter(Recording.id == recording_id).first()
            if recording:
                recording.diarization_status = "failed"
                db.commit()
            return
    finally:
        db.close()

    run_post_meeting_processing(recording_id)


@router.post("/{recording_id}/diarize", status_code=202)
def diarize_audio(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(
            Recording.id == recording_id,
            Recording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(
            status_code=404,
            detail="Enregistrement introuvable.",
        )

    recording_dir = UPLOAD_DIR / str(recording_id)

    if not recording_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Aucun fichier audio trouvé pour cet enregistrement.",
        )

    audio_files = [
        file
        for file in recording_dir.iterdir()
        if file.is_file()
        and file.suffix.lower() in ALLOWED_EXTENSIONS
    ]

    if not audio_files:
        raise HTTPException(
            status_code=404,
            detail="Aucun fichier audio trouvé pour cet enregistrement.",
        )

    audio_path = audio_files[0]

    recording.diarization_status = "processing"
    db.commit()

    background_tasks.add_task(run_diarization, request.app, recording.id, str(audio_path))

    return {
        "recording_id": recording.id,
        "status": recording.diarization_status,
    }


@router.get("/{recording_id}/diarize-status", response_model=DiarizeStatusResponse)
def get_diarize_status(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(
            Recording.id == recording_id,
            Recording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(
            status_code=404,
            detail="Enregistrement introuvable.",
        )

    segments = []
    if recording.diarization_status == "done":
        transcript_segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.recording_id == recording.id)
            .order_by(TranscriptSegment.start)
            .all()
        )
        segments = [
            SegmentOut(speaker_name=seg.speaker, text=seg.text, start=seg.start)
            for seg in transcript_segments
        ]

    return DiarizeStatusResponse(
        recording_id=recording.id,
        status=recording.diarization_status,
        segments=segments,
    )