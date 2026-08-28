from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.user import User
from app.schemas.dashboard import DashboardTrendsResponse, WeeklyTrend

router = APIRouter(prefix='/dashboard', tags=['dashboard'])

DEFAULT_WEEKS = 8


@router.get('/trends', response_model=DashboardTrendsResponse)
def get_dashboard_trends(
    weeks: int = Query(default=DEFAULT_WEEKS, ge=1, le=52, description='Nombre de semaines à agréger'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recordings = (
        db.query(Recording)
        .filter(Recording.user_id == current_user.id)
        .options(selectinload(Recording.actions))
        .all()
    )

    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    week_starts = [current_week_start - timedelta(weeks=offset) for offset in range(weeks - 1, -1, -1)]

    trends = []
    for week_start in week_starts:
        week_end = week_start + timedelta(days=7)
        week_recordings = [
            recording for recording in recordings
            if recording.started_at and week_start <= recording.started_at.date() < week_end
        ]
        trends.append(WeeklyTrend(
            week_start=week_start,
            meetings_count=len(week_recordings),
            actions_count=sum(len(recording.actions) for recording in week_recordings),
        ))

    return DashboardTrendsResponse(weeks=trends)
