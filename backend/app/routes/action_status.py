from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.action import Action
from app.models.recording import Recording
from app.models.user import User
from app.schemas.action import ActionDueDateUpdate, ActionResponse, ActionStatusUpdate, OverdueActionOut

router = APIRouter(prefix='/actions', tags=['actions'])

@router.get('', response_model=list[ActionResponse])
def list_actions(
    status: str | None = Query(default=None, description="Filtre par statut : todo, in_progress ou done"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les actions de l'utilisateur courant, avec filtre optionnel par statut.

    Args:
        status: Filtre optionnel sur le statut ('todo', 'in_progress' ou 'done').

    Returns:
        Liste des actions correspondantes, triées par identifiant décroissant.
    """
    query = (
        db.query(Action)
        .join(Recording, Action.recording_id == Recording.id)
        .filter(Recording.user_id == current_user.id)
    )
    if status:
        query = query.filter(Action.status == status)
    actions = query.order_by(Action.id.desc()).all()
    return [
        ActionResponse(
            id=a.id,
            description=a.description,
            status=a.status,
            due_date=a.due_date,
            speaker_id=a.speaker_id,
        )
        for a in actions
    ]

@router.get('/open', response_model=list[ActionResponse])
def list_open_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les actions non terminées de l'utilisateur courant, triées par échéance.

    Les actions au statut 'todo' ou 'in_progress' sont retournées, les plus
    proches de leur échéance en premier ; celles sans échéance sont
    placées en dernier.

    Returns:
        Liste des actions ouvertes.
    """
    actions = (
        db.query(Action)
        .join(Recording, Action.recording_id == Recording.id)
        .filter(
            Recording.user_id == current_user.id,
            Action.status.in_(['todo', 'in_progress']),
        )
        .order_by(Action.due_date.is_(None), Action.due_date.asc())
        .all()
    )

    return [
        ActionResponse(
            id=a.id,
            description=a.description,
            status=a.status,
            due_date=a.due_date,
            speaker_id=a.speaker_id,
        )
        for a in actions
    ]

@router.get('/overdue', response_model=list[OverdueActionOut])
def list_overdue_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les actions en retard de l'utilisateur courant.

    Une action est considérée en retard si elle n'est pas terminée, possède
    une échéance et que celle-ci est déjà dépassée.

    Returns:
        Liste des actions en retard, avec le thème de la réunion associée.
    """
    actions = (
        db.query(Action)
        .join(Recording, Action.recording_id == Recording.id)
        .filter(
            Recording.user_id == current_user.id,
            Action.status != 'done',
            Action.due_date.isnot(None),
            Action.due_date < date.today(),
        )
        .order_by(Action.due_date.asc())
        .all()
    )

    return [
        OverdueActionOut(
            id=action.id,
            description=action.description,
            status=action.status,
            due_date=action.due_date,
            meeting_id=action.recording_id,
            meeting_theme=action.recording.theme,
        )
        for action in actions
    ]


@router.patch('/{action_id}', response_model=ActionResponse)
def update_action_status(
    action_id: int,
    payload: ActionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Met à jour le statut d'une action appartenant à l'utilisateur courant.

    Args:
        action_id: Identifiant de l'action à mettre à jour.
        payload: Nouveau statut à appliquer.

    Returns:
        L'action mise à jour.

    Raises:
        HTTPException: 404 si l'action est introuvable ou n'appartient pas à l'utilisateur.
    """
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


@router.delete('/{action_id}', status_code=204)
def delete_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprime une action appartenant à l'utilisateur courant.

    Args:
        action_id: Identifiant de l'action à supprimer.

    Raises:
        HTTPException: 404 si l'action est introuvable ou n'appartient pas à l'utilisateur.
    """
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
    db.delete(action)
    db.commit()


@router.patch('/{action_id}/due-date', response_model=ActionResponse)
def update_action_due_date(
    action_id: int,
    payload: ActionDueDateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Met à jour la date d'échéance d'une action appartenant à l'utilisateur courant.

    Args:
        action_id: Identifiant de l'action à mettre à jour.
        payload: Nouvelle date d'échéance à appliquer.

    Returns:
        L'action mise à jour.

    Raises:
        HTTPException: 404 si l'action est introuvable ou n'appartient pas à l'utilisateur.
    """
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
    action.due_date = payload.due_date
    db.commit()
    db.refresh(action)
    return ActionResponse(
        id=action.id,
        description=action.description,
        status=action.status,
        due_date=action.due_date,
        speaker_id=action.speaker_id,
    )