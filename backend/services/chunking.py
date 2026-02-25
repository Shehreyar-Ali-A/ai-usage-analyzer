from typing import List, Dict


def _split_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _chunk_paragraphs(paragraphs: List[str], target_words: int = 200, overlap_paragraphs: int = 0) -> List[str]:
    chunks: List[str] = []
    current: List[str] = []
    current_words = 0

    for para in paragraphs:
        words = para.split()
        if current_words + len(words) > target_words and current:
            chunks.append("\n\n".join(current))
            if overlap_paragraphs > 0:
                current = current[-overlap_paragraphs:]
                current_words = sum(len(p.split()) for p in current)
            else:
                current = []
                current_words = 0

        current.append(para)
        current_words += len(words)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def chunk_assignment_text(text: str, target_words: int = 200) -> List[Dict]:
    paragraphs = _split_paragraphs(text)
    raw_chunks = _chunk_paragraphs(paragraphs, target_words=target_words, overlap_paragraphs=1)
    return [
        {"id": f"assignment_{idx}", "source": "assignment", "original_index": idx, "text": chunk}
        for idx, chunk in enumerate(raw_chunks)
    ]


def chunk_ai_responses(responses: list[str], target_words: int = 200) -> List[Dict]:
    chunks: List[Dict] = []
    idx = 0
    for msg_index, text in enumerate(responses):
        paragraphs = _split_paragraphs(text)
        raw_chunks = _chunk_paragraphs(paragraphs, target_words=target_words, overlap_paragraphs=0)
        for chunk in raw_chunks:
            chunks.append(
                {
                    "id": f"ai_{idx}",
                    "source": "ai",
                    "original_index": msg_index,
                    "text": chunk,
                }
            )
            idx += 1
    return chunks

