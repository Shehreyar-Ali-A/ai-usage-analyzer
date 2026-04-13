"""Chat via OpenAI Responses API with optional file_search tool."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.services.openai.client import get_openai_client

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a helpful AI assistant for a student working on an assignment.
Help the student understand concepts, brainstorm ideas, review their work,
and provide guidance. Be educational and supportive. When you reference
information from uploaded files, mention the source clearly.
"""


async def generate_chat_response(
    messages: list[dict],
    vector_store_id: str | None = None,
) -> object:
    """Non-streaming response for backward compatibility."""
    settings = get_settings()
    client = get_openai_client()
    model = settings.openai_chat_model

    input_messages = [{"role": "developer", "content": _SYSTEM_PROMPT}]
    input_messages.extend(messages)

    tools = []
    if vector_store_id:
        tools.append({
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
        })

    kwargs = {"model": model, "input": input_messages}
    if tools:
        kwargs["tools"] = tools

    logger.info("Calling Responses API (model=%s, messages=%d, vector_store=%s)",
                model, len(messages), vector_store_id or "none")

    response = client.responses.create(**kwargs)
    return response


def stream_chat_response(
    messages: list[dict],
    vector_store_id: str | None = None,
):
    """Stream response tokens from the OpenAI Responses API.

    Yields (event_type, data) tuples. The caller iterates synchronously
    since the OpenAI SDK streaming is sync.
    """
    settings = get_settings()
    client = get_openai_client()
    model = settings.openai_chat_model

    input_messages = [{"role": "developer", "content": _SYSTEM_PROMPT}]
    input_messages.extend(messages)

    tools = []
    if vector_store_id:
        tools.append({
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
        })

    kwargs = {"model": model, "input": input_messages, "stream": True}
    if tools:
        kwargs["tools"] = tools

    logger.info("Streaming Responses API (model=%s, messages=%d, vector_store=%s)",
                model, len(messages), vector_store_id or "none")

    stream = client.responses.create(**kwargs)
    return stream
