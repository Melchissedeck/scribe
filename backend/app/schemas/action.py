from datetime import date
from typing import Literal

from pydantic import BaseModel


class ActionResponse(BaseModel):
    id: int
    description: str
    status: str
    due_date: date | None = None
    speaker_id: int | None = None

    model_config = {'from_attributes': True}


class ExtractActionsResponse(BaseModel):
    recording_id: int
    actions_count: int
    actions: list[ActionResponse]
    theme: str | None = None

class ActionStatusUpdate(BaseModel):
    status: Literal['todo', 'in_progress', 'done']


class ActionDueDateUpdate(BaseModel):
    due_date: date | None = None