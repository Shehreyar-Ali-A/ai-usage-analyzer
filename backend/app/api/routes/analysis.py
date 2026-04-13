from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.repositories import submission_repo
from app.db.schemas.analysis import ReportResponse

router = APIRouter()


@router.get("/workspaces/{workspace_id}/report", response_model=ReportResponse)
async def get_report(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    sub = await submission_repo.get_submission_by_workspace(db, workspace_id)
    if not sub:
        raise HTTPException(status_code=404, detail="No submission found")

    if not sub.analysis_runs:
        return ReportResponse(
            status=sub.status.value if hasattr(sub.status, "value") else sub.status,
        )

    latest_run = sub.analysis_runs[-1]
    status = latest_run.status.value if hasattr(latest_run.status, "value") else latest_run.status

    return ReportResponse(
        status=status,
        report=latest_run.report_json,
        markdown=latest_run.report_markdown,
    )
