# 项目命名

## 主推名：**迦勒底档案 / Chaldea Archive**

**副标题**：FGO × Type-Moon 智能检索问答系统  
**一句话定位**：一个支持 BYOK、自定义 API、可引用溯源的 Type-Moon / FGO 知识库 RAG。

**为什么叫这个**：迦勒底在 FGO 里本身就是“观测、记录、保障人理”的机构，“档案”又天然符合 RAG 知识库的定位。粉丝一眼能懂，非粉丝也能理解是资料检索工具。

**备选名**：
- **灵基图谱 / Spirit Origin Atlas**：偏从者数据查询。
- **月之背侧 / Moon Cell Retrieval**：偏 Type-Moon 世界观考据。
- **根源检索 / Root Access**：更极客，但 FGO 指向弱。
- **人理保障检索 / Human Order Archive**：适合做完整世界观资料库。

建议正式名用 **迦勒底档案 Chaldea Archive**，项目代号用 **Chaldea RAG**。

---

# 《迦勒底档案 Chaldea Archive》项目方案

## 1. 项目定位

面向 FGO 玩家、Type-Moon 设定考据党、同人创作者的智能检索问答系统。  
它不是通用 ChatGPT 克隆，而是：

- **BYOK**：用户自带 OpenAI 兼容 API Key。
- **可自定义**：支持自定义 `base_url`、`model`、`api_key`、代理。
- **可溯源**：回答尽量带出处，区分剧情、设定、游戏数据。
- **双轨制**：结构化游戏数据 + 非结构化剧情/ Wiki 文本。
- **非官方、非商业优先**：明确标注数据来源与许可。

## 2. 核心场景

| 场景 | 示例问题 | 数据来源 |
|---|---|---|
| 从者数据查询 | 摩根的三技能是什么？ | Atlas Academy |
| 宝具/技能精确查询 | 哪些从者有 50% 自充？ | Atlas Academy |
| 主线剧情问答 | 2.6 里摩根是怎么死的？ | 主线剧情文本 |
| 设定考据 | 抑制力在 FGO 里怎么解释？ | Mooncell / TYPE-MOON Wiki |
| 创作辅助 | 帮我写一段奥伯龙语气的台词 | 剧情语料 + LLM |
| 跨作品关系 | FGO 阿尔托莉雅和 FSN 什么关系？ | TYPE-MOON Wiki |

## 3. 数据层设计

采用 **结构化 + 文本双轨制**。

### 3.1 结构化轨道
- **Atlas Academy API**：从者、技能、宝具、礼装、活动、关卡等。
- 本地落库为 Postgres / SQLite，便于 Text-to-SQL 或函数调用。
- 回答“倍率、数值、效果、开放时间”这类精确问题。

### 3.2 文本轨道
- **FGO 主线剧情 EPUB**：1.0 - 2.7 等，已有社区整理版本。
- **Mooncell Wiki**：中文 FGO 资料最全。
- **TYPE-MOON Wiki / Fandom**：覆盖整个 Type-Moon 宇宙。
- 清洗后按章节、词条、对话切分，进入向量库。

### 3.3 术语词典
必须单独维护：
- 从者名、别名、形态：摩根、摩根·勒·菲、Alter、Lily、Santa。
- 宝具名、技能名、职阶、活动名、章节名。
- 日文 / 中文 / 英文三语别名。

用途：Embedding 前注入、分块锚点、BM25 关键词、查询改写。

## 4. RAG 架构

流程：

1. **采集**：Atlas API、剧情 EPUB、Wiki 页面。
2. **清洗**：去广告、去导航、统一标点、保留标题/说话人/章节。
3. **切分**：术语感知分块，避免把宝具描述切半。
4. **索引**：
   - 向量索引：pgvector。
   - 关键词索引：Postgres BM25 / Elasticsearch。
   - 元数据：从者 ID、章节、数据类型、年份、版本。
5. **检索**：
   - Hybrid Search：BM25 + 向量。
   - 元数据过滤：先缩小到从者/章节/数据类型。
   - Rerank：bge-reranker-v2-m3 或 Cohere Rerank。
6. **生成**：
   - 用户 BYOK 模型。
   - System Prompt 要求引用来源、冲突并列。
7. **引用**：返回 chunk 出处、章节、Wiki 链接或数据源。

### 关键优化
- **混合检索**：BM25 命中“摩根”“奥伯龙”，向量负责语义。
- **冲突消解 Prompt**：检索到矛盾设定时，分别列出并注明出处，不强行统一。
- **版本标记**：保留早期设定 / 最新设定，避免“吃书”混乱。
- **查询改写**：用户问“摩根”时，自动扩展为“摩根·勒·菲 / Morgan / 妖精骑士”。

