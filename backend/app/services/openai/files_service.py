"""OpenAI Files API integration."""

from __future__ import annotations

import io
import logging

from app.services.openai.client import get_openai_client

logger = logging.getLogger(__name__)


async def upload_file_to_openai(file_bytes: bytes, filename: str) -> str:
    """Upload a file to OpenAI Files API and return the file ID."""
    client = get_openai_client()
    file_obj = io.BytesIO(file_bytes)
    file_obj.name = filename

    result = client.files.create(
        file=file_obj,
        purpose="assistants",
    )
    logger.info("Uploaded file to OpenAI: %s -> %s", filename, result.id)
    return result.id


async def delete_openai_file(file_id: str) -> None:
    """Delete a file from OpenAI."""
    client = get_openai_client()
    client.files.delete(file_id)
    logger.info("Deleted OpenAI file: %s", file_id)
