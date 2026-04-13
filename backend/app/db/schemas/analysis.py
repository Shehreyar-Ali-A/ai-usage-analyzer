from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnalysisRunResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    report_json: Optional[dict] = None
    report_markdown: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    status: str
    report: Optional[dict] = None
    markdown: Optional[str] = None