## 5. 技术选型

> 2026-09-27 修订：项目确定为**本地单用户、Python 后端、Vue3 前端、自托管 Postgres**，本表已同步更新。
> 修订理由与完整架构见 [architecture.md](architecture.md)；流式方案（NDJSON over HTTP，不采用 SSE）见 [streaming-design.md](streaming-design.md)；Embedding 详解见 [embedding-guide.md](embedding-guide.md)。

| 层 | 选型 |
|---|---|
| 前端 | Vue3 + Vite + Pinia + Element Plus |
| 后端 | Python FastAPI（async + StreamingResponse） |
| 流式 | 自研 NDJSON over HTTP 流式（fetch + ReadableStream） |
| 数据库 | 自托管 Postgres 16 + pgvector（Docker Compose） |
| 关键词检索 | MVP: Python 侧 jieba+BM25 → 规模化后 Meilisearch / Elasticsearch |
| 文件 | 本地磁盘 |
| 认证 | 无（本地单用户免登录；多用户化时再加） |
| 部署 | Docker Compose（数据库）+ 本地 venv / vite dev |
| Embedding | bge-m3（默认 SiliconFlow 云 API，可切本地 sentence-transformers / Ollama） |
| Rerank | bge-reranker-v2-m3（Phase 2 接入） |
| LLM | 用户 BYOK：MVP 走 OpenAI-Compatible 协议（DeepSeek/OpenRouter/SiliconFlow/Ollama/vLLM…），Anthropic/Gemini 原生适配后续加 |

## 6. 自定义 API 设计

设置页至少包含：

- Provider：OpenAI-Compatible / Anthropic / Gemini / Ollama
- Base URL
- API Key
- Model
- Temperature / Max Tokens
- System Prompt
- 代理地址
- 测试连接

安全要求：
- 前端不直接暴露他人 Key。
- 用户 Key 本地存或 AES-GCM 加密存。
- 自定义 `base_url` 防 SSRF：限制内网 IP、禁止 `localhost`、`169.254` 等。
- 记录 Token 与成本，支持流式、重试、错误提示。

## 7. 核心数据表

- `users`
- `api_configs`
- `conversations`
- `messages`
- `documents`
- `chunks`
- `embeddings`
- `entities`
- `entity_aliases`
- `servant_data`
- `quests`
- `events`
- `citations`
- `eval_sets`
- `eval_runs`

## 8. MVP 路线

### Phase 0：底座，1 周（✅ 骨架已完成，见 architecture.md）
- 本地运行，免登录（本地单用户形态）
- API 设置页（BYOK，OpenAI 兼容协议 + mock 演示）
- 流式聊天（NDJSON over HTTP）
- 会话历史

### Phase 1：从者数据精确问答，2-3 周
- 接入 Atlas Academy API
- 本地结构化库
- 函数调用 / Text-to-SQL
- 回答“摩根三技能”“奥伯龙宝具效果”
- 目标：精确、可信、可引用

### Phase 2：主线剧情 RAG，1-2 个月
- 导入主线剧情 EPUB
- 术语词典 + Hybrid Search + Rerank
- 元数据过滤：从者、章节、数据类型
- 回答“2.6 摩根怎么死的”“奥伯龙最初身份”
- 目标：语义检索 + 出处引用

### Phase 3：全 Type-Moon 扩展
- 接入 TYPE-MOON Wiki
- 覆盖 FSN、Fate/Zero、空之境界等
- 跨作品设定问答
- 目标：长期资料库，但一致性难度最高

## 9. 评估与测试

建立 100-300 条标准问答对，分三类：
- 从者数据题
- 剧情事实题
- 跨作品设定题

指标：
- 检索命中率 Recall@k
- MRR
- 答案准确率
- 引用正确率
- 幻觉率
- 延迟与成本

FGO 粉丝对设定极敏感，必须定期跑评估集，避免“炎上”。

## 10. 风险与合规

- **版权**：非官方、非商业，标注数据来源与许可。  
  Atlas Academy、剧情 EPUB、Mooncell、TYPE-MOON Wiki 均需遵守各自条款。
- **幻觉**：强制引用，无法确认时回答“资料不足”。
- **专有名词**：术语词典 + 查询改写 + Hybrid Search。
- **吃书**：保留版本与出处，冲突并列。
- **安全**：API Key 加密、SSRF 防护、限流。
- **更新**：Atlas 数据随版本同步，Wiki 变更定期重建索引。