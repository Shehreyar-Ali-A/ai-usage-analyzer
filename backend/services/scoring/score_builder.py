"""Multi-factor structured scoring.

Builds a composite 0-100 reliance score from six explicit factors,
each producing a 0-1 sub-score with an explanation. The final score
is a weighted sum clamped to [0, 100].
"""

from __future__ import annotations

import logging
from typing import List

from models import (
    CoverageMetrics,
    PromptIntentResult,
    RelianceJudgment,
    ScoringFactor,
    ScoringResult,
    TransformationAnalysisResult,
)

logger = logging.getLogger(__name__)

# Factor weights — must sum to 1.0
_W_PROMPT_SEVERITY = 0.20
_W_COVERAGE = 0.25
_W_TRANSFORMATION = 0.20
_W_AUTHORSHIP = 0.15
_W_STRUCTURAL = 0.10
_W_LLM_RECOMMENDATION = 0.10


def build_score(
    intent: PromptIntentResult,
    transformation: TransformationAnalysisResult,
    judgment: RelianceJudgment,
    coverage: CoverageMetrics,
    total_turns: int,
    total_prompts: int,
) -> ScoringResult:
    """Compute the final structured reliance score."""
    factors: List[ScoringFactor] = []

    # 1. Prompt severity / outsourcing intent --------------------------------
    prompt_raw = intent.severity_score
    factors.append(ScoringFactor(
        name="Prompt severity",
        weight=_W_PROMPT_SEVERITY,
        raw_score=_clamp(prompt_raw),
        weighted_score=round(_W_PROMPT_SEVERITY * _clamp(prompt_raw), 4),
        explanation=_prompt_severity_explanation(intent),
    ))

    # 2. AI reuse coverage ---------------------------------------------------
    cov_raw = coverage.assignment_coverage_ratio
    factors.append(ScoringFactor(
        name="AI reuse coverage",
        weight=_W_COVERAGE,
        raw_score=_clamp(cov_raw),
        weighted_score=round(_W_COVERAGE * _clamp(cov_raw), 4),
        explanation=(
            f"{cov_raw:.0%} of assignment paragraphs have a strong semantic "
            f"match to AI output (mean best similarity {coverage.mean_best_semantic:.2f})."
        ),
    ))

    # 3. Transformation quality (inverted — low transformation = high score) -
    avg_transform = _avg_transformation_degree(transformation)
    transform_raw = 1.0 - avg_transform  # less transformation → higher risk
    factors.append(ScoringFactor(
        name="Transformation quality",
        weight=_W_TRANSFORMATION,
        raw_score=_clamp(transform_raw),
        weighted_score=round(_W_TRANSFORMATION * _clamp(transform_raw), 4),
        explanation=_transformation_explanation(transformation, avg_transform),
    ))

    # 4. Student authorship indicators (reduces score) -----------------------
    authorship_raw = _authorship_score(intent, total_turns, total_prompts)
    # Inverted: higher authorship signal → lower risk contribution
    authorship_for_weighted = 1.0 - authorship_raw
    factors.append(ScoringFactor(
        name="Student authorship indicators",
        weight=_W_AUTHORSHIP,
        raw_score=_clamp(authorship_for_weighted),
        weighted_score=round(_W_AUTHORSHIP * _clamp(authorship_for_weighted), 4),
        explanation=_authorship_explanation(intent, total_turns),
    ))

    # 5. Structural dependence -----------------------------------------------
    struct_raw = _structural_dependence(coverage)
    factors.append(ScoringFactor(
        name="Structural dependence",
        weight=_W_STRUCTURAL,
        raw_score=_clamp(struct_raw),
        weighted_score=round(_W_STRUCTURAL * _clamp(struct_raw), 4),
        explanation=(
            f"Section-level coverage pattern suggests "
            f"{'high' if struct_raw > 0.6 else 'moderate' if struct_raw > 0.3 else 'low'} "
            f"structural dependence on AI output."
        ),
    ))

    # 6. LLM reliance recommendation ----------------------------------------
    llm_raw = judgment.reliance_score_recommendation / 100.0
    factors.append(ScoringFactor(
        name="LLM reliance recommendation",
        weight=_W_LLM_RECOMMENDATION,
        raw_score=_clamp(llm_raw),
        weighted_score=round(_W_LLM_RECOMMENDATION * _clamp(llm_raw), 4),
        explanation=(
            f"LLM judged reliance as '{judgment.reliance_band}' with "
            f"recommendation {judgment.reliance_score_recommendation}/100 "
            f"(confidence {judgment.confidence:.2f})."
        ),
    ))

    # Composite score --------------------------------------------------------
    raw_total = sum(f.weighted_score for f in factors)
    final_score = int(round(_clamp(raw_total) * 100))

    if final_score <= 30:
        label = "Low"
    elif final_score <= 60:
        label = "Moderate"
    else:
        label = "High"

    # Confidence adjustment
    confidence = _compute_confidence(coverage, transformation, judgment)

    result = ScoringResult(
        final_score=final_score,
        label=label,
        factors=factors,
        confidence=confidence,
    )
    logger.info("Score built: %d (%s), confidence=%s", final_score, label, confidence)
    return result


