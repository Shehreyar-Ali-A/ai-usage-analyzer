"""LLM-based prompt intent analysis (Pass 1).

Uses the OpenAI Responses API with Structured Outputs.
"""

from __future__ import annotations

import json
import logging
from typing import List

from app.core.config import get_settings
from app.services.openai.client import get_openai_client
from app.services.analysis.models import PromptIntentResult

logger = logging.getLogger(__name__)

_MAX_PROMPTS_INLINE = 25
_MAX_PROMPT_CHARS = 500

_SYSTEM_PROMPT = """\
You are an academic integrity analyst. You will receive a list of user prompts
from a student's conversation with an AI assistant. Your task is to classify
the overall intent profile of these prompts.

For each intent category, estimate the count of prompts that fall into it and
your confidence (0-1) that those prompts genuinely belong there.

Categories:
- explanation_request: asking to explain a concept, clarify an idea, or teach
- brainstorming_request: asking for ideas, brainstorming, or creative suggestions
- outline_request: asking for an outline, structure, or plan
- rewrite_request: asking to rewrite, rephrase, polish, or improve existing text
- debugging_request: asking to debug code, fix errors, or troubleshoot
- direct_answer_request: asking for a direct answer to a question (short answers)
- full_assignment_generation_request: asking the AI to write an essay, generate
  a complete solution, or produce a full assignment deliverable

Determine the overall_intent_profile:
- "learning_focused": mostly explanation, brainstorming, debugging
- "outsourcing_focused": mostly full generation, rewriting, direct answers for
  substantial portions
- "mixed": a blend of both

Provide a severity_score (0.0 to 1.0) where:
- 0.0 = purely learning/tutoring use
- 1.0 = purely outsourcing/generation use

Include up to 5 notable prompt examples that best illustrate the intent profile.
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation_request": {
            "type": "object",
            "properties": {"count": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["count", "confidence"],
            "additionalProperties": False,
        },
        "brainstorming_request": {
            "type": "object",
            "properties": {"count": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["count", "confidence"],
            "additionalProperties": False,
        },
        "outline_request": {
            "type": "object",
            "properties": {"count": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["count", "confidence"],
            "additionalProperties": False,
        },
        "rewrite_request": {
            "type": "object",
            "properties": {"count": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["count", "confidence"],
            "additionalProperties": False,
        },
        "debugging_request": {
            "type": "object",
            "properties": {"count": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["count", "confidence"],
            "additionalProperties": False,
        },
        "direct_answer_request": {
            "type": "object",
            "properties": {"count": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["count", "confidence"],
            "additionalProperties": False,
        },
        "full_assignment_generation_request": {
            "type": "object",
            "properties": {"count": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["count", "confidence"],
            "additionalProperties": False,
        },
        "overall_intent_profile": {
            "type": "string",
            "enum": ["learning_focused", "outsourcing_focused", "mixed"],
        },
        "notable_prompt_examples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prompt_excerpt": {"type": "string"},
                    "classified_intent": {"type": "string"},
                },
                "required": ["prompt_excerpt", "classified_intent"],
                "additionalProperties": False,
            },
        },
        "severity_score": {"type": "number"},
    },
    "required": [
        "explanation_request", "brainstorming_request", "outline_request",
        "rewrite_request", "debugging_request", "direct_answer_request",
        "full_assignment_generation_request", "overall_intent_profile",
        "notable_prompt_examples", "severity_score",
    ],
    "additionalProperties": False,
}


def analyze_prompt_intent(user_prompts: List[str]) -> PromptIntentResult:
    if not user_prompts:
        logger.warning("No user prompts to analyze; returning default result.")
        return PromptIntentResult()

    settings = get_settings()
    client = get_openai_client()

    display_prompts = user_prompts[:_MAX_PROMPTS_INLINE]
    prompt_list = "\n".join(
        f"{i + 1}. {p[:_MAX_PROMPT_CHARS]}"
        for i, p in enumerate(display_prompts)
    )
    if len(user_prompts) > _MAX_PROMPTS_INLINE:
        prompt_list += f"\n... ({len(user_prompts) - _MAX_PROMPTS_INLINE} more prompts omitted)"

    user_content = (
        f"Total prompts in conversation: {len(user_prompts)}\n\n"
        f"User prompts:\n{prompt_list}"
    )

    model = settings.openai_analysis_model
    logger.info("Analyzing prompt intent for %d prompts via %s", len(user_prompts), model)

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
                    "name": "prompt_intent_result",
                    "schema": _RESPONSE_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw_json = response.output_text
        data = json.loads(raw_json)
        result = PromptIntentResult.model_validate(data)
        logger.info("Prompt intent: profile=%s, severity=%.2f", result.overall_intent_profile, result.severity_score)
        return result
    except Exception:
        logger.exception("Prompt intent analysis failed; returning default result.")
        return PromptIntentResult()
