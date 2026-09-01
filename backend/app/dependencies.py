from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import InvalidCredentialsError
from app.models.user import User
from app.services.jwt import decode_access_token

# Indique a FastAPI ou recuperer le token dans les requetes entrantes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Résout l'utilisateur authentifié à partir du token JWT de la requête.

    Dépendance FastAPI réutilisable pour protéger une route : l'ajouter en
    paramètre suffit à exiger un token valide et à recevoir l'utilisateur
    correspondant.

    Args:
        token: Token JWT extrait de l'en-tête Authorization par
            oauth2_scheme.
        db: Session de base de données injectée par FastAPI.

    Returns:
        L'utilisateur authentifié.

    Raises:
        TokenExpiredError: Si le token est valide mais a expiré.
        InvalidCredentialsError: Si le token est invalide, mal formé, ou
            si l'utilisateur qu'il désigne n'existe plus.
    """
    # Verifie le token et retourne l'utilisateur associe.
    # decode_access_token leve TokenExpiredError ou InvalidCredentialsError si le token
    # n'est pas exploitable ; ces exceptions sont converties en reponse HTTP par les
    # handlers globaux enregistres dans main.py.
    user_id = decode_access_token(token)

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise InvalidCredentialsError()

    return user


def require_consent(current_user: User = Depends(get_current_user)) -> User:
    """Exige que l'utilisateur ait donné son consentement RGPD au moins une
    fois, vérifié côté serveur (pas seulement l'écran de consentement
    côté client, contournable via sessionStorage ou un appel API direct).

    A ajouter en dépendance sur les routes qui démarrent une captation
    (visio ou dictaphone).

    Args:
        current_user: Utilisateur authentifié, résolu depuis le token JWT.

    Returns:
        L'utilisateur authentifié, si le consentement a bien été donné.

    Raises:
        HTTPException: Code 403 si aucun consentement n'a jamais été
            enregistré pour ce compte.
    """
    if current_user.consent_given_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Consentement RGPD requis avant de démarrer une captation.',
        )
    return current_user
