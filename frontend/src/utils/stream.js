/**
 * NDJSON 流式读取器（协议见 Docs/streaming-design.md）。
 *
 * 关键点：
 * - 残帧缓冲：一次 read() 的字节不一定以 \n 结尾，只消费完整行
 * - TextDecoder 的 stream:true：中文 UTF-8 可能被网络分片从字节中间切断
 * - signal：AbortController 实现"停止生成"
 */
export async function streamNdjson({ url, body, signal, onEvent }) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      /* 保留默认信息 */
    }
    throw new Error(detail)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let i
    while ((i = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, i).trim()
      buffer = buffer.slice(i + 1)
      if (line) onEvent(JSON.parse(line))
    }
  }
  const tail = buffer.trim()
  if (tail) {
    try {
      onEvent(JSON.parse(tail))
    } catch {
      /* 忽略无法解析的残余字节 */
    }
  }
}
