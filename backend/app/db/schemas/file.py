from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    file_role: str
    is_available_for_ai_context: bool
    openai_file_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FileUpdateRequest(BaseModel):
    file_role: Optional[str] = None
    is_available_for_ai_context: Optional[bool] = None


class FileListResponse(BaseModel):
    files: list[FileUploadResponse]
