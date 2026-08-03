from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RecordingCreate(BaseModel):
    platform: str
    native_meeting_id: str
    bot_name: str = 'Scribe'


class RecordingRead(BaseModel):
    id: int
    user_id: int
    platform: str
    native_meeting_id: str
    bot_name: str
    status: str
    transcript: Optional[str] = None
    started_at: datetime
    stopped_at: Optional[datetime] = None

    model_config = {'from_attributes': True}
