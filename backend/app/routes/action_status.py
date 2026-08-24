from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.action import Action
from app.models.recording import Recording
from app.models.user import User
from app.schemas.action import ActionResponse, ActionStatusUpdate

router = APIRouter(prefix='/actions', tags=['actions'])


@router.patch('/{action_id}', response_model=ActionResponse)
def update_action_status(
    action_id: int,
    payload: ActionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    action = (
        db.query(Action)
        .join(Recording, Action.recording_id == Recording.id)
        .filter(
            Action.id == action_id,
            Recording.user_id == current_user.id,
        )
        .first()
    )

    if not action:
        raise HTTPException(status_code=404, detail='Action introuvable.')

    action.status = payload.status
    db.commit()
    db.refresh(action)

    return ActionResponse(
        id=action.id,
        description=action.description,
        status=action.status,
        due_date=action.due_date,
        speaker_id=action.speaker_id,
    )
