from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix='/users', tags=['users'])


@router.patch('/me', response_model=UserRead)
def update_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Met à jour le nom et/ou l'email de l'utilisateur connecté.

    Seuls les champs présents dans le payload sont modifiés ; un champ
    absent (None) laisse la valeur existante inchangée.

    Args:
        payload: Nouveau nom et/ou nouvel email, tous deux optionnels.
        db: Session de base de données injectée par FastAPI.
        current_user: Utilisateur authentifié, résolu depuis le token JWT.

    Returns:
        Le profil utilisateur mis à jour.

    Raises:
        HTTPException: Code 400 si le nouvel email est déjà utilisé par
            un autre compte.
    """
    # Verifie que le nouvel email n'est pas deja utilise par un autre compte
    if payload.email is not None and payload.email != current_user.email:
        existing_user = db.query(User).filter(User.email == payload.email).first()
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Cet email est deja utilise',
            )
        current_user.email = payload.email

    if payload.name is not None:
        current_user.name = payload.name

    db.commit()
    db.refresh(current_user)

    return current_user
