
<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  deviceId: {
    type: Number,
    required: true
  },
  deviceType: {
    type: String,
    default: 'temperature_humidity'
  }
})

const chartElement = ref(null)
const error = ref('')
let chart = null
let timer = null
let requestVersion = 0

async function loadHistory() {
  const version = ++requestVersion
  const deviceId = props.deviceId
  const isSmoke = props.deviceType === 'smoke'

  try {
    const url = isSmoke
      ? `/api/smoke/history/${deviceId}`
      : `/api/history/${deviceId}`

    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`历史数据请求失败（${response.status}）`)
    }

    const history = await response.json()

    // 防止快速切换设备时旧请求覆盖新图表
    if (version !== requestVersion || !chart) return

    error.value = ''

    const times = history.map(item =>
      new Date(item.timestamp).toLocaleTimeString('zh-CN')
    )

    const commonOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis'
      },
      grid: {
        left: 60,
        right: 55,
        top: 65,
        bottom: 50
      },
      xAxis: {
        type: 'category',
        data: times,
        axisLabel: {
          color: '#94a3b8'
        }
      }
    }

    if (isSmoke) {
      chart.setOption({
        ...commonOption,
        legend: {
          data: ['烟雾指数'],
          textStyle: { color: '#cbd5e1' }
        },
        yAxis: {
          type: 'value',
          name: '烟雾指数',
          min: 0,
          max: 100,
          axisLabel: { color: '#94a3b8' }
        },
        series: [
          {
            name: '烟雾指数',
            type: 'line',
            smooth: true,
            data: history.map(item => item.smoke_value),
            itemStyle: {
              color: '#fb923c'
            },
            lineStyle: {
              width: 3
            },
            markLine: {
              silent: true,
              symbol: 'none',
              label: {
                formatter: '演示阈值 80',
                color: '#f87171'
              },
              lineStyle: {
                color: '#f87171',
                type: 'dashed',
                width: 2
              },
              data: [
                { yAxis: 80 }
              ]
            }
          }
        ]
      }, true)
    } else {
      chart.setOption({
        ...commonOption,
        legend: {
          data: ['温度', '湿度'],
          textStyle: { color: '#cbd5e1' }
        },
        yAxis: [
          {
            type: 'value',
            name: '温度 ℃',
            axisLabel: { color: '#94a3b8' }
          },
          {
            type: 'value',
            name: '湿度 %',
            min: 0,
            max: 100,
            axisLabel: { color: '#94a3b8' }
          }
        ],
        series: [
          {
            name: '温度',
            type: 'line',
            smooth: true,
            data: history.map(item => item.temperature)
          },
          {
            name: '湿度',
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            data: history.map(item => item.humidity)
          }
        ]
      }, true)
    }

  } catch (err) {
    if (version === requestVersion) {
      error.value = err.message
      chart?.clear()
    }
  }
}

function resizeChart() {
  chart?.resize()
}

onMounted(() => {
  chart = echarts.init(chartElement.value)
  loadHistory()

  timer = setInterval(loadHistory, 5000)
  window.addEventListener('resize', resizeChart)
})

watch(
  () => [props.deviceId, props.deviceType],
  loadHistory
)

onUnmounted(() => {
  requestVersion++
  clearInterval(timer)
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div class="history-panel">
    <h2>
      设备 {{ deviceId }}
      {{ deviceType === 'smoke' ? '烟雾指数趋势' : '温湿度历史趋势' }}
    </h2>

    <p v-if="error" class="error">{{ error }}</p>

    <div ref="chartElement" class="chart"></div>
  </div>
</template>

<style scoped>
.history-panel {
  margin-top: 30px;
  padding: 24px;
  border: 1px solid #334155;
  border-radius: 14px;
  background: #172338;
}

h2 {
  margin-bottom: 20px;
}

.chart {
  width: 100%;
  height: 360px;
}

.error {
  color: #f87171;
}
</style>
