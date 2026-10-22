
<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

// 统计数据
const stats = ref(null)
const error = ref('')
const chartRef = ref(null)

let chart = null
let timer = null

// 获取告警统计数据
async function loadStatistics() {
  try {
    const response = await fetch('/api/alerts/statistics')

    if (!response.ok) {
      throw new Error('获取告警统计失败')
    }

    stats.value = await response.json()
    error.value = ''

    await nextTick()
    updateChart()

  } catch (err) {
    error.value = '统计数据加载失败，请检查后端服务'
    console.error(err)
  }
}

// 更新柱状图
function updateChart() {
  if (!chartRef.value || !stats.value) return

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const distribution = stats.value.device_distribution || []

  chart.setOption({
    backgroundColor: 'transparent',

    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: params => {
        const item = params[0]
        if (!item) return ''
        return `${item.name}<br/>告警次数：${item.value}`
      }
    },

    grid: {
      left: 55,
      right: 25,
      top: 45,
      bottom: 100
    },

    xAxis: {
      type: 'category',
      data: distribution.map(item => item.device_name),
      axisLabel: {
        color: '#cbd5e1',
        interval: 0,
        rotate: 25,
        fontSize: 12
      },
      axisLine: {
        lineStyle: {
          color: '#475569'
        }
      }
    },

    yAxis: {
      type: 'value',
      name: '告警次数',
      min: 0,
      minInterval: 1,
      nameTextStyle: {
        color: '#94a3b8'
      },
      axisLabel: {
        color: '#cbd5e1'
      },
      splitLine: {
        lineStyle: {
          color: '#334155'
        }
      }
    },

    series: [
      {
        name: '告警次数',
        type: 'bar',
        barMaxWidth: 65,
        data: distribution.map(item => ({
          value: item.count,
          itemStyle: {
            color: item.count > 0
              ? '#3b82f6'
              : '#475569',
            borderRadius: [6, 6, 0, 0]
          }
        })),

        label: {
          show: true,
          position: 'top',
          color: '#f8fafc',
          formatter: '{c}'
        }
      }
    ]
  }, true)

  chart.resize()
}

// 浏览器窗口大小变化时调整图表
function handleResize() {
  chart?.resize()
}

// 页面加载
onMounted(() => {
  loadStatistics()

  // 每5秒自动更新
  timer = setInterval(loadStatistics, 5000)

  window.addEventListener('resize', handleResize)
})

// 页面销毁
onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }

  window.removeEventListener('resize', handleResize)

  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<template>
  <section class="statistics-panel">

    <h2>📊 告警统计分析</h2>

    <p v-if="error" class="error">
      {{ error }}
    </p>

    <template v-if="stats">

      <!-- 四个统计卡片 -->
      <div class="stats-grid">

        <div class="stat-card">
          <span>告警总数</span>
          <strong>{{ stats.total }}</strong>
        </div>

        <div class="stat-card">
          <span>待处理</span>
          <strong class="warning">
            {{ stats.pending }}
          </strong>
        </div>

        <div class="stat-card">
          <span>已处理</span>
          <strong class="success">
            {{ stats.resolved }}
          </strong>
        </div>

        <div class="stat-card">
          <span>严重告警</span>
          <strong class="danger">
            {{ stats.critical }}
          </strong>
        </div>

      </div>

      <!-- 设备告警分布图 -->
      <h3>各设备告警数量分布</h3>

      <p class="chart-description">
        统计数据库中各设备累计产生的告警记录，
        包括温度、湿度和烟雾异常。
      </p>

      <div ref="chartRef" class="chart"></div>

    </template>

    <p v-else-if="!error">
      正在加载统计数据...
    </p>

  </section>
</template>

<style scoped>
.statistics-panel {
  margin-top: 24px;
  padding: 24px;
  border: 1px solid #334155;
  border-radius: 18px;
  background: #1a263b;
  color: #f8fafc;
}

h2 {
  margin: 0 0 24px;
}

h3 {
  margin-top: 30px;
  color: #e2e8f0;
}

.chart-description {
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 16px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  padding: 20px;
  background: #243247;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-card span {
  color: #94a3b8;
}

.stat-card strong {
  font-size: 32px;
}

.warning {
  color: #fbbf24;
}

.success {
  color: #4ade80;
}

.danger {
  color: #f87171;
}

/* 图表 */
.chart {
  width: 100%;
  height: 380px;
}

.error {
  color: #f87171;
}

@media (max-width: 700px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat-card {
    padding: 14px;
  }

  .stat-card strong {
    font-size: 26px;
  }

  .chart {
    height: 350px;
  }
}
</style>
