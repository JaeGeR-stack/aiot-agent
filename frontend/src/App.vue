
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import HistoryChart from './components/HistoryChart.vue'
import AiChat from './components/AiChat.vue'
import AlertList from './components/AlertList.vue'
import AlertStatistics from './components/AlertStatistics.vue'
import DeviceManager from './components/DeviceManager.vue'

const devices = ref([])
const selectedDeviceId = ref(1)
const loading = ref(true)
const error = ref('')
let timer = null

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
  loadDevices()
  timer = setInterval(loadDevices, 5000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<template>
  <div class="dashboard">
    <header>
      <h1>AIoT 智能设备运维平台</h1>
      <p>设备实时监控 · 异常检测 · AI智能分析</p>
    </header>

    <section class="summary">
      <div class="summary-card">
        <span>设备总数</span>
        <strong>{{ devices.length }}</strong>
      </div>

      <div class="summary-card">
        <span>正常设备</span>
        <strong class="normal">
          {{ devices.filter(d => d.status === 'normal').length }}
        </strong>
      </div>

      <div class="summary-card">
        <span>异常设备</span>
        <strong class="warning">
          {{ devices.filter(d => d.status === 'warning').length }}
        </strong>
      </div>
<div class="summary-card">
  <span>离线设备</span>
  <strong class="offline-count">
    {{ devices.filter(d => d.status === 'offline').length }}
  </strong>
</div>
    </section>

    <h2>设备实时状态</h2>

    <p v-if="loading">正在加载设备数据...</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="device-grid">
      
<div
  v-for="device in devices"
  :key="device.device_id"
  class="device-card"
  @click="selectedDeviceId = device.device_id"
>
  <div class="device-header">
    <h3>{{ device.name }}</h3>

    <span :class="device.status">
      {{
        device.status === 'normal' ? '正常' :
        device.status === 'warning' ? '警告' : '离线'
      }}
    </span>
  </div>

  <div class="device-type">
    设备类型：
    {{ device.device_type === 'smoke' ? '烟雾传感器' : '温湿度传感器' }}
  </div>

  <!-- 温湿度传感器 -->
  <div
    v-if="device.device_type === 'temperature_humidity'"
    class="metrics"
  >
    <div>
      <span>温度</span>
      <strong>
        {{ device.temperature == null ? '--' : device.temperature + ' ℃' }}
      </strong>
    </div>

    <div>
      <span>湿度</span>
      <strong>
        {{ device.humidity == null ? '--' : device.humidity + ' %' }}
      </strong>
    </div>
  </div>

  <!-- 烟雾传感器 -->
<div v-else-if="device.device_type === 'smoke'" class="metrics">
  <div>
    <span>烟雾指数</span>
    <strong>
      {{ device.smoke_value == null ? '暂无数据' : device.smoke_value }}
    </strong>
  </div>

  <div>
    <span>检测状态</span>
    <strong>
      {{
        device.status === 'offline' ? '离线' :
        device.status === 'warning' ? '警告' : '正常'
      }}
    </strong>
  </div>
</div>


        <p class="time">
          更新时间：{{ device.timestamp }}
        </p>
      </div>
    </section>
    <!-- 历史趋势图 -->
    <HistoryChart
  :device-id="selectedDeviceId"
  :device-type="
    devices.find(d => d.device_id === selectedDeviceId)?.device_type
    || 'temperature_humidity'
  "
/>
    <AlertList />
    
    <AlertStatistics />
    <DeviceManager />
    <AiChat />
    <footer>
      数据每5秒自动刷新 · 当前为模拟传感器数据
    </footer>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  padding: 40px;
  background: #0b1220;
  color: #f1f5f9;
  font-family: Arial, sans-serif;
}

header {
  margin-bottom: 35px;
}

h1 {
  font-size: 30px;
  margin-bottom: 10px;
}

header p,
footer {
  color: #94a3b8;
}

.summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.summary-card,
.device-card {
  background: #172338;
  border: 1px solid #334155;
  border-radius: 14px;
  padding: 24px;
}

.summary-card span {
  display: block;
  color: #94a3b8;
  margin-bottom: 12px;
}

.summary-card strong {
  font-size: 32px;
}

.normal {
  color: #4ade80;
}

.warning {
  color: #fb923c;
}

h2 {
  margin-bottom: 20px;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(250px, 1fr)
  );
  gap: 20px;
}

.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.device-header h3 {
  font-size: 17px;
}

.device-header span {
  padding: 6px 12px;
  border-radius: 8px;
  background: #253348;
}

.metrics {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  margin-top: 35px;
}

.metrics span {
  display: block;
  color: #94a3b8;
  margin-bottom: 10px;
}

.metrics strong {
  font-size: 23px;
}

.time {
  color: #94a3b8;
  font-size: 12px;
  margin-top: 30px;
}

.error {
  color: #f87171;
}

footer {
  margin-top: 40px;
  text-align: center;
}

@media (max-width: 600px) {
  .dashboard {
    padding: 20px;
  }

  .summary {
    grid-template-columns: 1fr;
  }
}

.device-type {
  color: #94a3b8;
  font-size: 14px;
  margin: 12px 0;
}

.device-header .offline {
  color: #94a3b8;
  background: #334155;
}
.offline-count {
  color: #94a3b8;
}
</style>
