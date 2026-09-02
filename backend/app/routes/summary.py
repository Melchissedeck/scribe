from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.user import User
from app.schemas.recording import SummaryResponse
from app.services.summary_generation_service import run_summary_generation

router = APIRouter(prefix='/meetings', tags=['summary'])


@router.post('/{meeting_id}/generate-summary', response_model=SummaryResponse)
def generate_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Génère le résumé d'une réunion à partir de sa transcription.

    Args:
        meeting_id: Identifiant de la réunion.

    Returns:
        Le résumé généré pour la réunion.

    Raises:
        HTTPException: 404 si la réunion est introuvable ou n'appartient pas
            à l'utilisateur ; 400 si aucune transcription n'est disponible.
    """
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

    run_summary_generation(db, recording)
    db.refresh(recording)

    return SummaryResponse(recording_id=recording.id, summary=recording.summary)

@router.get('/{meeting_id}/summary', response_model=SummaryResponse)
def get_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère le résumé déjà généré d'une réunion.

    Args:
        meeting_id: Identifiant de la réunion.

    Returns:
        Le résumé de la réunion.

    Raises:
        HTTPException: 404 si la réunion est introuvable, n'appartient pas
            à l'utilisateur, ou si aucun résumé n'est encore disponible.
    """
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