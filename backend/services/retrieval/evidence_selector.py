"""Select top evidence pairs and compute coverage metrics.

Given the semantic and lexical similarity matrices between assignment
paragraph chunks and assistant output chunks, this module:
  - Picks the top-k pairs above the semantic threshold
  - Computes per-assignment-chunk best matches
  - Computes assignment coverage ratio and section-level coverage
  - Returns an ``EvidenceSet`` ready for downstream analysis
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List

import numpy as np

from config import get_settings
from models import (
    AssignmentChunk,
    AssistantOutputChunk,
    CoverageMetrics,
    EvidencePair,
    EvidenceSet,
)

logger = logging.getLogger(__name__)


def select_evidence(
    assignment_chunks: List[AssignmentChunk],
    assistant_chunks: List[AssistantOutputChunk],
    sem_matrix: np.ndarray,
    lex_matrix: np.ndarray,
) -> EvidenceSet:
    """Build an ``EvidenceSet`` from similarity matrices.

    Only paragraph-level assignment chunks are used for pairing.
    """
    settings = get_settings()
    top_k = settings.retrieval_top_k
    sem_thresh = settings.semantic_threshold
    max_pairs = settings.max_evidence_pairs

    para_chunks = [c for c in assignment_chunks if c.level == "paragraph"]
    if not para_chunks or not assistant_chunks or sem_matrix.size == 0:
        return EvidenceSet()

    # Build index map: para_chunks -> row index in the matrix
    para_id_to_idx: Dict[str, int] = {
        c.chunk_id: i for i, c in enumerate(para_chunks)
    }

    # Collect candidate pairs ------------------------------------------------
    candidates: List[EvidencePair] = []

    for a_chunk in para_chunks:
        a_idx = para_id_to_idx[a_chunk.chunk_id]
        if a_idx >= sem_matrix.shape[0]:
            continue
        row_sem = sem_matrix[a_idx]
        row_lex = lex_matrix[a_idx] if a_idx < lex_matrix.shape[0] else np.zeros(len(assistant_chunks))

        top_indices = np.argsort(row_sem)[::-1][:top_k]
        for b_idx in top_indices:
            b_idx = int(b_idx)
            if b_idx >= len(assistant_chunks):
                continue
            sem_score = float(row_sem[b_idx])
            if sem_score < sem_thresh:
                continue
            lex_score = float(row_lex[b_idx]) if b_idx < len(row_lex) else 0.0
            b_chunk = assistant_chunks[b_idx]

            candidates.append(EvidencePair(
                assignment_chunk_id=a_chunk.chunk_id,
                assistant_chunk_id=b_chunk.chunk_id,
                assignment_text=a_chunk.text,
                assistant_text=b_chunk.text,
                semantic_score=round(sem_score, 4),
                lexical_score=round(lex_score, 4),
            ))

    # Deduplicate by (assignment_id, assistant_id) keeping highest semantic
    dedup: Dict[tuple, EvidencePair] = {}
    for p in candidates:
        key = (p.assignment_chunk_id, p.assistant_chunk_id)
        if key not in dedup or p.semantic_score > dedup[key].semantic_score:
            dedup[key] = p

    pairs = sorted(dedup.values(), key=lambda p: p.semantic_score, reverse=True)[:max_pairs]

    # Coverage metrics -------------------------------------------------------
    best_sem_per_assignment: Dict[str, float] = {}
    best_lex_per_assignment: Dict[str, float] = {}
    for a_chunk in para_chunks:
        a_idx = para_id_to_idx[a_chunk.chunk_id]
        if a_idx < sem_matrix.shape[0]:
            best_sem_per_assignment[a_chunk.chunk_id] = float(np.max(sem_matrix[a_idx]))
        if a_idx < lex_matrix.shape[0]:
            best_lex_per_assignment[a_chunk.chunk_id] = float(np.max(lex_matrix[a_idx]))

    matched_count = sum(1 for v in best_sem_per_assignment.values() if v >= sem_thresh)
    coverage_ratio = matched_count / len(para_chunks) if para_chunks else 0.0

    # Section-level coverage
    section_hits: Dict[str, List[float]] = defaultdict(list)
    for c in para_chunks:
        key = c.section_title or "(untitled)"
        section_hits[key].append(best_sem_per_assignment.get(c.chunk_id, 0.0))

    section_coverage: Dict[str, float] = {}
    for sec_title, scores in section_hits.items():
        section_coverage[sec_title] = sum(1 for s in scores if s >= sem_thresh) / len(scores)

    mean_best_sem = float(np.mean(list(best_sem_per_assignment.values()))) if best_sem_per_assignment else 0.0
    mean_best_lex = float(np.mean(list(best_lex_per_assignment.values()))) if best_lex_per_assignment else 0.0

    coverage = CoverageMetrics(
        assignment_coverage_ratio=round(coverage_ratio, 4),
        section_coverage=section_coverage,
        mean_best_semantic=round(mean_best_sem, 4),
        mean_best_lexical=round(mean_best_lex, 4),
    )

    logger.info(
        "Evidence selected: %d pairs, coverage %.1f%%, mean_sem %.3f",
        len(pairs), coverage_ratio * 100, mean_best_sem,
    )
    return EvidenceSet(pairs=pairs, coverage=coverage)
