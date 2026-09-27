# 迦勒底档案 Chaldea Archive

FGO × Type-Moon 智能检索问答系统（BYOK · 可溯源 · 本地单用户）。

**当前状态**：Phase 0 骨架已完成 —— AI 网页聊天（NDJSON 流式）+ 会话历史 + BYOK API 配置 + Postgres/pgvector 就绪。RAG 检索按路线图在 Phase 2 接入。

## 文档

| 文档 | 内容 |
|---|---|
| [Docs/Plan.md](Docs/Plan.md) | 总体方案（定位、数据层、RAG 架构、路线） |
| [Docs/architecture.md](Docs/architecture.md) | 架构与技术选型修订（Vue3 + FastAPI + Postgres） |
| [Docs/embedding-guide.md](Docs/embedding-guide.md) | Embedding 从零指南（原理 / 选型 / 三种运行方式 / pgvector / 分块） |
| [Docs/streaming-design.md](Docs/streaming-design.md) | 流式输出协议与实现（NDJSON over HTTP，不采用 SSE） |

## 技术栈

- **前端**：Vue3 + Vite + Pinia + Element Plus（`frontend/`）
- **后端**：Python FastAPI（`backend/`）
- **数据库**：Postgres 16 + pgvector（Docker Compose）
- **LLM**：BYOK，一切 OpenAI 兼容服务（DeepSeek / OpenRouter / SiliconFlow / Ollama / vLLM…）；未配置时内置 mock 流式演示

## 快速开始

需要 Python 3.11+、Node 18+、Docker Desktop。

### 1. 启动数据库

```bash
docker compose up -d
```

### 2. 启动后端

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Git Bash（cmd 用 .venv\Scripts\activate）
pip install -r requirements.txt
cp .env.example .env               # 按需填写，不填也能跑
python -m uvicorn app.main:app --reload --port 8000
```

### 3. 启动前端（另开一个终端）

```bash
cd frontend
npm install
npm run dev
```

### 4. 打开 http://localhost:5173

- 未配置任何 API 时，聊天自动走 **mock 流式演示**（逐字输出、可中途停止），用于验证链路
- 在「API 设置」中新建配置（Base URL + API Key + 模型名），测试连接后即可真实对话

## Embedding 自检

配置好 SiliconFlow Key（`backend/.env` 里的 `CHALDEA_EMBEDDING_API_KEY`）后：

```bash
cd backend && python -m app.scripts.embed_demo
```

脚本对三句话算两两余弦相似度，直观验证"语义近 → 距离近"。原理与更多运行方式见 [Docs/embedding-guide.md](Docs/embedding-guide.md)。

## 路线图

见 [Docs/Plan.md](Docs/Plan.md) §8 与 [Docs/architecture.md](Docs/architecture.md) §8：Phase 0 底座（✅）→ 0.5 术语词典 → 1 Atlas 结构化问答 → 2 剧情 RAG → 3 Type-Moon 全宇宙。

## 许可

见 [LICENSE](LICENSE)。项目非官方、非商业；数据来源需遵守 Atlas Academy / Mooncell / TYPE-MOON Wiki 等各自条款。
