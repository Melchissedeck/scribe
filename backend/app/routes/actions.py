from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.user import User
from app.schemas.action import ActionResponse, ExtractActionsResponse
from app.services.action_extraction_service import run_action_extraction

router = APIRouter(prefix='/meetings', tags=['actions'])


@router.post('/{meeting_id}/extract-actions', response_model=ExtractActionsResponse)
def extract_actions(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extrait les actions, le thème et les décisions d'une réunion via le LLM.

    Args:
        meeting_id: Identifiant de la réunion à traiter.
        db: Session de base de données injectée par FastAPI.
        current_user: Utilisateur authentifié, résolu depuis le token JWT.

    Returns:
        Le nombre d'actions créées, le thème détecté et la liste des actions.

    Raises:
        HTTPException: 404 si la réunion est introuvable ou n'appartient pas à l'utilisateur.
        HTTPException: 400 si aucune transcription n'est disponible.
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

    created_actions = run_action_extraction(db, recording)

    return ExtractActionsResponse(
        recording_id=recording.id,
        actions_count=len(created_actions),
        theme=recording.theme,
        actions=[
            ActionResponse(
                id=a.id,
                description=a.description,
                status=a.status,
                due_date=a.due_date,
                speaker_id=a.speaker_id,
            )
            for a in created_actions
        ],
    )
