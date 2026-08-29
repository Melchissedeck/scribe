import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.database import get_db
from app.dependencies import get_current_user
from app.models.action import Action
from app.models.recording import Recording
from app.models.speaker import Speaker
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services.audit_log_service import record_log

router = APIRouter(prefix='/users', tags=['users'])

# Meme convention que app/routes/dictaphone.py : fichiers audio stockes dans
# uploads/<recording_id>/ relativement au repertoire de travail du backend.
UPLOAD_DIR = Path('uploads')


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


@router.delete('/me', status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Supprime définitivement le compte connecté et toutes ses données.

    Supprime en cascade les actions, segments de transcription et locuteurs
    de chaque réunion de l'utilisateur, puis les réunions elles-mêmes, les
    fichiers audio associés stockés sur le serveur, et enfin le compte,
    conformément au droit à l'effacement RGPD. Opération irréversible.

    Args:
        db: Session de base de données injectée par FastAPI.
        current_user: Utilisateur authentifié, résolu depuis le token JWT.

    Returns:
        Aucun contenu (204) en cas de succès.
    """
    recording_ids = [
        row[0]
        for row in db.query(Recording.id).filter(Recording.user_id == current_user.id).all()
    ]

    if recording_ids:
        db.query(Action).filter(Action.recording_id.in_(recording_ids)).delete(synchronize_session=False)
        db.query(TranscriptSegment).filter(
            TranscriptSegment.recording_id.in_(recording_ids)
        ).delete(synchronize_session=False)
        db.query(Speaker).filter(Speaker.recording_id.in_(recording_ids)).delete(synchronize_session=False)
        db.query(Recording).filter(Recording.id.in_(recording_ids)).delete(synchronize_session=False)

    record_log(db, action='account_deletion', user_id=current_user.id, detail=current_user.email)

    db.delete(current_user)
    db.commit()

    for recording_id in recording_ids:
        recording_dir = UPLOAD_DIR / str(recording_id)
        try:
            shutil.rmtree(recording_dir)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.error('Échec suppression fichiers réunion %s : %s', recording_id, exc)
