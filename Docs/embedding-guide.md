# Embedding 从零到一：原理、选型与落地方案

> 面向零基础读者，覆盖 Chaldea Archive 项目需要了解的 Embedding 全部内容。
> 配套实现见 `backend/app/services/embedding.py`，本文与代码一一对应。

---

## 1. Embedding 是什么？

一句话：**把一段文字变成一串固定长度的数字（向量），让"语义相近"变成"距离相近"。**

例如把三句话各编码成一个 1024 维向量（1024 个浮点数）：

- 「摩根是妖精国不列颠的女王」
- 「Morgan 是不列颠妖精国的女王」
- 「今天天气不错」

前两句用词不同（中文/英文）但意思几乎一样 → 向量距离非常近；第三句风马牛不相及 → 距离很远。

```
        语义空间（示意，实际是 1024 维，人眼无法想象，数学上完全可用）

   「摩根是妖精国不列颠的女王」●
   「Morgan 是不列颠妖精国的女王」●      ← 同义句挤在一起
                        ● 「妖精骑士的主人」  ← 沾边的也不算太远

   「今天天气不错」●                      ← 无关内容在很远的地方
```

向量本身没有可解释性——你不知道第 37 维代表什么，也不需要知道。**我们只关心向量之间的距离。**

---

## 2. 核心概念速查

| 概念 | 是什么 | 在本项目的意义 |
|---|---|---|
| 向量 / 维度 | 模型输出的固定长度浮点数组；bge-m3 是 1024 个数 | 建表时列类型要定维度，如 `vector(1024)` |
| 相似度 | 通常用 cosine 余弦相似度：1 最像，0 基本无关 | 检索 = "找出与问题向量 cosine 最大的 k 个 chunk" |
| 归一化 | 把向量缩放成长度 1，此时内积 = cosine | 主流模型输出已归一，一般不用管 |
| 上下文长度 | 模型一次最多吃多少 token；bge-m3 是 8192，e5 只有 512 | 决定 chunk 最大能切多大 |
| token | 模型的最小文本单位，中文粗略按 1 字 ≈ 1 token | 估算 chunk 大小与 API 成本 |
| MRL | 部分模型（Qwen3-Embedding、OpenAI v3）支持把高维向量截断成低维使用 | 省存储的进阶技巧，MVP 不用 |
| dense / sparse | dense 向量抓语义，sparse 向量抓关键词（类似 BM25） | bge-m3 一个模型两种都输出，天然支持混合检索 |
| query / passage 不对称 | 有的模型要求查询和文档加不同前缀（e5 系要加 `query: ` / `passage: `） | bge-m3 不需要；换模型时务必查文档 |

---

## 3. Embedding 在 RAG 流程中的位置

```
【离线入库】  文档 ──清洗──▶ 切分 chunk ──embedding──▶ 向量 ──▶ pgvector
【在线检索】  用户问题 ──embedding──▶ 向量 ──▶ 相似度 top-k ──▶ (rerank) ──▶ 拼进 prompt ──▶ LLM 流式回答
```

Embedding 质量决定了"能不能检索到对的片段"。但注意：**它只负责语义召回**。精确数值类问题（技能倍率、宝具等级、50% 自充列表）应该走结构化轨道（`Plan.md` 的双轨制），不要指望向量检索算数。

---

## 4. 模型选型

2026-09 时点，聚焦中文场景的主流选择：

| 模型 | 维度 | 上下文 | 大小 | 中文质量 | 运行方式 | 许可 | 点评 |
|---|---|---|---|---|---|---|---|
| **BAAI/bge-m3** | 1024 | 8192 | 568M（约 2.3GB） | 优秀 | 云 API（SiliconFlow 免费）/ 本地 / Ollama | MIT | 老牌多面手，dense+sparse 一体，生态最成熟，**本项目默认** |
| Qwen3-Embedding-0.6B | 1024+（MRL） | 32k | 0.6B | 优秀 | 本地 / Ollama / 云 | Apache-2.0 | 轻量新锐，MTEB 多语言高分 |
| Qwen3-Embedding-4B / 8B | 2560 / 4096 | 32k | 4B / 8B | 顶级 | 本地（建议 GPU）/ 云 | Apache-2.0 | 开源质量天花板，吃硬件 |
| multilingual-e5-large | 1024 | **512** | 560M | 良好 | 本地 / 云 | MIT | 稳定老将，但 512 上下文偏短、必须加前缀 |
| OpenAI text-embedding-3-small / large | 1536 / 3072 | 8191 | 闭源 | 良好 | 云 API | 闭源 | 省事，按量付费，中文不如 bge 系 |

### 选型结论（已写进项目默认配置）

