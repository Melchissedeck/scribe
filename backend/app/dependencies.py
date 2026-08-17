from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import InvalidCredentialsError
from app.models.user import User
from app.services.jwt import decode_access_token

# Indique a FastAPI ou recuperer le token dans les requetes entrantes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # Verifie le token et retourne l'utilisateur associe.
    # decode_access_token leve TokenExpiredError ou InvalidCredentialsError si le token
    # n'est pas exploitable ; ces exceptions sont converties en reponse HTTP par les
    # handlers globaux enregistres dans main.py.
    user_id = decode_access_token(token)

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise InvalidCredentialsError()

    return user
