"""Normalise chat JSON exports into structured form with turn grouping.

Keeps the flexible role/content extraction from the original
``chat_normalization`` module and adds ``ChatTurn`` grouping so that
each user prompt is associated with the assistant response(s) that
followed it.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from models import ChatMessage, ChatTurn, ParsedChat

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Role mapping
# ---------------------------------------------------------------------------

def _normalize_role(raw_role: Any) -> Optional[str]:
    if not isinstance(raw_role, str):
        return None
    r = raw_role.strip().lower()
    if r in ("user", "assistant"):
        return r
    if r in ("prompt", "human", "student"):
        return "user"
    if r in ("response", "reply", "ai", "assistant_bot", "model"):
        return "assistant"
    return None


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

def _extract_content(item: dict) -> Optional[str]:
    for key in ("content", "say", "message", "text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    content = item.get("content")
    if isinstance(content, dict):
        text_val = content.get("text")
        if isinstance(text_val, str) and text_val.strip():
            return text_val.strip()

    if isinstance(content, list):
        texts: List[str] = []
        for part in content:
            if isinstance(part, str) and part.strip():
                texts.append(part.strip())
            elif isinstance(part, dict):
                t = part.get("text")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())
        if texts:
            return "\n\n".join(texts)

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_chat(raw: Any) -> ParsedChat:
    """Normalise chat JSON and group into turns."""

    if isinstance(raw, dict) and "messages" in raw:
        messages_raw = raw["messages"]
    elif isinstance(raw, list):
        messages_raw = raw
    else:
        raise ValueError("Chat JSON must be a list or an object with a 'messages' array.")

    if not isinstance(messages_raw, list):
        raise ValueError("'messages' must be an array.")

    messages: List[ChatMessage] = []
    assistant_texts: List[str] = []
    user_prompts: List[str] = []

    for item in messages_raw:
        if not isinstance(item, dict):
            continue
        role = _normalize_role(item.get("role"))
        if role is None:
            continue
        content = _extract_content(item)
        if content is None:
            continue

        timestamp = item.get("timestamp")
        msg = ChatMessage(role=role, content=content, timestamp=timestamp)
        messages.append(msg)
        if role == "assistant":
            assistant_texts.append(content)
        else:
            user_prompts.append(content)

    if not messages:
        raise ValueError("No valid chat messages found after normalization.")

    turns = _group_turns(messages)
    logger.info(
        "Parsed chat: %d messages, %d turns, %d user prompts",
        len(messages), len(turns), len(user_prompts),
    )

    return ParsedChat(
        messages=messages,
        turns=turns,
        user_prompts=user_prompts,
        assistant_texts=assistant_texts,
    )


def _group_turns(messages: List[ChatMessage]) -> List[ChatTurn]:
    """Group sequential messages into user-initiated turns."""
    turns: List[ChatTurn] = []
    turn_id = 0
    current_user_msg: Optional[str] = None
    current_assistant_msgs: List[str] = []
    current_ts: Optional[str] = None

    def flush() -> None:
        nonlocal turn_id, current_user_msg, current_assistant_msgs, current_ts
        if current_user_msg is not None:
            turns.append(ChatTurn(
                turn_id=turn_id,
                user_message=current_user_msg,
                assistant_messages=current_assistant_msgs,
                timestamp=current_ts,
            ))
            turn_id += 1
        elif current_assistant_msgs:
            # Orphan assistant messages at the start (no preceding user msg)
            turns.append(ChatTurn(
                turn_id=turn_id,
                user_message="",
                assistant_messages=current_assistant_msgs,
                timestamp=current_ts,
            ))
            turn_id += 1
        current_user_msg = None
        current_assistant_msgs = []
        current_ts = None

    for msg in messages:
        if msg.role == "user":
            flush()
            current_user_msg = msg.content
            current_ts = msg.timestamp
        else:
            current_assistant_msgs.append(msg.content)

    flush()
    return turns
