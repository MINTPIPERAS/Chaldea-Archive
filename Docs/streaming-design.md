# 流式输出设计：NDJSON over HTTP（明确不采用 SSE）

> 结论先行：
> - **传输层**：普通 HTTP POST 响应，chunked 分块到达
> - **帧格式**：NDJSON（每行一个 JSON 对象，以 `\n` 结尾）
> - **读取方式**：前端 `fetch()` + `response.body.getReader()`（ReadableStream），手动按 `\n` 分帧
> - **不用** `text/event-stream` / EventSource（即 SSE），**不用** WebSocket
> - 这是 ChatGPT 网页版、Vercel AI SDK 等"当今主流"的同款机制（它们同样用 fetch 流式读取响应体，区别只在帧格式细节）

---

## 1. 为什么不用 SSE（EventSource）

先澄清一个常见误解：**"流式"的本质是 HTTP 分块传输**——浏览器把响应体当字节流，边到边读。SSE 只是这个字节流上的一种帧格式（`text/event-stream`）加一个浏览器内置读取器（EventSource）。我们弃用的是 EventSource 这一整层，保留 HTTP 流式传输本身，理由：

| SSE（EventSource）的限制 | 对本项目的影响 |
|---|---|
| 原生 EventSource 只支持 GET | 聊天请求要 POST JSON body（含多轮上下文），GET 放不下 |
| 自定义 Header 麻烦 | 无法自然地带 `Content-Type: application/json` |
| 自动重连语义固定 | LLM 生成不可重放，SSE 的断线重放/Last-Event-ID 语义对不上 |
| 帧格式冗余（`data:` 前缀、空行分隔） | 表达结构化事件（usage/citations/error）啰嗦 |
| 部分代理/网关对 text/event-stream 有缓冲行为 | fetch 流式同样要防缓冲，但可自定义头规避（见 §4） |

注：业界说的"SSE 流式"多数其实是 fetch + ReadableStream 读 `text/event-stream` 帧（Vercel AI SDK 的 Data Stream Protocol 就是 fetch 流式 + 自定义帧）。我们换成更简单的 NDJSON 帧，协议私有、前后端都完全可控。

## 2. 为什么暂时不用 WebSocket

| 维度 | HTTP 流式（选定） | WebSocket |
|---|---|---|
| 方向 | 服务端→客户端单向推送 token，聊天够用 | 双向，纯聊天用不上 |
| 中断生成 | `AbortController` 取消 fetch，原生简单 | 要自定义协议消息 |
| 鉴权 / 代理 / 负载均衡 | 标准 HTTP，无障碍 | Upgrade 握手，部分代理要额外配置 |
| 断线恢复 | 重发请求即可 | 要自己实现心跳/重连/状态机 |
| 复杂度 | 低 | 明显更高 |

除非将来要做"服务端主动推送多会话更新 / 实时协作"，HTTP 流式就是最小复杂度方案；真到那天再局部引入 WebSocket 不迟。

## 3. 线协议定义（NDJSON 事件流）

响应头：`Content-Type: application/x-ndjson`。每个事件一行 JSON，以 `\n` 结尾，顺序即时间序。

| type | 时机 | 字段 |
|---|---|---|
| `message_start` | 流开始 | `conversation_id`, `message_id` |
| `delta` | 每收到上游增量 | `content`（**增量文本**，不是全量） |
| `citations` | 生成前（Phase 2） | `items[]`: {chunk_id, source, chapter, doc_type, score} |
| `usage` | 生成结束 | `prompt_tokens`, `completion_tokens` |
| `error` | 任何失败（终止事件） | `code`, `message` |
| `done` | 正常结束（最后一条） | — |
| `ping` | 生成间隙 >15s 时保活 | — |

规则：

1. 收到 `done` 即本次生成成功结束，连接随后关闭。
2. `error` 是终止事件：收到后连接即将关闭，不会再有 `done`。
3. `delta.content` 是增量，前端负责拼接。
4. 未来扩展（reasoning 增量、tool_call、多模态）一律新增 type，不改动既有语义。

示例流：

```
{"type":"message_start","conversation_id":1,"message_id":101}
{"type":"delta","content":"摩根"}
{"type":"delta","content":"（Berserker）"}
{"type":"delta","content":"的三技能是……"}
{"type":"usage","prompt_tokens":812,"completion_tokens":233}
{"type":"done"}
```

## 4. 后端实现（FastAPI）

位置：`app/routers/chat.py` + `app/services/llm.py` + `app/services/stream.py`。核心骨架：

