from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.jwt import decode_access_token

# Indique a FastAPI ou recuperer le token dans les requetes entrantes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # Verifie le token et retourne l'utilisateur associe, ou rejette la requete
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Impossible de vérifier les identifiants',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_error

    return user
