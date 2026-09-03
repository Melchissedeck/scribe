import re
from datetime import date

from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.recording import Recording
from app.models.speaker import Speaker
from app.services.llm_service import LLMService

DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def run_action_extraction(db: Session, recording: Recording) -> list[Action]:
    """
    Extrait le thème, les décisions et les actions d'une réunion à partir
    de sa transcription, et les persiste (le thème et les décisions
    seulement s'ils ne sont pas déjà renseignés).

    Ne fait rien et retourne une liste vide si la transcription n'est pas
    encore disponible. Propage LLMError si l'appel API échoue.
    """
    if not recording.transcript or not str(recording.transcript).strip():
        return []

    existing = db.query(Action).filter(Action.recording_id == recording.id).first()
    if existing:
        return db.query(Action).filter(Action.recording_id == recording.id).all()

    llm_service = LLMService()
    structured = llm_service.generate_structured_summary(recording.transcript)
    if structured is None:
        return []

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

    return created_actions


def _match_speaker(responsable: str | None, speakers: list[Speaker]) -> Speaker | None:
    """Associe un nom de responsable à un Speaker existant de la réunion,
    par correspondance insensible à la casse sur le nom provisoire."""
    if not responsable:
        return None

    normalized = responsable.strip().lower()
    for speaker in speakers:
        if speaker.provisional_name and speaker.provisional_name.strip().lower() == normalized:
            return speaker

    return None


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
