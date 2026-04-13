"""Turn-aware chunking for chat conversations."""

from __future__ import annotations

import logging
from typing import List

import tiktoken

from app.core.config import get_settings
from app.services.analysis.models import AssistantOutputChunk, ChatTurnChunk, ParsedChat

logger = logging.getLogger(__name__)

_enc: tiktoken.Encoding | None = None


def _tokenizer() -> tiktoken.Encoding:
    global _enc
    if _enc is None:
        _enc = tiktoken.get_encoding("cl100k_base")
    return _enc


def _estimate_tokens(text: str) -> int:
    return len(_tokenizer().encode(text))


def _word_count(text: str) -> int:
    return len(text.split())


def chunk_chat(parsed: ParsedChat) -> tuple[List[ChatTurnChunk], List[AssistantOutputChunk]]:
    settings = get_settings()
    min_w = settings.chunk_min_words
    max_w = settings.chunk_max_words
    overlap_w = settings.chunk_overlap_words

    turn_chunks: List[ChatTurnChunk] = []
    assistant_chunks: List[AssistantOutputChunk] = []
    global_idx = 0

    for turn in parsed.turns:
        combined_assistant = "\n\n".join(turn.assistant_messages)
        turn_chunks.append(ChatTurnChunk(
            turn_id=turn.turn_id,
            prompt_text=turn.user_message,
            assistant_text=combined_assistant,
            timestamp=turn.timestamp,
        ))

        if not combined_assistant.strip():
            continue

        paragraphs = _split_paragraphs(combined_assistant)
        merged = _merge_small(paragraphs, min_w)

        for para in merged:
            sub_chunks = _split_large(para, max_w, overlap_w)
            for sub in sub_chunks:
                assistant_chunks.append(AssistantOutputChunk(
                    chunk_id=f"assistant_{global_idx}",
                    turn_id=turn.turn_id,
                    paragraph_index=global_idx,
                    estimated_tokens=_estimate_tokens(sub),
                    text=sub,
                ))
                global_idx += 1

    logger.info(
        "Chat chunked: %d turns, %d assistant output chunks",
        len(turn_chunks), len(assistant_chunks),
    )
    return turn_chunks, assistant_chunks


def _split_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _merge_small(paragraphs: List[str], min_words: int) -> List[str]:
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


def _split_large(text: str, max_words: int, overlap_words: int) -> List[str]:
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
