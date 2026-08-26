from datetime import datetime

from pydantic import BaseModel


class LogRead(BaseModel):
    id: int
    action: str
    user_id: int | None = None
    date: datetime
    detail: str | None = None

    model_config = {'from_attributes': True}
