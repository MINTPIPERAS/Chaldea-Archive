import { defineStore } from 'pinia'
import { api } from '../api/client'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    configs: [],
    loaded: false,
  }),
  getters: {
    defaultConfig: (state) => state.configs.find((c) => c.is_default) || state.configs[0] || null,
  },
  actions: {
    async load() {
      this.configs = await api.get('/api/settings/api-configs')
      this.loaded = true
    },
    async create(payload) {
      await api.post('/api/settings/api-configs', payload)
      await this.load()
    },
    async update(id, payload) {
      await api.put(`/api/settings/api-configs/${id}`, payload)
      await this.load()
    },
    async remove(id) {
      await api.del(`/api/settings/api-configs/${id}`)
      await this.load()
    },
    async test(payload) {
      return api.post('/api/settings/api-configs/test', payload)
    },
  },
})
