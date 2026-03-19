"""OpenAI embeddings wrapper with batching.

Uses ``text-embedding-3-large`` by default (configurable via settings).
Embeds in batches of up to 2 048 texts per API call and returns a numpy
array of shape ``(n_texts, dim)``.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
from openai import OpenAI

from config import get_settings

logger = logging.getLogger(__name__)

_BATCH_SIZE = 2048


def embed_texts(texts: List[str]) -> np.ndarray:
    """Return an (N, D) numpy array of embeddings for *texts*."""
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.embedding_model

    all_embeddings: List[List[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start:start + _BATCH_SIZE]
        logger.info(
            "Embedding batch %d–%d of %d texts with %s",
            start, start + len(batch), len(texts), model,
        )
        response = client.embeddings.create(input=batch, model=model)
        for item in response.data:
            all_embeddings.append(item.embedding)

    return np.array(all_embeddings, dtype=np.float32)
