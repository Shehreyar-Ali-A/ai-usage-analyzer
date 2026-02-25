import base64
from typing import List, Sequence, Tuple

import markdown as md

from models import EvidenceItem, Report


def build_report(
    summary: str,
    reliance_score: int,
    reliance_label: str,
    usage_types: List[str],
    evidence: Sequence[Tuple[dict, dict, float]],
    observations: List[str],
    confidence: str,
) -> Report:
    evidence_items: List[EvidenceItem] = []
    for assignment_chunk, ai_chunk, score in evidence:
        evidence_items.append(
            EvidenceItem(
                ai_excerpt=ai_chunk["text"],
                assignment_excerpt=assignment_chunk["text"],
                similarity=round(float(score), 3),
            )
        )

    return Report(
        summary=summary,
        reliance_score=reliance_score,
        reliance_label=reliance_label,  # type: ignore[arg-type]
        usage_type=usage_types,
        evidence=evidence_items,
        observations=observations,
        confidence=confidence,  # type: ignore[arg-type]
    )


def generate_markdown(report: Report) -> str:
    lines: List[str] = []
    lines.append("# AI Usage Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(report.summary)
    lines.append("")
    lines.append("## Reliance Score")
    lines.append("")
    lines.append(f"- Score: **{report.reliance_score}** ({report.reliance_label})")
    lines.append("")
    lines.append("## AI Usage Classification")
    lines.append("")
    if report.usage_type:
        for ut in report.usage_type:
            lines.append(f"- {ut}")
    else:
        lines.append("- Not clearly classified")
    lines.append("")
    lines.append("## Evidence Matches")
    lines.append("")
    if report.evidence:
        for idx, ev in enumerate(report.evidence, start=1):
            lines.append(f"### Match {idx}")
            lines.append("")
            lines.append(f"- Similarity: **{int(ev.similarity * 100)}%**")
            lines.append("")
            lines.append("**Assignment Excerpt**")
            lines.append("")
            # Avoid backslashes inside f-string expressions (not allowed); use concatenation instead.
            lines.append("> " + ev.assignment_excerpt.replace("\n", " "))
            lines.append("")
            lines.append("**AI Excerpt**")
            lines.append("")
            lines.append("> " + ev.ai_excerpt.replace("\n", " "))
            lines.append("")
    else:
        lines.append("No strong similarity matches were detected between assignment and AI responses.")
        lines.append("")

    lines.append("## Observations")
    lines.append("")
    if report.observations:
        for obs in report.observations:
            lines.append(f"- {obs}")
    else:
        lines.append("- No additional observations.")
    lines.append("")

    lines.append("## Confidence Level")
    lines.append("")
    lines.append(f"- {report.confidence}")
    lines.append("")

    return "\n".join(lines)


def generate_pdf_from_markdown(markdown_text: str) -> bytes:
    """
    Convert Markdown to PDF bytes using WeasyPrint via HTML.

    This import is done lazily so that environments without WeasyPrint's
    system dependencies can still run the app as long as PDF output
    remains disabled.
    """
    try:
        from weasyprint import HTML  # type: ignore[import]
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "PDF generation is not available in this environment. "
            "Set AI_ANALYZER_ENABLE_PDF_OUTPUT=false or install WeasyPrint system dependencies."
        ) from exc

    html = md.markdown(markdown_text, output_format="html5")
    html_document = HTML(string=html)
    return html_document.write_pdf()


def encode_pdf_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("ascii")

