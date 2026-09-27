"""流式聊天：POST /api/chat/stream，NDJSON 事件流（协议见 Docs/streaming-design.md）。"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal, get_db
from ..models import ApiConfig, Conversation, Message
from ..schemas import ChatRequest
from ..services import llm
from ..services.stream import ndjson

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

DEFAULT_SYSTEM_PROMPT = (
    "你是「迦勒底档案」的 FGO / Type-Moon 资料助手。"
    "回答时注意区分游戏数据、剧情与同人设定；资料不足或存在多种说法时如实说明。"
)
HISTORY_LIMIT = 20


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1) 解析 API 配置：指定 id > 默认配置 > 任意一个 > mock 回退（保证开箱即用）
    config: ApiConfig | None = None
    if req.api_config_id:
        config = await db.get(ApiConfig, req.api_config_id)
        if not config:
            raise HTTPException(status_code=404, detail="API 配置不存在")
    if config is None:
        config = (
            await db.execute(
                select(ApiConfig).where(ApiConfig.is_default.is_(True)).limit(1)
            )
        ).scalar_one_or_none()
    if config is None:
        config = (
            await db.execute(select(ApiConfig).order_by(ApiConfig.id).limit(1))
        ).scalar_one_or_none()
    if config is None:
        config = ApiConfig(id=0, name="mock", provider_kind="mock", model="mock-1")

    # 2) 会话与消息先落库，再做流式（中断/刷新后历史可恢复）
    conversation = None
    if req.conversation_id:
        conversation = await db.get(Conversation, req.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
    if conversation is None:
        conversation = Conversation(title=req.content[:24])
        db.add(conversation)
        await db.flush()

    user_message = Message(conversation_id=conversation.id, role="user", content=req.content)
    assistant_message = Message(
        conversation_id=conversation.id, role="assistant", content="", model=config.model
    )
    db.add_all([user_message, assistant_message])
    conversation.updated_at = func.now()
    await db.commit()

    # 3) 组装上下文：system + 最近历史 + 本条
    history = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.id.desc())
            .limit(HISTORY_LIMIT)
        )
    ).scalars().all()[::-1]
    messages = [{"role": "system", "content": config.system_prompt or DEFAULT_SYSTEM_PROMPT}]
    messages += [
        {"role": m.role, "content": m.content}
        for m in history
        if m.role in ("user", "assistant") and m.content
    ]

    return StreamingResponse(
        _generate(config, messages, conversation.id, assistant_message.id),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _generate(
    config: ApiConfig, messages: list[dict], conversation_id: int, message_id: int
):
    yield ndjson("message_start", conversation_id=conversation_id, message_id=message_id)
    full = ""
    usage: dict | None = None
    try:
        async for piece in llm.stream_llm(config, messages):
            if "delta" in piece:
                full += piece["delta"]
                yield ndjson("delta", content=piece["delta"])
            elif "usage" in piece:
                usage = piece["usage"]
        await _finalize(message_id, full, "ok", usage)
        if usage:
            yield ndjson("usage", **usage)
        yield ndjson("done")
    except asyncio.CancelledError:
        # 客户端断开/点停止。请求正被 anyio 取消作用域回收，
        # 此作用域内再 await 数据库会立刻被重新取消并污染连接池，
        # 因此派生独立任务在作用域之外完成落库。
        asyncio.get_running_loop().create_task(
            _finalize(message_id, full, "aborted", usage)
        )
        raise
    except Exception as exc:
        logger.exception("chat stream failed")
        await _finalize(message_id, full, "error", None)
        yield ndjson("error", code="upstream_error", message=str(exc))


async def _finalize(
    message_id: int, content: str, status: str, usage: dict | None
) -> None:
    try:
        async with SessionLocal() as db:
            msg = await db.get(Message, message_id)
            if msg:
                msg.content = content
                msg.status = status
                if usage:
                    msg.prompt_tokens = usage.get("prompt_tokens")
                    msg.completion_tokens = usage.get("completion_tokens")
                await db.commit()
    except Exception:
        logger.exception("failed to finalize message %s", message_id)
