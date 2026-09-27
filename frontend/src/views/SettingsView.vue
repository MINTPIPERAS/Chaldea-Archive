<script setup>
import { Back, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reactive, ref } from 'vue'
import { useSettingsStore } from '../stores/settings'

const emit = defineEmits(['back'])
const settings = useSettingsStore()

const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const testing = ref(false)

const PROVIDER_OPTIONS = [
  { value: 'openai-compatible', label: 'OpenAI 兼容（DeepSeek / OpenRouter / SiliconFlow / Ollama…）' },
  { value: 'mock', label: 'Mock 演示（不调用外部 API）' },
  { value: 'anthropic', label: 'Anthropic（待实现）', disabled: true },
  { value: 'gemini', label: 'Gemini（待实现）', disabled: true },
]

function blank() {
  return {
    name: '',
    provider_kind: 'openai-compatible',
    base_url: 'https://api.siliconflow.cn/v1',
    api_key: '',
    model: 'deepseek-ai/DeepSeek-V3',
    temperature: 0.7,
    max_tokens: null,
    system_prompt: '',
    is_default: false,
  }
}
const form = reactive(blank())

function openCreate() {
  Object.assign(form, blank())
  editingId.value = null
  dialogVisible.value = true
}

function openEdit(cfg) {
  Object.assign(form, cfg)
  editingId.value = cfg.id
  dialogVisible.value = true
}

function onProviderChange(kind) {
  if (kind === 'mock') form.model = 'mock-1'
  else if (!form.model || form.model === 'mock-1') form.model = 'deepseek-ai/DeepSeek-V3'
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写配置名称')
    return
  }
  if (form.provider_kind !== 'mock' && !form.model.trim()) {
    ElMessage.warning('请填写模型名')
    return
  }
  saving.value = true
  try {
    const payload = { ...form }
    if (payload.provider_kind === 'mock' && !payload.model.trim()) payload.model = 'mock-1'
    if (editingId.value) await settings.update(editingId.value, payload)
    else await settings.create(payload)
    ElMessage.success('已保存')
    dialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    saving.value = false
  }
}

async function test(cfg) {
  testing.value = true
  try {
    const payload = cfg
      ? { id: cfg.id }
      : { id: editingId.value, ...form }
    const res = await settings.test(payload)
    if (res.ok) ElMessage.success(res.message)
    else ElMessage.error(res.message)
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    testing.value = false
  }
}

async function remove(cfg) {
  try {
    await ElMessageBox.confirm(`删除配置「${cfg.name}」？`, '确认删除', { type: 'warning' })
  } catch {
    return
  }
  await settings.remove(cfg.id)
  ElMessage.success('已删除')
}
</script>

<template>
  <div class="settings-view">
    <header class="header">
      <el-button text :icon="Back" @click="emit('back')">返回</el-button>
      <div class="title">API 设置</div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建配置</el-button>
    </header>

    <div class="body">
      <el-alert
        type="info"
        show-icon
        :closable="false"
        title="BYOK（自带 Key）：支持一切 OpenAI 兼容服务，填对 Base URL 即可。API Key 仅保存在本地数据库。"
        class="tip"
      />

      <el-empty v-if="!settings.configs.length" description="还没有配置，先新建一个吧" />

      <div v-for="cfg in settings.configs" :key="cfg.id" class="card">
        <div class="card-main">
          <div class="card-title">
            {{ cfg.name }}
            <el-tag v-if="cfg.is_default" size="small" type="success">默认</el-tag>
            <el-tag size="small" type="info">{{ cfg.provider_kind }}</el-tag>
          </div>
          <div class="card-sub">
            {{ cfg.model }}<span v-if="cfg.base_url"> · {{ cfg.base_url }}</span>
          </div>
        </div>
        <div class="card-actions">
          <el-button size="small" :loading="testing" @click="test(cfg)">测试连接</el-button>
          <el-button size="small" @click="openEdit(cfg)">编辑</el-button>
          <el-button size="small" type="danger" plain @click="remove(cfg)">删除</el-button>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑配置' : '新建配置'"
      width="560px"
    >
      <el-form label-width="110px" label-position="left">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="例如：DeepSeek 官方" />
        </el-form-item>
        <el-form-item label="Provider">
          <el-select v-model="form.provider_kind" @change="onProviderChange">
            <el-option
              v-for="opt in PROVIDER_OPTIONS"
              :key="opt.value"
              :value="opt.value"
              :label="opt.label"
              :disabled="opt.disabled"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.provider_kind !== 'mock'" label="Base URL">
          <el-input v-model="form.base_url" placeholder="https://api.siliconflow.cn/v1" />
        </el-form-item>
        <el-form-item v-if="form.provider_kind !== 'mock'" label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            placeholder="sk-..."
          />
        </el-form-item>
        <el-form-item label="模型" :required="form.provider_kind !== 'mock'">
          <el-input v-model="form.model" placeholder="deepseek-ai/DeepSeek-V3" />
        </el-form-item>
        <el-form-item label="Temperature">
          <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" />
        </el-form-item>
        <el-form-item label="Max Tokens">
          <el-input-number v-model="form.max_tokens" :min="0" :step="256" placeholder="留空跟随服务端" />
        </el-form-item>
        <el-form-item label="System Prompt">
          <el-input
            v-model="form.system_prompt"
            type="textarea"
            :rows="3"
            placeholder="留空使用默认提示词"
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :loading="testing" @click="test(null)">测试连接</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.settings-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  border-bottom: 1px solid #ebeef5;
}
.title {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
}
.body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
}
.tip {
  margin-bottom: 16px;
}
.card {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.card-main {
  flex: 1;
  min-width: 0;
}
.card-title {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-sub {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-actions {
  flex-shrink: 0;
}
</style>
