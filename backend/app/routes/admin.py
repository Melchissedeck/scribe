from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.log import Log
from app.schemas.log import LogRead

router = APIRouter(prefix='/admin', tags=['admin'])


def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    """Protège les routes internes par une clé partagée (ADMIN_API_KEY).

    Pas de système de rôles complet ici, hors périmètre de ce ticket : une
    simple clé côté serveur suffit pour un usage interne à l'équipe.

    Args:
        x_admin_key: Valeur de l'en-tête X-Admin-Key fourni par l'appelant.

    Raises:
        HTTPException: Code 403 si la clé est absente ou incorrecte, ou si
            ADMIN_API_KEY n'est pas configurée côté serveur (échec fermé).
    """
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Accès réservé.')


@router.get('/logs', response_model=list[LogRead], dependencies=[Depends(require_admin_key)])
def list_logs(db: Session = Depends(get_db)) -> list[Log]:
    """Liste le journal d'audit (connexions, suppressions de données).

    Args:
        db: Session de base de données injectée par FastAPI.

    Returns:
        Toutes les entrées du journal, les plus récentes en premier.

    Raises:
        HTTPException: Code 403 si l'en-tête X-Admin-Key est absent ou
            incorrect.
    """
    return db.query(Log).order_by(Log.date.desc()).all()
