from datetime import date

from pydantic import BaseModel


class WeeklyTrend(BaseModel):
    week_start: date
    meetings_count: int
    actions_count: int


class DashboardTrendsResponse(BaseModel):
    weeks: list[WeeklyTrend]
