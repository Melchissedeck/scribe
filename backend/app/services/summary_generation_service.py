import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.exceptions import LLMError
from app.models.recording import Recording
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def run_summary_generation(db: Session, recording: Recording) -> None:
    """
    Génère le résumé d'une réunion et fait avancer recording.summary_status
    (pending -> generating -> done/failed) au fil de l'appel, pour que le
    dashboard puisse afficher un statut fiable même si l'appelant est un
    endpoint synchrone ou une tâche de fond.

    Ne fait rien si la transcription n'est pas encore disponible (statut
    laissé à "pending"). Propage LLMError si l'appel API échoue, après
    avoir enregistré le statut "failed".
    """
    if not recording.transcript or not str(recording.transcript).strip():
        return

    recording.summary_status = 'generating'
    db.commit()

    llm_service = LLMService()
    try:
        recording.summary = llm_service.generate_summary(recording.transcript)
        recording.summary_status = 'done'
        db.commit()
    except LLMError:
        recording.summary_status = 'failed'
        db.commit()
        raise


def generate_summary_in_background(recording_id: int) -> None:
    """
    Variante pour BackgroundTasks : ouvre sa propre session DB (celle de
    la requête d'origine est déjà fermée quand la tâche de fond s'exécute)
    et absorbe LLMError - déjà logguée par LLMService, et il n'y a personne
    côté HTTP pour la recevoir à ce stade.
    """
    db = SessionLocal()
    try:
        recording = db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            return
        try:
            run_summary_generation(db, recording)
        except LLMError:
            pass
    finally:
        db.close()
