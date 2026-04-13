"""LLM-based overall reliance judgment (Pass 3).

Uses the OpenAI Responses API with Structured Outputs.
"""

from __future__ import annotations

import json
import logging
from typing import List

from app.core.config import get_settings
from app.services.openai.client import get_openai_client
from app.services.analysis.models import (
    CoverageMetrics,
    EvidencePair,
    PromptIntentResult,
    RelianceJudgment,
    TransformationAnalysisResult,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an academic integrity analyst making a final judgment on how much a
student relied on AI to produce their assignment.

You will receive:
  - Prompt intent analysis results (categories, severity, profile)
  - Transformation analysis results (per-pair relation types and degrees)
  - Coverage metrics (what fraction of the assignment matches AI output)
  - A summary of the conversation size

Based on all evidence, determine:
1. reliance_band: "low", "moderate", or "high"
2. reliance_score_recommendation: 0 to 100 (0 = no reliance, 100 = fully AI-generated)
3. primary_reasons: up to 5 reasons supporting your judgment
4. counter_indicators: up to 3 factors that argue against higher/lower reliance
5. confidence: 0.0 to 1.0 in your judgment

Be fair and evidence-based. Consider counter-indicators seriously.
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "reliance_band": {"type": "string", "enum": ["low", "moderate", "high"]},
        "reliance_score_recommendation": {"type": "integer"},
        "primary_reasons": {"type": "array", "items": {"type": "string"}},
        "counter_indicators": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": [
        "reliance_band", "reliance_score_recommendation",
        "primary_reasons", "counter_indicators", "confidence",
    ],
    "additionalProperties": False,
}


def judge_reliance(
    intent_result: PromptIntentResult,
    transformation_result: TransformationAnalysisResult,
    coverage: CoverageMetrics,
    evidence_pairs: List[EvidencePair],
    total_turns: int,
    total_prompts: int,
) -> RelianceJudgment:
    settings = get_settings()
    client = get_openai_client()

    transformation_summary_parts: List[str] = []
    for pr in transformation_result.pair_results:
        transformation_summary_parts.append(
            f"  Pair {pr.pair_index}: {pr.relation_type} "
            f"(transformation={pr.transformation_degree:.2f})"
        )
    transformation_summary = "\n".join(transformation_summary_parts) or "  (no pairs analysed)"

    section_cov_str = ", ".join(
        f"{k}: {v:.0%}" for k, v in coverage.section_coverage.items()
    ) or "(no sections)"

    user_content = f"""\
=== Prompt Intent ===
Profile: {intent_result.overall_intent_profile}
Severity: {intent_result.severity_score:.2f}
Full-generation requests: {intent_result.full_assignment_generation_request.count}
Rewrite requests: {intent_result.rewrite_request.count}
Explanation requests: {intent_result.explanation_request.count}
Brainstorming requests: {intent_result.brainstorming_request.count}

=== Transformation Results ===
{transformation_summary}

=== Coverage Metrics ===
Assignment coverage ratio: {coverage.assignment_coverage_ratio:.2%}
Mean best semantic similarity: {coverage.mean_best_semantic:.3f}
Mean best lexical overlap: {coverage.mean_best_lexical:.3f}
Section coverage: {section_cov_str}

=== Conversation Size ===
Total turns: {total_turns}
Total user prompts: {total_prompts}
Evidence pairs found: {len(evidence_pairs)}
"""

    model = settings.openai_analysis_model
    logger.info("Judging overall reliance via %s", model)

    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "developer", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "reliance_judgment",
                    "schema": _RESPONSE_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw_json = response.output_text
        data = json.loads(raw_json)
        result = RelianceJudgment.model_validate(data)
        logger.info(
            "Reliance judgment: band=%s, score=%d, confidence=%.2f",
            result.reliance_band, result.reliance_score_recommendation, result.confidence,
        )
        return result
    except Exception:
        logger.exception("Reliance judgment failed; returning default.")
        return RelianceJudgment()
