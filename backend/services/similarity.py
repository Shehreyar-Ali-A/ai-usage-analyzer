from typing import Dict, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import get_settings


_embedding_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        model_name = get_settings().embedding_model_name
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def _compute_embeddings(texts: List[str]) -> np.ndarray:
    model = _get_model()
    return np.array(model.encode(texts, convert_to_numpy=True, show_progress_bar=False))


def _lexical_overlap_matrix(texts_a: List[str], texts_b: List[str]) -> np.ndarray:
    vectorizer = CountVectorizer(binary=True)
    combined = texts_a + texts_b
    X = vectorizer.fit_transform(combined)
    A = X[: len(texts_a)]
    B = X[len(texts_a) :]
    # Jaccard similarity approximation using intersection over union
    intersection = A @ B.T
    A_sum = A.sum(axis=1)
    B_sum = B.sum(axis=1)
    union = A_sum + B_sum.T - intersection
    with np.errstate(divide="ignore", invalid="ignore"):
        jaccard = intersection / union
        jaccard[np.isnan(jaccard)] = 0.0
    return jaccard.A


def compute_similarity(
    assignment_chunks: List[Dict],
    ai_chunks: List[Dict],
) -> List[Tuple[Dict, Dict, float]]:
    """
    Compute combined semantic + lexical similarity and return top evidence pairs.
    """
    if not assignment_chunks or not ai_chunks:
        return []

    settings = get_settings()
    texts_a = [c["text"] for c in assignment_chunks]
    texts_b = [c["text"] for c in ai_chunks]

    emb_a = _compute_embeddings(texts_a)
    emb_b = _compute_embeddings(texts_b)

    emb_sim = cosine_similarity(emb_a, emb_b)
    lex_sim = _lexical_overlap_matrix(texts_a, texts_b)

    # Weight semantic similarity higher than lexical
    combined = 0.7 * emb_sim + 0.3 * lex_sim

    evidence: List[Tuple[Dict, Dict, float]] = []

    for i, row in enumerate(combined):
        top_indices = np.argsort(row)[::-1][: settings.similarity_top_k]
        for j in top_indices:
            score = float(row[j])
            if score < settings.similarity_threshold:
                continue
            evidence.append((assignment_chunks[i], ai_chunks[j], score))

    # Deduplicate by (assignment_id, ai_id) keeping highest score
    dedup: Dict[Tuple[str, str], float] = {}
    meta: Dict[Tuple[str, str], Tuple[Dict, Dict]] = {}
    for a, b, score in evidence:
        key = (a["id"], b["id"])
        if key not in dedup or score > dedup[key]:
            dedup[key] = score
            meta[key] = (a, b)

    final: List[Tuple[Dict, Dict, float]] = []
    for key, score in dedup.items():
        a, b = meta[key]
        final.append((a, b, score))

    # Sort by score descending
    final.sort(key=lambda x: x[2], reverse=True)
    return final

