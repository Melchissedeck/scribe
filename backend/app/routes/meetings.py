from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.schemas.action import ActionResponse
from app.schemas.recording import (
    DiarizedTranscriptResponse,
    MeetingDetailResponse,
    MeetingListItem,
    SegmentOut,
    SpeakerOut,
    SpeakingTimeEntry,
    SpeakingTimeResponse,
)

router = APIRouter(prefix='/meetings', tags=['meetings'])

EXCERPT_LENGTH = 150


def _build_excerpt(summary: str | None) -> str | None:
    if not summary:
        return None
    if len(summary) <= EXCERPT_LENGTH:
        return summary
    return summary[:EXCERPT_LENGTH].rstrip() + '...'


@router.get('', response_model=list[MeetingListItem])
def list_meetings(
    theme: str | None = Query(default=None, description="Filtre sur le thème (recherche partielle, insensible à la casse)"),
    date_from: date | None = Query(default=None, description="Réunions à partir de cette date (incluse)"),
    date_to: date | None = Query(default=None, description="Réunions jusqu'à cette date (incluse)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Recording).filter(Recording.user_id == current_user.id)

    if theme:
        query = query.filter(Recording.theme.ilike(f'%{theme}%'))

    if date_from:
        query = query.filter(Recording.started_at >= datetime.combine(date_from, time.min))

    if date_to:
        query = query.filter(Recording.started_at <= datetime.combine(date_to, time.max))

    recordings = query.order_by(Recording.started_at.desc()).all()

    return [
        MeetingListItem(
            id=recording.id,
            theme=recording.theme,
            date=recording.started_at,
            status=recording.status,
            summary_excerpt=_build_excerpt(recording.summary),
        )
        for recording in recordings
    ]


@router.get('/{meeting_id}/speaking-time', response_model=SpeakingTimeResponse)
def get_speaking_time(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = db.query(Recording).filter(
        Recording.id == meeting_id, Recording.user_id == current_user.id
    ).first()
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    segments = db.query(TranscriptSegment).filter(
        TranscriptSegment.recording_id == meeting_id
    ).all()

    durations: dict[str, float] = {}
    for seg in segments:
        duration = max(0.0, seg.end - seg.start)
        durations[seg.speaker] = durations.get(seg.speaker, 0.0) + duration

    total = sum(durations.values())

    if total == 0:
        return SpeakingTimeResponse(meeting_id=meeting_id, entries=[])

    entries = [
        SpeakingTimeEntry(
            speaker=speaker,
            seconds=round(seconds, 1),
            percentage=round(seconds / total * 100, 1),
        )
        for speaker, seconds in sorted(durations.items(), key=lambda x: -x[1])
    ]

    return SpeakingTimeResponse(meeting_id=meeting_id, entries=entries)


@router.get('/{meeting_id}/diarized-transcript', response_model=DiarizedTranscriptResponse)
def get_diarized_transcript(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(Recording.id == meeting_id, Recording.user_id == current_user.id)
        .first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.recording_id == meeting_id)
        .order_by(TranscriptSegment.start)
        .all()
    )

    if not segments:
        raise HTTPException(
            status_code=404,
            detail='Aucune diarisation disponible pour cette réunion.',
        )

    return DiarizedTranscriptResponse(
        meeting_id=meeting_id,
        segments=[
            SegmentOut(speaker_name=seg.speaker, text=seg.text)
            for seg in segments
        ],
    )


@router.get('/{meeting_id}/details', response_model=MeetingDetailResponse)
def get_meeting_details(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = (
        db.query(Recording)
        .filter(Recording.id == meeting_id, Recording.user_id == current_user.id)
        .options(
            selectinload(Recording.speakers),
            selectinload(Recording.segments),
            selectinload(Recording.actions),
        )
        .first()
    )
    if not recording:
        raise HTTPException(status_code=404, detail='Réunion introuvable.')

    segments = sorted(recording.segments, key=lambda seg: seg.start)

    return MeetingDetailResponse(
        id=recording.id,
        theme=recording.theme,
        status=recording.status,
        started_at=recording.started_at,
        stopped_at=recording.stopped_at,
        summary=recording.summary,
        speakers=[SpeakerOut.model_validate(speaker) for speaker in recording.speakers],
        segments=[SegmentOut(speaker_name=seg.speaker, text=seg.text) for seg in segments],
        actions=[ActionResponse.model_validate(action) for action in recording.actions],
    )