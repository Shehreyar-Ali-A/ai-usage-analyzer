from typing import Any, List, Tuple

from models import ChatMessage, NormalizedChat


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
        role = item.get("role")
        content = item.get("content")
        timestamp = item.get("timestamp")

        if role not in ("user", "assistant"):
            continue
        if not isinstance(content, str) or not content.strip():
            continue

        msg = ChatMessage(role=role, content=content.strip(), timestamp=timestamp)
        messages.append(msg)

        if role == "assistant":
            assistant_texts.append(msg.content)
        elif role == "user":
            user_prompts.append(msg.content)

    if not messages:
        raise ValueError("No valid chat messages found after normalization.")

    return NormalizedChat(messages=messages), assistant_texts, user_prompts

