from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.db.models.uploaded_file import FileRole
from app.db.repositories import file_repo, workspace_repo
from app.db.schemas.file import FileListResponse, FileUpdateRequest, FileUploadResponse

router = APIRouter()


@router.post("/workspaces/{workspace_id}/files", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
):
    ws = await workspace_repo.get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if ws.status.value == "submitted":
        raise HTTPException(status_code=400, detail="Workspace is submitted; no new files allowed")

    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024

    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail="File exceeds maximum upload size")

    from app.services.storage.file_storage import get_file_storage
    storage = get_file_storage()
    storage_key = storage.save(str(workspace_id), file.filename or "unnamed", data)

    db_file = await file_repo.create_file(
        db,
        workspace_id=workspace_id,
        original_filename=file.filename or "unnamed",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(data),
        storage_key=storage_key,
    )

    # Upload to OpenAI if available for AI context
    if db_file.is_available_for_ai_context and settings.openai_use_vector_stores:
        try:
            from app.services.openai.files_service import upload_file_to_openai
            from app.services.openai.vector_store_service import (
                add_file_to_vector_store,
                ensure_workspace_vector_store,
            )

            openai_file_id = await upload_file_to_openai(data, db_file.original_filename)
            db_file = await file_repo.update_file(db, db_file, openai_file_id=openai_file_id)

            vs_id = await ensure_workspace_vector_store(db, ws)
            vs_file_id = await add_file_to_vector_store(vs_id, openai_file_id)
            db_file = await file_repo.update_file(db, db_file, openai_vs_file_id=vs_file_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("OpenAI file upload failed: %s", e)

    return FileUploadResponse.model_validate(db_file)


@router.get("/workspaces/{workspace_id}/files", response_model=FileListResponse)
async def list_files(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    files = await file_repo.list_files(db, workspace_id)
    return FileListResponse(files=[FileUploadResponse.model_validate(f) for f in files])


@router.patch("/files/{file_id}", response_model=FileUploadResponse)
async def update_file(
    file_id: uuid.UUID,
    body: FileUpdateRequest,
    db: AsyncSession = Depends(get_session),
):
    f = await file_repo.get_file(db, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    update_kwargs = {}
    if body.file_role is not None:
        try:
            update_kwargs["file_role"] = FileRole(body.file_role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid file role: {body.file_role}")
    if body.is_available_for_ai_context is not None:
        update_kwargs["is_available_for_ai_context"] = body.is_available_for_ai_context

    f = await file_repo.update_file(db, f, **update_kwargs)
    return FileUploadResponse.model_validate(f)


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    f = await file_repo.get_file(db, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    await file_repo.soft_delete_file(db, f)
