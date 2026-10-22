
<script setup>
import { ref, onMounted } from 'vue'

const devices = ref([])
const loading = ref(false)
const error = ref('')
const editingId = ref(null)
const form = ref({
  name: '',
  location: '',
  description: '',
  device_type: 'temperature_humidity'
})

async function loadDevices() {
  try {
    const response = await fetch('/api/devices/manage')
    if (!response.ok) throw new Error('加载设备失败')
    devices.value = await response.json()
    error.value = ''
  } catch (err) {
    error.value = err.message
  }
}

function resetForm() {
  editingId.value = null
  form.value = {
    name: '',
    location: '',
    description: '',
    device_type: 'temperature_humidity'
  }
}

// 点击修改按钮时，把设备信息填入表单
function editDevice(device) {
  editingId.value = device.id

  form.value = {
    name: device.name,
    location: device.location || '',
    description: device.description || '',
    device_type: device.device_type || 'temperature_humidity'
  }
}

async function saveDevice() {
  if (!form.value.name.trim() || loading.value) return

  loading.value = true
  error.value = ''

  try {
    const isEditing = editingId.value !== null
    const url = isEditing
      ? `/api/devices/manage/${editingId.value}`
      : '/api/devices/create'

    const response = await fetch(url, {
      method: isEditing ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(typeof data.detail === 'string' ? data.detail : '保存失败')
    }

    resetForm()
    await loadDevices()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function deleteDevice(device) {
  if (!confirm(`确定删除设备“${device.name}”吗？`)) return

  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`/api/devices/manage/${device.id}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(typeof data.detail === 'string' ? data.detail : '删除失败')
    }

    if (editingId.value === device.id) resetForm()
    await loadDevices()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(loadDevices)
</script>

<template>
  <section class="manager">
    <h2>⚙️ 设备信息管理</h2>
    <p class="subtitle">管理数据库中的设备档案</p>

    <form class="device-form" @submit.prevent="saveDevice">
      <h3>{{ editingId === null ? '新增设备' : '修改设备' }}</h3>

      <input v-model="form.name" placeholder="设备名称（必填）" required />

     <select v-model="form.device_type">
     <option value="temperature_humidity">温湿度传感器</option>
     <option value="smoke">烟雾传感器</option>
     </select>

     <input v-model="form.location" placeholder="安装位置" />
     <input v-model="form.description" placeholder="设备描述" />

      <div class="actions">
        <button type="submit" :disabled="loading">
          {{ editingId === null ? '新增设备' : '保存修改' }}
        </button>
        <button v-if="editingId !== null" type="button" @click="resetForm">
          取消修改
        </button>
      </div>
    </form>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>设备名称</th>
            <th>设备类型</th>
            <th>安装位置</th>
            <th>设备描述</th>
            <th>操作</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="device in devices" :key="device.id">
            <td>{{ device.id }}</td>
            <td>{{ device.name }}</td>
            <td>
                    {{ device.device_type === 'smoke' ? '烟雾传感器' : '温湿度传感器' }}
            </td>
            <td>{{ device.location || '未设置' }}</td>
            <td>{{ device.description || '无' }}</td>
            <td>
              <div class="actions">
                <button type="button" @click="editDevice(device)">修改</button>
                <button
                  type="button"
                  class="danger"
                  :disabled="device.id <= 3 || loading"
                  @click="deleteDevice(device)"
                >
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.manager {
  margin-top: 24px;
  padding: 24px;
  border: 1px solid #334155;
  border-radius: 18px;
  background: #1a263b;
  color: #f8fafc;
}

.subtitle { color: #94a3b8; }

.device-form {
  display: grid;
  gap: 12px;
  margin: 20px 0 28px;
}

.device-form input {
  padding: 12px;
  border: 1px solid #475569;
  border-radius: 8px;
  background: #0f172a;
  color: white;
}

.device-form select {
  padding: 12px;
  border: 1px solid #475569;
  border-radius: 8px;
  background: #0f172a;
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

button {
  padding: 9px 16px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  cursor: pointer;
}

button.danger { background: #b91c1c; }

button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.table-wrapper { overflow-x: auto; }

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 14px;
  text-align: left;
  border-bottom: 1px solid #334155;
}

th { background: #243247; }

.error { color: #f87171; }
</style>
