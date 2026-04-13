"""File storage abstraction.

Currently implements local filesystem storage. Structured so it can be
swapped for S3/R2/etc by adding alternative implementations.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FileStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_path = Path(settings.local_storage_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def save(self, workspace_id: str, filename: str, data: bytes) -> str:
        """Save file and return the storage key."""
        ws_dir = self._base_path / workspace_id
        ws_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = ws_dir / unique_name
        file_path.write_bytes(data)
        storage_key = f"{workspace_id}/{unique_name}"
        logger.info("Saved file: %s (%d bytes)", storage_key, len(data))
        return storage_key

    def read(self, storage_key: str) -> bytes:
        file_path = self._base_path / storage_key
        return file_path.read_bytes()

    def delete(self, storage_key: str) -> None:
        file_path = self._base_path / storage_key
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted file: %s", storage_key)

    def get_full_path(self, storage_key: str) -> str:
        return str(self._base_path / storage_key)


_storage: FileStorage | None = None


def get_file_storage() -> FileStorage:
    global _storage
    if _storage is None:
        _storage = FileStorage()
    return _storage
