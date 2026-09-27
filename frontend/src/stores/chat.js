import { defineStore } from 'pinia'
import { api } from '../api/client'
import { streamNdjson } from '../utils/stream'

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [],
    currentId: null,
    // 消息对象：{id, role, content, status, prompt_tokens, completion_tokens}
    messages: [],
    streaming: false,
    controller: null,
    error: '',
  }),
  actions: {
    async loadConversations() {
      this.conversations = await api.get('/api/conversations')
    },
    async openConversation(id) {
      if (this.streaming) this.stop()
      this.currentId = id
      this.error = ''
      this.messages = await api.get(`/api/conversations/${id}/messages`)
    },
    async newConversation() {
      if (this.streaming) this.stop()
      this.currentId = null
      this.messages = []
      this.error = ''
    },
    async renameConversation(id, title) {
      await api.patch(`/api/conversations/${id}`, { title })
      await this.loadConversations()
    },
    async deleteConversation(id) {
      await api.del(`/api/conversations/${id}`)
      if (this.currentId === id) {
        this.currentId = null
        this.messages = []
      }
      await this.loadConversations()
    },
    stop() {
      this.controller?.abort()
    },
    async sendMessage(content) {
      if (this.streaming || !content.trim()) return
      this.error = ''

      // 本地乐观插入；message_start 事件到达后替换为服务端真实 id
      this.messages.push({ id: -Date.now(), role: 'user', content })
      this.messages.push({ id: -Date.now() - 1, role: 'assistant', content: '', status: 'streaming' })
      // 从响应式数组取回代理引用，保证后续 mutation 触发视图更新
      const assistant = this.messages[this.messages.length - 1]

      this.streaming = true
      this.controller = new AbortController()
      try {
        await streamNdjson({
          url: '/api/chat/stream',
          body: { content, conversation_id: this.currentId },
          signal: this.controller.signal,
          onEvent: (evt) => this._handleEvent(evt, assistant),
        })
      } catch (err) {
        if (err.name === 'AbortError') {
          assistant.status = 'aborted'
          if (!assistant.content) assistant.content = '（已停止生成）'
        } else {
          this.error = err.message
          assistant.status = 'error'
          if (!assistant.content) assistant.content = `请求失败：${err.message}`
        }
      } finally {
        this.streaming = false
        this.controller = null
        if (assistant.status === 'streaming') assistant.status = 'ok'
        await this.loadConversations()
      }
    },
    _handleEvent(evt, assistant) {
      switch (evt.type) {
        case 'message_start':
          this.currentId = evt.conversation_id
          assistant.id = evt.message_id
          break
        case 'delta':
          assistant.content += evt.content
          break
        case 'usage':
          assistant.prompt_tokens = evt.prompt_tokens
          assistant.completion_tokens = evt.completion_tokens
          break
        case 'error':
          assistant.status = 'error'
          assistant.content += `\n\n> ⚠️ 生成失败：${evt.message}`
          break
        // ping / citations / done：MVP 无需处理
        default:
          break
      }
    },
  },
})
