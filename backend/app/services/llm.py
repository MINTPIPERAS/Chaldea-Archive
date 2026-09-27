"""BYOK LLM 流式封装。

统一产出两种标准化增量（上层路由不感知各家 SDK 的 chunk 结构）：
- {"delta": "..."}   文本增量
- {"usage": {...}}   token 用量（上游支持时，最后一个 chunk 附带）
"""

import asyncio
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from ..models import ApiConfig

MOCK_REPLY = (
    "这是 **mock 模式** 的流式回复（未调用任何外部 API）。\n\n"
    "摩根（Morgan，Berserker）在 2.6 章「断绝魔轮篇」中以妖精国不列颠女王的身份登场，"
    "与 Altria Caster、Fairy Knight Lancelot 等共同构成不列颠的妖精势力格局。\n\n"
    "- 列表项用来观察 Markdown 渲染\n"
    "- 行内代码 `stream=True` 与 **加粗** 都应正常显示\n\n"
    "```python\nprint('hello chaldea')\n```\n\n"
    "在「API 设置」中配置任意 OpenAI 兼容服务后，即可获得真实模型回复。"
)


async def stream_llm(config: ApiConfig, messages: list[dict]) -> AsyncIterator[dict]:
    if config.provider_kind == "mock":
        async for piece in _mock_stream():
            yield piece
        return

    client = AsyncOpenAI(api_key=config.api_key or "", base_url=config.base_url or None)
    kwargs: dict = {
        "model": config.model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": config.temperature,
    }
    if config.max_tokens:
        kwargs["max_tokens"] = config.max_tokens
    stream = await client.chat.completions.create(**kwargs)
    async for chunk in stream:
        if getattr(chunk, "usage", None):
            yield {
                "usage": {
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                }
            }
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield {"delta": chunk.choices[0].delta.content}


async def _mock_stream() -> AsyncIterator[dict]:
    """逐字吐出预设文本模拟上游 chunk，便于无 Key 自测整条流式链路。"""
    for i in range(0, len(MOCK_REPLY), 2):
        await asyncio.sleep(0.03)
        yield {"delta": MOCK_REPLY[i : i + 2]}
    yield {"usage": {"prompt_tokens": 128, "completion_tokens": len(MOCK_REPLY) // 2}}
