from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubmitRequest(BaseModel):
    primary_file_id: uuid.UUID
    supporting_file_ids: list[uuid.UUID] = []


class SubmissionFileResponse(BaseModel):
    file_id: uuid.UUID
    role: str

    model_config = {"from_attributes": True}


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    primary_file_id: uuid.UUID
    submitted_at: datetime
    status: str
    files: list[SubmissionFileResponse] = []

    model_config = {"from_attributes": True}
