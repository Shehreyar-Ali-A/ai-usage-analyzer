from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workspace import Workspace, WorkspaceStatus
from app.db.models.chat import Chat
from app.db.models.uploaded_file import UploadedFile


async def create_workspace(db: AsyncSession, title: str) -> Workspace:
    ws = Workspace(title=title)
    db.add(ws)
    await db.flush()
    await db.refresh(ws)
    return ws


async def list_workspaces(db: AsyncSession) -> list[Workspace]:
    result = await db.execute(
        select(Workspace)
        .where(Workspace.deleted_at.is_(None))
        .order_by(Workspace.created_at.desc())
    )
    return list(result.scalars().all())


async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace | None:
    result = await db.execute(
        select(Workspace)
        .where(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def update_workspace(db: AsyncSession, ws: Workspace, **kwargs) -> Workspace:
    for key, value in kwargs.items():
        if value is not None:
            setattr(ws, key, value)
    ws.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ws)
    return ws


async def soft_delete_workspace(db: AsyncSession, ws: Workspace) -> None:
    ws.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def get_chat_count(db: AsyncSession, workspace_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Chat)
        .where(Chat.workspace_id == workspace_id, Chat.deleted_at.is_(None))
    )
    return result.scalar_one()


async def get_file_count(db: AsyncSession, workspace_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(UploadedFile)
        .where(UploadedFile.workspace_id == workspace_id, UploadedFile.deleted_at.is_(None))
    )
    return result.scalar_one()
