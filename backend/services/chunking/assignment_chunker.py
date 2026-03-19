"""Structure-aware, hierarchical chunking for assignment documents.

Produces three levels of chunks:
  - document  : single chunk containing the full text (for summary use)
  - section   : one chunk per detected section
  - paragraph : individual paragraphs with merge/split logic

Small paragraphs (< ``chunk_min_words``) are merged with neighbours.
Large paragraphs (> ``chunk_max_words``) are split into sub-chunks
with configurable word overlap.
"""

from __future__ import annotations

import logging
from typing import List

import tiktoken

from config import get_settings
from models import AssignmentChunk, ParsedAssignment

logger = logging.getLogger(__name__)

_enc: tiktoken.Encoding | None = None


def _tokenizer() -> tiktoken.Encoding:
    global _enc
    if _enc is None:
        _enc = tiktoken.get_encoding("cl100k_base")
    return _enc


def _estimate_tokens(text: str) -> int:
    return len(_tokenizer().encode(text))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_assignment(parsed: ParsedAssignment) -> List[AssignmentChunk]:
    """Return a flat list of hierarchical assignment chunks."""
    settings = get_settings()
    min_w = settings.chunk_min_words
    max_w = settings.chunk_max_words
    overlap_w = settings.chunk_overlap_words

    chunks: List[AssignmentChunk] = []

    # Document-level chunk
    if parsed.full_text:
        chunks.append(AssignmentChunk(
            chunk_id="assignment_doc_0",
            level="document",
            section_title=None,
            paragraph_index=0,
            char_start=0,
            char_end=len(parsed.full_text),
            estimated_tokens=_estimate_tokens(parsed.full_text),
            text=parsed.full_text,
        ))

    char_offset = 0
    para_global_idx = 0
    sec_idx = 0

    for section in parsed.sections:
        section_text_parts: List[str] = []
        if section.title:
            section_text_parts.append(section.title)
        section_text_parts.extend(section.paragraphs)
        section_text = "\n\n".join(section_text_parts)

        if section_text.strip():
            sec_start = parsed.full_text.find(section_text[:80], char_offset)
            if sec_start == -1:
                sec_start = char_offset
            sec_end = sec_start + len(section_text)

            chunks.append(AssignmentChunk(
                chunk_id=f"assignment_sec_{sec_idx}",
                level="section",
                section_title=section.title,
                paragraph_index=0,
                char_start=sec_start,
                char_end=sec_end,
                estimated_tokens=_estimate_tokens(section_text),
                text=section_text,
            ))

        # Paragraph-level chunks with merge/split
        merged_paragraphs = _merge_small_paragraphs(section.paragraphs, min_w)

        for para in merged_paragraphs:
            sub_chunks = _split_large_paragraph(para, max_w, overlap_w)
            for sub in sub_chunks:
                p_start = parsed.full_text.find(sub[:60], char_offset)
                if p_start == -1:
                    p_start = char_offset
                p_end = p_start + len(sub)

                chunks.append(AssignmentChunk(
                    chunk_id=f"assignment_para_{para_global_idx}",
                    level="paragraph",
                    section_title=section.title,
                    paragraph_index=para_global_idx,
                    char_start=p_start,
                    char_end=p_end,
                    estimated_tokens=_estimate_tokens(sub),
                    text=sub,
                ))
                para_global_idx += 1
                char_offset = max(char_offset, p_end)

        sec_idx += 1

    para_chunks = [c for c in chunks if c.level == "paragraph"]
    logger.info(
        "Assignment chunked: %d sections, %d paragraph chunks, %d total",
        sec_idx, len(para_chunks), len(chunks),
    )
    return chunks


# ---------------------------------------------------------------------------
# Merge / Split helpers
# ---------------------------------------------------------------------------

def _word_count(text: str) -> int:
    return len(text.split())


def _merge_small_paragraphs(paragraphs: List[str], min_words: int) -> List[str]:
    """Merge adjacent paragraphs that are below *min_words*."""
    if not paragraphs:
        return []

    merged: List[str] = []
    buffer: List[str] = []
    buf_words = 0

    for para in paragraphs:
        pw = _word_count(para)
        if buf_words + pw < min_words:
            buffer.append(para)
            buf_words += pw
        else:
            if buffer:
                # Merge buffered small paragraphs with this one
                buffer.append(para)
                merged.append("\n\n".join(buffer))
                buffer = []
                buf_words = 0
            else:
                merged.append(para)

    if buffer:
        if merged:
            merged[-1] = merged[-1] + "\n\n" + "\n\n".join(buffer)
        else:
            merged.append("\n\n".join(buffer))

    return merged


def _split_large_paragraph(text: str, max_words: int, overlap_words: int) -> List[str]:
    """Split a paragraph exceeding *max_words* into overlapping sub-chunks."""
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap_words

    return chunks