1. **默认：SiliconFlow 托管的 BAAI/bge-m3**。免费、OpenAI 兼容协议（与 BYOK 的 LLM 用同一套客户端）、中文优秀、1024 维。到 siliconflow.cn 注册拿一个 API Key 即用。
2. **离线 / 隐私优先：本地 sentence-transformers 加载 bge-m3**（CPU 可跑，批量入库慢一些）。
3. **质量升级路线：Qwen3-Embedding-4B/8B**（需要 GPU，或找托管了它的云 API）。
4. ⚠️ **换 Embedding 模型 = 全量重建向量索引**。不同模型的向量空间互不相通，维度也可能不同。所以 `chunks` 表里冗余记录了 `embedding_model`，这是将来换模型的"后悔药"。

---

## 5. 三种运行方式（都已支持，改配置即可切换）

项目把 Embedding 抽象成一个 Provider 接口，三种方式只是不同配置（实现见 `backend/app/services/embedding.py`）：

### 方式 A：云 API（默认）

以 SiliconFlow 免费托管为例：

1. 注册 https://siliconflow.cn → 控制台「API 密钥」新建 Key
2. 接口就是 OpenAI 兼容的 `POST /v1/embeddings`

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="sk-xxx", base_url="https://api.siliconflow.cn/v1")
resp = await client.embeddings.create(model="BAAI/bge-m3", input=["摩根是妖精国的女王"])
vec = resp.data[0].embedding   # 1024 个浮点数，len(vec) == 1024
```

- 优点：零算力、零下载、免费额度对个人足够
- 缺点：文本要出本机；免费档有 RPM 限流（批量入库要做分批 + 重试，见 §9）

### 方式 B：本地加载（sentence-transformers）

```bash
pip install sentence-transformers

# 国内加速模型下载（bge-m3 约 2.3GB），Git Bash：
export HF_ENDPOINT=https://hf-mirror.com
```

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")   # 首次运行自动下载
vecs = model.encode(
    ["摩根是妖精国的女王", "奥伯龙是何人"],
    normalize_embeddings=True,
)
```

性能量级参考：CPU 单条几十毫秒，批量约 10–30 chunk/秒（视 CPU）；有 NVIDIA GPU 快一个数量级以上。十万级 chunk 的一次性入库：CPU 需要数小时，GPU 几分钟——入库是离线操作，慢点无妨。

### 方式 C：Ollama 托管

```bash
ollama pull bge-m3        # 约 1.2GB
# 之后它就是一个 OpenAI 兼容服务：
#   base_url = http://localhost:11434/v1
#   model    = bge-m3
```

适合已经在用 Ollama 管理 LLM 的情况：模型常驻内存/显存，由 Ollama 进程统一管理。

### Provider 抽象（项目已实现）

```python
class EmbeddingProvider(ABC):
    model_name: str
    dimension: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

三个实现：`OpenAICompatibleEmbedding`（覆盖云 API 与 Ollama，仅 base_url 不同）、`LocalEmbedding`（sentence-transformers，懒加载）。`.env` 里 `CHALDEA_EMBEDDING_PROVIDER=cloud|local|ollama` 切换，**上层代码永远只面对接口**。

**自检脚本**（填好 Key 后跑一次，直观看到"语义近 → 距离近"）：

```bash
cd backend && python -m app.scripts.embed_demo
```

它对三句话算两两相似度：中文原句 vs 英文同义句（应 > 0.9）vs 无关句（应 < 0.5）。

---

## 6. 向量库：pgvector 实操

**选 pgvector 的理由**：向量与业务数据（会话、消息、chunk 元数据）同库；"只在 2.6 章、剧情类型里搜"这类元数据过滤就是普通 SQL `WHERE`；备份一份搞定。本项目数据库方案已定 Postgres，pgvector 是顺路的最优解。

建表（骨架已含于 `app/models.py`，这里是等价 SQL，便于理解）：

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
  id              bigserial PRIMARY KEY,
  document_id     bigint REFERENCES documents(id),
  seq             int NOT NULL,                -- 在文档内的顺序
  content         text NOT NULL,               -- chunk 正文
  meta            jsonb NOT NULL DEFAULT '{}', -- doc_type/chapter/servant_id/...
  embedding       vector(1024),                -- 维度与所选模型一致（bge-m3=1024）
  embedding_model text,                        -- 冗余记录，防换模型后混用
  created_at      timestamptz DEFAULT now()
);

-- 检索索引：HNSW（查询快、构建稍慢），cosine 距离
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
```

检索就是一条 SQL：

```sql
SELECT id, content, meta,
       1 - (embedding <=> :query_vec) AS score   -- <=> 是 cosine 距离，1-距离=相似度
FROM chunks
WHERE meta->>'doc_type' = 'story'                -- 元数据过滤先缩小范围
  AND meta->>'chapter'  LIKE '2.6%'
ORDER BY embedding <=> :query_vec
LIMIT 8;
```

补充说明：

- pgvector 两种索引：**HNSW**（推荐，查询快）与 IVFFlat（需要先有数据再训练）。MVP 直接 HNSW。
- **中文 BM25**：Postgres 原生全文检索对中文分词支持弱。MVP 阶段混合检索的"关键词腿"建议在 Python 侧做（jieba 分词 + BM25，或 tantivy-py）；数据量到百万 chunk 再考虑 Meilisearch / Elasticsearch。bge-m3 自带的 sparse 向量是第三条路（进阶，Phase 2 评估）。

