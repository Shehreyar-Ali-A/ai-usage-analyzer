from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.uploaded_file import FileRole, UploadedFile


async def create_file(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    original_filename: str,
    mime_type: str,
    file_size_bytes: int,
    storage_key: str,
    file_role: FileRole = FileRole.context,
    is_available_for_ai_context: bool = True,
) -> UploadedFile:
    f = UploadedFile(
        workspace_id=workspace_id,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        storage_key=storage_key,
        file_role=file_role,
        is_available_for_ai_context=is_available_for_ai_context,
    )
    db.add(f)
    await db.flush()
    await db.refresh(f)
    return f


async def list_files(db: AsyncSession, workspace_id: uuid.UUID) -> list[UploadedFile]:
    result = await db.execute(
        select(UploadedFile)
        .where(UploadedFile.workspace_id == workspace_id, UploadedFile.deleted_at.is_(None))
        .order_by(UploadedFile.created_at.desc())
    )
    return list(result.scalars().all())


async def get_file(db: AsyncSession, file_id: uuid.UUID) -> UploadedFile | None:
    result = await db.execute(
        select(UploadedFile)
        .where(UploadedFile.id == file_id, UploadedFile.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def update_file(db: AsyncSession, f: UploadedFile, **kwargs) -> UploadedFile:
    for key, value in kwargs.items():
        if value is not None:
            setattr(f, key, value)
    f.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(f)
    return f


async def soft_delete_file(db: AsyncSession, f: UploadedFile) -> None:
    f.deleted_at = datetime.now(timezone.utc)
    await db.flush()
