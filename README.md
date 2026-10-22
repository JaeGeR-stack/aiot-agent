# AIoT-Agent：智能设备运维平台

> 基于 Vue 3、FastAPI 和 DeepSeek Function Calling 的物联网设备监控与 AI 辅助运维分析项目。

## 项目简介

AIoT-Agent 是一个面向智能设备运维场景的全栈演示项目。系统通过**模拟传感器数据**展示设备运行状态，支持设备信息管理、历史趋势分析、阈值告警、告警处理和 AI 辅助分析。

AI 助手通过 DeepSeek 的 Function Calling 调用后端查询工具，基于数据库中的设备统计信息和待处理告警回答问题，而非凭空生成设备数据。

**说明：** 当前版本使用模拟数据，未连接真实传感器；AI 诊断建议仅供项目演示，不应作为真实安全决策依据。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 前端 | Vue 3、Vite、JavaScript |
| 图表 | Apache ECharts |
| 后端 | Python、FastAPI、Uvicorn |
| 数据库 | SQLite |
| AI | DeepSeek API（兼容 OpenAI SDK）、Function Calling |
| 配置 | python-dotenv |

## 已实现功能

- **设备管理：** 新增、查看、编辑和删除设备信息；支持温湿度及烟雾传感器类型。
- **实时监控：** 定期更新模拟设备数据，展示设备状态。
- **历史曲线：** 查询最近 50 条采样记录，绘制温湿度或烟雾指数变化曲线。
- **异常检测：** 基于演示阈值判断温度、湿度和烟雾指数异常。
- **告警管理：** 自动保存告警、避免同设备同类型重复待处理告警、支持手动标记处理。
- **告警统计：** 汇总告警总数、待处理数、已处理数、严重告警数及各设备告警数量。
- **AI 辅助分析：** 通过工具调用查询设备历史统计和待处理告警，并用中文生成分析及建议。

## 系统结构

```text
浏览器（Vue 3 + ECharts）
        │
        │ HTTP /api（Vite 开发代理）
        ▼
FastAPI 后端
  ├── 设备管理接口
  ├── 设备历史与告警接口
  ├── 模拟数据生成 / 异常检测
  ├── SQLite 数据库
  └── AI 聊天接口
        │
        ├── 设备统计查询工具
        ├── 待处理告警查询工具
        └── DeepSeek API
```

## 目录结构

```text
aiot-agent/
├── main.py                  # FastAPI 后端及 AI 工具
├── frontend/                # Vue 3 前端
│   ├── src/
│   └── package.json
├── .env                     # 本地 API Key（禁止上传）
├── .venv/                   # 本地 Python 环境（禁止上传）
└── aiot.db                  # 本地 SQLite 数据库（建议不上传）
```

实际目录可能包含额外的开发或备份文件。

## 本地运行

### 环境要求

- Python 3（使用与项目依赖兼容的版本）
- Node.js 和 npm
- 可用的 DeepSeek API Key（仅 AI 功能需要）

### 1. 获取项目

```bash
git clone <你的仓库地址>
cd aiot-agent
```

### 2. 安装后端依赖

Windows 命令提示符（CMD）：

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install fastapi uvicorn openai python-dotenv
```

### 3. 配置 AI Key

在项目根目录创建 `.env`：

```dotenv
DEEPSEEK_API_KEY=替换成你自己的API_Key
```

**切勿把真实 API Key 上传到 GitHub。**

### 4. 启动后端

```bat
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

后端地址：`http://127.0.0.1:8000`  
接口文档：`http://127.0.0.1:8000/docs`

### 5. 启动前端

另开一个 CMD 窗口：

```bat
cd frontend
npm install
npm run dev
```

浏览器打开：`http://localhost:5173/`（若 Vite 显示其他端口，以终端输出为准）。

> 首次运行前，请确认数据库初始化逻辑包含项目所需的设备类型字段和烟雾历史表；现有本地开发数据库可能已经过迁移。不要直接删除正在使用的 `aiot.db`。

## 演示场景

1. 查看温湿度和烟雾传感器的实时模拟数据。
2. 打开设备历史曲线，观察最近 50 条记录。
3. 查看自动生成的异常告警和设备告警分布。
4. 手动将一条待处理告警标记为已处理。
5. 向 AI 助手提问：
   - `分析5号烟雾传感器最近50条数据。`
   - `分析1号温湿度传感器的运行情况。`
   - `查询当前未处理告警，并给出处理建议。`

设备编号取决于本地数据库中的实际设备。

## 项目技术亮点

1. **前后端分离：** Vue 组件通过 RESTful API 获取设备及告警数据。
2. **多类型设备数据模型：** 针对温湿度和烟雾数据分别保存历史记录、绘制图表。
3. **告警业务闭环：** 模拟采样 → 阈值检测 → 告警持久化 → 前端展示 → 人工处理。
4. **大模型工具调用：** 将数据库查询封装为可调用工具，让 AI 根据真实查询结果进行分析。
5. **可视化展示：** 使用 ECharts 展示趋势和设备告警分布。

## 当前限制与后续方向

- 数据由软件模拟，尚未接入 MQTT 或真实物联网硬件。
- 当前主要提供 AI 辅助分析，并非具备完整自主规划、RAG 和长期记忆的 Agent。
- 尚未完善用户认证、自动化测试及生产环境部署。
- 目前使用 SQLite 和本地开发模式，适合个人演示，不直接用于生产环境。

## 上传 GitHub 前的安全检查

请确保 `.gitignore` 至少包含：

```gitignore
.env
.env.*
!.env.example
.venv/
__pycache__/
*.pyc
frontend/node_modules/
frontend/dist/
aiot.db
aiot_backup.db
*.db
```

另外检查源码、测试脚本和提交历史中没有明文 API Key。若密钥曾经泄露，应到服务提供方撤销并重新生成。

## 项目截图

上传 GitHub 前可在这里添加实际截图：

- 设备实时监控
- 历史趋势曲线
- 告警统计
- AI 分析对话

---

**项目定位：** AI 应用开发 / AI Agent 开发实习求职作品（V1.0）。
