"""LLM-based transformation analysis (Pass 2).

For each evidence pair (assignment chunk matched to AI output chunk), the LLM
judges the nature of the relationship: direct copy, paraphrase, shared ideas,
or weak match.

Uses the OpenAI Responses API with Structured Outputs.
"""

from __future__ import annotations

import json
import logging
from typing import List

from openai import OpenAI

from config import get_settings
from models import EvidencePair, TransformationAnalysisResult

logger = logging.getLogger(__name__)

_MAX_PAIR_TEXT_CHARS = 800

_SYSTEM_PROMPT = """\
You are an academic integrity analyst. You will receive a list of evidence
pairs. Each pair contains:
  - An assignment excerpt (from the student's submitted work)
  - An AI output excerpt (from the student's AI conversation)
  - A semantic similarity score and a lexical similarity score

For each pair, determine:
1. relation_type: one of
   - "direct_copy": the assignment text is essentially identical to the AI output
   - "light_paraphrase": minor rewording with the same structure and meaning
   - "heavy_paraphrase": substantial rewording; same core ideas but different expression
   - "shared_ideas_only": overlapping concepts but clearly different writing
   - "weak_match": similarity is incidental or superficial
2. transformation_degree: 0.0 (no transformation, identical) to 1.0 (fully original)
3. reasoning: one sentence explaining your judgment

Be precise. Consider both semantic and lexical scores as context but make your
own judgment by reading the actual text.
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "pair_results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pair_index": {"type": "integer"},
                    "relation_type": {
                        "type": "string",
                        "enum": [
                            "direct_copy",
                            "light_paraphrase",
                            "heavy_paraphrase",
                            "shared_ideas_only",
                            "weak_match",
                        ],
                    },
                    "transformation_degree": {"type": "number"},
                    "reasoning": {"type": "string"},
                },
                "required": ["pair_index", "relation_type", "transformation_degree", "reasoning"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["pair_results"],
    "additionalProperties": False,
}


def analyze_transformations(pairs: List[EvidencePair]) -> TransformationAnalysisResult:
    """Classify each evidence pair via LLM and return transformation results."""
    if not pairs:
        logger.warning("No evidence pairs to analyze; returning empty result.")
        return TransformationAnalysisResult()

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    pair_descriptions: List[str] = []
    for i, pair in enumerate(pairs):
        a_text = pair.assignment_text[:_MAX_PAIR_TEXT_CHARS]
        b_text = pair.assistant_text[:_MAX_PAIR_TEXT_CHARS]
        pair_descriptions.append(
            f"--- Pair {i} ---\n"
            f"Assignment excerpt:\n{a_text}\n\n"
            f"AI output excerpt:\n{b_text}\n\n"
            f"Semantic score: {pair.semantic_score:.3f}\n"
            f"Lexical score: {pair.lexical_score:.3f}"
        )

    user_content = (
        f"Number of evidence pairs: {len(pairs)}\n\n"
        + "\n\n".join(pair_descriptions)
    )

    logger.info("Analyzing %d transformation pairs via %s", len(pairs), settings.llm_model)

    try:
        response = client.responses.create(
            model=settings.llm_model,
            input=[
                {"role": "developer", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "transformation_analysis_result",
                    "schema": _RESPONSE_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw_json = response.output_text
        data = json.loads(raw_json)
        result = TransformationAnalysisResult.model_validate(data)
        logger.info(
            "Transformation analysis complete: %d pair results",
            len(result.pair_results),
        )
        return result
    except Exception:
        logger.exception("Transformation analysis failed; returning empty result.")
        return TransformationAnalysisResult()
