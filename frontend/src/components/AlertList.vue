<script setup>
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'

const { isAdmin, adminToken } = inject('aiotAdmin')
const alerts = ref([])
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const processingId = ref(null)
const searchText = ref('')
const levelFilter = ref('all')
const statusFilter = ref('all')
let timer = null
let requestInProgress = false

const filteredAlerts = computed(() => alerts.value.filter((item) => {
  const keyword = searchText.value.trim().toLowerCase()
  const searchable = `${item.device_name ?? ''} ${item.alert_message ?? ''} ${item.id ?? ''}`.toLowerCase()
  return (!keyword || searchable.includes(keyword)) &&
    (levelFilter.value === 'all' || item.alert_level === levelFilter.value) &&
    (statusFilter.value === 'all' || item.status === statusFilter.value)
}))
const pendingCount = computed(() => alerts.value.filter(a => a.status === 'pending').length)
const resolvedCount = computed(() => alerts.value.filter(a => a.status !== 'pending').length)
const criticalCount = computed(() => alerts.value.filter(a => a.alert_level === 'critical').length)

async function loadAlerts() {
  if (requestInProgress) return
  requestInProgress = true
  refreshing.value = true
  try {
    const response = await fetch('/api/alerts')
    if (!response.ok) throw new Error(`获取告警数据失败 (${response.status})`)
    const data = await response.json()
    if (!Array.isArray(data)) throw new Error('告警数据格式错误')
    alerts.value = data
    error.value = ''
  } catch (err) {
    console.error(err)
    error.value = '告警数据加载失败，请检查后端服务'
  } finally {
    loading.value = false
    refreshing.value = false
    requestInProgress = false
  }
}

