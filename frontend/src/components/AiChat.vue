
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
    <div class="chat-header">
      <div class="ai-avatar">🤖</div>

      <div>
        <h2>AIoT智能运维助手</h2>
        <span class="ai-status">
          <span class="status-dot"></span>
          DeepSeek智能分析
        </span>
      </div>
    </div>
    <!-- AI快捷分析按钮 -->
    <div class="quick-actions">
      <button
        type="button"
        :disabled="loading"
        @click="quickAsk('请查询当前未处理的设备告警，告诉我哪些设备需要优先处理，并给出处理建议。')"
      >
        🚨 分析未处理告警
      </button>

      <button
        type="button"
        :disabled="loading"
        @click="quickAsk('请分析1号设备最近50条运行记录，包括报警次数、最高温度、平均温度，并给出建议。')"
      >
        🌡️ 分析1号设备
      </button>

      <button
        type="button"
        :disabled="loading"
        @click="quickAsk('请分析2号设备最近50条运行记录，包括报警次数、最高温度、平均温度，并给出建议。')"
      >
        📦 分析2号设备
      </button>

      <button
        type="button"
        :disabled="loading"
        @click="quickAsk('请分析3号设备最近50条运行记录，包括报警次数、最高温度、平均温度，并给出建议。')"
      >
        🖥️ 分析3号设备
      </button>
    </div>
    <div ref="chatMessages" class="chat-messages">
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon">🤖</div>
        <h3>你好，我是AIoT智能运维助手</h3>
        <p>
          可以分析设备历史数据、报警情况，
          并提供故障排查建议。
        </p>
      </div>

      <div
        v-for="(message, index) in messages"
        :key="index"
        class="message-row"
        :class="message.role"
      >
        <div class="message-avatar">
          {{ message.role === 'user' ? '👤' : '🤖' }}
        </div>

        <div class="message-bubble">
          <div class="message-name">
            {{ message.role === 'user' ? '你' : 'AI助手' }}
          </div>

          <div
            v-if="message.role === 'assistant'"
            class="markdown-body"
            v-html="renderMarkdown(message.content)"
          ></div>

          <div v-else class="user-content">
            {{ message.content }}
          </div>
        </div>
      </div>

      <div v-if="loading" class="message-row assistant">
        <div class="message-avatar">🤖</div>

        <div class="message-bubble">
          <div class="message-name">AI助手</div>

          <div class="loading-content">
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
            <span>正在分析设备数据...</span>
          </div>
        </div>
      </div>
    </div>

    <form class="chat-input" @submit.prevent="sendMessage">
      <input
        v-model="question"
        placeholder="例如：分析1号设备最近50条记录"
        :disabled="loading"
      />

      <button
        type="submit"
        :disabled="loading || !question.trim()"
      >
        {{ loading ? '分析中...' : '发送 ➤' }}
      </button>
    </form>

    <p class="chat-tip">
      AI分析基于模拟设备数据，仅供项目演示与学习使用。
    </p>
  </section>
</template>

<style scoped>
.ai-chat {
  margin-top: 24px;
  padding: 24px;
  border: 1px solid #334155;
  border-radius: 18px;
  background: #1a263b;
  color: #f8fafc;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.ai-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  border-radius: 14px;
  background: #243b63;
  font-size: 28px;
}

.chat-header h2 {
  margin: 0 0 6px;
  font-size: 22px;
}

.ai-status {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #94a3b8;
  font-size: 13px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
}

.chat-messages {
  min-height: 280px;
  max-height: 500px;
  overflow-y: auto;
  padding: 20px;
  border-radius: 14px;
  background: #0f172a;
  scroll-behavior: smooth;
}

.welcome {
  padding: 45px 15px;
  text-align: center;
  color: #94a3b8;
}

.welcome-icon {
  font-size: 42px;
}

.welcome h3 {
  color: #e2e8f0;
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 20px;
}

.message-row.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #263a58;
}

.message-bubble {
  max-width: 85%;
  min-width: 0;
  padding: 14px 18px;
  border-radius: 14px;
  background: #334155;
  overflow-wrap: anywhere;
}

.message-row.user .message-bubble {
  background: #1d4ed8;
}

.message-name {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: bold;
  color: #cbd5e1;
}

.message-row.user .message-name {
  color: #dbeafe;
}

.user-content {
  white-space: pre-wrap;
  line-height: 1.7;
}

/* Markdown样式 */
.markdown-body {
  line-height: 1.8;
  font-size: 14px;
  overflow-wrap: anywhere;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 18px 0 10px;
  color: #f8fafc;
}

.markdown-body :deep(h1) {
  font-size: 22px;
}

.markdown-body :deep(h2) {
  font-size: 19px;
}

.markdown-body :deep(h3) {
  font-size: 16px;
}

.markdown-body :deep(p) {
  margin: 8px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 24px;
  margin: 10px 0;
}

.markdown-body :deep(li) {
  margin: 5px 0;
}

.markdown-body :deep(strong) {
  color: #93c5fd;
}

.markdown-body :deep(code) {
  padding: 2px 5px;
  border-radius: 4px;
  background: #0f172a;
  color: #86efac;
}

.markdown-body :deep(pre) {
  padding: 14px;
  border-radius: 8px;
  background: #020617;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
}

.markdown-body :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  margin: 12px 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 8px 12px;
  border: 1px solid #475569;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #1e293b;
}

.markdown-body :deep(a) {
  color: #93c5fd;
}

.loading-content {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #cbd5e1;
  font-size: 13px;
}

.loading-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #60a5fa;
  animation: pulse 1s infinite alternate;
}

.loading-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes pulse {
  from {
    opacity: 0.3;
    transform: translateY(0);
  }

  to {
    opacity: 1;
    transform: translateY(-4px);
  }
}

.chat-input {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.chat-input input {
  flex: 1;
  min-width: 0;
  padding: 13px 15px;
  border: 1px solid #475569;
  border-radius: 10px;
  outline: none;
  background: #0f172a;
  color: white;
}

.chat-input input:focus {
  border-color: #60a5fa;
}

.chat-input button {
  padding: 12px 22px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: white;
  cursor: pointer;
  font-weight: bold;
  white-space: nowrap;
}

.chat-input button:hover:not(:disabled) {
  background: #1d4ed8;
}

.chat-input button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-tip {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 12px;
  text-align: center;
}

@media (max-width: 600px) {
  .ai-chat {
    padding: 14px;
  }

  .chat-messages {
    padding: 12px;
  }

  .message-bubble {
    max-width: 90%;
    padding: 12px;
  }

  .chat-header h2 {
    font-size: 18px;
  }
}

/* AI快捷分析按钮样式 */
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 16px 0;
}

.quick-actions button {
  padding: 10px 16px;
  border: 1px solid #3b82f6;
  border-radius: 10px;
  background: #1e3a5f;
  color: #dbeafe;
  cursor: pointer;
  transition: 0.2s;
}

.quick-actions button:hover:not(:disabled) {
  background: #2563eb;
}

.quick-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
