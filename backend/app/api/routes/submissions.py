from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.models.workspace import WorkspaceStatus
from app.db.repositories import file_repo, submission_repo, workspace_repo
from app.db.schemas.submission import SubmissionResponse, SubmissionFileResponse, SubmitRequest

router = APIRouter()


@router.post("/workspaces/{workspace_id}/submit", response_model=SubmissionResponse, status_code=201)
async def submit_workspace(
    workspace_id: uuid.UUID,
    body: SubmitRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    ws = await workspace_repo.get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if ws.status == WorkspaceStatus.submitted:
        raise HTTPException(status_code=400, detail="Workspace already submitted")

    existing = await submission_repo.get_submission_by_workspace(db, workspace_id)
    if existing:
        raise HTTPException(status_code=400, detail="Workspace already has a submission")

    primary = await file_repo.get_file(db, body.primary_file_id)
    if not primary or primary.workspace_id != workspace_id:
        raise HTTPException(status_code=400, detail="Primary file not found in this workspace")

    for fid in body.supporting_file_ids:
        f = await file_repo.get_file(db, fid)
        if not f or f.workspace_id != workspace_id:
            raise HTTPException(status_code=400, detail=f"Supporting file {fid} not found in this workspace")

    sub = await submission_repo.create_submission(
        db,
        workspace_id=workspace_id,
        primary_file_id=body.primary_file_id,
        supporting_file_ids=body.supporting_file_ids,
    )

    ws.status = WorkspaceStatus.submitted
    ws.submitted_at = datetime.now(timezone.utc)
    await db.flush()

    await submission_repo.create_analysis_run(db, sub.id)

    await db.commit()

    background_tasks.add_task(_run_analysis_background, sub.workspace_id)

    sub = await submission_repo.get_submission_by_workspace(db, workspace_id)
    return _sub_to_response(sub)


@router.get("/workspaces/{workspace_id}/submission", response_model=SubmissionResponse)
async def get_submission(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    sub = await submission_repo.get_submission_by_workspace(db, workspace_id)
    if not sub:
        raise HTTPException(status_code=404, detail="No submission found for this workspace")
    return _sub_to_response(sub)


def _sub_to_response(sub) -> SubmissionResponse:
    files = [
        SubmissionFileResponse(file_id=sf.file_id, role=sf.role.value if hasattr(sf.role, "value") else sf.role)
        for sf in (sub.submission_files or [])
    ]
    return SubmissionResponse(
        id=sub.id,
        workspace_id=sub.workspace_id,
        primary_file_id=sub.primary_file_id,
        submitted_at=sub.submitted_at,
        status=sub.status.value if hasattr(sub.status, "value") else sub.status,
        files=files,
    )


async def _run_analysis_background(workspace_id: uuid.UUID) -> None:
    """Run analysis in background with its own DB session."""
    from app.db.base import async_session_factory
    from app.services.analysis.pipeline import run_analysis

    async with async_session_factory() as db:
        try:
            sub = await submission_repo.get_submission_by_workspace(db, workspace_id)
            if sub:
                await run_analysis(workspace_id, db)
                await db.commit()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Background analysis failed for workspace %s", workspace_id)
            await db.rollback()