# ---------------------------------------------------------------------------
# Sub-score helpers
# ---------------------------------------------------------------------------

def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _avg_transformation_degree(t: TransformationAnalysisResult) -> float:
    if not t.pair_results:
        return 1.0  # no evidence → assume original work
    return sum(pr.transformation_degree for pr in t.pair_results) / len(t.pair_results)


def _authorship_score(intent: PromptIntentResult, turns: int, prompts: int) -> float:
    """Higher value = more student authorship signals."""
    signals = 0.0
    # Iterative refinement: many turns suggest engagement
    if turns >= 8:
        signals += 0.3
    elif turns >= 4:
        signals += 0.15
    # Explanation/tutoring focus
    if intent.overall_intent_profile == "learning_focused":
        signals += 0.4
    elif intent.overall_intent_profile == "mixed":
        signals += 0.15
    # High ratio of explanation requests
    total_cats = (
        intent.explanation_request.count
        + intent.brainstorming_request.count
        + intent.debugging_request.count
    )
    if prompts > 0 and total_cats / max(prompts, 1) > 0.5:
        signals += 0.3
    return _clamp(signals)


def _structural_dependence(coverage: CoverageMetrics) -> float:
    """Estimate structural dependence from section coverage uniformity."""
    if not coverage.section_coverage:
        return coverage.assignment_coverage_ratio
    values = list(coverage.section_coverage.values())
    high_cov_sections = sum(1 for v in values if v > 0.5)
    ratio = high_cov_sections / len(values) if values else 0.0
    return _clamp(ratio)


# ---------------------------------------------------------------------------
# Explanation helpers
# ---------------------------------------------------------------------------

def _prompt_severity_explanation(intent: PromptIntentResult) -> str:
    profile = intent.overall_intent_profile.replace("_", "-")
    gen_count = intent.full_assignment_generation_request.count
    rewrite_count = intent.rewrite_request.count
    parts = [f"Intent profile is {profile} (severity {intent.severity_score:.2f})."]
    if gen_count:
        parts.append(f"{gen_count} full-generation request(s) detected.")
    if rewrite_count:
        parts.append(f"{rewrite_count} rewrite request(s) detected.")
    return " ".join(parts)


def _transformation_explanation(t: TransformationAnalysisResult, avg: float) -> str:
    if not t.pair_results:
        return "No evidence pairs were analyzed for transformation."
    type_counts: dict[str, int] = {}
    for pr in t.pair_results:
        type_counts[pr.relation_type] = type_counts.get(pr.relation_type, 0) + 1
    breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1]))
    return (
        f"Average transformation degree {avg:.2f} across {len(t.pair_results)} pairs. "
        f"Relation types: {breakdown}."
    )


def _authorship_explanation(intent: PromptIntentResult, turns: int) -> str:
    parts: list[str] = []
    if intent.overall_intent_profile == "learning_focused":
        parts.append("Prompts are primarily learning-focused.")
    if turns >= 8:
        parts.append(f"Conversation has {turns} turns, suggesting iterative engagement.")
    if intent.explanation_request.count > 0:
        parts.append(f"{intent.explanation_request.count} explanation request(s) detected.")
    if not parts:
        parts.append("Limited authorship indicators found.")
    return " ".join(parts)


def _compute_confidence(
    coverage: CoverageMetrics,
    transformation: TransformationAnalysisResult,
    judgment: RelianceJudgment,
) -> str:
    score = judgment.confidence
    # Reduce confidence if very few evidence pairs
    if len(transformation.pair_results) < 3:
        score -= 0.2
    # Reduce confidence if coverage is very low (sparse evidence)
    if coverage.assignment_coverage_ratio < 0.1:
        score -= 0.15
    if score >= 0.7:
        return "High"
    if score >= 0.4:
        return "Medium"
    return "Low"
