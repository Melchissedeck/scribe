from sqlalchemy.orm import Session

from app.models.log import Log


def record_log(db: Session, action: str, user_id: int | None, detail: str | None = None) -> None:
    """Enregistre une entrée d'audit (connexion, suppression de donnée...).

    N'effectue pas de commit : l'appelant décide dans quelle transaction
    l'entrée s'inscrit (par exemple avec la suppression qu'elle documente).

    Args:
        db: Session de base de données.
        action: Type d'événement journalisé (ex. 'login', 'account_deletion').
        user_id: Identifiant de l'utilisateur concerné, si connu.
        detail: Contexte libre optionnel (ex. email concerné).
    """
    db.add(Log(action=action, user_id=user_id, detail=detail))