function levelText(level) {
  if (level === 'critical') return '严重告警'
  if (level === 'warning') return '一般告警'
  return '未知等级'
}
function typeText(type) {
  if (type === 'temperature') return '🌡️ 温度异常'
  if (type === 'humidity') return '💧 湿度异常'
  if (type === 'smoke') return '💨 烟雾异常'
  return '其他异常'
}
function formatTime(time) {
  if (!time) return '-'
  const date = new Date(time)
  return Number.isNaN(date.getTime()) ? String(time) : date.toLocaleString('zh-CN', { hour12: false })
}
async function resolveAlert(alertId) {
  if (!isAdmin.value) return
  if (processingId.value !== null) return
  processingId.value = alertId
  try {
    const response = await fetch(`/api/alerts/${alertId}/resolve`, { method: 'PATCH', headers: { 'Authorization': `Bearer ${adminToken.value}` } })
    if (!response.ok) throw new Error('告警处理失败')
    await loadAlerts()
  } catch (err) {
    console.error(err)
    window.alert('处理失败，请检查后端服务')
  } finally {
    processingId.value = null
  }
}
function clearFilters() {
  searchText.value = ''
  levelFilter.value = 'all'
  statusFilter.value = 'all'
}
onMounted(() => {
  loadAlerts()
  timer = setInterval(loadAlerts, 5000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <section class="aiot-alerts">
    <header class="aiot-alerts__header">
      <div>
        <p class="aiot-alerts__eyebrow">ALERT MANAGEMENT</p>
        <h2>设备告警管理</h2>
        <p class="aiot-alerts__sub">模拟设备异常记录 · 告警查询 · 处理状态跟踪</p>
      </div>
      <button class="aiot-alerts__refresh" type="button" :disabled="refreshing" @click="loadAlerts">
        {{ refreshing ? '刷新中...' : '↻ 刷新告警' }}
      </button>
    </header>

    <div class="aiot-alerts__stats">
      <div class="aiot-alerts__stat"><span>当前记录</span><strong>{{ alerts.length }}</strong><small>接口返回的告警条数</small></div>
      <div class="aiot-alerts__stat"><span>待处理</span><strong class="aiot-alerts__number--orange">{{ pendingCount }}</strong><small>需要人工确认</small></div>
      <div class="aiot-alerts__stat"><span>已处理</span><strong class="aiot-alerts__number--green">{{ resolvedCount }}</strong><small>已标记处理完成</small></div>
      <div class="aiot-alerts__stat"><span>严重告警</span><strong class="aiot-alerts__number--red">{{ criticalCount }}</strong><small>当前记录中严重等级</small></div>
    </div>

    <div class="aiot-alerts__panel">
      <div class="aiot-alerts__toolbar-head">
        <div><h3>告警记录</h3><p>支持设备名称、内容搜索与条件筛选</p></div>
        <span class="aiot-alerts__count">显示 {{ filteredAlerts.length }} / {{ alerts.length }} 条</span>
      </div>
      <div class="aiot-alerts__filters">
        <label class="aiot-alerts__field aiot-alerts__field--search">
          <span>搜索告警</span>
          <input v-model="searchText" type="search" placeholder="设备名称 / 告警内容 / 编号" />
        </label>
        <label class="aiot-alerts__field">
          <span>告警等级</span>
          <select v-model="levelFilter"><option value="all">全部等级</option><option value="critical">严重告警</option><option value="warning">一般告警</option></select>
        </label>
        <label class="aiot-alerts__field">
          <span>处理状态</span>
          <select v-model="statusFilter"><option value="all">全部状态</option><option value="pending">待处理</option><option value="resolved">已处理</option></select>
        </label>
        <button type="button" class="aiot-alerts__clear" @click="clearFilters">重置筛选</button>
      </div>

      <p v-if="loading" class="aiot-alerts__notice">正在加载告警数据...</p>
      <p v-if="error" class="aiot-alerts__notice aiot-alerts__notice--error" role="alert">{{ error }}（下方如有数据则为上次成功加载的记录）</p>
      <p v-if="!loading && !error && filteredAlerts.length === 0" class="aiot-alerts__notice">{{ alerts.length ? '没有符合筛选条件的告警' : '暂无告警记录' }}</p>

      <div v-if="filteredAlerts.length" class="aiot-alerts__table-scroll">
        <table class="aiot-alerts__table">
          <thead><tr><th>设备名称</th><th>告警类型</th><th>告警等级</th><th>告警内容</th><th>发生时间</th><th>处理状态</th></tr></thead>
          <tbody>
            <tr v-for="alert in filteredAlerts" :key="alert.id">
              <td class="aiot-alerts__device">{{ alert.device_name || '未知设备' }}</td>
              <td>{{ typeText(alert.alert_type) }}</td>
              <td><span class="aiot-alerts__level" :class="'aiot-alerts__level--' + alert.alert_level">{{ levelText(alert.alert_level) }}</span></td>
              <td class="aiot-alerts__message">{{ alert.alert_message }}</td>
              <td class="aiot-alerts__time">{{ formatTime(alert.created_at) }}</td>
              <td>
                <button v-if="isAdmin && alert.status === 'pending'" class="aiot-alerts__resolve" type="button" :disabled="processingId !== null" @click="resolveAlert(alert.id)">{{ processingId === alert.id ? '处理中...' : '处理完成' }}</button>
                <span v-else-if="alert.status !== 'pending'" class="aiot-alerts__resolved">✓ 已处理</span><span v-else>待处理（只读）</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="aiot-alerts__footnote">数据来源：数据库模拟设备告警；页面每 5 秒自动刷新。处理完成仅更新记录状态，不代表现场故障已经排除。</div>
    </div>
  </section>
</template>

<style>
.aiot-alerts { width:100%; min-width:0; color:#e8f1ff; font-size:14px; }
.aiot-alerts *, .aiot-alerts *::before, .aiot-alerts *::after { box-sizing:border-box; }
.aiot-alerts__header { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:22px; }
.aiot-alerts__eyebrow { margin:0 0 8px; color:#48b6ff; font-size:11px; font-weight:800; letter-spacing:2px; }
.aiot-alerts__header h2 { margin:0 0 7px; color:#f4f8ff; font-size:23px; font-weight:700; }
.aiot-alerts__sub { margin:0; color:#8ea7c8; font-size:13px; }
.aiot-alerts__refresh, .aiot-alerts__clear { border:1px solid #294969; background:#193553; color:#a8d8ff; border-radius:9px; padding:11px 15px; cursor:pointer; white-space:nowrap; font:inherit; }
.aiot-alerts__refresh:hover, .aiot-alerts__clear:hover { background:#244668; }
.aiot-alerts button:disabled { opacity:.5; cursor:not-allowed; }
.aiot-alerts__stats { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:20px; }
.aiot-alerts__stat { display:flex; flex-direction:column; gap:9px; padding:19px 20px; background:#13243b; border:1px solid #273e5b; border-radius:13px; }
.aiot-alerts__stat span { color:#91a9c7; font-size:13px; }
.aiot-alerts__stat strong { font-size:31px; line-height:1.2; font-weight:700; color:#f4f8ff; }
.aiot-alerts__stat small { color:#6e8cac; font-size:12px; }
.aiot-alerts__stat .aiot-alerts__number--orange { color:#ffbd64; }
.aiot-alerts__stat .aiot-alerts__number--green { color:#44d6a2; }
.aiot-alerts__stat .aiot-alerts__number--red { color:#ff8181; }
.aiot-alerts__panel { padding:22px; background:#16263d; border:1px solid #2a3d59; border-radius:15px; }
.aiot-alerts__toolbar-head { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:18px; }
.aiot-alerts__toolbar-head h3 { margin:0 0 6px; font-size:18px; color:#f1f7ff; }
.aiot-alerts__toolbar-head p { margin:0; font-size:12px; color:#8ea7c8; }
.aiot-alerts__count { border:1px solid #315479; background:#193553; padding:7px 12px; border-radius:8px; white-space:nowrap; color:#a7d4ff; }
.aiot-alerts__filters { display:grid; grid-template-columns:minmax(180px,2fr) minmax(140px,1fr) minmax(140px,1fr) auto; gap:12px; align-items:end; margin-bottom:20px; }
.aiot-alerts__field { display:flex; flex-direction:column; min-width:0; gap:8px; color:#a9bdd6; font-size:12px; }
.aiot-alerts__field input, .aiot-alerts__field select { width:100%; height:43px; padding:0 12px; border:1px solid #2b4565; border-radius:9px; outline:none; color:#edf5ff; background:#0c192d; font:inherit; font-size:13px; }
.aiot-alerts__field input:focus, .aiot-alerts__field select:focus { border-color:#40a9ff; }
.aiot-alerts__field input::placeholder { color:#728ba9; }
.aiot-alerts__clear { height:43px; }
.aiot-alerts__notice { margin:12px 0; padding:22px; border-radius:9px; text-align:center; color:#9ab1cc; background:#0d1b30; }
.aiot-alerts__notice--error { color:#ffaaa8; background:#382330; }
.aiot-alerts__table-scroll { width:100%; overflow-x:auto; }
.aiot-alerts__table { width:100%; min-width:850px; border-collapse:collapse; table-layout:auto; font-size:13px; }
.aiot-alerts__table th { padding:15px 12px; text-align:left; background:#233751; color:#a8c1de; font-weight:600; white-space:nowrap; }
.aiot-alerts__table th:first-child { border-radius:7px 0 0 0; }
.aiot-alerts__table th:last-child { border-radius:0 7px 0 0; }
.aiot-alerts__table td { padding:16px 12px; border-bottom:1px solid #2b3e57; color:#dbe8f8; vertical-align:middle; }
.aiot-alerts__table tbody tr:hover { background:#1d3450; }
.aiot-alerts__device { font-weight:600; white-space:nowrap; }
.aiot-alerts__message { min-width:210px; line-height:1.6; overflow-wrap:anywhere; }
.aiot-alerts__time { white-space:nowrap; color:#9eb6d3 !important; }
.aiot-alerts__level { display:inline-block; border-radius:6px; padding:6px 9px; font-size:12px; font-weight:700; white-space:nowrap; color:#a8bed8; background:#34465d; }
.aiot-alerts__level--critical { color:#ffb4b4; background:#642731; }
.aiot-alerts__level--warning { color:#ffd18c; background:#653e1d; }
.aiot-alerts__resolve { padding:9px 13px; border:1px solid #3579e2; border-radius:8px; background:#2056ba; color:#fff; font:inherit; cursor:pointer; white-space:nowrap; }
.aiot-alerts__resolve:hover { background:#2868d5; }
.aiot-alerts__resolved { color:#48d7a4; font-weight:600; white-space:nowrap; }
.aiot-alerts__footnote { padding-top:16px; color:#7e9bbd; font-size:12px; line-height:1.6; }
@media(max-width:1000px) { .aiot-alerts__stats { grid-template-columns:repeat(2,minmax(0,1fr)); } .aiot-alerts__filters { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media(max-width:560px) { .aiot-alerts__header { align-items:flex-start; flex-direction:column; } .aiot-alerts__stats { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; } .aiot-alerts__stat { padding:13px; } .aiot-alerts__panel { padding:12px; } .aiot-alerts__filters { grid-template-columns:1fr; } }
</style>
