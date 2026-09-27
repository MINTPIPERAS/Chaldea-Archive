# 架构与技术选型修订

> 2026-09-27：`Plan.md` 初版按"云托管 SaaS"设想（Next.js / Supabase / Clerk / Vercel）。经确认，实际形态为：**本地单用户、Python 后端、Vue3 前端、自托管 Postgres**。本文记录修订后的完整架构与理由，`Plan.md` 第 5 节选型表已同步。

---

## 1. 选型修订总表

| 层 | Plan.md 原定 | 修订后 | 理由 |
|---|---|---|---|
| 前端 | Next.js + Tailwind + shadcn/ui | **Vue3 + Vite + Pinia + Element Plus** | 项目要求；前端非重点，Element Plus 出活快 |
| 后端 | （Next API Routes） | **FastAPI (Python)** | 要求 Python；原生 async + StreamingResponse 流式顺手；openai SDK 生态成熟 |
| 流式 | Vercel AI SDK | **自研 NDJSON over HTTP 流式** | 不采用 SSE；协议设计见 [streaming-design.md](streaming-design.md) |
| 数据库 | Supabase Postgres + pgvector | **自托管 Postgres 16 + pgvector（Docker Compose）** | 本地单用户，免云依赖 |
| 关键词检索 | Postgres BM25 / Elasticsearch | MVP：Python 侧 jieba+BM25（或 tantivy-py）→ 规模化后 Meilisearch | 中文分词与轻运维优先 |
| 文件存储 | Cloudflare R2 / S3 | 本地磁盘 | 单机 |
| 认证 | Clerk / NextAuth | **无（本地单用户免登录）** | 多用户需求出现时再加轻量账号层 |
| 部署 | Vercel / Docker | Docker Compose（数据库）+ 本地 venv / vite dev | 开发期简单直接，后续可整体容器化 |
| Embedding | bge-m3 / mE5 / OpenAI | **bge-m3（默认 SiliconFlow 云 API，可切本地 / Ollama）** | 详见 [embedding-guide.md](embedding-guide.md) |
| Rerank | bge-reranker-v2-m3 / Cohere | 不变，Phase 2 接入 | |
| LLM | BYOK 多 Provider | **MVP 仅 OpenAI 兼容协议**，Anthropic/Gemini 原生适配后加 | OpenAI 兼容已覆盖 DeepSeek / OpenRouter / SiliconFlow / Moonshot / Qwen / Ollama / vLLM 等绝大多数场景，适配层单点扩展 |

## 2. 系统分层

```
┌─────────────────────────────────────────────────┐
│  Browser   Vue3 + Pinia + Element Plus          │
│    聊天页 / 会话侧栏 / API 设置页                  │
│    fetch + ReadableStream（NDJSON 事件流解析）     │
└───────────────┬─────────────────────────────────┘
                │ HTTP（REST + NDJSON 流）
┌───────────────▼─────────────────────────────────┐
│  FastAPI   backend/                              │
│    routers: chat / conversations / settings      │
│    services: llm（BYOK 流式）embedding（RAG）      │
└───┬──────────────────┬─────────────────────┬────┘
    │ SQLAlchemy async  │ openai 兼容协议      │ embedding provider
┌───▼──────────┐  ┌────▼───────────┐  ┌──────▼────────┐
│ Postgres 16  │  │ 用户自带 LLM     │  │ 云 API / 本地 / │
│ + pgvector   │  │ (DeepSeek/     │  │ Ollama         │
│ 业务表 + 向量  │  │ OpenRouter…)   │  │ (bge-m3)      │
└──────────────┘  └────────────────┘  └───────────────┘
```

## 3. 目录结构（骨架已建）

```
backend/
  app/
    main.py               # FastAPI 入口（CORS、lifespan 建表）
    config.py             # pydantic-settings，读 .env
    db.py                 # async engine / session / init_db
    models.py             # ORM：api_configs, conversations, messages, documents, chunks
    schemas.py            # Pydantic 请求/响应模型
    routers/
      chat.py             # POST /api/chat/stream（NDJSON 流式，含 mock 回退）
      conversations.py    # 会话 CRUD + 历史消息
      settings.py         # API 配置 CRUD + 测试连接
    services/
      llm.py              # BYOK 流式封装（openai SDK + mock 模拟器）
      embedding.py        # EmbeddingProvider 抽象（cloud/ollama/local）
      stream.py           # NDJSON 事件编码
    scripts/
      embed_demo.py       # 语义相似度自检脚本
  requirements.txt
  .env.example

frontend/
  src/
    main.js               # Vue3 + Pinia + Element Plus 装配
    App.vue               # 布局：侧栏 + 主区（聊天/设置切换）
    api/client.js         # fetch 封装
    utils/stream.js       # NDJSON 流式解析器（核心）
    utils/markdown.js     # markdown-it + highlight.js
    stores/chat.js        # 会话/消息/流式状态机
    stores/settings.js    # API 配置状态
    components/           # SessionList / MessageBubble / ChatInput
    views/                # ChatView / SettingsView
  package.json / vite.config.js
```

