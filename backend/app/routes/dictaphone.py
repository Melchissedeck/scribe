import traceback
from datetime import timedelta
from functools import partial
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from pydub import AudioSegment
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_consent
from app.models.recording import Recording
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.recording import DiarizeStatusResponse, SegmentOut
from app.services.audio_capture_service import run_capture_background_job
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
    """Crée un nouvel enregistrement dictaphone en attente d'un fichier audio.

    Returns:
        L'identifiant et le statut de l'enregistrement créé.
    """
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
    """Reçoit et enregistre sur disque le fichier audio d'un enregistrement dictaphone.

    Le fichier est sauvegardé sous `UPLOAD_DIR/{recording_id}/` et la durée
    de l'enregistrement est déduite de l'audio pour renseigner
    `stopped_at` (échec silencieux si la durée ne peut être calculée).

    Args:
        recording_id: Identifiant de l'enregistrement concerné.
        audio: Fichier audio envoyé par le client.

    Returns:
        Les informations du fichier audio reçu (identifiant, nom, chemin, message).

    Raises:
        HTTPException: 404 si l'enregistrement est introuvable ; 400 si
            aucun fichier n'est fourni ou si son format n'est pas
            supporté ; 500 si la sauvegarde du fichier échoue.
    """
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
    """Transcrit le fichier audio d'un enregistrement dictaphone via Whisper.

    Args:
        recording_id: Identifiant de l'enregistrement concerné.

    Returns:
        L'identifiant de l'enregistrement et la transcription obtenue.

    Raises:
        HTTPException: 404 si l'enregistrement ou son fichier audio est
            introuvable ; 502 si la transcription échoue.
    """
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


def _process_dictaphone_diarization(app: FastAPI, audio_path: str, db: Session, recording: Recording) -> bool:
    """Transcrit avec horodatage puis diarise avec Pyannote.

    Fonction de traitement de la source de capture dictaphone, passée
    (via `functools.partial` pour lier `app` et `audio_path`) à
    `run_capture_background_job` (abstraction commune avec le pipeline
    visio) : celui-ci ouvre la session et charge l'enregistrement, cette
    fonction se limite au travail propre au dictaphone. Traitement
    purement CPU (pas de GPU sur l'hébergement) et potentiellement long
    sur un enregistrement de plusieurs dizaines de minutes, largement
    au-delà du délai qu'accepte une requête HTTP synchrone — d'où
    l'exécution en tâche de fond.

    Args:
        app: Application FastAPI, pour accéder au cache du pipeline Pyannote.
        audio_path: Chemin du fichier audio local à traiter.
        db: Session de base de données ouverte par `run_capture_background_job`.
        recording: Enregistrement déjà chargé par `run_capture_background_job`.

    Returns:
        True si la diarisation a réussi et les segments ont été persistés.
    """
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
        return True

    except Exception:
        db.rollback()

        # Affiche le traceback complet dans le terminal Uvicorn
        # pendant la phase de diagnostic.
        traceback.print_exc()

        failed = db.query(Recording).filter(Recording.id == recording.id).first()
        if failed:
            failed.diarization_status = "failed"
            db.commit()
        return False


@router.post("/{recording_id}/diarize", status_code=202)
def diarize_audio(
    recording_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lance en tâche de fond la diarisation du fichier audio d'un enregistrement.

    Marque l'enregistrement en statut de diarisation 'processing' puis
    délègue le traitement (transcription horodatée + diarisation Pyannote)
    à `_process_dictaphone_diarization`, exécuté en tâche de fond via
    `run_capture_background_job` (abstraction commune avec le pipeline visio).

    Args:
        recording_id: Identifiant de l'enregistrement concerné.

    Returns:
        L'identifiant de l'enregistrement et son nouveau statut de diarisation.

    Raises:
        HTTPException: 404 si l'enregistrement ou son fichier audio est introuvable.
    """
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

    background_tasks.add_task(
        run_capture_background_job,
        recording.id,
        partial(_process_dictaphone_diarization, request.app, str(audio_path)),
    )

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
    """Récupère le statut de diarisation d'un enregistrement et ses segments si terminée.

    Args:
        recording_id: Identifiant de l'enregistrement concerné.

    Returns:
        Le statut de diarisation, avec la liste des segments si le
        traitement est terminé (liste vide sinon).

    Raises:
        HTTPException: 404 si l'enregistrement est introuvable.
    """
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