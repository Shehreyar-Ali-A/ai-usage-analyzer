"""Analysis pipeline orchestrator.

Runs the full analysis pipeline on a submitted workspace:
  1. Load workspace data from DB
  2. Reconstruct ParsedChat from stored messages
  3. Parse primary submission file
  4. Chunk, embed, retrieve evidence
  5. Run 3 LLM analysis passes
  6. Score and build report
  7. Store results in analysis_run
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis_run import AnalysisStatus
from app.db.models.submission import SubmissionStatus
from app.db.repositories import file_repo, message_repo, submission_repo
from app.services.analysis.models import (
    PromptIntentResult,
    RelianceJudgment,
    TransformationAnalysisResult,
)

logger = logging.getLogger(__name__)


async def run_analysis(workspace_id: uuid.UUID, db: AsyncSession) -> None:
    """Execute the full analysis pipeline for a submitted workspace."""

    sub = await submission_repo.get_submission_by_workspace(db, workspace_id)
    if not sub:
        logger.error("Submission not found for workspace: %s", workspace_id)
        return

    runs = sub.analysis_runs
    if not runs:
        logger.error("No analysis run found for workspace: %s", workspace_id)
        return

    run = runs[-1]
    run.status = AnalysisStatus.running
    run.started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        # 1. Load all messages from workspace
        all_messages = await message_repo.get_all_workspace_messages(db, sub.workspace_id)

        # 2. Reconstruct ParsedChat
        from app.services.parsers.chat_reconstructor import reconstruct_parsed_chat
        parsed_chat = reconstruct_parsed_chat(all_messages)

        # 3. Load and parse primary submission file
        primary_file = await file_repo.get_file(db, sub.primary_file_id)
        if not primary_file:
            raise ValueError("Primary submission file not found")

        from app.services.storage.file_storage import get_file_storage
        storage = get_file_storage()
        file_bytes = storage.read(primary_file.storage_key)

        from app.services.parsers.assignment_parser import parse_assignment
        parsed_assignment = parse_assignment(primary_file.original_filename, file_bytes)

        # 4. Chunk
        from app.services.chunking.assignment_chunker import chunk_assignment
        from app.services.chunking.chat_chunker import chunk_chat

        assignment_chunks = chunk_assignment(parsed_assignment)
        turn_chunks, assistant_chunks = chunk_chat(parsed_chat)

        para_chunks = [c for c in assignment_chunks if c.level == "paragraph"]

        # 5. Embed + similarity
        from app.services.retrieval.embeddings import embed_texts
        from app.services.retrieval.similarity import (
            lexical_similarity_matrix,
            semantic_similarity_matrix,
        )

        para_texts = [c.text for c in para_chunks]
        asst_texts = [c.text for c in assistant_chunks]

        para_embeddings = embed_texts(para_texts)
        asst_embeddings = embed_texts(asst_texts)

        sem_matrix = semantic_similarity_matrix(para_embeddings, asst_embeddings)
        lex_matrix = lexical_similarity_matrix(para_texts, asst_texts)

        # 6. Select evidence
        from app.services.retrieval.evidence_selector import select_evidence
        evidence_set = select_evidence(para_chunks, assistant_chunks, sem_matrix, lex_matrix)

        # 7. LLM analysis (3 passes)
        from app.services.analysis.prompt_intent_analyzer import analyze_prompt_intent
        try:
            intent_result = analyze_prompt_intent(parsed_chat.user_prompts)
        except Exception:
            logger.exception("Prompt intent analysis failed; using default")
            intent_result = PromptIntentResult()

        from app.services.analysis.transformation_analyzer import analyze_transformations
        try:
            transformation_result = analyze_transformations(evidence_set.pairs)
        except Exception:
            logger.exception("Transformation analysis failed; using default")
            transformation_result = TransformationAnalysisResult()

        from app.services.analysis.reliance_judge import judge_reliance
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
            reliance_judgment = RelianceJudgment()

        # 8. Score
        from app.services.scoring.score_builder import build_score
        scoring_result = build_score(
            intent=intent_result,
            transformation=transformation_result,
            judgment=reliance_judgment,
            coverage=evidence_set.coverage,
            total_turns=len(turn_chunks),
            total_prompts=len(parsed_chat.user_prompts),
        )

        # 9. Report
        from app.services.reporting.report_builder import build_report, generate_markdown
        report = build_report(
            scoring=scoring_result,
            intent=intent_result,
            transformation=transformation_result,
            judgment=reliance_judgment,
            evidence_set=evidence_set,
        )
        markdown_report = generate_markdown(report)

        # 10. Store results
        run.status = AnalysisStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        run.report_json = report.model_dump()
        run.report_markdown = markdown_report

        sub.status = SubmissionStatus.completed
        await db.flush()

        logger.info("Analysis completed for workspace %s: score=%d", workspace_id, report.reliance_score)

    except Exception as e:
        logger.exception("Analysis pipeline failed for workspace %s", workspace_id)
        run.status = AnalysisStatus.failed
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = str(e)
        sub.status = SubmissionStatus.failed
        await db.flush()
