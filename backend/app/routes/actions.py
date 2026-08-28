import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.action import Action
from app.models.recording import Recording
from app.models.speaker import Speaker
from app.models.user import User
from app.schemas.action import ActionResponse, ExtractActionsResponse
from app.services.llm_service import LLMService

router = APIRouter(prefix='/meetings', tags=['actions'])


@router.post('/{meeting_id}/extract-actions', response_model=ExtractActionsResponse)
def extract_actions(
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
    structured = llm_service.generate_structured_summary(recording.transcript)

    if structured is None:
        # Ne peut se produire ici : generate_structured_summary ne renvoie
        # None que pour une transcription vide, déjà exclue par le contrôle
        # plus haut. Un échec réel de l'appel API lève LLMError, gérée
        # globalement (voir app/main.py). Ce garde-fou reste pour le typage.
        raise HTTPException(
            status_code=502,
            detail="Le service de génération du compte-rendu structuré est momentanément indisponible.",
        )

    if not recording.theme and structured.themes:
        recording.theme = structured.themes[0].strip() or None

    if structured.decisions:
        recording.decisions = structured.decisions

    speakers = db.query(Speaker).filter(Speaker.recording_id == recording.id).all()

    created_actions = []
    for item in structured.actions:
        speaker = _match_speaker(item.responsable, speakers)
        due_date = _parse_due_date(item.echeance)

        action = Action(
            recording_id=recording.id,
            speaker_id=speaker.id if speaker else None,
            description=item.description,
            status='todo',
            due_date=due_date,
        )
        db.add(action)
        created_actions.append(action)

    db.commit()

    for action in created_actions:
        db.refresh(action)

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


def _match_speaker(responsable: str | None, speakers: list[Speaker]) -> Speaker | None:
    """Associe un nom de responsable à un Speaker existant de la réunion,
    par correspondance insensible à la casse sur le nom réel ou provisoire."""
    if not responsable:
        return None

    normalized = responsable.strip().lower()
    for speaker in speakers:
        if speaker.real_name and speaker.real_name.strip().lower() == normalized:
            return speaker
        if speaker.provisional_name and speaker.provisional_name.strip().lower() == normalized:
            return speaker

    return None


DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _parse_due_date(echeance: str | None) -> date | None:
    """Tente de parser une échéance au format ISO (AAAA-MM-JJ).
    Retourne None si le texte n'est pas une date exploitable (ex: 'vendredi'),
    plutôt que de faire planter l'insertion en base."""
    if not echeance:
        return None

    text = echeance.strip()
    if DATE_PATTERN.match(text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    return None