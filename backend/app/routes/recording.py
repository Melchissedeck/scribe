import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user, require_consent
from app.exceptions import VexaConnectionError
from app.models.recording import Recording
from app.models.speaker import Speaker
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.recording import RecordingCreate, RecordingRead
from app.services.post_meeting_processing_service import run_post_meeting_processing
from vexa_agent import VexaAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/recording', tags=['recording'])


def _deduplicate_segments(raw_segments: list[dict]) -> list[dict]:
    """Supprime les segments redondants retournés par Vexa.

    Vexa retourne un transcript cumulatif et peut renvoyer le même contenu
    d'abord sous forme d'un grand bloc, puis redécoupé en petits segments.
    On filtre les doublons exacts consécutifs et les segments dont le texte
    est un sous-ensemble d'un segment existant du même locuteur.

    Args:
        raw_segments: Liste brute des segments retournés par l'API Vexa.

    Returns:
        Liste dédoublonnée conservant l'ordre chronologique.
    """
    clean: list[dict] = []
    for seg in raw_segments:
        text = seg.get('text', '').strip()
        if not text:
            continue
        speaker = seg.get('speaker')
        # Doublon consécutif exact
        last = clean[-1] if clean else None
        if last and last.get('speaker') == speaker and last.get('text', '').strip() == text:
            continue
        # Texte déjà contenu dans un segment existant du même locuteur
        if any(
            s.get('speaker') == speaker and text in s.get('text', '').strip()
            for s in clean
        ):
            continue
        clean.append(seg)
    return clean


def _save_diarized_segments(db: Session, recording_id: int, raw_segments: list[dict]) -> None:
    """Persiste les segments diarisés en base après dédoublonnage.

    Vide les segments existants avant réinsertion : Vexa étant cumulatif,
    chaque appel contient tous les segments depuis le début de la réunion.
    Crée les entrées Speaker manquantes à la volée.

    Args:
        db: Session de base de données.
        recording_id: Identifiant de la réunion concernée.
        raw_segments: Segments bruts retournés par l'API Vexa.
    """
    db.query(TranscriptSegment).filter(TranscriptSegment.recording_id == recording_id).delete()
    db.flush()

    segments = _deduplicate_segments(raw_segments)
    speaker_map: dict[str, Speaker] = {}

    for seg in segments:
        vexa_label = seg.get('speaker', 'Inconnu')
        if vexa_label not in speaker_map:
            existing = (
                db.query(Speaker)
                .filter(Speaker.recording_id == recording_id, Speaker.provisional_name == vexa_label)
                .first()
            )
            if existing:
                speaker_map[vexa_label] = existing
            else:
                speaker = Speaker(recording_id=recording_id, provisional_name=vexa_label)
                db.add(speaker)
                db.flush()
                speaker_map[vexa_label] = speaker

    for seg in segments:
        vexa_label = seg.get('speaker', 'Inconnu')
        db.add(TranscriptSegment(
            recording_id=recording_id,
            speaker=vexa_label,
            text=seg.get('text', '').strip(),
            start=seg.get('start', 0),
            end=seg.get('end', 0),
        ))

    db.commit()


