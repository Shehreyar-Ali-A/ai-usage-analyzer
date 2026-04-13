from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.submission import Submission, SubmissionFile, SubmissionFileRole, SubmissionStatus
from app.db.models.analysis_run import AnalysisRun, AnalysisStatus


async def create_submission(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    primary_file_id: uuid.UUID,
    supporting_file_ids: list[uuid.UUID],
) -> Submission:
    sub = Submission(
        workspace_id=workspace_id,
        primary_file_id=primary_file_id,
    )
    db.add(sub)
    await db.flush()

    primary_sf = SubmissionFile(
        submission_id=sub.id,
        file_id=primary_file_id,
        role=SubmissionFileRole.primary,
    )
    db.add(primary_sf)

    for fid in supporting_file_ids:
        sf = SubmissionFile(
            submission_id=sub.id,
            file_id=fid,
            role=SubmissionFileRole.supporting,
        )
        db.add(sf)

    await db.flush()
    await db.refresh(sub)
    return sub


async def get_submission_by_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Submission | None:
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.submission_files), selectinload(Submission.analysis_runs))
        .where(Submission.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def create_analysis_run(db: AsyncSession, submission_id: uuid.UUID) -> AnalysisRun:
    run = AnalysisRun(submission_id=submission_id)
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def update_analysis_run(db: AsyncSession, run: AnalysisRun, **kwargs) -> AnalysisRun:
    for key, value in kwargs.items():
        if value is not None:
            setattr(run, key, value)
    await db.flush()
    await db.refresh(run)
    return run
