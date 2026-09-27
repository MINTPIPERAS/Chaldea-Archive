<script setup>
import { ChatDotRound, Delete, Plus, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useChatStore } from '../stores/chat'

defineProps({ active: { type: String, default: 'chat' } })
const emit = defineEmits(['open-settings'])
const chat = useChatStore()

async function onOpen(conv) {
  await chat.openConversation(conv.id)
}

async function onDelete(conv) {
  try {
    await ElMessageBox.confirm(`删除会话「${conv.title}」？删除后不可恢复。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await chat.deleteConversation(conv.id)
  ElMessage.success('已删除')
}
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-name">迦勒底档案</div>
      <div class="brand-sub">Chaldea Archive</div>
    </div>

    <el-button class="new-btn" type="primary" plain :icon="Plus" @click="chat.newConversation()">
      新对话
    </el-button>

    <div class="list">
      <div
        v-for="conv in chat.conversations"
        :key="conv.id"
        class="item"
        :class="{ active: conv.id === chat.currentId && active === 'chat' }"
        @click="onOpen(conv)"
      >
        <el-icon class="item-icon"><ChatDotRound /></el-icon>
        <span class="item-title">{{ conv.title }}</span>
        <el-icon class="item-del" title="删除" @click.stop="onDelete(conv)"><Delete /></el-icon>
      </div>
      <div v-if="!chat.conversations.length" class="empty-tip">暂无会话</div>
    </div>

    <el-button class="settings-btn" :icon="Setting" @click="emit('open-settings')">
      API 设置
    </el-button>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #1f2430;
  color: #d4d7de;
  padding: 16px 12px;
}
.brand {
  padding: 4px 8px 16px;
}
.brand-name {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}
.brand-sub {
  font-size: 12px;
  color: #8a90a0;
}
.new-btn {
  width: 100%;
  margin-bottom: 12px;
  border-color: #4c5164;
  color: #d4d7de;
}
.list {
  flex: 1;
  overflow-y: auto;
}
.item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #b9bdc9;
}
.item:hover {
  background: #2b3040;
}
.item.active {
  background: #343b4f;
  color: #fff;
}
.item-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-del {
  opacity: 0;
  color: #8a90a0;
}
.item:hover .item-del {
  opacity: 1;
}
.item-del:hover {
  color: #f56c6c;
}
.empty-tip {
  text-align: center;
  color: #6b7180;
  font-size: 12px;
  padding: 24px 0;
}
.settings-btn {
  width: 100%;
  margin-top: 12px;
  border-color: #4c5164;
  color: #d4d7de;
  background: transparent;
}
</style>