## 4. API 一览

| Method | Path | 说明 |
|---|---|---|
| GET | /api/health | 健康检查 |
| POST | /api/chat/stream | 流式对话（NDJSON 事件流） |
| GET | /api/conversations | 会话列表 |
| POST | /api/conversations | 新建会话 |
| PATCH | /api/conversations/{id} | 重命名 |
| DELETE | /api/conversations/{id} | 删除会话（连带消息） |
| GET | /api/conversations/{id}/messages | 历史消息 |
| GET / POST | /api/settings/api-configs | 配置列表 / 新建 |
| PUT / DELETE | /api/settings/api-configs/{id} | 更新 / 删除 |
| POST | /api/settings/api-configs/test | 测试连通性（GET /models） |

## 5. 数据模型（对应 Plan.md 第 7 节）

**MVP 已建**：`api_configs`、`conversations`、`messages`、`documents`（备）、`chunks`（备，含 pgvector 向量列）。

**延后**：`users`（本地免登录，暂不需要）；`entities` / `entity_aliases`（术语词典，Phase 0.5）；`servant_data` / `quests` / `events`（Phase 1）；`citations` / `eval_sets` / `eval_runs`（Phase 2+）。

关键设计点：

- `messages` 存 `prompt_tokens` / `completion_tokens` 与 `status`（ok | error | aborted），为成本统计与中断恢复打基础。
- `chunks.embedding` 维度 1024 绑定 bge-m3；换模型需全量重建并改列宽（见 embedding-guide.md §9 坑 1/2）。
- MVP 建表用 `Base.metadata.create_all`（启动时自动），引入 Alembic 迁移放在 Phase 1 前。

## 6. BYOK 设计（本地单用户版）

- `provider_kind`：`openai-compatible`（MVP 实现）、`mock`（无 Key 演示）、`anthropic` / `gemini` / `ollama`（预留枚举，后续适配）。
- 自定义 `base_url` 即可接入 DeepSeek、OpenRouter、SiliconFlow、Moonshot、Qwen、vLLM、Ollama(/v1) 等一切 OpenAI 兼容服务。
- **API Key 本地库明文存储**（单用户本地可接受）；Pydantic schema 已预留扩展位，多用户化时启用 AES-GCM（密钥由用户口令派生），对应 Plan.md §6 的安全要求届时生效。
- **SSRF 防护**：本地单用户风险低；多用户化时启用内网地址黑名单（禁 localhost / 169.254 / 内网段）。
- **测试连接**：请求 `{base_url}/models`，成功返回发现的模型数量与列表。
- 未配置任何 API 时，聊天接口**自动回退 mock provider**，保证开箱即用验证流式链路。

## 7. RAG 管线落位（Phase 2 展望）

```
backend/app/services/
  llm.py          ✅ BYOK 流式
  embedding.py    ✅ Provider 抽象（云 API 默认）
  ingest.py       🔜 EPUB/Wiki → 清洗 → 术语感知切分 → 嵌入 → 入库
  retriever.py    🔜 hybrid 检索 + 元数据过滤 + rerank
```

聊天链路集成点：`chat.py` 组装消息前调用 retriever，检索结果以 `citations` 事件先于 delta 发出（协议已预留，见 streaming-design.md §3）。

## 8. 修订版路线

- **Phase 0 ✅（本次骨架）**：流式聊天 + 会话历史 + API 设置 + Postgres/pgvector 就绪
- **Phase 0.5**：术语词典表与管理页
- **Phase 1**：Atlas Academy 结构化问答（函数调用 / Text-to-SQL）＋ 评估集起步
- **Phase 2**：剧情 RAG（ingest pipeline + hybrid + rerank + citations）
- **Phase 3**：Type-Moon 全宇宙扩展

## 9. 环境与启动

见根目录 `README.md`。需要 Python 3.11+、Node 18+、Docker Desktop（跑 Postgres）。
