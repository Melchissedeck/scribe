from datetime import datetime, timedelta

from jose import ExpiredSignatureError, JWTError, jwt

from app.config import settings
from app.exceptions import InvalidCredentialsError, TokenExpiredError


def create_access_token(user_id: int) -> str:
    """Génère un token JWT signé contenant l'identifiant de l'utilisateur.

    Args:
        user_id: Identifiant de l'utilisateur à encoder dans le token.

    Returns:
        Le token JWT encodé, avec une expiration calculée à partir de
        `settings.jwt_expiration_minutes`.
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {'sub': str(user_id), 'exp': expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    """Décode un token JWT et retourne l'identifiant utilisateur qu'il contient.

    Args:
        token: Token JWT à décoder.

    Returns:
        L'identifiant de l'utilisateur encodé dans le token.

    Raises:
        TokenExpiredError: Si le token a expiré.
        InvalidCredentialsError: Si le token est invalide ou ne contient pas d'identifiant.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError:
        raise TokenExpiredError() from None
    except JWTError:
        raise InvalidCredentialsError() from None

    user_id = payload.get('sub')
    if user_id is None:
        raise InvalidCredentialsError()

    return int(user_id)
