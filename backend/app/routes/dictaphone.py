import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
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
    current_user: User = Depends(get_current_user),
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


@router.post("/{recording_id}/diarize")
def diarize_audio(
    recording_id: int,
    request: Request,
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
        # 1. Transcription avec les timestamps de chaque segment
        whisper_service = WhisperService()

        transcription_segments = (
            whisper_service.transcribe_segments(str(audio_path))
        )

        # 2. Diarisation avec Pyannote
        # Import différé : évite de charger torch/pyannote au démarrage de
        # l'application, seulement lors de la première diarisation.
        from app.services.pyannote_service import get_pyannote_service

        pyannote_service = get_pyannote_service(request.app)

        diarization_segments = (
            pyannote_service.diarize(str(audio_path))
        )

        # 3. Association des segments Whisper avec les speakers Pyannote
        assignment_service = SpeakerAssignmentService()

        assigned_segments = assignment_service.assign_speakers(
            transcription_segments,
            diarization_segments,
        )

        # 4. Suppression des anciens segments du recording
        db.query(TranscriptSegment).filter(
            TranscriptSegment.recording_id == recording.id
        ).delete(
            synchronize_session=False
        )

        # 5. Enregistrement des nouveaux segments en base
        for segment in assigned_segments:
            transcript_segment = TranscriptSegment(
                recording_id=recording.id,
                start=segment["start"],
                end=segment["end"],
                text=segment["text"],
                speaker=segment["speaker"],
            )

            db.add(transcript_segment)

        # 6. Validation de la transaction
        db.commit()

    except Exception as exc:
        db.rollback()

        # Affiche le traceback complet dans le terminal Uvicorn
        # pendant la phase de diagnostic.
        traceback.print_exc()

        raise HTTPException(
            status_code=502,
            detail=f"Erreur lors de la diarisation : {exc}",
        ) from exc

    return {
        "recording_id": recording.id,
        "segments": assigned_segments,
    }