from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class WorkspaceUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    submitted_at: Optional[datetime] = None
    openai_vector_store_id: Optional[str] = None
    chat_count: int = 0
    file_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]
