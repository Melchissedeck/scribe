from datetime import date
from typing import Optional
from typing import Literal

from pydantic import BaseModel


class ActionResponse(BaseModel):
    id: int
    description: str
    status: str
    due_date: Optional[date] = None
    speaker_id: Optional[int] = None

    model_config = {'from_attributes': True}


class ExtractActionsResponse(BaseModel):
    recording_id: int
    actions_count: int
    actions: list[ActionResponse]

class ActionStatusUpdate(BaseModel):
    status: Literal['todo', 'in_progress', 'done']    