---

## 7. 切分 Chunking（RAG 效果的第一决定因素）

向量检索质量 = embedding 模型质量 × **切分质量**。后者常常影响更大。

### 基本原则

- **大小**：300–500 token / 块（中文约 500–800 字），块间 overlap 10–15%。太小 → 语义不完整；太大 → 目标句子被稀释，检索精度下降。
- **不切碎结构**：优先按标题/章节/小节边界切。Wiki 词条保留"词条名/小节路径"作为每块前缀，如 `【摩根/持有技能】…`——前缀随正文一起被向量化，显著提升命中率。
- **剧情文本特殊处理**：对话按"说话人"行保留；每块头部带章节+场景信息（如 `【2.6 断绝魔轮篇/王城】`）。用户问"摩根怎么死的"能命中对应块，靠的就是这些锚点。
- **术语词典参与切分**：`Plan.md` 3.3 的术语词典在这里发力——识别块属于哪个从者/章节，写入 `meta.servant_id`、`meta.chapter`，检索时先过滤后相似。
- **结构化数据不进向量库**：技能/宝具数值走 Atlas Academy 结构化轨道（Phase 1）。"哪些从者有 50% 自充"靠精确查询，不是"最像的段落"。

### chunk 元数据 schema（写入 `chunks.meta`）

```json
{
  "doc_type": "story | wiki | setting",
  "source": "文件名或 Wiki 页面 URL",
  "chapter": "2.6 断绝魔轮篇",
  "servant_id": "morgan",
  "section_path": "摩根/宝具",
  "version": "2024-08 整理版",
  "lang": "zh"
}
```

---

## 8. 端到端示例（Phase 2 的雏形）

入库：

```python
async def ingest_document(title: str, text: str):
    doc = await create_document(title)
    chunks = split_by_structure(text, max_tokens=450, overlap=0.12)  # §7 策略
    provider = get_embedding_provider()                              # §5 抽象
    for batch in batched(chunks, 32):                                # 批量省请求
        vecs = await provider.embed([c.content for c in batch])
        await insert_chunks(doc, batch, vecs)                        # §6 SQL
```

查询 + 生成（聊天时）：

```python
qvec = (await provider.embed([question]))[0]
hits = await search_topk(qvec, filter={"doc_type": "story"}, k=8)    # §6 SQL
context = render_context(hits)   # 编号[1][2]…，供模型引用、供 citations 事件回传前端
messages = [system(引用规范)] + history + [user(question + context)]
```

---

## 9. 常见坑清单（每条都真实绊倒过人）

1. **换模型不重建索引** → 新旧向量混在一个空间，检索结果莫名其妙。换模型必须全量重嵌。
2. **维度对不上** → pgvector 列定长 `vector(1024)`，换成 1536 维模型插入直接报错。建表维度与模型维度必须一致。
3. **不记录 embedding_model** → 三个月后不知道库里向量是谁生成的。骨架已把模型名写进 `chunks.embedding_model`。
4. **超长文本直接喂** → 超过模型上下文会被截断，块尾语义丢失。切分时按 token 数控制。
5. **e5 系模型不加前缀** → e5 要求查询加 `query: `、文档加 `passage: `，忘了效果骤降。bge-m3 / Qwen3 不需要。
6. **云 API 批量入库不限速** → 免费档 RPM 触顶，批量任务半路 429。分批 + 指数退避重试。
7. **拿向量检索做精确数值问答** → "宝具倍率 900%" 这类问题向量召回不可靠，走结构化轨道。
8. **归一化不一致** → 混用"未归一向量 + 内积"与"归一向量 + cosine"会静默出错。统一 cosine + 模型默认输出即可。
9. **chunk 丢失出处信息** → 检索到了却说不出自哪章哪页，引用功能做不了。元数据和正文一样重要。
10. **成本心里没数**：10 万 chunk × 450 token ≈ 4500 万 token。SiliconFlow bge-m3 免费；OpenAI text-embedding-3-small 约 $0.9；本地 CPU 只有电费。**Embedding 是 RAG 里最便宜的一环，别怕多嵌。**

---

## 10. 与代码的对应关系

| 本文章节 | 代码位置 |
|---|---|
| §5 Provider 抽象 | `backend/app/services/embedding.py` |
| §6 数据表 | `backend/app/models.py`（documents / chunks，含 embedding 向量列与 embedding_model 字段） |
| §5 自检脚本 | `backend/app/scripts/embed_demo.py` |
| §7/§8 切分与入库 | Phase 2 新增 `services/ingest.py` 与 `services/retriever.py`，直接消费上述接口 |

## 参考

- bge-m3: https://huggingface.co/BAAI/bge-m3
- Qwen3-Embedding: https://huggingface.co/Qwen
- pgvector: https://github.com/pgvector/pgvector
- MTEB 榜单: https://huggingface.co/spaces/mteb/leaderboard
