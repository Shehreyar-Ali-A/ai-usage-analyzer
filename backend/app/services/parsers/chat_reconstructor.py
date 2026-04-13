"""Reconstruct a ParsedChat from DB message rows.

This is the key adapter that allows the existing analysis pipeline to operate
on workspace chats stored in the database rather than uploaded JSON files.
It combines messages from ALL chats in a workspace into a single ParsedChat.
"""

from __future__ import annotations

from typing import List

from app.db.models.message import Message
from app.services.analysis.models import ChatMessage, ChatTurn, ParsedChat


def reconstruct_parsed_chat(messages: List[Message]) -> ParsedChat:
    """Build a ParsedChat from a flat list of DB Message rows.

    Messages should already be ordered by chat creation time then sequence number.
    """
    chat_messages: List[ChatMessage] = []
    user_prompts: List[str] = []
    assistant_texts: List[str] = []

    for msg in messages:
        role_str = msg.role.value if hasattr(msg.role, "value") else msg.role
        if role_str in ("user", "assistant"):
            chat_messages.append(ChatMessage(
                role=role_str,
                content=msg.content_text,
                timestamp=msg.created_at.isoformat() if msg.created_at else None,
            ))
            if role_str == "user":
                user_prompts.append(msg.content_text)
            else:
                assistant_texts.append(msg.content_text)

    turns = _group_turns(chat_messages)

    return ParsedChat(
        messages=chat_messages,
        turns=turns,
        user_prompts=user_prompts,
        assistant_texts=assistant_texts,
    )


def _group_turns(messages: List[ChatMessage]) -> List[ChatTurn]:
    """Group consecutive user/assistant messages into turns."""
    turns: List[ChatTurn] = []
    turn_id = 0
    i = 0

    while i < len(messages):
        if messages[i].role == "user":
            user_message = messages[i].content
            timestamp = messages[i].timestamp
            i += 1
            assistant_messages: List[str] = []
            while i < len(messages) and messages[i].role == "assistant":
                assistant_messages.append(messages[i].content)
                i += 1
            turns.append(ChatTurn(
                turn_id=turn_id,
                user_message=user_message,
                assistant_messages=assistant_messages,
                timestamp=timestamp,
            ))
            turn_id += 1
        else:
            i += 1

    return turns
