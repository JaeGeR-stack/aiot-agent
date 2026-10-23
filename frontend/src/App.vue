<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick, provide } from 'vue'
import * as echarts from 'echarts'
import HistoryChart from './components/HistoryChart.vue'
import AiChat from './components/AiChat.vue'
import AlertList from './components/AlertList.vue'
import AlertStatistics from './components/AlertStatistics.vue'
import DeviceManager from './components/DeviceManager.vue'

const adminToken = ref('')
const isAdmin = computed(() => Boolean(adminToken.value))
const loginOpen = ref(false)
const loginPassword = ref('')
const loginError = ref('')
const loginBusy = ref(false)
provide('aiotAdmin', { isAdmin, adminToken })
async function loginAdmin() {
  if (!loginPassword.value || loginBusy.value) return
  loginBusy.value = true
  loginError.value = ''
  try {
    const response = await fetch('/api/admin/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: loginPassword.value })
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || '登录失败')
    adminToken.value = data.access_token
    loginPassword.value = ''
    loginOpen.value = false
  } catch (e) { loginError.value = e.message || '登录失败' }
  finally { loginBusy.value = false }
}
function logoutAdmin() { adminToken.value = ''; loginPassword.value = ''; loginOpen.value = false }
const activeSection = ref('overview')
const navItems = [
  { id: 'overview', label: '监控总览', icon: '▦', group: 'workspace' },
  { id: 'realtime', label: '实时传感器', icon: '◉', group: 'workspace' },
  { id: 'trends', label: '历史趋势', icon: '⌁', group: 'workspace' },
  { id: 'devices', label: '设备管理', icon: '▤', group: 'manage' },
  { id: 'alerts', label: '告警中心', icon: '⚑', group: 'manage' },
  { id: 'ai', label: 'AI 智能分析', icon: '✧', group: 'manage' },
]
function navigateTo(id) {
  activeSection.value = id
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
const clock = ref(new Date())
let clockTimer = null
const formattedClock = computed(() => clock.value.toLocaleString('zh-CN', { hour12: false }))
const normalCount = computed(() => devices.value.filter(d => d.status === 'normal').length)
const warningCount = computed(() => devices.value.filter(d => d.status === 'warning').length)
const offlineCount = computed(() => devices.value.filter(d => d.status === 'offline').length)
const latestTimestamp = computed(() => realSensor.value?.timestamp ? new Date(realSensor.value.timestamp).toLocaleString('zh-CN', { hour12: false }) : '暂无采样')
const devices = ref([])
const deviceSearch = ref('')
const deviceStatusFilter = ref('all')
const filteredDevices = computed(() => devices.value.filter(device => {
  const keyword = deviceSearch.value.trim().toLowerCase()
  const matchesKeyword = !keyword || String(device.name || '').toLowerCase().includes(keyword) || String(device.device_id ?? '').includes(keyword)
  const matchesStatus = deviceStatusFilter.value === 'all' || device.status === deviceStatusFilter.value
  return matchesKeyword && matchesStatus
}))
function formatDeviceTime(timestamp) {
  if (!timestamp) return '暂无记录'
  const date = new Date(timestamp)
  return Number.isNaN(date.getTime()) ? String(timestamp) : date.toLocaleString('zh-CN', { hour12: false })
}
const selectedDeviceId = ref(1)
const loading = ref(true)
const error = ref('')
let timer = null
const realSensor = ref(null)
const realError = ref('')
const realBusy = ref(false)
const realHistory = ref([])
const historyError = ref('')
const chartTempEl = ref(null)
const chartHumidityEl = ref(null)
const chartSmokeEl = ref(null)
const charts = []
let historyBusy = false

function buildChart(el, title, field, unit, color, maxValue = null) {
  if (!el) return null
  const chart = echarts.init(el)
  const seriesData = realHistory.value.map(item => {
    const value = Number(item[field])
    // 烟雾 ADC 满量程时不作为有效曲线读数
    return field === 'smoke' && (item.smoke_saturated || value >= 4095) ? null : value
  })
  chart.setOption({
    backgroundColor: 'transparent',
    title: { text: title, left: 12, top: 10, textStyle: { color: '#e2e8f0', fontSize: 15, fontWeight: 500 } },
    tooltip: { trigger: 'axis', valueFormatter: value => value == null ? 'ADC 饱和' : `${value} ${unit}` },
    grid: { left: 48, right: 20, top: 52, bottom: 52 },
    xAxis: { type: 'category', boundaryGap: false, data: realHistory.value.map(item => new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour12: false })), axisLabel: { color: '#94a3b8', hideOverlap: true }, axisLine: { lineStyle: { color: '#475569' } } },
    yAxis: { type: 'value', name: unit, min: field === 'smoke' ? 0 : undefined, max: maxValue ?? undefined, nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#29364b' } } },
    series: [{ type: 'line', name: title, data: seriesData, showSymbol: false, connectNulls: false, smooth: false, lineStyle: { width: 2, color }, itemStyle: { color }, areaStyle: { opacity: 0.08, color } }]
  })
  charts.push(chart)
  return chart
}

