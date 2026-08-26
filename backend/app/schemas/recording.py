from datetime import datetime

from pydantic import BaseModel

from app.schemas.action import ActionResponse


class RecordingCreate(BaseModel):
    platform: str
    native_meeting_id: str
    bot_name: str = 'Scribe'
    meeting_url: str | None = None


class RecordingRead(BaseModel):
    id: int
    user_id: int
    platform: str
    native_meeting_id: str
    bot_name: str
    status: str
    transcript: str | None = None
    summary: str | None = None
    started_at: datetime
    stopped_at: datetime | None = None

    model_config = {'from_attributes': True}


class SummaryResponse(BaseModel):
    recording_id: int
    summary: str


class ThemeUpdate(BaseModel):
    theme: str | None = None


class ThemeResponse(BaseModel):
    recording_id: int
    theme: str | None = None


class MeetingListItem(BaseModel):
    id: int
    theme: str | None = None
    date: datetime
    status: str
    summary_excerpt: str | None = None
    duration_minutes: float | None = None

    model_config = {'from_attributes': True}


class SegmentOut(BaseModel):
    speaker_name: str
    text: str
    start: float | None = None

    model_config = {'from_attributes': True}


class DiarizedTranscriptResponse(BaseModel):
    meeting_id: int
    segments: list[SegmentOut]


class SpeakerOut(BaseModel):
    id: int
    provisional_name: str
    real_name: str | None = None

    model_config = {'from_attributes': True}


class SpeakingTimeEntry(BaseModel):
    speaker: str
    seconds: float
    percentage: float


class SpeakingTimeResponse(BaseModel):
    meeting_id: int
    entries: list[SpeakingTimeEntry]


class MeetingDetailResponse(BaseModel):
    id: int
    theme: str | None = None
    status: str
    started_at: datetime
    stopped_at: datetime | None = None
    summary: str | None = None
    speakers: list[SpeakerOut]
    segments: list[SegmentOut]
    actions: list[ActionResponse]