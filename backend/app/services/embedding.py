"""Embedding Provider 抽象（原理与选型详见 Docs/embedding-guide.md §5）。

三种运行方式，由 CHALDEA_EMBEDDING_PROVIDER 切换：
- cloud  : OpenAI 兼容云 API，默认 SiliconFlow 免费托管的 BAAI/bge-m3
- ollama : 本地 Ollama 服务（同为 OpenAI 兼容协议，仅 base_url 不同）
- local  : sentence-transformers 进程内加载（数据不出本机，CPU 可跑）
"""

import asyncio
from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from ..config import settings


class EmbeddingProvider(ABC):
    model_name: str
    dimension: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """把一批文本编码为向量，输出顺序与输入一致。"""


class OpenAICompatibleEmbedding(EmbeddingProvider):
    """SiliconFlow / OpenAI / Ollama(/v1) 等一切 OpenAI 兼容 /embeddings 接口。"""

    def __init__(self, base_url: str, api_key: str, model: str, dimension: int):
        self._client = AsyncOpenAI(api_key=api_key or "not-needed", base_url=base_url)
        self.model_name = model
        self.dimension = dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self.model_name, input=texts)
        data = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in data]


class LocalEmbedding(EmbeddingProvider):
    """sentence-transformers 进程内加载。懒加载，仅在选择 local 模式时初始化。"""

    def __init__(self, model: str, dimension: int):
        self._model_name = model
        self._model = None
        self.dimension = dimension

    def _load(self):
        if self._model is None:
            # 延迟导入：未选择 local 模式时无需安装 sentence-transformers
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        vecs = await asyncio.to_thread(
            self._model.encode, texts, normalize_embeddings=True, show_progress_bar=False
        )
        return [v.tolist() for v in vecs]


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        if settings.embedding_provider == "local":
            _provider = LocalEmbedding(settings.embedding_model, settings.embedding_dimension)
        else:
            base_url = (
                "http://localhost:11434/v1"
                if settings.embedding_provider == "ollama"
                else settings.embedding_base_url
            )
            _provider = OpenAICompatibleEmbedding(
                base_url, settings.embedding_api_key, settings.embedding_model, settings.embedding_dimension
            )
    return _provider
