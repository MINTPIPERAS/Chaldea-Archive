"""Embedding 语义相似度自检脚本。

用法（backend 目录下）：
    python -m app.scripts.embed_demo

预期：「摩根…女王」与英文同义句的相似度显著高于无关句
（详见 Docs/embedding-guide.md §5）。需先在 .env 中填好 CHALDEA_EMBEDDING_API_KEY。
"""

import asyncio
import math


def cosine(u: list[float], v: list[float]) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    return dot / (nu * nv) if nu and nv else 0.0


async def main() -> None:
    from ..services.embedding import get_embedding_provider

    provider = get_embedding_provider()
    print(f"provider={type(provider).__name__}  model={provider.model_name}  dim={provider.dimension}")

    texts = [
        "摩根是妖精国不列颠的女王",
        "Morgan 是不列颠妖精国的女王",
        "今天中午吃什么好呢",
    ]
    print("正在编码 3 条文本……")
    vecs = await provider.embed(texts)

    print(f"\n两两 cosine 相似度（共 {len(vecs)} 条文本）：")
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            score = cosine(vecs[i], vecs[j])
            print(f"  [{i}] vs [{j}] = {score:.4f}   {texts[i]!r} vs {texts[j]!r}")

    print("\n预期：[0] vs [1]（同义）显著高于 [0] vs [2]（无关）。")


if __name__ == "__main__":
    asyncio.run(main())
