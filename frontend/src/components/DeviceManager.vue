<script setup>
import { ref, computed, onMounted, nextTick, inject } from 'vue'

const { isAdmin, adminToken } = inject('aiotAdmin')
const devices = ref([])
const loading = ref(false)
const fetching = ref(false)
const error = ref('')
const success = ref('')
const editingId = ref(null)
const search = ref('')
const typeFilter = ref('all')
const formRef = ref(null)
const form = ref({ name: '', location: '', description: '', device_type: 'temperature_humidity' })

const filteredDevices = computed(() => devices.value.filter(device => {
  const keyword = search.value.trim().toLowerCase()
  const matchesKeyword = !keyword || String(device.id).includes(keyword) ||
    String(device.name || '').toLowerCase().includes(keyword) ||
    String(device.location || '').toLowerCase().includes(keyword)
  return matchesKeyword && (typeFilter.value === 'all' || device.device_type === typeFilter.value)
}))

const temperatureCount = computed(() => devices.value.filter(d => d.device_type === 'temperature_humidity').length)
const smokeCount = computed(() => devices.value.filter(d => d.device_type === 'smoke').length)

async function loadDevices() {
  fetching.value = true
  try {
    const response = await fetch('/api/devices/manage')
    if (!response.ok) throw new Error('加载设备失败')
    const data = await response.json()
    if (!Array.isArray(data)) throw new Error('设备列表格式不正确')
    devices.value = data
    error.value = ''
  } catch (err) {
    error.value = err.message || '加载设备失败'
  } finally {
    fetching.value = false
  }
}

function resetForm() {
  editingId.value = null
  form.value = { name: '', location: '', description: '', device_type: 'temperature_humidity' }
}

