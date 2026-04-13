from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.repositories import workspace_repo
from app.db.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter()


def _ws_to_response(ws, chat_count: int = 0, file_count: int = 0) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=ws.id,
        title=ws.title,
        status=ws.status.value if hasattr(ws.status, "value") else ws.status,
        submitted_at=ws.submitted_at,
        openai_vector_store_id=ws.openai_vector_store_id,
        chat_count=chat_count,
        file_count=file_count,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    db: AsyncSession = Depends(get_session),
):
    ws = await workspace_repo.create_workspace(db, title=body.title)
    return _ws_to_response(ws)


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(db: AsyncSession = Depends(get_session)):
    workspaces = await workspace_repo.list_workspaces(db)
    items = []
    for ws in workspaces:
        cc = await workspace_repo.get_chat_count(db, ws.id)
        fc = await workspace_repo.get_file_count(db, ws.id)
        items.append(_ws_to_response(ws, cc, fc))
    return WorkspaceListResponse(workspaces=items)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    ws = await workspace_repo.get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    cc = await workspace_repo.get_chat_count(db, ws.id)
    fc = await workspace_repo.get_file_count(db, ws.id)
    return _ws_to_response(ws, cc, fc)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: uuid.UUID,
    body: WorkspaceUpdate,
    db: AsyncSession = Depends(get_session),
):
    ws = await workspace_repo.get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ws = await workspace_repo.update_workspace(db, ws, title=body.title)
    cc = await workspace_repo.get_chat_count(db, ws.id)
    fc = await workspace_repo.get_file_count(db, ws.id)
    return _ws_to_response(ws, cc, fc)


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    ws = await workspace_repo.get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await workspace_repo.soft_delete_workspace(db, ws)