```python
@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, db=Depends(get_db)):
    # 同步部分：解析配置、落库用户消息与 assistant 占位、组装上下文
    return StreamingResponse(
        _generate(...),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

async def _generate(config, messages, conversation_id, message_id):
    yield ndjson("message_start", conversation_id=conversation_id, message_id=message_id)
    full = ""
    try:
        async for piece in llm.stream_llm(config, messages):   # openai SDK stream=True
            if "delta" in piece:
                full += piece["delta"]
                yield ndjson("delta", content=piece["delta"])
            elif "usage" in piece:
                usage = piece["usage"]
        await finalize(full, status="ok", usage=usage)
        yield ndjson("usage", **usage)                          # 有才发
        yield ndjson("done")
    except asyncio.CancelledError:                              # 客户端断开/点停止
        await finalize(full, status="aborted")
        raise
    except Exception as exc:
        await finalize(full, status="error")
        yield ndjson("error", code="upstream_error", message=str(exc))
```

要点清单：

- **media_type 必须是 `application/x-ndjson`**（或 `text/plain`），不要 `application/json`——后者会诱导中间层整体缓冲。
- **`X-Accel-Buffering: no`**：存在 nginx 时禁用其响应缓冲；本地直连带上无害。
- openai SDK `stream=True` 返回异步迭代器，`chunk.choices[0].delta.content` 为增量；带 `stream_options={"include_usage": True}` 让上游在最后一个 chunk 附带 token 用量（主流 OpenAI 兼容服务均支持）。
- **客户端点"停止"** → 浏览器 abort 连接 → uvicorn 取消协程 → 捕获 `CancelledError`，把已生成的半截落库（status=aborted）。
- 上游异常（401/429/超时）统一转成 error 事件：HTTP 200 头已发出，之后只能靠事件传错误。
- **先落库再流式**：流式开始前 user 消息与 assistant 占位已入库，done/aborted/error 时更新终稿 → 页面刷新后历史可恢复。
- uvicorn 开发服务器本身不缓冲；若日后加 nginx 反代，`X-Accel-Buffering: no` 已覆盖，注意不要加 gzip 中间件压缩流式响应。

## 5. 前端实现（Vue3）

位置：`frontend/src/utils/stream.js` + `frontend/src/stores/chat.js`。

### 解析器（与后端协议一一对应）

```js
export async function streamNdjson({ url, body, signal, onEvent }) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })  // stream:true 处理中文多字节截断
    let i
    while ((i = buffer.indexOf('\n')) >= 0) {          // 按 \n 分帧
      const line = buffer.slice(0, i).trim()
      buffer = buffer.slice(i + 1)
      if (line) onEvent(JSON.parse(line))
    }                                                  // 不足一行的残帧留在 buffer
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer.trim()))  // 兜底：最后无换行的残余行
}
```

### 关键细节

- **残帧缓冲**：一次 `read()` 到的字节不一定以 `\n` 结尾（网络分片），必须缓冲、只消费完整行。
- **`TextDecoder` 的 `stream: true`**：中文 UTF-8 字符可能被网络分片从字节中间切断，该参数保证不产生乱码。
- **停止生成**：`AbortController`。`stop()` 调 `controller.abort()` → fetch 读取抛 AbortError → 后端收到断开并落库半截内容。效果与 WebSocket 的双向"停止"消息等价，但简单得多。
- **Pinia 状态机**：`streaming: true/false`；流式期间输入框显示"停止"按钮；assistant 消息的 `content` 直接拼 delta（Vue 响应式自动更新 UI）。
- **Markdown 增量渲染**：MVP 直接对整段 content 重渲 markdown-it，节流 ~50ms/次即可，不必做逐字符 diff。代码块未闭合时 markdown-it 按普通文本渲染，视觉可接受；追求精致可在渲染前补齐未闭合的 ```。
- **自动滚动**：仅当用户本来就在底部（距底 < 50px）才跟随滚动，避免回看历史被强行拽到底。

## 6. 异常与边界情况矩阵

| 场景 | 表现 | 处理 |
|---|---|---|
| 上游 401 / 无效 Key | error 事件 | 气泡内联错误提示，引导去设置页检查 |
| 上游 429 / 超时 | error 事件 | message 透传 provider 的错误信息 |
| 上游流中途断 | 连接结束但无 done | 前端保留已收文本，状态标记"生成中断" |
| 用户点停止 | abort | 半截内容落库（aborted），可继续追问 |
| 页面刷新 | 流断 | 消息以落库内容恢复（可能少最后一截，MVP 接受） |
| 长时间无事件 | 迟迟无输出 | 后端 ping 心跳保活；前端可加 60s 无事件超时提示 |

## 7. 演进说明

后端把"编码一行事件"收敛在 `app/services/ndjson` 单一函数里。将来如果某些客户端需要 SSE 或 WebSocket，只需替换帧编码/传输层，业务事件定义（§3 的 type 语义）不变。
