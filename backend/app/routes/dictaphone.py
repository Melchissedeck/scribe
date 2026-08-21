from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
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
        )

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
        )

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
        whisper_service = WhisperService()

        transcription_segments = (
            whisper_service.transcribe_segments(str(audio_path))
        )

        pyannote_service = request.app.state.pyannote_service

        diarization_segments = (
            pyannote_service.diarize(str(audio_path))
        )

        assignment_service = SpeakerAssignmentService()

        assigned_segments = assignment_service.assign_speakers(
            transcription_segments,
            diarization_segments,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur lors de la diarisation : {exc}",
        )

    return {
        "recording_id": recording.id,
        "segments": assigned_segments,
    }