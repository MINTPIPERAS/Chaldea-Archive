<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import { useChatStore } from '../stores/chat'
import { useSettingsStore } from '../stores/settings'
import MessageBubble from '../components/MessageBubble.vue'
import ChatInput from '../components/ChatInput.vue'

const emit = defineEmits(['open-settings'])
const chat = useChatStore()
const settings = useSettingsStore()

const currentConv = computed(() => chat.conversations.find((c) => c.id === chat.currentId))
const configLabel = computed(() => {
  if (!settings.defaultConfig) return 'mock 模式（未配置 API）'
  return `${settings.defaultConfig.name} · ${settings.defaultConfig.model}`
})

// 自动滚动：仅当用户本来就在底部时跟随
const messagesEl = ref(null)
let shouldStick = true

function onScroll() {
  const el = messagesEl.value
  if (!el) return
  shouldStick = el.scrollHeight - el.scrollTop - el.clientHeight < 50
}

watch(
  () => chat.messages.map((m) => m.content.length).join(','),
  async () => {
    if (!shouldStick) return
    await nextTick()
    const el = messagesEl.value
    if (el) el.scrollTop = el.scrollHeight
  }
)
</script>

<template>
  <div class="chat-view">
    <header class="chat-header">
      <div class="conv-title">{{ currentConv?.title || '新对话' }}</div>
      <el-tag size="small" type="info" effect="plain">{{ configLabel }}</el-tag>
      <el-button text :icon="Setting" @click="emit('open-settings')">设置</el-button>
    </header>

    <el-alert
      v-if="chat.error"
      :title="chat.error"
      type="error"
      show-icon
      closable
      class="error-alert"
      @close="chat.error = ''"
    />

    <div v-if="chat.messages.length" ref="messagesEl" class="messages" @scroll="onScroll">
      <MessageBubble v-for="(m, idx) in chat.messages" :key="idx" :message="m" />
    </div>
    <div v-else class="empty">
      <h1>迦勒底档案</h1>
      <p>FGO × Type-Moon 智能检索问答 · RAG 检索建设中，当前为纯对话模式</p>
      <p class="hint">
        未配置 API 时自动使用 mock 流式演示；
        在「API 设置」中填入任意 OpenAI 兼容服务（DeepSeek / OpenRouter / SiliconFlow / Ollama…）即可真实对话。
      </p>
    </div>

    <ChatInput />
  </div>
</template>

<style scoped>
.chat-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  border-bottom: 1px solid #ebeef5;
}
.conv-title {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.error-alert {
  margin: 10px 24px 0;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 24px 6px;
}
.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  padding: 0 40px;
  text-align: center;
}
.empty h1 {
  color: #303133;
  font-size: 26px;
  margin: 0 0 12px;
}
.empty p {
  margin: 4px 0;
  max-width: 560px;
  line-height: 1.8;
}
.empty .hint {
  font-size: 13px;
}
</style>
