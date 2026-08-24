from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.action import ActionResponse


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
    summary: Optional[str] = None
    started_at: datetime
    stopped_at: Optional[datetime] = None

    model_config = {'from_attributes': True}


class SummaryResponse(BaseModel):
    recording_id: int
    summary: str


class MeetingListItem(BaseModel):
    id: int
    theme: Optional[str] = None
    date: datetime
    status: str
    summary_excerpt: Optional[str] = None

    model_config = {'from_attributes': True}


class SegmentOut(BaseModel):
    speaker_name: str
    text: str

    model_config = {'from_attributes': True}


class DiarizedTranscriptResponse(BaseModel):
    meeting_id: int
    segments: list[SegmentOut]


class SpeakerOut(BaseModel):
    id: int
    provisional_name: str
    real_name: Optional[str] = None

    model_config = {'from_attributes': True}


class MeetingDetailResponse(BaseModel):
    id: int
    theme: Optional[str] = None
    status: str
    started_at: datetime
    stopped_at: Optional[datetime] = None
    summary: Optional[str] = None
    speakers: list[SpeakerOut]
    segments: list[SegmentOut]
    actions: list[ActionResponse]