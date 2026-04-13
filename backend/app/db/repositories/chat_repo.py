from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.chat import Chat
from app.db.models.message import Message


async def create_chat(db: AsyncSession, workspace_id: uuid.UUID, title: str = "New Chat") -> Chat:
    chat = Chat(workspace_id=workspace_id, title=title)
    db.add(chat)
    await db.flush()
    await db.refresh(chat)
    return chat


async def list_chats(db: AsyncSession, workspace_id: uuid.UUID) -> list[Chat]:
    result = await db.execute(
        select(Chat)
        .where(Chat.workspace_id == workspace_id, Chat.deleted_at.is_(None))
        .order_by(Chat.created_at.desc())
    )
    return list(result.scalars().all())


async def get_chat(db: AsyncSession, chat_id: uuid.UUID) -> Chat | None:
    result = await db.execute(
        select(Chat)
        .options(selectinload(Chat.messages))
        .where(Chat.id == chat_id, Chat.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def update_chat(db: AsyncSession, chat: Chat, **kwargs) -> Chat:
    for key, value in kwargs.items():
        if value is not None:
            setattr(chat, key, value)
    chat.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(chat)
    return chat


async def soft_delete_chat(db: AsyncSession, chat: Chat) -> None:
    chat.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def get_message_count(db: AsyncSession, chat_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Message)
        .where(Message.chat_id == chat_id, Message.deleted_at.is_(None))
    )
    return result.scalar_one()