async function editDevice(device) {
  if (!isAdmin.value) return
  editingId.value = device.id
  success.value = ''
  form.value = {
    name: device.name,
    location: device.location || '',
    description: device.description || '',
    device_type: device.device_type || 'temperature_humidity'
  }
  await nextTick()
  formRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

async function saveDevice() {
  if (!isAdmin.value) return
  if (!form.value.name.trim() || loading.value) return
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    const isEditing = editingId.value !== null
    const url = isEditing ? `/api/devices/manage/${editingId.value}` : '/api/devices/create'
    const response = await fetch(url, {
      method: isEditing ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${adminToken.value}` },
      body: JSON.stringify(form.value)
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(typeof data.detail === 'string' ? data.detail : '保存失败')
    }
    resetForm()
    await loadDevices()
    success.value = isEditing ? '设备信息已更新' : '设备已添加'
  } catch (err) {
    error.value = err.message || '保存失败'
  } finally {
    loading.value = false
  }
}

async function deleteDevice(device) {
  if (!isAdmin.value) return
  if (device.id <= 3 || loading.value) return
  if (!window.confirm(`确定删除设备“${device.name}”吗？此操作不可撤销。`)) return
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    const response = await fetch(`/api/devices/manage/${device.id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${adminToken.value}` } })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(typeof data.detail === 'string' ? data.detail : '删除失败')
    }
    if (editingId.value === device.id) resetForm()
    await loadDevices()
    success.value = `设备“${device.name}”已删除`
  } catch (err) {
    error.value = err.message || '删除失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadDevices)
</script>

<template>
  <section class="dm-manager">
    <header class="dm-header">
      <div>
        <div class="dm-eyebrow">DEVICE REGISTRY</div>
        <h2>设备信息管理</h2>
        <p>维护模拟设备档案，管理设备名称、类型、安装位置和描述</p>
      </div>
      <button class="dm-refresh" type="button" :disabled="fetching || loading" @click="loadDevices">
        {{ fetching ? '刷新中…' : '↻ 刷新列表' }}
      </button>
    </header>

    <div class="dm-summary">
      <div class="dm-summary-item"><span>设备档案</span><strong>{{ devices.length }}</strong><small>数据库记录</small></div>
      <div class="dm-summary-item"><span>温湿度传感器</span><strong>{{ temperatureCount }}</strong><small>模拟设备</small></div>
      <div class="dm-summary-item"><span>烟雾传感器</span><strong>{{ smokeCount }}</strong><small>模拟设备</small></div>
    </div>

    <p v-if="error" class="dm-message dm-error" role="alert">{{ error }}</p>
    <p v-if="success" class="dm-message dm-success" role="status">{{ success }}</p>

    <div class="dm-workspace">
      <div v-if="isAdmin" ref="formRef" class="dm-panel dm-editor">
        <div class="dm-panel-head">
          <div>
            <h3>{{ editingId === null ? '新增设备' : '编辑设备' }}</h3>
            <p>{{ editingId === null ? '填写设备基础档案' : `正在编辑设备 #${editingId}` }}</p>
          </div>
          <span class="dm-pill">{{ editingId === null ? '新增' : '修改' }}</span>
        </div>

        <form class="dm-form" @submit.prevent="saveDevice">
          <label for="dm-name">设备名称 <em>*</em></label>
          <input id="dm-name" v-model="form.name" placeholder="请输入设备名称" maxlength="100" required />

          <label for="dm-type">设备类型</label>
          <select id="dm-type" v-model="form.device_type">
            <option value="temperature_humidity">温湿度传感器</option>
            <option value="smoke">烟雾传感器</option>
          </select>

          <label for="dm-location">安装位置</label>
          <input id="dm-location" v-model="form.location" placeholder="例如：实验室 B 区" />

          <label for="dm-description">设备描述</label>
          <textarea id="dm-description" v-model="form.description" rows="3" placeholder="填写设备用途、备注等信息"></textarea>

          <div class="dm-form-actions">
            <button class="dm-primary" type="submit" :disabled="loading || !form.name.trim()">
              {{ loading ? '处理中…' : editingId === null ? '+ 新增设备' : '保存修改' }}
            </button>
            <button v-if="editingId !== null" class="dm-secondary" type="button" :disabled="loading" @click="resetForm">取消修改</button>
          </div>
        </form>
        <p class="dm-form-note">这里管理的是数据库模拟设备档案，不会改变 ESP32-S3 的硬件配置。</p>
      </div>

      <div class="dm-panel dm-registry">
        <p v-if="!isAdmin" class="dm-table-note">当前为游客只读模式。登录管理员账号后可新增、修改和删除设备。</p>
        <div class="dm-panel-head">
          <div>
            <h3>设备档案列表</h3>
            <p>支持按设备编号、名称和安装位置搜索</p>
          </div>
          <span class="dm-count">{{ filteredDevices.length }} / {{ devices.length }} 台</span>
        </div>
        <div class="dm-filters">
          <input v-model="search" aria-label="搜索设备" placeholder="⌕ 搜索设备名称 / ID / 安装位置" />
          <select v-model="typeFilter" aria-label="设备类型筛选">
            <option value="all">全部类型</option>
            <option value="temperature_humidity">温湿度传感器</option>
            <option value="smoke">烟雾传感器</option>
          </select>
        </div>
        <div class="dm-table-scroll">
          <table class="dm-table">
            <thead><tr><th>ID</th><th>设备名称</th><th>类型</th><th>安装位置</th><th>设备描述</th><th v-if="isAdmin">操作</th></tr></thead>
            <tbody>
              <tr v-for="device in filteredDevices" :key="device.id">
                <td><span class="dm-id">#{{ device.id }}</span></td>
                <td class="dm-name">{{ device.name }}</td>
                <td><span class="dm-type">{{ device.device_type === 'smoke' ? '烟雾传感器' : '温湿度传感器' }}</span></td>
                <td>{{ device.location || '未设置' }}</td>
                <td class="dm-description" :title="device.description || ''">{{ device.description || '无' }}</td>
                <td v-if="isAdmin">
                  <div class="dm-row-actions">
                    <button type="button" class="dm-edit" :disabled="loading" @click="editDevice(device)">修改</button>
                    <button type="button" class="dm-delete" :disabled="device.id <= 3 || loading" :title="device.id <= 3 ? '系统预置设备不可删除' : '删除设备'" @click="deleteDevice(device)">删除</button>
                  </div>
                </td>
              </tr>
              <tr v-if="!filteredDevices.length"><td  :colspan="isAdmin ? 6 : 5" class="dm-empty">{{ fetching ? '正在加载设备…' : '没有符合条件的设备' }}</td></tr>
            </tbody>
          </table>
        </div>
        <p class="dm-table-note">说明：系统预置的 1～3 号设备不可删除；删除其他设备前需要确认。</p>
      </div>
    </div>
  </section>
</template>

<style>
.dm-manager { margin-top: 24px; padding: 26px; border: 1px solid #263952; border-radius: 18px; background: #142137; color: #e9f2ff; min-width: 0; }
.dm-header,.dm-panel-head { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }
.dm-eyebrow { color:#4bb5ff; font-size:11px; font-weight:800; letter-spacing:2px; margin-bottom:8px; }
.dm-header h2 { margin:0; font-size:23px; font-weight:750; }
.dm-header p,.dm-panel-head p { margin:7px 0 0; color:#8ea6c4; font-size:13px; line-height:1.6; }
.dm-refresh { background:#1c3451; border:1px solid #35516f; color:#b7d9f9; padding:10px 14px; border-radius:9px; white-space:nowrap; cursor:pointer; }
.dm-summary { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin:23px 0; }
.dm-summary-item { background:#0e1b2f; border:1px solid #293b55; border-radius:12px; padding:16px 18px; display:flex; flex-direction:column; gap:5px; }
.dm-summary-item span { color:#9eb4d1; font-size:13px; }.dm-summary-item strong { font-size:29px; line-height:1.3; }.dm-summary-item small { color:#6687ad; font-size:11px; }
.dm-workspace { display:grid; grid-template-columns:minmax(270px,0.85fr) minmax(0,2fr); align-items:start; gap:18px; }
.dm-panel { min-width:0; background:#101d32; border:1px solid #2a3c55; border-radius:14px; padding:20px; }
.dm-panel-head { margin-bottom:20px; }.dm-panel-head h3 { margin:0; font-size:17px; }
.dm-pill,.dm-count { border:1px solid #2c5681; color:#79c4ff; background:#173450; padding:6px 10px; border-radius:8px; font-size:12px; white-space:nowrap; }
.dm-form { display:flex; flex-direction:column; gap:9px; }.dm-form label { color:#b8cbe3; font-size:12px; margin-top:7px; }.dm-form label em { color:#ff9b8d; font-style:normal; }
.dm-form input,.dm-form select,.dm-form textarea,.dm-filters input,.dm-filters select { width:100%; min-width:0; border:1px solid #344860; border-radius:9px; background:#0b1628; color:#eef6ff; padding:11px 12px; font:inherit; font-size:13px; outline:none; }
.dm-form input:focus,.dm-form select:focus,.dm-form textarea:focus,.dm-filters input:focus,.dm-filters select:focus { border-color:#3caaff; box-shadow:0 0 0 2px #3caaff22; }
.dm-form textarea { resize:vertical; min-height:75px; }.dm-form-actions,.dm-row-actions { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }.dm-form-actions { margin-top:14px; }
.dm-primary,.dm-secondary,.dm-edit,.dm-delete { border:1px solid transparent; border-radius:8px; padding:9px 13px; font:inherit; font-size:12px; font-weight:650; cursor:pointer; white-space:nowrap; }
.dm-primary { background:#2673e8; color:white; }.dm-secondary { background:#25364f; color:#d1e3f9; }.dm-edit { background:#1c426a; color:#7bc4ff; border-color:#32608c; }.dm-delete { background:#53252e; color:#ffb5b5; border-color:#70303a; }
button:disabled { opacity:.38; cursor:not-allowed; }.dm-form-note,.dm-table-note { margin:16px 0 0; font-size:11px; color:#7792b2; line-height:1.7; }
.dm-filters { display:grid; grid-template-columns:minmax(0,1fr) 155px; gap:10px; margin-bottom:14px; }.dm-table-scroll { overflow-x:auto; }
.dm-table { width:100%; min-width:670px; border-collapse:collapse; font-size:12px; }.dm-table th { color:#94aac7; font-weight:600; text-align:left; background:#1b2d45; }.dm-table th,.dm-table td { padding:13px 10px; border-bottom:1px solid #2a3b52; vertical-align:middle; }.dm-table td { color:#d6e4f7; }.dm-table tr:hover td { background:#182a42; }
.dm-id { color:#7c9fcb; }.dm-name { font-weight:700; }.dm-type { color:#a5d2f9; background:#1a3551; border-radius:6px; padding:5px 7px; white-space:nowrap; }.dm-description { max-width:160px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.dm-empty { text-align:center; padding:34px!important; color:#91a8c5!important; }
.dm-message { padding:11px 14px; border-radius:8px; font-size:13px; }.dm-error { color:#ffb5b5; background:#52262b; }.dm-success { color:#7be6bb; background:#163e35; }
@media (max-width:1200px) { .dm-workspace { grid-template-columns:1fr; } }
@media (max-width:650px) { .dm-manager { padding:15px; }.dm-summary { gap:8px; }.dm-summary-item { padding:12px; }.dm-filters { grid-template-columns:1fr; }.dm-header { flex-wrap:wrap; } }
</style>
