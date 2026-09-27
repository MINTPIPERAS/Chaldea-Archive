<script setup>
import { onMounted, ref } from 'vue'
import { useChatStore } from './stores/chat'
import { useSettingsStore } from './stores/settings'
import SessionList from './components/SessionList.vue'
import ChatView from './views/ChatView.vue'
import SettingsView from './views/SettingsView.vue'

const chat = useChatStore()
const settings = useSettingsStore()
const view = ref('chat') // chat | settings

onMounted(() => {
  chat.loadConversations()
  settings.load()
})
</script>

<template>
  <div class="app-shell">
    <SessionList :active="view" @open-settings="view = 'settings'" />
    <main class="main-area">
      <SettingsView v-if="view === 'settings'" @back="view = 'chat'" />
      <ChatView v-else @open-settings="view = 'settings'" />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: 100%;
}
.main-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}
</style>
