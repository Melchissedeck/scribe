from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.user import User
from app.schemas.recording import SummaryResponse
from app.services.llm_service import LLMService

router = APIRouter(prefix='/meetings', tags=['summary'])


@router.post('/{meeting_id}/generate-summary', response_model=SummaryResponse)
def generate_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(
            Recording.id == meeting_id,
            Recording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    if not recording.transcript or not recording.transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="Aucune transcription disponible pour cette réunion.",
        )

    llm_service = LLMService()
    summary = llm_service.generate_summary(recording.transcript)

    if summary is None:
        raise HTTPException(
            status_code=502,
            detail="Le service de génération de résumé est momentanément indisponible.",
        )

    recording.summary = summary
    db.commit()
    db.refresh(recording)

    return SummaryResponse(recording_id=recording.id, summary=recording.summary)

@router.get('/{meeting_id}/summary', response_model=SummaryResponse)
def get_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(
            Recording.id == meeting_id,
            Recording.user_id == current_user.id,
        )
        .first()
    )

    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    if not recording.summary or not recording.summary.strip():
        raise HTTPException(
            status_code=404,
            detail="Aucun résumé n'est disponible pour cette réunion pour le moment.",
        )

    return SummaryResponse(recording_id=recording.id, summary=recording.summary)