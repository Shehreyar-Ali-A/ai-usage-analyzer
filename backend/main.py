"""AI Usage Analyzer — FastAPI application.

Pipeline:
  parse → chunk → embed → retrieve evidence → LLM analysis (3 passes) → score → report
"""

from __future__ import annotations

import json
import logging
from typing import Any, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from models import AnalyzeResponse

# New pipeline imports
from services.parsers.assignment_parser import parse_assignment
from services.parsers.chat_parser import parse_chat
from services.chunking.assignment_chunker import chunk_assignment
from services.chunking.chat_chunker import chunk_chat
from services.retrieval.embeddings import embed_texts
from services.retrieval.similarity import lexical_similarity_matrix, semantic_similarity_matrix
from services.retrieval.evidence_selector import select_evidence
from services.analysis.prompt_intent_analyzer import analyze_prompt_intent
from services.analysis.transformation_analyzer import analyze_transformations
from services.analysis.reliance_judge import judge_reliance
from services.scoring.score_builder import build_score
from services.reporting.report_builder import (
    build_report,
    encode_pdf_base64,
    generate_markdown,
    generate_pdf_from_markdown,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="AI Usage Analyzer", version="0.2.0")

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
    # --- Validate file types -------------------------------------------------
    if assignment_file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        raise HTTPException(status_code=400, detail="Assignment must be a PDF or DOCX file.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    # --- Read files ----------------------------------------------------------
    try:
        assignment_bytes = await _read_upload_file_bytes(assignment_file, max_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read assignment file: {exc}") from exc

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
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read chat JSON file: {exc}") from exc

    # --- 1. Parse ------------------------------------------------------------
    try:
        parsed_assignment = parse_assignment(assignment_file.filename or "", assignment_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse assignment: {exc}") from exc

    try:
        parsed_chat = parse_chat(raw_chat_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse chat JSON: {exc}") from exc

    # --- 2. Chunk ------------------------------------------------------------
    assignment_chunks = chunk_assignment(parsed_assignment)
    turn_chunks, assistant_chunks = chunk_chat(parsed_chat)

    para_chunks = [c for c in assignment_chunks if c.level == "paragraph"]
    if not para_chunks or not assistant_chunks:
        logger.warning("Insufficient chunks for analysis (para=%d, asst=%d)", len(para_chunks), len(assistant_chunks))

    # --- 3. Embed ------------------------------------------------------------
    para_texts = [c.text for c in para_chunks]
    asst_texts = [c.text for c in assistant_chunks]

    try:
        para_embeddings = embed_texts(para_texts)
        asst_embeddings = embed_texts(asst_texts)
    except Exception as exc:
        logger.exception("Embedding failed")
        raise HTTPException(status_code=502, detail=f"OpenAI embedding request failed: {exc}") from exc

    # --- 4. Retrieve evidence ------------------------------------------------
    sem_matrix = semantic_similarity_matrix(para_embeddings, asst_embeddings)
    lex_matrix = lexical_similarity_matrix(para_texts, asst_texts)

    evidence_set = select_evidence(para_chunks, assistant_chunks, sem_matrix, lex_matrix)

    # --- 5. LLM analysis (3 passes) -----------------------------------------
    try:
        intent_result = analyze_prompt_intent(parsed_chat.user_prompts)
    except Exception:
        logger.exception("Prompt intent analysis failed; using default")
        from models import PromptIntentResult
        intent_result = PromptIntentResult()

    try:
        transformation_result = analyze_transformations(evidence_set.pairs)
    except Exception:
        logger.exception("Transformation analysis failed; using default")
        from models import TransformationAnalysisResult
        transformation_result = TransformationAnalysisResult()

    try:
        reliance_judgment = judge_reliance(
            intent_result=intent_result,
            transformation_result=transformation_result,
            coverage=evidence_set.coverage,
            evidence_pairs=evidence_set.pairs,
            total_turns=len(turn_chunks),
            total_prompts=len(parsed_chat.user_prompts),
        )
    except Exception:
        logger.exception("Reliance judgment failed; using default")
        from models import RelianceJudgment
        reliance_judgment = RelianceJudgment()

    # --- 6. Score ------------------------------------------------------------
    scoring_result = build_score(
        intent=intent_result,
        transformation=transformation_result,
        judgment=reliance_judgment,
        coverage=evidence_set.coverage,
        total_turns=len(turn_chunks),
        total_prompts=len(parsed_chat.user_prompts),
    )

    # --- 7. Report -----------------------------------------------------------
    report = build_report(
        scoring=scoring_result,
        intent=intent_result,
        transformation=transformation_result,
        judgment=reliance_judgment,
        evidence_set=evidence_set,
    )

    markdown_report = generate_markdown(report)

    pdf_base64: str | None = None
    if settings.enable_pdf_output:
        try:
            pdf_bytes = generate_pdf_from_markdown(markdown_report)
            pdf_base64 = encode_pdf_base64(pdf_bytes)
        except Exception:
            logger.exception("PDF generation failed; skipping")
            pdf_base64 = None

    response = AnalyzeResponse(report=report, markdown_report=markdown_report, pdf_base64=pdf_base64)
    return JSONResponse(content=response.model_dump())
