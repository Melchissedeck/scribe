from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.user import User
from app.schemas.recording import RecordingCreate, RecordingRead
from vexa_agent import VexaAgent

router = APIRouter(prefix='/recording', tags=['recording'])


@router.post('/start', response_model=RecordingRead)
def start_recording(
    payload: RecordingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = VexaAgent()
    try:
        agent.send_bot(payload.platform, payload.native_meeting_id, payload.bot_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Vexa error: {exc}')

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
        raise HTTPException(status_code=400, detail='La session n\'est pas active')

    agent = VexaAgent()
    agent.stop_bot(recording.platform, recording.native_meeting_id)

    try:
        recording.transcript = agent.get_transcript(recording.platform, recording.native_meeting_id)
    except Exception:
        pass

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
    try:
        recording.transcript = agent.get_transcript(recording.platform, recording.native_meeting_id)
        db.commit()
        db.refresh(recording)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Vexa error: {exc}')

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
