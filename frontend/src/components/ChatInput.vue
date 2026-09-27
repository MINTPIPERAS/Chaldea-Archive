<script setup>
import { ref } from 'vue'
import { Promotion, VideoPause } from '@element-plus/icons-vue'
import { useChatStore } from '../stores/chat'

const chat = useChatStore()
const draft = ref('')

function onKeydown(e) {
  // isComposing：中文输入法选词回车不发送
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

async function send() {
  const content = draft.value.trim()
  if (!content || chat.streaming) return
  draft.value = ''
  await chat.sendMessage(content)
}
</script>

<template>
  <div class="input-bar">
    <el-input
      v-model="draft"
      type="textarea"
      resize="none"
      :autosize="{ minRows: 1, maxRows: 6 }"
      placeholder="输入问题，Enter 发送，Shift + Enter 换行"
      @keydown="onKeydown"
    />
    <el-button
      v-if="chat.streaming"
      type="danger"
      :icon="VideoPause"
      class="send-btn"
      @click="chat.stop()"
    >
      停止
    </el-button>
    <el-button
      v-else
      type="primary"
      :icon="Promotion"
      class="send-btn"
      :disabled="!draft.trim()"
      @click="send"
    >
      发送
    </el-button>
  </div>
</template>

<style scoped>
.input-bar {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 14px 24px 18px;
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
}
.send-btn {
  height: 40px;
}
</style>
