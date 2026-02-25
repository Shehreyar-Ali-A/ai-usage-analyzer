import json
from typing import Any, List, Tuple

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from models import AnalyzeResponse
from services.chat_normalization import normalize_chat_json
from services.chunking import chunk_ai_responses, chunk_assignment_text
from services.classification import classify_prompts
from services.report_generator import (
    build_report,
    encode_pdf_base64,
    generate_markdown,
    generate_pdf_from_markdown,
)
from services.scoring import (
    compute_direct_reuse_similarity,
    compute_iteration_depth,
    compute_reliance_score,
    compute_transformation_degree,
)
from services.similarity import compute_similarity
from services.text_extraction import extract_assignment_text


settings = get_settings()

app = FastAPI(title="AI Usage Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_allow_origin],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


async def _read_upload_file_bytes(upload_file: UploadFile, max_bytes: int) -> bytes:
    size = 0
    chunks: List[bytes] = []
    while True:
        chunk = await upload_file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file exceeds maximum allowed size.")
        chunks.append(chunk)
    return b"".join(chunks)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    assignment_file: UploadFile = File(...),
    chat_json_file: UploadFile = File(...),
) -> Any:
    # Validate file types
    if assignment_file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        raise HTTPException(status_code=400, detail="Assignment must be a PDF or DOCX file.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    try:
        assignment_bytes = await _read_upload_file_bytes(assignment_file, max_bytes)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=f"Failed to read assignment file: {exc}") from exc

    # Read and parse chat JSON
    try:
        raw_chat_bytes = await _read_upload_file_bytes(chat_json_file, max_bytes)
        raw_chat_text = raw_chat_bytes.decode("utf-8")
        raw_chat_json = json.loads(raw_chat_text)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Chat JSON must be UTF-8 encoded: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Malformed chat JSON: {exc}") from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=f"Failed to read chat JSON file: {exc}") from exc

    try:
        assignment_text, word_count = extract_assignment_text(assignment_file.filename or "", assignment_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Failed to extract assignment text: {exc}") from exc

    try:
        normalized_chat, assistant_texts, user_prompts = normalize_chat_json(raw_chat_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Failed to normalize chat JSON: {exc}") from exc

    assignment_chunks = chunk_assignment_text(assignment_text)
    ai_chunks = chunk_ai_responses(assistant_texts)

    evidence_pairs = compute_similarity(assignment_chunks, ai_chunks)

    similarity_scores: List[float] = [score for _, _, score in evidence_pairs]
    # For transformation degree we approximate semantic vs lexical scores from similarity matrix inputs
    direct_reuse_similarity = compute_direct_reuse_similarity(similarity_scores)

    usage_types, prompt_severity = classify_prompts(user_prompts)

    # Approximate transformation degree and iteration depth
    # For v0, reuse direct_reuse_similarity as proxy for semantic score and assume lexical a bit lower.
    semantic_scores = similarity_scores
    lexical_scores = [max(0.0, s - 0.2) for s in similarity_scores]
    transformation_degree = compute_transformation_degree(semantic_scores, lexical_scores)
    iteration_depth = compute_iteration_depth(len(normalized_chat.messages))

    reliance_score, reliance_label = compute_reliance_score(
        direct_reuse_similarity=direct_reuse_similarity,
        prompt_severity=prompt_severity,
        transformation_degree=transformation_degree,
        iteration_depth=iteration_depth,
    )

    observations: List[str] = []
    if direct_reuse_similarity > 0.8:
        observations.append("Detected highly similar passages between AI outputs and assignment text.")
    if "Direct Generation" in usage_types:
        observations.append("User prompts include requests for full solution or essay generation.")
    if "Rewriting" in usage_types:
        observations.append("User requested rewriting or polishing of existing text.")
    if not observations:
        observations.append("AI usage appears primarily supportive or exploratory based on available evidence.")

    # Confidence heuristic
    if not evidence_pairs and reliance_score <= 30:
        confidence = "Low"
    elif len(evidence_pairs) >= 3 or reliance_score >= 60:
        confidence = "High"
    else:
        confidence = "Medium"

    # Summary synthesis
    if reliance_label == "High":
        summary = (
            "The assignment shows high reliance on AI, with strong similarity between AI-generated text and "
            "the submitted work, and prompts that often request direct generation or substantial rewriting."
        )
    elif reliance_label == "Moderate":
        summary = (
            "The assignment demonstrates moderate AI reliance, where AI appears to have influenced structure or "
            "phrasing, but the submission still reflects notable user contribution."
        )
    else:
        summary = (
            "The assignment indicates low AI reliance, with limited direct reuse of AI responses and prompts "
            "focused more on explanation, clarification, or light support."
        )

    report = build_report(
        summary=summary,
        reliance_score=reliance_score,
        reliance_label=reliance_label,
        usage_types=usage_types,
        evidence=evidence_pairs,
        observations=observations,
        confidence=confidence,
    )

    markdown_report = generate_markdown(report)

    pdf_base64: str | None = None
    if settings.enable_pdf_output:
        try:
            pdf_bytes = generate_pdf_from_markdown(markdown_report)
            pdf_base64 = encode_pdf_base64(pdf_bytes)
        except Exception:
            # Fail soft on PDF generation; still return JSON and Markdown
            pdf_base64 = None

    response = AnalyzeResponse(report=report, markdown_report=markdown_report, pdf_base64=pdf_base64)
    return JSONResponse(content=response.model_dump())

