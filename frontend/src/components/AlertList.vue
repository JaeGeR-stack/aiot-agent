
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// 告警数据
const alerts = ref([])
const loading = ref(true)
const error = ref('')

// 当前正在处理的告警编号
const processingId = ref(null)

let timer = null

// 获取告警列表
async function loadAlerts() {
  try {
    const response = await fetch('/api/alerts')

    if (!response.ok) {
      throw new Error('获取告警数据失败')
    }

    alerts.value = await response.json()
    error.value = ''
  } catch (err) {
    error.value = '告警数据加载失败，请检查后端服务'
    console.error(err)
  } finally {
    loading.value = false
  }
}

// 告警等级转换
function levelText(level) {
  if (level === 'critical') {
    return '严重告警'
  }

  if (level === 'warning') {
    return '一般告警'
  }

  return '未知等级'
}

// 告警类型转换
function typeText(type) {
  if (type === 'temperature') {
    return '🌡️ 温度异常'
  }

  if (type === 'humidity') {
    return '💧 湿度异常'
  }

  if (type === 'smoke') {
    return '💨 烟雾异常'
  }

  return '其他异常'
}

// 格式化时间
function formatTime(time) {
  return time
    ? new Date(time).toLocaleString('zh-CN')
    : '-'
}

// 处理告警
async function resolveAlert(alertId) {
  if (processingId.value !== null) return

  processingId.value = alertId

  try {
    const response = await fetch(
      `/api/alerts/${alertId}/resolve`,
      {
        method: 'PATCH'
      }
    )

    if (!response.ok) {
      throw new Error('告警处理失败')
    }

    // 重新加载告警数据
    await loadAlerts()

  } catch (err) {
    console.error(err)
    window.alert('处理失败，请检查后端服务')
  } finally {
    processingId.value = null
  }
}

// 页面加载时获取告警
onMounted(() => {
  loadAlerts()

  // 每5秒刷新一次
  timer = setInterval(loadAlerts, 5000)
})

// 页面销毁时清除定时器
onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<template>
  <section class="alert-panel">

    <!-- 标题 -->
    <div class="panel-header">
      <h2>🚨 设备告警管理</h2>

      <span class="alert-count">
        最近 {{ alerts.length }} 条告警
      </span>
    </div>

    <!-- 加载状态 -->
    <p v-if="loading">
      正在加载告警数据...
    </p>

    <!-- 错误提示 -->
    <p v-if="error" class="error">
      {{ error }}
    </p>

    <!-- 没有告警 -->
    <div
      v-if="!loading && !error && alerts.length === 0"
      class="empty"
    >
      暂无告警记录
    </div>

    <!-- 告警列表 -->
    <div
      v-if="alerts.length > 0"
      class="table-wrapper"
    >
      <table>
        <thead>
          <tr>
            <th>设备名称</th>
            <th>告警类型</th>
            <th>告警等级</th>
            <th>告警内容</th>
            <th>发生时间</th>
            <th>处理状态</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="alert in alerts"
            :key="alert.id"
          >
            <!-- 设备名称 -->
            <td>
              {{ alert.device_name }}
            </td>

            <!-- 告警类型 -->
            <td>
              {{ typeText(alert.alert_type) }}
            </td>

            <!-- 告警等级 -->
            <td>
              <span
                class="level"
                :class="alert.alert_level"
              >
                {{ levelText(alert.alert_level) }}
              </span>
            </td>

            <!-- 告警内容 -->
            <td>
              {{ alert.alert_message }}
            </td>

            <!-- 发生时间 -->
            <td>
              {{ formatTime(alert.created_at) }}
            </td>

            <!-- 处理状态 -->
            <td>
              <button
                v-if="alert.status === 'pending'"
                class="resolve-btn"
                :disabled="processingId !== null"
                @click="resolveAlert(alert.id)"
              >
                {{
                  processingId === alert.id
                    ? '处理中...'
                    : '处理完成'
                }}
              </button>

              <span
                v-else
                class="resolved-status"
              >
                ✓ 已处理
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

  </section>
</template>

<style scoped>
.alert-panel {
  margin-top: 24px;
  padding: 24px;
  border: 1px solid #334155;
  border-radius: 18px;
  background: #1a263b;
  color: #f8fafc;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}

.panel-header h2 {
  margin: 0;
  font-size: 22px;
}

.alert-count {
  color: #94a3b8;
  font-size: 14px;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 14px;
}

th,
td {
  padding: 14px 10px;
  border-bottom: 1px solid #334155;
  text-align: left;
  white-space: normal;
  overflow-wrap: anywhere;
  vertical-align: middle;
}

th:nth-child(1) {
  width: 18%;
}

th:nth-child(2) {
  width: 12%;
}

th:nth-child(3) {
  width: 13%;
}

th:nth-child(4) {
  width: 21%;
}

th:nth-child(5) {
  width: 21%;
}

th:nth-child(6) {
  width: 15%;
}

th {
  background: #243247;
  color: #cbd5e1;
}

td {
  color: #e2e8f0;
}

/* 告警等级 */
.level {
  display: inline-block;
  padding: 5px 10px;
  border-radius: 6px;
  font-weight: bold;
}

.level.warning {
  background: #78350f;
  color: #fde68a;
}

.level.critical {
  background: #7f1d1d;
  color: #fecaca;
}

/* 错误提示 */
.error {
  color: #f87171;
}

/* 空状态 */
.empty {
  padding: 30px;
  text-align: center;
  color: #94a3b8;
}

/* 告警处理按钮 */
.resolve-btn {
  padding: 8px 14px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.resolve-btn:hover {
  background: #1d4ed8;
}

.resolve-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 已处理状态 */
.resolved-status {
  color: #4ade80;
  font-weight: bold;
}
</style>
