"""Build the final ``Report`` from structured analysis outputs and generate
Markdown / PDF artefacts.

The report is assembled entirely from structured facts — the LLM is *not*
given free-form control over the narrative.
"""

from __future__ import annotations

import base64
import logging
from typing import List

import markdown as md

from models import (
    EvidenceItem,
    EvidenceSet,
    FactorBreakdown,
    PromptIntentResult,
    RelianceJudgment,
    Report,
    ScoringResult,
    TransformationAnalysisResult,
    TransformationPairResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def build_report(
    scoring: ScoringResult,
    intent: PromptIntentResult,
    transformation: TransformationAnalysisResult,
    judgment: RelianceJudgment,
    evidence_set: EvidenceSet,
) -> Report:
    """Construct a ``Report`` from all upstream structured outputs."""

    evidence_items = _build_evidence_items(evidence_set, transformation)

    usage_types = _derive_usage_types(intent)

    summary = _build_summary(scoring, intent, judgment)
    observations = _build_observations(scoring, intent, evidence_set, judgment)

    # Factor breakdown for the frontend
    factor_breakdown = [
        FactorBreakdown(
            name=f.name,
            weight=f.weight,
            score=round(f.raw_score, 3),
            explanation=f.explanation,
        )
        for f in scoring.factors
    ]

    # Increasing / decreasing factors
    increasing: List[str] = []
    decreasing: List[str] = []
    for reason in judgment.primary_reasons:
        increasing.append(reason)
    for counter in judgment.counter_indicators:
        decreasing.append(counter)

    # Caveats
    caveats: List[str] = []
    if scoring.confidence == "Low":
        caveats.append("Confidence in this assessment is low due to limited evidence.")
    if evidence_set.coverage.assignment_coverage_ratio < 0.1:
        caveats.append("Very few assignment sections matched AI output; the score may underestimate reliance.")
    if not transformation.pair_results:
        caveats.append("No evidence pairs were available for transformation analysis.")

    # Prompt intent summary
    profile = intent.overall_intent_profile.replace("_", " ")
    intent_summary = (
        f"The student's prompts are classified as {profile} "
        f"(severity {intent.severity_score:.2f}/1.0). "
    )
    if intent.full_assignment_generation_request.count:
        intent_summary += (
            f"{intent.full_assignment_generation_request.count} prompt(s) requested "
            f"full assignment generation. "
        )
    if intent.explanation_request.count:
        intent_summary += (
            f"{intent.explanation_request.count} prompt(s) were explanation/tutoring requests."
        )

    # Transformation findings
    transformation_findings = _build_transformation_findings(transformation)

    return Report(
        summary=summary,
        reliance_score=scoring.final_score,
        reliance_label=scoring.label,
        usage_type=usage_types,
        evidence=evidence_items,
        observations=observations,
        confidence=scoring.confidence,
        prompt_intent_summary=intent_summary,
        transformation_findings=transformation_findings,
        factor_breakdown=factor_breakdown,
        increasing_factors=increasing,
        decreasing_factors=decreasing,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_markdown(report: Report) -> str:
    lines: List[str] = []
    lines.append("# AI Usage Report\n")

    lines.append("## Overview\n")
    lines.append(report.summary + "\n")

    lines.append("## Reliance Score\n")
    lines.append(f"- **Score:** {report.reliance_score} / 100 ({report.reliance_label})")
    lines.append(f"- **Confidence:** {report.confidence}\n")

    if report.factor_breakdown:
        lines.append("## Factor Breakdown\n")
        lines.append("| Factor | Weight | Score | Explanation |")
        lines.append("|--------|--------|-------|-------------|")
        for fb in report.factor_breakdown:
            lines.append(
                f"| {fb.name} | {fb.weight:.0%} | {fb.score:.2f} | {fb.explanation} |"
            )
        lines.append("")

    if report.prompt_intent_summary:
        lines.append("## Prompt Intent\n")
        lines.append(report.prompt_intent_summary + "\n")

    if report.usage_type:
        lines.append("## AI Usage Classification\n")
        for ut in report.usage_type:
            lines.append(f"- {ut}")
        lines.append("")

    if report.evidence:
        lines.append("## Evidence Matches\n")
        for idx, ev in enumerate(report.evidence, start=1):
            lines.append(f"### Match {idx}\n")
            sim_pct = int(ev.similarity * 100)
            lines.append(f"- **Similarity:** {sim_pct}% (semantic {ev.semantic_score:.2f}, lexical {ev.lexical_score:.2f})")
            if ev.relation_type:
                lines.append(f"- **Relation:** {ev.relation_type.replace('_', ' ')}")
            lines.append("")
            lines.append("**Assignment Excerpt**\n")
            lines.append("> " + ev.assignment_excerpt.replace("\n", " ") + "\n")
            lines.append("**AI Excerpt**\n")
            lines.append("> " + ev.ai_excerpt.replace("\n", " ") + "\n")
    else:
        lines.append("## Evidence Matches\n")
        lines.append("No strong similarity matches were detected between assignment and AI responses.\n")

    if report.transformation_findings:
        lines.append("## Transformation Findings\n")
        for tf in report.transformation_findings:
            lines.append(f"- {tf}")
        lines.append("")

    if report.increasing_factors:
        lines.append("## Factors Increasing Score\n")
        for f in report.increasing_factors:
            lines.append(f"- {f}")
        lines.append("")

    if report.decreasing_factors:
        lines.append("## Factors Decreasing Score\n")
        for f in report.decreasing_factors:
            lines.append(f"- {f}")
        lines.append("")

    if report.observations:
        lines.append("## Observations\n")
        for obs in report.observations:
            lines.append(f"- {obs}")
        lines.append("")

    if report.caveats:
        lines.append("## Caveats\n")
        for c in report.caveats:
            lines.append(f"- {c}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PDF generation (lazy import)
# ---------------------------------------------------------------------------

def generate_pdf_from_markdown(markdown_text: str) -> bytes:
    try:
        from weasyprint import HTML  # type: ignore[import]
    except Exception as exc:
        raise RuntimeError(
            "PDF generation is not available in this environment. "
            "Set AI_ANALYZER_ENABLE_PDF_OUTPUT=false or install WeasyPrint system dependencies."
        ) from exc
    html = md.markdown(markdown_text, output_format="html5")
    return HTML(string=html).write_pdf()


def encode_pdf_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("ascii")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_evidence_items(
    evidence_set: EvidenceSet,
    transformation: TransformationAnalysisResult,
) -> List[EvidenceItem]:
    pair_result_map: dict[int, TransformationPairResult] = {
        pr.pair_index: pr for pr in transformation.pair_results
    }
    items: List[EvidenceItem] = []
    for i, pair in enumerate(evidence_set.pairs):
        tr = pair_result_map.get(i)
        combined = max(pair.semantic_score, pair.lexical_score)
        items.append(EvidenceItem(
            ai_excerpt=pair.assistant_text,
            assignment_excerpt=pair.assignment_text,
            similarity=round(combined, 3),
            semantic_score=round(pair.semantic_score, 3),
            lexical_score=round(pair.lexical_score, 3),
            relation_type=tr.relation_type if tr else None,
        ))
    return items


def _derive_usage_types(intent: PromptIntentResult) -> List[str]:
    types: List[str] = []
    if intent.full_assignment_generation_request.count > 0:
        types.append("Direct Generation")
    if intent.rewrite_request.count > 0:
        types.append("Rewriting")
    if intent.explanation_request.count > 0 or intent.debugging_request.count > 0:
        types.append("Tutoring")
    if intent.brainstorming_request.count > 0 or intent.outline_request.count > 0:
        types.append("Ideation")
    if intent.direct_answer_request.count > 0:
        types.append("Direct Answers")
    return types


def _build_summary(
    scoring: ScoringResult,
    intent: PromptIntentResult,
    judgment: RelianceJudgment,
) -> str:
    label = scoring.label
    if label == "High":
        return (
            "The assignment shows high reliance on AI. Significant portions of the "
            "submitted work closely match AI-generated content, and prompt patterns "
            "indicate substantial outsourcing of the writing task."
        )
    if label == "Moderate":
        return (
            "The assignment demonstrates moderate AI reliance. AI appears to have "
            "influenced parts of the work, but there is evidence of student "
            "contribution and transformation of AI material."
        )
    return (
        "The assignment indicates low AI reliance. The student appears to have "
        "used AI primarily for learning support, and the submitted work shows "
        "limited direct reuse of AI-generated content."
    )


def _build_observations(
    scoring: ScoringResult,
    intent: PromptIntentResult,
    evidence_set: EvidenceSet,
    judgment: RelianceJudgment,
) -> List[str]:
    obs: List[str] = []
    cov = evidence_set.coverage.assignment_coverage_ratio
    if cov > 0.5:
        obs.append(f"{cov:.0%} of the assignment has strong AI content matches.")
    if intent.full_assignment_generation_request.count > 0:
        obs.append("User prompts include requests for full solution or essay generation.")
    if intent.rewrite_request.count > 0:
        obs.append("User requested rewriting or polishing of existing text.")
    if intent.overall_intent_profile == "learning_focused":
        obs.append("AI usage appears primarily learning-focused based on prompt analysis.")
    if not obs:
        obs.append("AI usage appears primarily supportive or exploratory based on available evidence.")
    return obs


def _build_transformation_findings(
    transformation: TransformationAnalysisResult,
) -> List[str]:
    if not transformation.pair_results:
        return []
    findings: List[str] = []
    type_counts: dict[str, int] = {}
    for pr in transformation.pair_results:
        type_counts[pr.relation_type] = type_counts.get(pr.relation_type, 0) + 1
    for rtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        label = rtype.replace("_", " ")
        findings.append(f"{count} evidence pair(s) classified as {label}.")
    # Include up to 3 specific reasonings
    for pr in transformation.pair_results[:3]:
        if pr.reasoning:
            findings.append(f"Pair {pr.pair_index}: {pr.reasoning}")
    return findings