function updateCharts() {
  const configs = [
    ['真实温度趋势', 'temperature', '℃', '#38bdf8', null],
    ['真实湿度趋势', 'humidity', '%', '#4ade80', 100],
    ['烟雾 ADC 趋势（相对读数）', 'smoke', 'ADC', '#fbbf24', 4095]
  ]
  ;[chartTempEl, chartHumidityEl, chartSmokeEl].forEach((target, index) => {
    const el = target.value
    if (!el) return
    const existing = echarts.getInstanceByDom(el)
    if (existing) {
      const field = configs[index][1]
      existing.setOption({
        xAxis: { data: realHistory.value.map(item => new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour12: false })) },
        series: [{ data: realHistory.value.map(item => field === 'smoke' && (item.smoke_saturated || Number(item.smoke) >= 4095) ? null : Number(item[field])) }]
      })
    } else buildChart(el, ...configs[index])
  })
}

async function loadRealHistory() {
  if (historyBusy) return
  historyBusy = true
  try {
    const response = await fetch('/api/sensor/history', { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    if (!Array.isArray(data)) throw new Error('历史数据格式不正确')
    realHistory.value = data
    historyError.value = ''
    await nextTick()
    updateCharts()
  } catch (err) {
    historyError.value = '真实历史曲线获取失败：' + err.message
  } finally {
    historyBusy = false
  }
}

function resizeCharts() { charts.forEach(chart => chart.resize()) }

const lastSampleAge = computed(() => {
  if (!realSensor.value?.timestamp) return null
  const age = Date.now() - new Date(realSensor.value.timestamp).getTime()
  return Number.isFinite(age) ? Math.max(0, Math.floor(age / 1000)) : null
})
const sensorOnline = computed(() => lastSampleAge.value !== null && lastSampleAge.value <= 30)

async function loadRealSensor() {
  if (realBusy.value) return
  realBusy.value = true
  try {
    const response = await fetch('/api/sensor/latest', { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    realSensor.value = data && data.temperature != null ? data : null
    realError.value = realSensor.value ? '' : '暂无真实传感器数据'
  } catch (err) {
    realError.value = '真实传感器接口连接失败：' + err.message
  } finally {
    realBusy.value = false
  }
}


async function loadDevices() {
  try {
    const response = await fetch('/api/devices')

    if (!response.ok) {
      throw new Error('请求失败')
    }

    devices.value = await response.json()
    error.value = ''
  } catch (err) {
    error.value = '设备数据获取失败：' + err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  clockTimer = setInterval(() => { clock.value = new Date() }, 1000)
  loadDevices()
  loadRealSensor()
  loadRealHistory()
  window.addEventListener('resize', resizeCharts)
  timer = setInterval(() => { loadDevices(); loadRealSensor(); loadRealHistory() }, 5000)
})

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(clockTimer)
  window.removeEventListener('resize', resizeCharts)
  charts.forEach(chart => chart.dispose())
})
</script>

<template>
  <div class="web-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">A<span>·</span></div>
        <div><div class="brand-title">AIoT Agent</div><div class="brand-subtitle">智能设备运维平台</div></div>
      </div>
      <div class="sidebar-divider"></div>
      <div class="nav-caption">工作台</div>
      <nav class="nav-list" aria-label="主导航">
        <button v-for="item in navItems.filter(n => n.group === 'workspace')" :key="item.id" type="button" class="nav-link" :class="{ active: activeSection === item.id }" @click="navigateTo(item.id)"><span class="nav-icon">{{ item.icon }}</span><span>{{ item.label }}</span><span v-if="activeSection === item.id" class="nav-active-dot"></span></button>
      </nav>
      <div class="nav-caption secondary-nav">管理中心</div>
      <nav class="nav-list" aria-label="管理导航">
        <button v-for="item in navItems.filter(n => n.group === 'manage')" :key="item.id" type="button" class="nav-link" :class="{ active: activeSection === item.id }" @click="navigateTo(item.id)"><span class="nav-icon">{{ item.icon }}</span><span>{{ item.label }}</span><span v-if="activeSection === item.id" class="nav-active-dot"></span></button>
      </nav>
      <div class="sidebar-bottom">
        <div class="system-indicator"><span class="status-pulse" :class="{ disconnected: !sensorOnline }"></span><div><strong>硬件连接状态</strong><small>{{ sensorOnline ? 'ESP32-S3 数据正常' : '设备离线 / 数据过期' }}</small></div></div>
        <div class="sidebar-foot">AIoT Agent <span>Web Console</span></div>
      </div>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="breadcrumb"><span>工作台</span><span class="breadcrumb-sep">/</span><strong>{{ navItems.find(n => n.id === activeSection)?.label || '监控总览' }}</strong></div>
        <div class="topbar-actions"><span class="topbar-clock">{{ formattedClock }}</span><span class="topbar-divider"></span><span class="environment-tag"><span class="tiny-dot"></span>本地运行</span><button type="button" class="aiot-auth-button" @click="isAdmin ? logoutAdmin() : (loginOpen = true)">{{ isAdmin ? '管理员 · 退出' : '游客模式 · 管理员登录' }}</button></div>
      </header>
      <main class="content">
        <div v-if="loginOpen" class="aiot-login-overlay" @click.self="loginOpen = false">
          <form class="aiot-login-box" @submit.prevent="loginAdmin">
            <h3>管理员登录</h3><p>游客无需登录，只有管理员可以修改设备及处理告警。</p>
            <input v-model="loginPassword" type="password" autocomplete="current-password" placeholder="输入管理员密码" required />
            <p v-if="loginError" class="aiot-login-error">{{ loginError }}</p>
            <div class="aiot-login-actions"><button type="button" @click="loginOpen = false">取消</button><button type="submit" :disabled="loginBusy">{{ loginBusy ? '登录中…' : '登录' }}</button></div>
          </form>
        </div>
        <section id="overview" class="page-intro scroll-section">
          <div><div class="eyebrow">OPERATIONS OVERVIEW <span class="eyebrow-line"></span></div><h1>设备监控总览</h1><p>实时掌握设备运行状态、环境数据与异常趋势</p></div>
          <div class="refresh-info"><span class="refresh-dot"></span>每 5 秒自动同步</div>
        </section>

        <section class="summary-grid" aria-label="设备状态统计">
          <div class="stat-card"><div class="stat-top"><span>设备总数</span><span class="stat-symbol blue">▣</span></div><div class="stat-value">{{ devices.length }}</div><div class="stat-caption">数据库模拟设备</div></div>
          <div class="stat-card"><div class="stat-top"><span>正常设备</span><span class="stat-symbol green">✓</span></div><div class="stat-value">{{ normalCount }}</div><div class="stat-caption">当前状态正常</div></div>
          <div class="stat-card"><div class="stat-top"><span>异常设备</span><span class="stat-symbol amber">!</span></div><div class="stat-value">{{ warningCount }}</div><div class="stat-caption">需关注运行状态</div></div>
          <div class="stat-card"><div class="stat-top"><span>离线设备</span><span class="stat-symbol muted">⌁</span></div><div class="stat-value">{{ offlineCount }}</div><div class="stat-caption">尚未获得最新状态</div></div>
        </section>

        <section id="realtime" class="panel-section scroll-section">
          <div class="section-heading"><div><div class="section-overline">LIVE MONITORING</div><h2>ESP32-S3 实时传感器</h2><p>硬件真实采样数据 · 与模拟设备独立显示</p></div><div class="sensor-status" :class="sensorOnline ? 'online' : 'offline'"><span class="status-pulse" :class="{ disconnected: !sensorOnline }"></span>{{ sensorOnline ? '设备在线' : '设备离线 / 数据过期' }}</div></div>
          <div class="surface live-surface">
            <p v-if="realError" class="error-banner">{{ realError }}</p>
            <div class="live-grid">
              <div class="live-metric"><div class="metric-label"><span class="metric-icon temp">♨</span> 实时温度</div><div class="metric-value">{{ realSensor?.temperature ?? '--' }} <small>℃</small></div><div class="metric-sub">DHT11 · 真实采集</div></div>
              <div class="live-metric"><div class="metric-label"><span class="metric-icon humid">◈</span> 实时湿度</div><div class="metric-value">{{ realSensor?.humidity ?? '--' }} <small>%</small></div><div class="metric-sub">DHT11 · 真实采集</div></div>
              <div class="live-metric"><div class="metric-label"><span class="metric-icon smoke">≋</span> 烟雾 ADC</div><div class="metric-value">{{ realSensor?.smoke ?? '--' }} <small>ADC</small></div><div class="metric-sub">MQ-2 · 未标定相对读数</div></div>
              <div class="live-metric alarm-metric"><div class="metric-label"><span class="metric-icon alarm">⚑</span> 烟雾测试状态</div><div class="alarm-value" :class="{ 'alarm-active': sensorOnline && realSensor?.smoke_alarm }">{{ !sensorOnline ? '数据过期' : realSensor?.smoke_saturated ? 'ADC 饱和' : realSensor?.smoke_alarm ? '超过测试阈值' : '未超过阈值' }}</div><div class="metric-sub">阈值 4000 · 仅用于测试</div></div>
            </div>
            <div class="live-footer"><span><span class="footer-dot"></span>数据源：ESP32-S3</span><span>最后采样：{{ latestTimestamp }}<template v-if="lastSampleAge !== null">（{{ lastSampleAge }} 秒前）</template></span></div>
          </div>
          <div class="safety-note"><span>!</span><p>烟雾 ADC 为未标定的相对读数，4000 仅为程序测试阈值，不能作为消防报警依据；MQ-2 的 5V AO 直接连接 ESP32-S3 存在过压风险。</p></div>
        </section>

        <section id="trends" class="panel-section scroll-section">
          <div class="section-heading"><div><div class="section-overline">DATA ANALYTICS</div><h2>真实传感器历史趋势</h2><p>最近 {{ realHistory.length }} 条真实采样记录 · 自动更新</p></div><span class="section-tag">ECharts 可视化</span></div>
          <p v-if="historyError" class="error-banner">{{ historyError }}</p>
          <p v-if="!historyError && !realHistory.length" class="muted-message">暂无历史数据，等待 ESP32-S3 上传。</p>
          <div class="chart-grid"><div class="chart-card"><div ref="chartTempEl" class="real-chart"></div></div><div class="chart-card"><div ref="chartHumidityEl" class="real-chart"></div></div><div class="chart-card chart-wide"><div ref="chartSmokeEl" class="real-chart"></div></div></div>
          <div class="chart-footnote">注：烟雾 ADC 满量程 4095 的采样点已作为无效值留空，不代表真实烟雾浓度。</div>
        </section>

        <section id="devices" class="panel-section scroll-section">
          <div class="section-heading"><div><div class="section-overline">DEVICE MANAGEMENT</div><h2>设备运行状态</h2><p>以下为原有模拟设备，与上方真实传感器数据分开</p></div><span class="section-tag">{{ devices.length }} 台设备</span></div>
          <p v-if="loading" class="muted-message">正在加载设备数据...</p><p v-if="error" class="error-banner">{{ error }}</p>
          <div class="device-toolbar">
            <label class="device-search-label">
              <span>搜索设备</span>
              <input v-model="deviceSearch" class="device-search-input" type="search" placeholder="输入设备名称或编号" />
            </label>
            <label class="device-filter-label">
              <span>运行状态</span>
              <select v-model="deviceStatusFilter" class="device-status-select">
                <option value="all">全部状态</option>
                <option value="normal">正常</option>
                <option value="warning">警告</option>
                <option value="offline">离线</option>
              </select>
            </label>
            <span class="device-result-count">显示 {{ filteredDevices.length }} / {{ devices.length }} 台模拟设备</span>
          </div>
          <p v-if="!loading && !error && filteredDevices.length === 0" class="muted-message">没有符合条件的设备，请调整搜索或筛选条件。</p>
          <div class="device-grid">
            <button v-for="device in filteredDevices" :key="device.device_id" type="button" class="device-card" :class="{ selected: selectedDeviceId === device.device_id }" @click="selectedDeviceId = device.device_id">
              <div class="device-header"><div class="device-name"><span class="device-symbol">▣</span><h3>{{ device.name }}</h3></div><span class="device-badge" :class="device.status">{{ device.status === 'normal' ? '正常' : device.status === 'warning' ? '警告' : '离线' }}</span></div>
              <div class="device-type">{{ device.device_type === 'smoke' ? '烟雾传感器 · 模拟' : '温湿度传感器 · 模拟' }}</div>
              <div v-if="device.device_type === 'temperature_humidity'" class="device-metrics"><div><span>温度</span><strong>{{ device.temperature == null ? '--' : device.temperature + ' ℃' }}</strong></div><div><span>湿度</span><strong>{{ device.humidity == null ? '--' : device.humidity + ' %' }}</strong></div></div>
              <div v-else-if="device.device_type === 'smoke'" class="device-metrics"><div><span>烟雾指数</span><strong>{{ device.smoke_value == null ? '--' : device.smoke_value }}</strong></div><div><span>检测状态</span><strong>{{ device.status === 'offline' ? '离线' : device.status === 'warning' ? '警告' : '正常' }}</strong></div></div>
              <div class="device-updated">更新时间：{{ formatDeviceTime(device.timestamp) }}</div>
            </button>
          </div>
          <div class="embedded-section"><div class="embedded-title">设备历史记录 <small>点击上方设备卡片切换</small></div><HistoryChart :device-id="selectedDeviceId" :device-type="devices.find(d => d.device_id === selectedDeviceId)?.device_type || 'temperature_humidity'" /></div>
          <div class="embedded-section"><div class="embedded-title">设备档案管理 <small>游客只读，管理员可编辑</small></div><DeviceManager /></div>
        </section>

        <section id="alerts" class="panel-section scroll-section"><div class="section-heading"><div><div class="section-overline">ALERT CENTER</div><h2>告警中心</h2><p>异常记录、告警处理与统计分析</p></div></div><div class="embedded-section"><AlertList /></div><div class="embedded-section"><AlertStatistics /></div></section>
        <section id="ai" class="panel-section scroll-section"><div class="section-heading"><div><div class="section-overline">AI OPERATIONS</div><h2>DeepSeek 智能运维助手</h2><p>基于真实传感器数据和设备记录提供分析建议</p></div><span class="section-tag ai-tag">✧ AI Agent</span></div><div class="embedded-section ai-container"><AiChat /></div></section>
        <footer class="page-footer"><span>© 2026 AIoT Agent · 智能设备运维 Web 控制台</span><span>真实数据与模拟数据已区分 · 本地开发环境</span></footer>
      </main>
    </div>
  </div>
</template>

<style>
/* 覆盖 Vite 初始项目对 #app 的居中与宽度限制 */
html, body, #app { width:100%; min-width:0; min-height:100%; margin:0; padding:0; max-width:none !important; }
body { display:block !important; place-items:initial !important; overflow-x:hidden; }
#app { display:block !important; text-align:left !important; }
.web-shell { width:100%; min-width:0; }

* { box-sizing: border-box; }
.web-shell { --bg:#0b1220; --surface:#141f31; --border:#26364d; --text:#eaf1fb; --muted:#8da0b8; min-height:100vh; background:var(--bg); color:var(--text); font-family:Inter,'Microsoft YaHei','PingFang SC',Arial,sans-serif; }
.sidebar { position:fixed; inset:0 auto 0 0; width:246px; z-index:30; background:#0f1a2b; border-right:1px solid #243349; padding:27px 15px 18px; display:flex; flex-direction:column; }
.brand { display:flex; align-items:center; gap:12px; padding:0 11px; }
.brand-mark { width:41px; height:41px; border-radius:12px; background:linear-gradient(145deg,#267ce6,#25c2ec); display:grid; place-items:center; font-weight:800; font-size:22px; color:white; box-shadow:0 5px 20px #0c69bd44; }
.brand-mark span { color:#adf2ff; }
.brand-title { font-weight:800; font-size:17px; letter-spacing:.2px; }
.brand-subtitle { color:#8296b0; font-size:11px; margin-top:4px; }
.sidebar-divider { height:1px; background:#25364a; margin:28px 11px 22px; }
.nav-caption { color:#657a94; letter-spacing:1.4px; font-size:11px; padding:0 16px; margin-bottom:11px; }
.secondary-nav { margin-top:28px; }
.nav-list { display:grid; gap:5px; }
.nav-link { width:100%; display:flex; align-items:center; gap:13px; padding:13px 15px; border:0; border-radius:9px; background:transparent; color:#9bacc1; text-align:left; cursor:pointer; font-size:13px; font-weight:500; font-family:inherit; }
.nav-link:hover { background:#1a2c44; color:white; }
.nav-link.active { background:#183a5c; color:#e7f5ff; font-weight:700; }
.nav-icon { width:19px; text-align:center; font-size:19px; color:#74a6d2; }
.nav-active-dot { margin-left:auto; width:5px; height:5px; border-radius:50%; background:#48b6f7; }
.sidebar-bottom { margin-top:auto; }
.system-indicator { display:flex; align-items:center; gap:10px; padding:14px 12px; background:#15263a; border:1px solid #29415a; border-radius:10px; }
.system-indicator strong { display:block; font-size:12px; }
.system-indicator small { display:block; font-size:11px; color:#8da4b9; margin-top:5px; }
.status-pulse,.tiny-dot,.refresh-dot,.footer-dot { width:8px; height:8px; border-radius:50%; background:#36d3a1; display:inline-block; flex:none; box-shadow:0 0 0 3px #36d3a11c; }
.status-pulse.disconnected { background:#f4ad53; box-shadow:0 0 0 3px #f4ad531c; }
.sidebar-foot { color:#657a94; font-size:11px; margin-top:20px; padding:0 10px; display:flex; justify-content:space-between; }
.workspace { margin-left:246px; min-width:0; width:calc(100% - 246px); }
.topbar { height:70px; position:sticky; top:0; z-index:20; display:flex; align-items:center; justify-content:space-between; padding:0 36px; border-bottom:1px solid #243349; background:#0d1726f5; backdrop-filter:blur(12px); }
.breadcrumb { display:flex; gap:13px; align-items:center; font-size:13px; color:#8396ad; }
.breadcrumb strong { color:#e8f1fc; font-weight:600; }
.breadcrumb-sep { color:#526982; }
.topbar-actions { display:flex; gap:17px; align-items:center; }
.topbar-clock { font-size:12px; color:#9bacc1; font-variant-numeric:tabular-nums; }
.topbar-divider { width:1px; height:21px; background:#304056; }
.environment-tag { display:flex; gap:8px; align-items:center; font-size:12px; color:#a5b7cb; }
.tiny-dot { width:6px; height:6px; }
.user-avatar { display:grid; place-items:center; width:33px; height:33px; border-radius:50%; background:#214c78; border:1px solid #3574a7; font-size:12px; font-weight:800; }
.content { max-width:1660px; margin:auto; padding:37px 36px 24px; }
.scroll-section { scroll-margin-top:95px; }
.page-intro { display:flex; align-items:end; justify-content:space-between; gap:20px; margin-bottom:27px; }
.eyebrow,.section-overline { color:#50adf3; font-size:10px; letter-spacing:1.9px; font-weight:800; }
.eyebrow-line { display:inline-block; vertical-align:middle; margin-left:10px; width:28px; height:1px; background:#3479a9; }
h1 { font-size:28px; line-height:1.3; margin:12px 0 9px; letter-spacing:.3px; }
.page-intro p,.section-heading p { color:#8da0b8; font-size:13px; margin:0; }
.refresh-info { color:#91a6ba; font-size:12px; display:flex; align-items:center; gap:10px; padding-bottom:5px; white-space:nowrap; }
.summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; margin-bottom:40px; }
.stat-card { border:1px solid #283b52; border-radius:12px; background:linear-gradient(145deg,#17263a,#131f30); padding:20px 22px; min-width:0; }
.stat-top { display:flex; align-items:center; justify-content:space-between; color:#9eafc3; font-size:13px; }
.stat-symbol { width:31px; height:31px; display:grid; place-items:center; border-radius:9px; font-size:17px; font-weight:800; }
.stat-symbol.blue { color:#60b9ff; background:#16466a; }.stat-symbol.green { color:#5be3b1; background:#174c43; }.stat-symbol.amber { color:#ffc078; background:#594024; }.stat-symbol.muted { color:#b4c5d7; background:#344256; }
.stat-value { font-size:34px; font-weight:750; line-height:1.3; margin-top:10px; font-variant-numeric:tabular-nums; }.stat-caption { font-size:11px; color:#7289a2; margin-top:5px; }
.panel-section { margin-top:36px; }.section-heading { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:18px; }.section-heading h2 { margin:7px 0 8px; font-size:20px; font-weight:700; }.section-tag { color:#9eb5c9; font-size:11px; background:#182b40; border:1px solid #294158; border-radius:7px; padding:8px 11px; white-space:nowrap; }.ai-tag { color:#74c5ff; }
.surface,.chart-card,.embedded-section { border:1px solid #2b3d54; border-radius:12px; background:#152237; }
.live-surface { padding:23px; }.live-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; }.live-metric { background:#101c2d; border:1px solid #27394e; border-radius:10px; padding:20px 18px; min-width:0; }.metric-label { color:#9bafc5; font-size:12px; display:flex; align-items:center; gap:8px; }.metric-icon { display:grid; place-items:center; width:26px; height:26px; border-radius:7px; font-size:15px; }.metric-icon.temp { background:#193d5d; color:#5bbcf5; }.metric-icon.humid { background:#164840; color:#4fd6ac; }.metric-icon.smoke { background:#554123; color:#ffc36b; }.metric-icon.alarm { background:#3e3150; color:#c5a5ff; }.metric-value { font-size:30px; font-weight:750; letter-spacing:-.6px; margin:17px 0 10px; white-space:nowrap; }.metric-value small { font-size:14px; color:#91a6bb; font-weight:500; }.metric-sub { color:#71879e; font-size:11px; }.alarm-value { color:#56dfb0; font-size:17px; font-weight:700; margin:24px 0 14px; }.alarm-value.alarm-active { color:#ffba75; }.live-footer { display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-top:20px; padding-top:17px; border-top:1px solid #2a3c52; color:#8fa4bb; font-size:11px; }.live-footer span:first-child { display:flex; align-items:center; gap:8px; }.footer-dot { width:6px; height:6px; }
.safety-note { display:flex; gap:10px; align-items:start; margin-top:12px; border:1px solid #5b4a2c; background:#2b251d; border-radius:8px; padding:11px 14px; color:#e4b97c; font-size:11px; line-height:1.7; }.safety-note > span { font-weight:800; font-size:14px; }.safety-note p { margin:0; }
.chart-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }.chart-card { min-width:0; overflow:hidden; background:#111e30; }.chart-wide { grid-column:1/-1; }.real-chart { width:100%; height:295px; }.chart-wide .real-chart { height:315px; }.chart-footnote { color:#879bb0; font-size:11px; margin-top:12px; }.muted-message { color:#9ab0c7; font-size:13px; }.error-banner { background:#4d282b; border:1px solid #9c494d; border-radius:8px; padding:11px 14px; color:#ffc5c5; font-size:12px; }
.device-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }.device-card { width:100%; min-width:0; text-align:left; font-family:inherit; color:inherit; background:#152237; border:1px solid #2a3b52; border-radius:11px; padding:18px; cursor:pointer; }.device-card:hover { border-color:#4388bd; }.device-card.selected { border-color:#399de0; box-shadow:inset 0 0 0 1px #399de02a; }.device-header { display:flex; justify-content:space-between; align-items:center; gap:10px; }.device-name { display:flex; align-items:center; gap:9px; min-width:0; }.device-symbol { color:#59b6f3; font-size:18px; }.device-header h3 { margin:0; font-size:13px; overflow-wrap:anywhere; }.device-badge { font-size:11px; padding:5px 9px; border-radius:5px; background:#344355; color:#a9b8c7; white-space:nowrap; }.device-badge.normal { background:#184b3d; color:#5ee1b2; }.device-badge.warning { background:#62402a; color:#ffc18a; }.device-type { color:#7d93a9; font-size:11px; margin-top:13px; }.device-metrics { display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:18px 0; }.device-metrics span { display:block; color:#8298ae; font-size:11px; margin-bottom:7px; }.device-metrics strong { font-size:19px; }.device-updated { border-top:1px solid #2b3d52; padding-top:12px; color:#71889f; font-size:10px; overflow-wrap:anywhere; }
.embedded-section { padding:22px; margin-top:16px; min-width:0; overflow:hidden; }.embedded-title { color:#e7f1fd; font-size:16px; font-weight:700; margin-bottom:14px; }.embedded-title small { color:#8ba1b6; font-size:11px; font-weight:400; margin-left:10px; }.ai-container { min-height:300px; }
.page-footer { display:flex; justify-content:space-between; flex-wrap:wrap; gap:12px; border-top:1px solid #26384d; padding:24px 0 5px; margin-top:44px; font-size:11px; color:#7389a0; }
@media (max-width:1280px) { .live-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }.device-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:900px) { .sidebar { width:205px; }.workspace { margin-left:205px; width:calc(100% - 205px); }.content { padding:28px 20px; }.topbar { padding:0 20px; }.summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }.chart-grid { grid-template-columns:1fr; }.chart-wide { grid-column:auto; } }
@media (max-width:700px) { .sidebar { position:relative; width:auto; height:auto; padding:14px; }.brand { margin-bottom:10px; }.sidebar-divider,.nav-caption,.sidebar-bottom { display:none; }.nav-list { display:flex; flex-wrap:wrap; gap:6px; }.nav-link { width:auto; padding:8px 10px; font-size:12px; }.nav-icon { font-size:14px; width:auto; }.secondary-nav + .nav-list { margin-top:7px; }.workspace { margin-left:0; width:100%; }.topbar { height:55px; }.topbar-clock,.topbar-divider { display:none; }.content { padding:22px 14px; }.page-intro { align-items:start; }.refresh-info { display:none; }.live-grid,.device-grid { grid-template-columns:1fr; }.live-footer { display:block; }.live-footer > span { margin-bottom:8px; }.section-heading { align-items:start; }.section-tag { display:none; } }
/* 设备管理：搜索与状态筛选 */
.device-toolbar { display:flex; flex-wrap:wrap; align-items:end; gap:14px; padding:16px 18px; margin-bottom:16px; border:1px solid #2b3d54; border-radius:11px; background:#152237; }
.device-search-label,.device-filter-label { display:flex; flex-direction:column; gap:8px; color:#91a9c1; font-size:12px; }
.device-search-label { flex:1 1 260px; max-width:420px; }
.device-filter-label { flex:0 1 190px; }
.device-search-input,.device-status-select { width:100%; height:40px; border:1px solid #344a63; border-radius:8px; background:#0d192b; color:#e7f1fd; padding:0 12px; font:inherit; font-size:13px; outline:none; }
.device-search-input:focus,.device-status-select:focus { border-color:#4da9ef; box-shadow:0 0 0 2px #4da9ef24; }
.device-search-input::placeholder { color:#7189a1; }
.device-result-count { margin-left:auto; padding-bottom:10px; color:#8da5bb; font-size:12px; }
@media (max-width:700px) { .device-toolbar { align-items:stretch; }.device-search-label,.device-filter-label { max-width:none; flex:1 1 100%; }.device-result-count { margin-left:0; padding-bottom:0; } }


/* 设备管理搜索工具栏 */
.device-toolbar {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 16px;
  margin: 24px 0;
  padding: 20px;
  background: #16243a;
  border: 1px solid #263b56;
  border-radius: 12px;
}

.device-toolbar label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #9fb6d4;
  font-size: 14px;
}

.device-toolbar input,
.device-toolbar select {
  min-height: 42px;
  padding: 0 14px;
  color: #eaf3ff;
  background: #0c1729;
  border: 1px solid #30445f;
  border-radius: 8px;
}

.device-toolbar input {
  min-width: 240px;
}

.device-toolbar select {
  min-width: 150px;
}

.device-toolbar .toolbar-count {
  margin-left: auto;
  color: #91a9c7;
  white-space: nowrap;
}

</style>

<style>
.aiot-auth-button{border:1px solid #3b526c;background:#1b3149;color:#e8f3ff;border-radius:9px;padding:9px 13px;cursor:pointer;font-size:12px}
.aiot-login-overlay{position:fixed;inset:0;background:#0009;z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px}
.aiot-login-box{width:min(400px,100%);background:#142338;border:1px solid #42617f;color:#fff;padding:28px;border-radius:16px;box-shadow:0 20px 80px #0009}
.aiot-login-box h3{margin:0 0 12px}.aiot-login-box p{font-size:13px;color:#c2d4e8;line-height:1.7}
.aiot-login-box input{width:100%;box-sizing:border-box;padding:12px;border-radius:8px;border:1px solid #54708c;background:#0e1c2e;color:white}
.aiot-login-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:18px}.aiot-login-actions button{padding:9px 18px;border-radius:8px;cursor:pointer}
.aiot-login-error{color:#ff9898!important}
</style>
