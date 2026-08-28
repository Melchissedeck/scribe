from sqlalchemy.orm import Session

from app.exceptions import LLMError
from app.models.recording import Recording
from app.services.llm_service import LLMService


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


