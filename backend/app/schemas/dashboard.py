from datetime import date

from pydantic import BaseModel


class TrendPoint(BaseModel):
    period_start: date
    meetings_count: int
    actions_count: int


class DashboardTrendsResponse(BaseModel):
    granularity: str
    points: list[TrendPoint]
