import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.log import Log

logger = logging.getLogger(__name__)

# 12 mois glissants, cf. docs/audit-log.md (principe de minimisation RGPD).
RETENTION_DAYS = 365
# Une purge par jour suffit largement pour une fenêtre de rétention en
# mois ; pas besoin d'une fréquence plus fine.
PURGE_INTERVAL_SECONDS = 24 * 60 * 60


def purge_expired_logs(db: Session, retention_days: int = RETENTION_DAYS) -> int:
    """Supprime les entrées du journal d'audit plus anciennes que la durée
    de rétention.

    Args:
        db: Session de base de données.
        retention_days: Durée de rétention en jours (12 mois par défaut).

    Returns:
        Le nombre d'entrées supprimées.
    """
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    deleted = db.query(Log).filter(Log.date < cutoff).delete(synchronize_session=False)
    db.commit()
    return deleted


async def run_log_retention_loop() -> None:
    """Purge les entrées expirées du journal d'audit une fois par jour,
    tant que l'application tourne.

    Démarrée en tâche de fond depuis le lifespan de l'application
    (voir app/main.py) ; annulée proprement à l'arrêt.
    """
    while True:
        db = SessionLocal()
        try:
            deleted = purge_expired_logs(db)
            if deleted:
                logger.info(
                    "Purge automatique du journal d'audit : %d entrée(s) supprimée(s).",
                    deleted,
                )
        except Exception as exc:
            logger.error("Échec de la purge automatique du journal d'audit : %s", exc)
        finally:
            db.close()

        await asyncio.sleep(PURGE_INTERVAL_SECONDS)
