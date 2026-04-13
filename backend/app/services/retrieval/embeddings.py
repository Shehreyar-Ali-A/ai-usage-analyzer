"""OpenAI embeddings wrapper with batching."""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from app.services.openai.client import get_openai_client
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_BATCH_SIZE = 2048


def embed_texts(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    settings = get_settings()
    client = get_openai_client()
    model = settings.openai_embedding_model

    all_embeddings: List[List[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start:start + _BATCH_SIZE]
        logger.info(
            "Embedding batch %d-%d of %d texts with %s",
            start, start + len(batch), len(texts), model,
        )
        response = client.embeddings.create(input=batch, model=model)
        for item in response.data:
            all_embeddings.append(item.embedding)

    return np.array(all_embeddings, dtype=np.float32)
