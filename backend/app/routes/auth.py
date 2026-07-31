from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.services.jwt import create_access_token
from app.services.password import hash_password, verify_password

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> User:
    # Verifie que l'email n'est pas deja utilise avant de creer le compte
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cet email est deja utilise',
        )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post('/login', response_model=Token)
def login(email: str, password: str, db: Session = Depends(get_db)) -> Token:
    # Verifie les identifiants et retourne un token d'acces en cas de succes
    user = db.query(User).filter(User.email == email).first()

    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Email ou mot de passe incorrect',
        )

    access_token = create_access_token(user.id)
    return Token(access_token=access_token)
