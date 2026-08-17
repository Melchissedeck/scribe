from datetime import datetime, timedelta

from jose import ExpiredSignatureError, JWTError, jwt

from app.config import settings
from app.exceptions import InvalidCredentialsError, TokenExpiredError


def create_access_token(user_id: int) -> str:
    # Genere un token JWT contenant l'identifiant de l'utilisateur
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {'sub': str(user_id), 'exp': expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    # Decode un token JWT et retourne l'identifiant utilisateur qu'il contient.
    # Leve TokenExpiredError ou InvalidCredentialsError si le token n'est pas exploitable.
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
