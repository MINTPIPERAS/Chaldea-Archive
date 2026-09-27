<script setup>
import { computed } from 'vue'
import { renderMarkdown } from '../utils/markdown'

const props = defineProps({ message: { type: Object, required: true } })

const isUser = computed(() => props.message.role === 'user')
const html = computed(() => (isUser.value ? '' : renderMarkdown(props.message.content)))
const tokens = computed(() => {
  const { prompt_tokens, completion_tokens } = props.message
  if (!completion_tokens) return ''
  return `tokens: ${prompt_tokens ?? '?'} + ${completion_tokens}`
})
</script>

<template>
  <div class="bubble-row" :class="isUser ? 'user' : 'assistant'">
    <div class="avatar">{{ isUser ? '我' : '迦' }}</div>
    <div class="bubble" :class="{ streaming: message.status === 'streaming' }">
      <div v-if="isUser" class="plain">{{ message.content }}</div>
      <div v-else class="md" v-html="html"></div>
      <span v-if="message.status === 'streaming'" class="cursor">▍</span>
      <div v-if="message.status === 'aborted'" class="status-tag">已停止生成</div>
      <div v-if="tokens" class="status-tag">{{ tokens }}</div>
    </div>
  </div>
</template>

<style scoped>
.bubble-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}
.bubble-row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.assistant .avatar {
  background: #626aef;
}
.bubble {
  max-width: 76%;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.user .bubble {
  background: #d9ecff;
}
.assistant .bubble {
  background: #f5f7fa;
}
.plain {
  white-space: pre-wrap;
}
.cursor {
  display: inline-block;
  color: #409eff;
  animation: blink 1s step-start infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
.status-tag {
  margin-top: 6px;
  font-size: 11px;
  color: #909399;
}

/* markdown 内容 */
.md :deep(p) {
  margin: 0 0 8px;
}
.md :deep(p:last-child) {
  margin-bottom: 0;
}
.md :deep(pre) {
  background: #282c34;
  border-radius: 8px;
  padding: 12px;
  overflow-x: auto;
  margin: 8px 0;
}
.md :deep(pre code) {
  color: #abb2bf;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
}
.md :deep(code) {
  background: #e8eaee;
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 13px;
}
.md :deep(pre code) {
  background: transparent;
  padding: 0;
}
.md :deep(ul),
.md :deep(ol) {
  margin: 4px 0;
  padding-left: 22px;
}
.md :deep(blockquote) {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid #d0d3d9;
  color: #606266;
  background: #eceef1;
  border-radius: 4px;
}
.md :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
}
.md :deep(th),
.md :deep(td) {
  border: 1px solid #d0d3d9;
  padding: 4px 10px;
  font-size: 13px;
}
</style>
