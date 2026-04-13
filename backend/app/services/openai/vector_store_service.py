"""OpenAI Vector Store management."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workspace import Workspace
from app.db.repositories import workspace_repo
from app.services.openai.client import get_openai_client

logger = logging.getLogger(__name__)


async def ensure_workspace_vector_store(db: AsyncSession, ws: Workspace) -> str:
    """Get or create an OpenAI vector store for the workspace. Returns the vs_id."""
    if ws.openai_vector_store_id:
        return ws.openai_vector_store_id

    client = get_openai_client()
    vs = client.vector_stores.create(name=f"workspace-{ws.id}-{ws.title[:50]}")
    logger.info("Created vector store %s for workspace %s", vs.id, ws.id)

    await workspace_repo.update_workspace(db, ws, openai_vector_store_id=vs.id)
    return vs.id


async def add_file_to_vector_store(vector_store_id: str, file_id: str) -> str:
    """Add a file to a vector store. Returns the vector store file ID."""
    client = get_openai_client()
    vs_file = client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=file_id,
    )
    logger.info("Added file %s to vector store %s -> vs_file %s", file_id, vector_store_id, vs_file.id)
    return vs_file.id


async def remove_file_from_vector_store(vector_store_id: str, vs_file_id: str) -> None:
    """Remove a file from a vector store."""
    client = get_openai_client()
    client.vector_stores.files.delete(
        vector_store_id=vector_store_id,
        file_id=vs_file_id,
    )
    logger.info("Removed file %s from vector store %s", vs_file_id, vector_store_id)


async def delete_vector_store(vector_store_id: str) -> None:
    """Delete an OpenAI vector store."""
    client = get_openai_client()
    client.vector_stores.delete(vector_store_id)
    logger.info("Deleted vector store: %s", vector_store_id)
