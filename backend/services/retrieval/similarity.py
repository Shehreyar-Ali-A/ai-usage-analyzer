"""Compute semantic and lexical similarity matrices separately.

Semantic similarity uses cosine similarity on pre-computed embedding vectors.
Lexical similarity uses Jaccard overlap via scikit-learn CountVectorizer.
The two matrices are returned independently so that downstream consumers
can weight them as needed.
"""

from __future__ import annotations

from typing import List

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def semantic_similarity_matrix(emb_a: np.ndarray, emb_b: np.ndarray) -> np.ndarray:
    """Cosine similarity between two sets of embedding vectors.

    Returns an (M, N) matrix where M = len(emb_a), N = len(emb_b).
    """
    if emb_a.size == 0 or emb_b.size == 0:
        return np.zeros((emb_a.shape[0], emb_b.shape[0]), dtype=np.float32)
    return cosine_similarity(emb_a, emb_b).astype(np.float32)


def lexical_similarity_matrix(texts_a: List[str], texts_b: List[str]) -> np.ndarray:
    """Jaccard-style binary term overlap between two sets of texts.

    Returns an (M, N) matrix.
    """
    if not texts_a or not texts_b:
        return np.zeros((len(texts_a), len(texts_b)), dtype=np.float32)

    vectorizer = CountVectorizer(binary=True)
    combined = texts_a + texts_b
    X = vectorizer.fit_transform(combined)
    A = X[:len(texts_a)]
    B = X[len(texts_a):]

    intersection = (A @ B.T).toarray().astype(np.float64)
    A_sum = np.asarray(A.sum(axis=1)).astype(np.float64)
    B_sum = np.asarray(B.sum(axis=1)).astype(np.float64)
    union = A_sum + B_sum.T - intersection

    with np.errstate(divide="ignore", invalid="ignore"):
        jaccard = np.divide(
            intersection,
            union,
            out=np.zeros_like(intersection),
            where=union != 0,
        )
    return jaccard.astype(np.float32)
