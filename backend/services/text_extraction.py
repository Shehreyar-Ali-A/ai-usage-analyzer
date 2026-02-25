from io import BytesIO
from typing import Tuple

import pdfplumber
import docx


def _normalize_whitespace(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    non_empty = [line for line in lines if line]
    return "\n\n".join(non_empty)


def extract_assignment_text(filename: str, file_bytes: bytes) -> Tuple[str, int]:
    suffix = filename.lower().rsplit(".", 1)[-1]

    if suffix == "pdf":
        text = _extract_pdf_text(file_bytes)
    elif suffix == "docx":
        text = _extract_docx_text(file_bytes)
    else:
        raise ValueError("Unsupported assignment file type. Only PDF and DOCX are allowed.")

    normalized = _normalize_whitespace(text)
    words = normalized.split()
    return normalized, len(words)


def _extract_pdf_text(file_bytes: bytes) -> str:
    buffer = BytesIO(file_bytes)
    text_parts = []
    with pdfplumber.open(buffer) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_docx_text(file_bytes: bytes) -> str:
    buffer = BytesIO(file_bytes)
    document = docx.Document(buffer)
    paragraphs = [p.text for p in document.paragraphs if p.text]
    return "\n\n".join(paragraphs)

