from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.repositories import chat_repo, message_repo, workspace_repo
from app.db.models.message import MessageRole
from app.db.schemas.chat import ChatCreate, ChatListResponse, ChatResponse, ChatUpdate
from app.db.schemas.message import ChatWithMessagesResponse, MessageCreate, MessageResponse

router = APIRouter()


@router.post("/workspaces/{workspace_id}/chats", response_model=ChatResponse, status_code=201)
async def create_chat(
    workspace_id: uuid.UUID,
    body: ChatCreate,
    db: AsyncSession = Depends(get_session),
):
    ws = await workspace_repo.get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    title = body.title or "New Chat"
    chat = await chat_repo.create_chat(db, workspace_id=workspace_id, title=title)
    return ChatResponse(
        id=chat.id,
        workspace_id=chat.workspace_id,
        title=chat.title,
        message_count=0,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.get("/workspaces/{workspace_id}/chats", response_model=ChatListResponse)
async def list_chats(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    chats = await chat_repo.list_chats(db, workspace_id)
    items = []
    for c in chats:
        mc = await chat_repo.get_message_count(db, c.id)
        items.append(ChatResponse(
            id=c.id,
            workspace_id=c.workspace_id,
            title=c.title,
            message_count=mc,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))
    return ChatListResponse(chats=items)


@router.get("/chats/{chat_id}", response_model=ChatWithMessagesResponse)
async def get_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    chat = await chat_repo.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = await message_repo.list_messages(db, chat_id)
    return ChatWithMessagesResponse(
        id=chat.id,
        workspace_id=chat.workspace_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.patch("/chats/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: uuid.UUID,
    body: ChatUpdate,
    db: AsyncSession = Depends(get_session),
):
    chat = await chat_repo.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat = await chat_repo.update_chat(db, chat, title=body.title)
    mc = await chat_repo.get_message_count(db, chat.id)
    return ChatResponse(
        id=chat.id,
        workspace_id=chat.workspace_id,
        title=chat.title,
        message_count=mc,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.delete("/chats/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    chat = await chat_repo.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    await chat_repo.soft_delete_chat(db, chat)


def _sse_event(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_session),
):
    chat = await chat_repo.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    ws = await workspace_repo.get_workspace(db, chat.workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if ws.status.value == "submitted":
        raise HTTPException(status_code=400, detail="Workspace is submitted; no new messages allowed")

    seq = await message_repo.get_next_sequence_number(db, chat_id)
    user_msg = await message_repo.create_message(
        db,
        chat_id=chat_id,
        role=MessageRole.user,
        content_text=body.content,
        sequence_number=seq,
    )

    if seq == 1:
        auto_title = body.content[:80].strip()
        if len(body.content) > 80:
            auto_title += "..."
        await chat_repo.update_chat(db, chat, title=auto_title)

    messages = await message_repo.list_messages(db, chat_id)
    conversation = [
        {"role": m.role.value if hasattr(m.role, "value") else m.role, "content": m.content_text}
        for m in messages
    ]

    user_msg_data = MessageResponse.model_validate(user_msg).model_dump(mode="json")

    # Capture DB session-scoped values we need after the generator outlives the request DI scope
    _chat_id = chat_id
    _seq = seq
    _vector_store_id = ws.openai_vector_store_id

    async def event_stream():
        from app.services.openai.responses_service import stream_chat_response
        from app.db.base import async_session_factory

        yield _sse_event("user_message", user_msg_data)

        full_text = ""
        response_id = None
        error_text = None

        try:
            stream = stream_chat_response(
                messages=conversation,
                vector_store_id=_vector_store_id,
            )
            for event in stream:
                if event.type == "response.output_text.delta":
                    full_text += event.delta
                    yield _sse_event("delta", {"text": event.delta})
                    await asyncio.sleep(0)
                elif event.type == "response.completed":
                    if hasattr(event, "response") and hasattr(event.response, "id"):
                        response_id = event.response.id
        except Exception as e:
            error_text = f"I'm sorry, I encountered an error: {e}"
            full_text = error_text
            yield _sse_event("error", {"text": error_text})

        async with async_session_factory() as session:
            assistant_msg = await message_repo.create_message(
                session,
                chat_id=_chat_id,
                role=MessageRole.assistant,
                content_text=full_text or "(empty response)",
                sequence_number=_seq + 1,
                openai_response_id=response_id,
            )
            await session.commit()
            msg_data = MessageResponse.model_validate(assistant_msg).model_dump(mode="json")

        yield _sse_event("assistant_message", msg_data)
        yield _sse_event("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
