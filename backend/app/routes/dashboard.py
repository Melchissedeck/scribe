from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.recording import Recording
from app.models.user import User
from app.schemas.dashboard import DashboardTrendsResponse, TrendPoint

router = APIRouter(prefix='/dashboard', tags=['dashboard'])

DEFAULT_WEEKS = 8


@router.get('/trends', response_model=DashboardTrendsResponse)
def get_dashboard_trends(
    granularity: Literal['day', 'week'] = Query(
        default='week', description="'day' : semaine en cours jour par jour. 'week' : plusieurs semaines."
    ),
    periods: int = Query(
        default=DEFAULT_WEEKS, ge=1, le=52, description='Nombre de périodes à agréger (ignoré en granularité day, toujours 7 jours)'
    ),
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

    if granularity == 'day':
        period_starts = [current_week_start + timedelta(days=offset) for offset in range(7)]
        step = timedelta(days=1)
    else:
        period_starts = [current_week_start - timedelta(weeks=offset) for offset in range(periods - 1, -1, -1)]
        step = timedelta(days=7)

    points = []
    for period_start in period_starts:
        period_end = period_start + step
        period_recordings = [
            recording for recording in recordings
            if recording.started_at and period_start <= recording.started_at.date() < period_end
        ]
        points.append(TrendPoint(
            period_start=period_start,
            meetings_count=len(period_recordings),
            actions_count=sum(len(recording.actions) for recording in period_recordings),
        ))

    return DashboardTrendsResponse(granularity=granularity, points=points)
