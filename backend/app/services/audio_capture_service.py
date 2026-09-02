import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.recording import Recording
from app.services.post_meeting_processing_service import run_post_meeting_processing

logger = logging.getLogger(__name__)


def run_capture_background_job(recording_id: int, process: Callable[[Session, Recording], bool]) -> None:
    """Exécute une tâche de fond de capture audio dans sa propre session DB.

    Point d'entrée commun aux deux sources de capture (visio via Vexa,
    dictaphone via fichier téléversé) : ouvre une session dédiée (celle de
    la requête HTTP d'origine est déjà fermée au moment où BackgroundTasks
    s'exécute), charge l'enregistrement, puis délègue le travail propre à
    la source via `process`. Le traitement post-réunion partagé (résumé,
    extraction d'actions) n'est déclenché que si `process` a réussi.

    Args:
        recording_id: Identifiant de la réunion à traiter.
        process: Fonction spécifique à la source de capture. Reçoit la
            session DB déjà ouverte et l'enregistrement déjà chargé,
            effectue le travail (récupération de transcription,
            diarisation...) et retourne True en cas de succès, False sinon.
    """
    db = SessionLocal()
    success = False
    try:
        recording = db.query(Recording).filter(Recording.id == recording_id).first()
        if recording:
            success = process(db, recording)
        else:
            logger.warning('Réunion %s introuvable pour la capture audio en tâche de fond', recording_id)
    finally:
        db.close()

    if success:
        run_post_meeting_processing(recording_id)