@router.post('/start', response_model=RecordingRead)
def start_recording(
    payload: RecordingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_consent),
):
    """Démarre une session d'enregistrement visio via le bot Vexa.

    Args:
        payload: Plateforme, identifiant natif, nom du bot et URL optionnelle.
        db: Session de base de données injectée par FastAPI.
        current_user: Utilisateur authentifié ayant donné son consentement RGPD.

    Returns:
        L'enregistrement créé avec le statut 'active'.

    Raises:
        HTTPException: 422 si le lien de réunion est invalide.
        HTTPException: 503 si l'API Vexa est inaccessible.
    """
    agent = VexaAgent()
    agent.send_bot(payload.platform, payload.native_meeting_id, payload.bot_name, payload.meeting_url)

    recording = Recording(
        user_id=current_user.id,
        platform=payload.platform,
        native_meeting_id=payload.native_meeting_id,
        bot_name=payload.bot_name,
        status='active',
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    return recording


def _fetch_final_transcript(recording_id: int, platform: str, native_meeting_id: str) -> None:
    """Récupère la transcription diarisée finale depuis Vexa en tâche de fond.

    Appelée via BackgroundTasks après l'arrêt du bot. Ouvre sa propre session
    DB car la session de la requête d'origine est déjà fermée. Délègue ensuite
    le résumé et l'extraction d'actions à run_post_meeting_processing, commune
    au pipeline dictaphone.

    Args:
        recording_id: Identifiant de la réunion en base.
        platform: Plateforme de visioconférence (ex. 'google_meet').
        native_meeting_id: Identifiant natif de la réunion sur la plateforme.
    """
    db = SessionLocal()
    got_transcript = False
    try:
        agent = VexaAgent()
        raw_segments = agent.get_diarized_segments(platform, native_meeting_id)
        transcript = agent.get_transcript(platform, native_meeting_id)
        recording = db.query(Recording).filter(Recording.id == recording_id).first()
        if recording:
            recording.transcript = transcript
            _save_diarized_segments(db, recording_id, raw_segments)
            db.commit()
            got_transcript = True
    except VexaConnectionError:
        logger.warning('Transcription Vexa indisponible pour la session %s', recording_id)
    except Exception as exc:
        logger.error('Erreur inattendue lors de la récupération finale de la transcription: %s', exc)
    finally:
        db.close()

    if got_transcript:
        run_post_meeting_processing(recording_id)


@router.post('/{recording_id}/stop', response_model=RecordingRead)
def stop_recording(
    recording_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Arrête le bot Vexa et déclenche la récupération de la transcription finale.

    La transcription est récupérée en tâche de fond pour ne pas bloquer la
    réponse HTTP. Le résumé et les actions sont générés à la suite.

    Args:
        recording_id: Identifiant de la session à arrêter.
        background_tasks: Gestionnaire de tâches de fond FastAPI.
        db: Session de base de données injectée par FastAPI.
        current_user: Utilisateur authentifié, résolu depuis le token JWT.

    Returns:
        L'enregistrement mis à jour avec le statut 'stopped'.

    Raises:
        HTTPException: 404 si la session est introuvable.
        HTTPException: 400 si la session n'est pas active.
    """
    recording = db.query(Recording).filter(
        Recording.id == recording_id,
        Recording.user_id == current_user.id,
    ).first()
    if not recording:
        raise HTTPException(status_code=404, detail='Session introuvable')
    if recording.status != 'active':
        raise HTTPException(status_code=400, detail="La session n'est pas active")

    agent = VexaAgent()
    agent.stop_bot(recording.platform, recording.native_meeting_id)

    recording.status = 'stopped'
    recording.stopped_at = datetime.utcnow()
    db.commit()
    db.refresh(recording)

    background_tasks.add_task(
        _fetch_final_transcript,
        recording.id,
        recording.platform,
        recording.native_meeting_id,
    )

    return recording


@router.get('/{recording_id}/transcript', response_model=RecordingRead)
def refresh_transcript(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rafraîchit la transcription d'une session en cours depuis Vexa.

    Args:
        recording_id: Identifiant de la session.
        db: Session de base de données injectée par FastAPI.
        current_user: Utilisateur authentifié, résolu depuis le token JWT.

    Returns:
        L'enregistrement avec la transcription mise à jour.

    Raises:
        HTTPException: 404 si la session est introuvable.
        HTTPException: 503 si l'API Vexa est temporairement indisponible.
    """
    recording = db.query(Recording).filter(
        Recording.id == recording_id,
        Recording.user_id == current_user.id,
    ).first()
    if not recording:
        raise HTTPException(status_code=404, detail='Session introuvable')

    agent = VexaAgent()
    try:
        raw_segments = agent.get_diarized_segments(recording.platform, recording.native_meeting_id)
        recording.transcript = agent.get_transcript(recording.platform, recording.native_meeting_id)
    except VexaConnectionError as exc:
        raise HTTPException(status_code=503, detail='La transcription est temporairement indisponible. Veuillez réessayer dans quelques instants.') from exc
    _save_diarized_segments(db, recording.id, raw_segments)
    db.commit()
    db.refresh(recording)
    return recording


@router.get('/', response_model=list[RecordingRead])
def list_recordings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste toutes les sessions d'enregistrement de l'utilisateur connecté.

    Args:
        db: Session de base de données injectée par FastAPI.
        current_user: Utilisateur authentifié, résolu depuis le token JWT.

    Returns:
        Liste des enregistrements triés par date décroissante.
    """
    return (
        db.query(Recording)
        .filter(Recording.user_id == current_user.id)
        .order_by(Recording.started_at.desc())
        .all()
    )
