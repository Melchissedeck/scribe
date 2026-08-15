from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.user import User
from app.schemas.recording import MeetingListItem

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recordings = (
        db.query(Recording)
        .filter(Recording.user_id == current_user.id)
        .order_by(Recording.started_at.desc())
        .all()
    )

    return [
        MeetingListItem(
            id=recording.id,
            theme=recording.theme,
            date=recording.started_at,
            summary_excerpt=_build_excerpt(recording.summary),
        )
        for recording in recordings
    ]