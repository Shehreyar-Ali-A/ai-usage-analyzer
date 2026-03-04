from typing import Any, List, Optional, Tuple

from models import ChatMessage, NormalizedChat


def _normalize_role(raw_role: Any) -> Optional[str]:
    """
    Map various role labels into 'user' or 'assistant'.
    Returns None for roles we want to ignore.
    """
    if not isinstance(raw_role, str):
        return None

    r = raw_role.strip().lower()

    # Standard roles
    if r in ("user", "assistant"):
        return r

    # Common alternates
    if r in ("prompt", "human", "student"):
        return "user"
    if r in ("response", "reply", "ai", "assistant_bot", "model"):
        return "assistant"

    # Ignore anything else (system, metadata, etc.)
    return None


def _extract_content(item: dict) -> Optional[str]:
    """
    Extract message text from a variety of plausible shapes.
    Ignores metadata fields.
    """
    # Simple string fields
    for key in ("content", "say", "message", "text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # Some exports use { content: { type, text } } or arrays
    content = item.get("content")
    if isinstance(content, dict):
        # e.g. { "type": "text", "text": "..." }
        text_val = content.get("text")
        if isinstance(text_val, str) and text_val.strip():
            return text_val.strip()

    if isinstance(content, list):
        # e.g. [{ "type": "text", "text": "..." }, ...]
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


def normalize_chat_json(raw: Any) -> Tuple[NormalizedChat, List[str], List[str]]:
    """
    Normalize various plausible chat JSON formats into NormalizedChat.
    Returns NormalizedChat plus assistant texts and user prompts lists.
    """
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

        raw_role = item.get("role")
        role = _normalize_role(raw_role)
        if role is None:
            # Ignore system / metadata / unknown roles
            continue

        content = _extract_content(item)
        if content is None:
            continue

        timestamp = item.get("timestamp")

        msg = ChatMessage(role=role, content=content, timestamp=timestamp)
        messages.append(msg)

        if role == "assistant":
            assistant_texts.append(msg.content)
        elif role == "user":
            user_prompts.append(msg.content)

    if not messages:
        raise ValueError("No valid chat messages found after normalization.")

    return NormalizedChat(messages=messages), assistant_texts, user_prompts

