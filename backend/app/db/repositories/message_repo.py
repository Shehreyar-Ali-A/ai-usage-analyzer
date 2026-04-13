from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message, MessageRole


async def get_next_sequence_number(db: AsyncSession, chat_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(Message.sequence_number), 0))
        .where(Message.chat_id == chat_id)
    )
    return result.scalar_one() + 1


async def create_message(
    db: AsyncSession,
    chat_id: uuid.UUID,
    role: MessageRole,
    content_text: str,
    sequence_number: int,
    openai_response_id: str | None = None,
    metadata_jsonb: dict | None = None,
) -> Message:
    msg = Message(
        chat_id=chat_id,
        role=role,
        content_text=content_text,
        sequence_number=sequence_number,
        openai_response_id=openai_response_id,
        metadata_jsonb=metadata_jsonb,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def list_messages(db: AsyncSession, chat_id: uuid.UUID) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id, Message.deleted_at.is_(None))
        .order_by(Message.sequence_number)
    )
    return list(result.scalars().all())


async def get_all_workspace_messages(db: AsyncSession, workspace_id: uuid.UUID) -> list[Message]:
    """Get all messages across all chats in a workspace, ordered by chat then sequence."""
    from app.db.models.chat import Chat

    result = await db.execute(
        select(Message)
        .join(Chat, Chat.id == Message.chat_id)
        .where(
            Chat.workspace_id == workspace_id,
            Chat.deleted_at.is_(None),
            Message.deleted_at.is_(None),
        )
        .order_by(Chat.created_at, Message.sequence_number)
    )
    return list(result.scalars().all())
