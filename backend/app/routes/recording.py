import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import VexaConnectionError
from app.models.recording import Recording
from app.models.speaker import Speaker
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.recording import RecordingCreate, RecordingRead
from vexa_agent import VexaAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/recording', tags=['recording'])


def _deduplicate_segments(raw_segments: list[dict]) -> list[dict]:
    """Supprime les segments consécutifs identiques (même speaker, même texte).

    Vexa retourne un transcript cumulatif : chaque appel inclut tous les segments
    depuis le début, ce qui produit des doublons quand on poll plusieurs fois.
    """
    clean: list[dict] = []
    for seg in raw_segments:
        text = seg.get('text', '').strip()
        if not text:
            continue
        last = clean[-1] if clean else None
        if last and last.get('speaker') == seg.get('speaker') and last.get('text', '').strip() == text:
            continue
        clean.append(seg)
    return clean


def _save_diarized_segments(db: Session, recording_id: int, raw_segments: list[dict]) -> None:
    # Vide les segments existants avant de réinsérer : Vexa est cumulatif,
    # chaque appel contient tous les segments depuis le début de la réunion.
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
    current_user: User = Depends(get_current_user),
):
    agent = VexaAgent()
    agent.send_bot(payload.platform, payload.native_meeting_id, payload.bot_name)

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


@router.post('/{recording_id}/stop', response_model=RecordingRead)
def stop_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    try:
        raw_segments = agent.get_diarized_segments(recording.platform, recording.native_meeting_id)
        recording.transcript = agent.get_transcript(recording.platform, recording.native_meeting_id)
        _save_diarized_segments(db, recording.id, raw_segments)
    except VexaConnectionError:
        logger.warning('Transcription Vexa indisponible pour la session %s', recording_id)
    except Exception as exc:
        logger.error('Erreur inattendue lors de la récupération de la transcription: %s', exc)

    recording.status = 'stopped'
    recording.stopped_at = datetime.utcnow()
    db.commit()
    db.refresh(recording)
    return recording


@router.get('/{recording_id}/transcript', response_model=RecordingRead)
def refresh_transcript(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = db.query(Recording).filter(
        Recording.id == recording_id,
        Recording.user_id == current_user.id,
    ).first()
    if not recording:
        raise HTTPException(status_code=404, detail='Session introuvable')

    agent = VexaAgent()
    raw_segments = agent.get_diarized_segments(recording.platform, recording.native_meeting_id)
    recording.transcript = agent.get_transcript(recording.platform, recording.native_meeting_id)
    _save_diarized_segments(db, recording.id, raw_segments)
    db.commit()
    db.refresh(recording)
    return recording


@router.get('/', response_model=list[RecordingRead])
def list_recordings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Recording)
        .filter(Recording.user_id == current_user.id)
        .order_by(Recording.started_at.desc())
        .all()
    )
