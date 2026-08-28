from app.database import SessionLocal
from app.exceptions import LLMError
from app.models.recording import Recording
from app.services.action_extraction_service import run_action_extraction
from app.services.summary_generation_service import run_summary_generation


def run_post_meeting_processing(recording_id: int) -> None:
    """
    Point d'entrée unique du traitement automatique post-réunion : résumé
    et thème/décisions/actions, chacun indépendant - l'échec de l'un ne
    bloque pas l'autre. Ouvre sa propre session DB (utilisé depuis
    BackgroundTasks, où la session de la requête d'origine est déjà
    fermée) et absorbe LLMError, déjà logguée par LLMService.
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

        try:
            run_action_extraction(db, recording)
        except LLMError:
            pass
    finally:
        db.close()
