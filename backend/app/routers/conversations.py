from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Conversation, Message
from ..schemas import ConversationCreate, ConversationOut, ConversationRename, MessageOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(body: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conversation = Conversation(title=body.title or "新对话")
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: int, body: ConversationRename, db: AsyncSession = Depends(get_db)
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    conversation.title = body.title or conversation.title
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.delete(conversation)
    await db.commit()


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(conversation_id: int, db: AsyncSession = Depends(get_db)):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
    )
    return result.scalars().all()
