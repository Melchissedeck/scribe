from datetime import datetime, timedelta

from jose import JWTError, jwt

from app.config import settings


def create_access_token(user_id: int) -> str:
    # Genere un token JWT contenant l'identifiant de l'utilisateur
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {'sub': str(user_id), 'exp': expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    # Decode un token JWT et retourne l'identifiant utilisateur qu'il contient
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get('sub')
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None
