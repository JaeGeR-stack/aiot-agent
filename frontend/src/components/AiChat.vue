
<script setup>
import { ref, nextTick, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const question = ref('')
const messages = ref([])
const loading = ref(false)
// 快捷提问
function quickAsk(text) {
  if (loading.value) return

  question.value = text
  sendMessage()
}
const chatMessages = ref(null)
const quickPrompts = [
  { icon: '◉', title: '真实数据分析', detail: '当前 ESP32-S3 状态', prompt: '请调用真实传感器统计工具，分析当前 ESP32-S3 的温度、湿度和烟雾 ADC 数据，说明当前状态、可能的异常和维护建议。请区分 ADC 测试阈值与实际烟雾浓度。', primary: true },
  { icon: '↗', title: '最近 50 条趋势', detail: '真实采样记录', prompt: '请调用真实传感器统计工具，分析 ESP32-S3 最近50条真实传感器记录的温度、湿度和烟雾 ADC 变化趋势，并给出维护建议。', primary: true },
  { icon: '⚑', title: '待处理告警', detail: '模拟设备告警', prompt: '请查询当前未处理的设备告警，告诉我哪些设备需要优先处理，并给出处理建议。', primary: false },
  { icon: '▤', title: '设备 1 分析', detail: '模拟设备记录', prompt: '请分析1号设备最近50条运行记录，包括报警次数、最高温度、平均温度，并给出建议。', primary: false },
  { icon: '▤', title: '设备 2 分析', detail: '模拟设备记录', prompt: '请分析2号设备最近50条运行记录，包括报警次数、最高温度、平均温度，并给出建议。', primary: false },
  { icon: '▤', title: '设备 3 分析', detail: '模拟设备记录', prompt: '请分析3号设备最近50条运行记录，包括报警次数、最高温度、平均温度，并给出建议。', primary: false }
]

// 配置Markdown解析器
marked.setOptions({
  gfm: true,
  breaks: true
})

// 安全渲染AI回答
function renderMarkdown(content) {
  const html = marked.parse(content || '')
  return DOMPurify.sanitize(html)
}

// 自动滚动到底部
async function scrollToBottom() {
  await nextTick()

  if (chatMessages.value) {
    chatMessages.value.scrollTop =
      chatMessages.value.scrollHeight
  }
}

// 消息或加载状态改变时自动滚动
watch(
  [messages, loading],
  scrollToBottom,
  { deep: true, flush: 'post' }
)

async function sendMessage() {
  const text = question.value.trim()

  if (!text || loading.value) return

  messages.value.push({
    role: 'user',
    content: text
  })

  question.value = ''
  loading.value = true

  try {
    const response = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: text
      })
    })

    if (!response.ok) {
      throw new Error('AI接口请求失败')
    }

    const data = await response.json()

    messages.value.push({
      role: 'assistant',
      content: data.reply || 'AI没有返回内容'
    })

  } catch (error) {
    console.error('AI聊天请求失败：', error)

    messages.value.push({
      role: 'assistant',
      content: '请求失败，请检查FastAPI后端或DeepSeek服务。'
    })

  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="ai-chat">
    <header class="chat-header">
      <div class="brand-icon">✦</div>
      <div class="header-copy">
        <h2>AIoT 智能运维助手</h2>
        <p>连接 DeepSeek · 真实硬件监测与设备运维分析</p>
      </div>
      <div class="model-chip"><span class="status-dot"></span> DeepSeek AI</div>
    </header>

    <div class="section-label"><span>快捷分析</span><small>选择任务即可发送分析请求</small></div>
    <div class="quick-actions">
      <button v-for="item in quickPrompts" :key="item.title" type="button"
        :class="['action-card', { featured: item.primary }]" :disabled="loading" @click="quickAsk(item.prompt)">
        <span class="action-icon">{{ item.icon }}</span>
        <span class="action-copy"><strong>{{ item.title }}</strong><small>{{ item.detail }}</small></span>
        <span class="action-arrow">↗</span>
      </button>
    </div>

    <div class="conversation-head">
      <div><span class="conversation-indicator"></span><strong>智能分析对话</strong></div>
      <span class="conversation-meta">{{ messages.length ? `${messages.length} 条消息` : '等待提问' }}</span>
    </div>

    <div ref="chatMessages" class="chat-messages" role="log" aria-live="polite" aria-label="AI 对话记录">
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon">✦</div>
        <h3>让数据帮助你判断设备状态</h3>
        <p>可以直接分析 ESP32-S3 真实采样记录，也可以查询模拟设备的历史数据和告警。</p>
        <div class="welcome-tags"><span>真实传感器</span><span>趋势解读</span><span>告警排查</span><span>维护建议</span></div>
      </div>

      <div v-for="(message, index) in messages" :key="index" class="message-row" :class="message.role">
        <div class="message-avatar">{{ message.role === 'user' ? '我' : '✦' }}</div>
        <div class="message-bubble">
          <div class="message-name">{{ message.role === 'user' ? '我的提问' : 'DeepSeek 运维助手' }}</div>
          <div v-if="message.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(message.content)"></div>
          <div v-else class="user-content">{{ message.content }}</div>
        </div>
      </div>

      <div v-if="loading" class="message-row assistant">
        <div class="message-avatar">✦</div>
        <div class="message-bubble">
          <div class="message-name">DeepSeek 运维助手</div>
          <div class="loading-content"><span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span><span>正在读取并分析数据...</span></div>
        </div>
      </div>
    </div>

    <form class="chat-input" @submit.prevent="sendMessage">
      <input v-model="question" aria-label="输入运维分析问题" placeholder="输入问题，例如：分析 ESP32-S3 最近 50 条真实采样数据..." :disabled="loading" />
      <button type="submit" :disabled="loading || !question.trim()">{{ loading ? '分析中…' : '发送 ↗' }}</button>
    </form>
    <div class="chat-footer"><span>数据来源：ESP32-S3 真实传感器 / 数据库模拟设备</span><span>AI 结论仅供实验及辅助运维参考</span></div>
  </section>
</template>
<style scoped>
.ai-chat { width:100%; min-width:0; margin-top:16px; padding:24px; border:1px solid #263955; border-radius:16px; background:#142238; color:#eaf3ff; font-family:inherit; }
.chat-header { display:flex; align-items:center; gap:14px; padding-bottom:22px; border-bottom:1px solid #2a3b55; }
.brand-icon { display:grid; place-items:center; flex-shrink:0; width:48px; height:48px; border-radius:13px; color:#91d6ff; font-size:28px; background:linear-gradient(140deg,#214c79,#162d52); }
.header-copy { flex:1; min-width:0; }
.header-copy h2 { margin:0 0 5px; color:#f5f9ff; font-size:21px; font-weight:700; }
.header-copy p { margin:0; color:#8ca7c7; font-size:13px; }
.model-chip { display:flex; align-items:center; gap:8px; flex-shrink:0; padding:8px 12px; border:1px solid #2c4a66; border-radius:30px; background:#10263b; color:#b7d4f2; font-size:12px; }
.status-dot,.conversation-indicator { display:inline-block; width:8px; height:8px; border-radius:50%; background:#31d5a0; box-shadow:0 0 0 3px #31d5a018; }
.section-label { display:flex; align-items:center; justify-content:space-between; gap:12px; margin:22px 0 12px; }
.section-label span { font-size:14px; font-weight:700; color:#e3efff; }
.section-label small { color:#819bb9; font-size:12px; }
.quick-actions { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:11px; margin-bottom:22px; }
.action-card { display:flex; align-items:center; min-width:0; gap:12px; padding:15px 14px; border:1px solid #314662; border-radius:11px; background:#101d30; color:#dcecff; cursor:pointer; text-align:left; transition:background .2s,border-color .2s,transform .2s; }
.action-card.featured { border-color:#2772b2; background:linear-gradient(110deg,#173c65,#132e4d); }
.action-card:hover:not(:disabled) { border-color:#4ca8f1; background:#1c3857; transform:translateY(-1px); }
.action-card:disabled { opacity:.55; cursor:not-allowed; }
.action-icon { display:grid; place-items:center; flex-shrink:0; width:34px; height:34px; border-radius:9px; background:#224262; color:#62bfff; font-size:19px; }
.action-copy { display:flex; flex:1; min-width:0; flex-direction:column; gap:5px; }
.action-copy strong { font-size:13px; font-weight:650; }
.action-copy small { font-size:11px; color:#87a7c8; }
.action-arrow { color:#6592b9; font-size:15px; }
.conversation-head { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:0 2px 12px; }
.conversation-head>div { display:flex; align-items:center; gap:9px; font-size:14px; }
.conversation-meta { color:#819ab9; font-size:12px; }
.chat-messages { height:390px; min-height:290px; overflow-y:auto; padding:24px; border:1px solid #22334e; border-radius:12px; background:#0c172a; scroll-behavior:smooth; }
.welcome { display:flex; height:100%; flex-direction:column; align-items:center; justify-content:center; gap:12px; text-align:center; }
.welcome-icon { display:grid; place-items:center; width:58px; height:58px; border:1px solid #315d8b; border-radius:17px; background:#16375a; color:#77c9ff; font-size:32px; }
.welcome h3 { margin:2px 0 0; font-size:19px; color:#e9f4ff; }
.welcome p { max-width:580px; margin:0; color:#8ea9c7; font-size:13px; line-height:1.8; }
.welcome-tags { display:flex; flex-wrap:wrap; justify-content:center; gap:8px; margin-top:7px; }
.welcome-tags span { padding:5px 10px; border:1px solid #2a4565; border-radius:20px; color:#90b9dc; font-size:11px; }
.message-row { display:flex; align-items:flex-start; gap:11px; margin-bottom:19px; }
.message-row.user { flex-direction:row-reverse; }
.message-avatar { display:grid; place-items:center; flex-shrink:0; width:34px; height:34px; border-radius:10px; background:#1b4063; color:#a1d6ff; font-size:16px; font-weight:700; }
.message-row.user .message-avatar { background:#275b9a; color:white; }
.message-bubble { max-width:min(86%,880px); min-width:0; padding:15px 18px; border:1px solid #2c405d; border-radius:13px; background:#1b2b43; overflow-wrap:anywhere; }
.message-row.user .message-bubble { background:#1b4778; border-color:#2b68a8; }
.message-name { margin-bottom:8px; font-size:12px; font-weight:700; color:#95bce2; }
.message-row.user .message-name { color:#cde6ff; }
.user-content { white-space:pre-wrap; font-size:14px; line-height:1.8; }
.markdown-body { font-size:14px; line-height:1.85; overflow-wrap:anywhere; }
.markdown-body :deep(h1),.markdown-body :deep(h2),.markdown-body :deep(h3) { margin:15px 0 9px; color:#f4f8ff; }
.markdown-body :deep(h1) { font-size:21px; } .markdown-body :deep(h2) { font-size:18px; } .markdown-body :deep(h3) { font-size:16px; }
.markdown-body :deep(p) { margin:7px 0; } .markdown-body :deep(ul),.markdown-body :deep(ol) { margin:8px 0; padding-left:23px; }
.markdown-body :deep(li) { margin:4px 0; } .markdown-body :deep(strong) { color:#9bd5ff; }
.markdown-body :deep(code) { padding:2px 5px; border-radius:4px; background:#101c2f; color:#9cf3c4; }
.markdown-body :deep(pre) { overflow-x:auto; padding:12px; border-radius:8px; background:#071122; }
.markdown-body :deep(pre code) { padding:0; background:transparent; }
.markdown-body :deep(table) { display:block; max-width:100%; overflow-x:auto; margin:12px 0; border-collapse:collapse; }
.markdown-body :deep(th),.markdown-body :deep(td) { padding:8px 12px; border:1px solid #3c536e; text-align:left; }
.markdown-body :deep(th) { background:#20314b; } .markdown-body :deep(a) { color:#7fc9ff; }
.loading-content { display:flex; align-items:center; gap:6px; color:#b9cce2; font-size:13px; }
.loading-dot { width:7px; height:7px; border-radius:50%; background:#59b9ff; animation:pulse 1s infinite alternate; }
.loading-dot:nth-child(2) { animation-delay:.2s; } .loading-dot:nth-child(3) { animation-delay:.4s; }
@keyframes pulse { from { opacity:.25; transform:translateY(0); } to { opacity:1; transform:translateY(-4px); } }
.chat-input { display:flex; gap:11px; margin-top:15px; }
.chat-input input { flex:1; min-width:0; padding:14px 16px; border:1px solid #354d6c; border-radius:10px; outline:none; background:#0c172a; color:#f2f8ff; font-size:14px; }
.chat-input input::placeholder { color:#6f89aa; } .chat-input input:focus { border-color:#54aeef; box-shadow:0 0 0 3px #368de31f; }
.chat-input button { flex-shrink:0; padding:0 25px; border:0; border-radius:10px; background:#2374cf; color:white; font-weight:700; cursor:pointer; }
.chat-input button:hover:not(:disabled) { background:#328bea; } .chat-input button:disabled { opacity:.5; cursor:not-allowed; }
.chat-footer { display:flex; justify-content:space-between; flex-wrap:wrap; gap:7px 15px; margin-top:13px; color:#7993b3; font-size:11px; }
@media(max-width:1100px) { .quick-actions { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media(max-width:680px) { .ai-chat { padding:15px; } .chat-header { flex-wrap:wrap; } .model-chip { margin-left:62px; } .quick-actions { grid-template-columns:1fr; } .chat-messages { padding:13px; } .message-bubble { max-width:88%; padding:12px; } .chat-input button { padding:0 14px; } .header-copy h2 { font-size:18px; } }
</style>
