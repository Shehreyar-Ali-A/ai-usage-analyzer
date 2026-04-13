from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)


class ChatResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatListResponse(BaseModel):
    chats: list[ChatResponse]
