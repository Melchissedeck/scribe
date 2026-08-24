from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import InvalidCredentialsError
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.jwt import create_access_token
from app.services.password import hash_password, verify_password

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> User:
    """Crée un nouveau compte utilisateur.

    Args:
        user_data: Nom, email et mot de passe en clair du nouveau compte.
        db: Session de base de données injectée par FastAPI.

    Returns:
        L'utilisateur créé, sans le mot de passe.

    Raises:
        HTTPException: Code 400 si l'email est déjà utilisé par un autre
            compte.
    """
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
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Authentifie un utilisateur et retourne un token d'accès JWT.

    Args:
        credentials: Email et mot de passe en clair à vérifier.
        db: Session de base de données injectée par FastAPI.

    Returns:
        Un token d'accès JWT à utiliser dans l'en-tête Authorization des
        requêtes suivantes.

    Raises:
        InvalidCredentialsError: Si l'email est inconnu ou si le mot de
            passe ne correspond pas (convertie en réponse HTTP 401 par
            le handler global enregistré dans main.py).
    """
    # Verifie les identifiants et retourne un token d'acces en cas de succes
    user = db.query(User).filter(User.email == credentials.email).first()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise InvalidCredentialsError('Email ou mot de passe incorrect')

    access_token = create_access_token(user.id)
    return Token(access_token=access_token)
