import json
from openai import OpenAIError
import asyncio
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from datetime import datetime
import sqlite3
import random
from pydantic import BaseModel, Field



DB_NAME = "aiot.db"

devices = [
    {"id": 1, "name": "车间温度传感器"},
    {"id": 2, "name": "仓库环境传感器"},
    {"id": 3, "name": "机房环境传感器"}
]


# 初始化数据库
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        
        # 告警记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                alert_level TEXT NOT NULL,
                alert_message TEXT NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)

        # 设备信息表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)



init_db()

# 将初始三台设备导入数据库
def seed_devices():
    with sqlite3.connect(DB_NAME) as conn:
        for device in devices:
            conn.execute("""
                INSERT OR IGNORE INTO device_info
                (id, name, location, description, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                device["id"],
                device["name"],
                "",
                "",
                datetime.now().astimezone().isoformat()
            ))

seed_devices()


# 自动检查设备告警
def check_device_alert(device_id, temperature, humidity, timestamp):
    alerts = []

    # 判断温度是否异常
    if temperature > 35:
        level = "critical" if temperature > 40 else "warning"

        alerts.append((
            "temperature",
            level,
            f"设备{device_id}温度异常：{temperature}℃"
        ))

    # 判断湿度是否异常
    if humidity > 70:
        alerts.append((
            "humidity",
            "warning",
            f"设备{device_id}湿度异常：{humidity}%"
        ))

    # 保存告警到SQLite数据库
    with sqlite3.connect(DB_NAME) as conn:
        for alert_type, level, message in alerts:

            # 检查是否已有相同类型的待处理告警
            existing = conn.execute(
                """
                SELECT id
                FROM device_alerts
                WHERE device_id = ?
                  AND alert_type = ?
                  AND status = 'pending'
                LIMIT 1
                """,
                (device_id, alert_type)
            ).fetchone()

            # 不存在相同告警才新增
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO device_alerts
                    (device_id, alert_type, alert_level,
                     alert_message, temperature, humidity,
                     status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        device_id,
                        alert_type,
                        level,
                        message,
                        temperature,
                        humidity,
                        timestamp
                    )
                )


# 生成模拟设备数据
def generate_device_data(device):
    temperature = round(random.uniform(20, 45), 1)
    humidity = round(random.uniform(30, 80), 1)

    status = (
        "warning"
        if temperature > 35 or humidity > 70
        else "normal"
    )

    timestamp = datetime.now().astimezone().isoformat()

    # 保存数据
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO device_history
            (device_id, temperature, humidity, status, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            device["id"],
            temperature,
            humidity,
            status,
            timestamp
        ))

    # 检查设备是否异常，并生成告警
    check_device_alert(
        device["id"],
        temperature,
        humidity,
        timestamp
    )

    return {
        "device_id": device["id"],
        "name": device["name"],
        "temperature": temperature,
        "humidity": humidity,
        "status": status,
        "timestamp": timestamp
    }


# 后台定时采集设备数据
async def collect_device_data():
    while True:
        for device in devices:
            generate_device_data(device)

        #print("设备数据采集完成")

        # 每5秒采集一次
        await asyncio.sleep(5)


# 管理后台采集任务的启动和关闭
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(collect_device_data())

    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="AIoT智能运维平台",
    lifespan=lifespan
)

@app.get("/")
def home():
    return {"message": "AIoT平台运行成功"}




@app.get("/devices")
def get_devices():
    result = []

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        # 从数据库读取所有设备
        device_rows = conn.execute("""
            SELECT id, name, device_type
            FROM device_info
            ORDER BY id
        """).fetchall()

        for row in device_rows:
            device = dict(row)
            device_id = device["id"]
            device_type = device["device_type"]

            # 烟雾传感器：生成模拟数据
            if device_type == "smoke":
                result.append(generate_smoke_data(device))
                continue

            # 温湿度传感器：读取最新历史数据
            history = conn.execute("""
                SELECT device_id, temperature, humidity,
                       status, timestamp
                FROM device_history
                WHERE device_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (device_id,)).fetchone()

            if history:
                device_data = dict(history)
                device_data["name"] = device["name"]
                device_data["device_type"] = device_type
                result.append(device_data)
            else:
                # 没有历史记录的设备显示离线
                result.append({
                    "device_id": device_id,
                    "name": device["name"],
                    "device_type": device_type,
                    "temperature": None,
                    "humidity": None,
                    "status": "offline",
                    "timestamp": None
                })

    return result




@app.get("/device/{device_id}")
def get_device(device_id: int):
    device = next(
        (d for d in devices if d["id"] == device_id),
        None
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="设备不存在"
        )

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT device_id, temperature, humidity,
                   status, timestamp
            FROM device_history
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (device_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="该设备暂无采集数据"
        )

    result = dict(row)
    result["name"] = device["name"]

    return result



@app.get("/history/{device_id}")
def get_history(device_id: int):
    if not any(d["id"] == device_id for d in devices):
        raise HTTPException(
            status_code=404,
            detail="设备不存在"
        )

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT *
            FROM device_history
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT 50
        """, (device_id,)).fetchall()

    return [dict(row) for row in reversed(rows)]


# 查询设备告警记录
@app.get("/alerts")
def get_alerts():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT a.id, a.device_id, a.alert_type, a.alert_level,
                   a.alert_message, a.temperature, a.humidity,
                   a.status, a.created_at, a.resolved_at,
                   COALESCE(d.name, '未知设备') AS device_name
            FROM device_alerts AS a
            LEFT JOIN device_info AS d ON a.device_id = d.id
            ORDER BY a.id DESC
            LIMIT 100
        """).fetchall()
    return [dict(row) for row in rows]

@app.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int):
    resolved_at = datetime.now().astimezone().isoformat()

    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute(
            "SELECT status FROM device_alerts WHERE id = ?",
            (alert_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="告警记录不存在"
            )

        if row[0] == "resolved":
            return {
                "message": "该告警已经处理过",
                "alert_id": alert_id
            }

        conn.execute(
            """
            UPDATE device_alerts
            SET status = ?, resolved_at = ?
            WHERE id = ?
            """,
            ("resolved", resolved_at, alert_id)
        )

    return {
        "message": "告警处理成功",
        "alert_id": alert_id,
        "status": "resolved",
        "resolved_at": resolved_at
    }

# 告警统计分析接口：按数据库全部设备统计（含烟雾传感器）
@app.get("/alerts/statistics")
def get_alert_statistics():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        totals = conn.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                   SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) AS resolved,
                   SUM(CASE WHEN alert_level = 'critical' THEN 1 ELSE 0 END) AS critical
            FROM device_alerts
        """).fetchone()

        distribution = conn.execute("""
            SELECT d.id AS device_id, d.name AS device_name,
                   COUNT(a.id) AS count
            FROM device_info AS d
            LEFT JOIN device_alerts AS a ON a.device_id = d.id
            GROUP BY d.id, d.name
            ORDER BY d.id
        """).fetchall()

    return {
        "total": totals["total"] or 0,
        "pending": totals["pending"] or 0,
        "resolved": totals["resolved"] or 0,
        "critical": totals["critical"] or 0,
        "device_distribution": [dict(row) for row in distribution]
    }

# ==========================
# DeepSeek AI 聊天接口
# ==========================

load_dotenv()

class ChatRequest(BaseModel):
    message: str


@app.post("/ai/chat")
def ai_chat(request: ChatRequest):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="服务器未配置DeepSeek API Key"
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=60.0,
        max_retries=1
    )

    # 告诉大模型可以使用哪些工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_device_statistics",
                "description": "查询指定设备最近50条模拟运行记录，自动识别温湿度或烟雾传感器，返回对应指标、异常采样次数和时间。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "integer",
                            "description": "数据库中的设备编号，例如1、2、3、5、7"
                        }
                    },
                    "required": ["device_id"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_pending_alerts",
                "description": "查询当前未处理的设备告警，包括告警等级、设备名称、告警内容和发生时间，用于分析告警处理优先级。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False
                }
            }
        }
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "你是AIoT智能设备运维平台的AI助手。"
                "当用户要求分析指定设备运行数据时，必须调用get_device_statistics工具。"
                "当用户询问当前待处理告警时，必须调用get_pending_alerts工具。"
                "只能根据工具返回的数据报告统计数值，不得编造读数。"
                "注意异常采样次数不等于告警记录条数。"
                "烟雾指数80及90是本演示系统的模拟阈值，不是消防标准。"
                "当前数据来自模拟传感器，不代表真实设备故障。"
                "请使用中文回答，语言清晰、简洁。"
            )
        },
        {
            "role": "user",
            "content": request.message
        }
    ]

    try:
        # 第一次请求：由DeepSeek决定是否调用工具
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []

        print("===== DeepSeek工具调用检查 =====", flush=True)
        print("tool_calls =", tool_calls, flush=True)

        # 如果不需要工具，直接返回普通回答
        if not tool_calls:
            return {
                "reply": assistant_message.content or "AI没有返回内容"
            }

        # 将模型的工具调用请求加入对话
        messages.append(
            assistant_message.model_dump(exclude_none=True)
        )

        # 执行模型选择的工具
        # 执行AI选择的工具
        for tool_call in tool_calls:
            tool_name = tool_call.function.name

            print(f"[AI Agent] 请求调用工具：{tool_name}")

            if tool_name == "get_pending_alerts":
                result = get_pending_alerts()

            elif tool_name == "get_device_statistics":
                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                    )
                    device_id = arguments.get("device_id")

                    if type(device_id) is not int or device_id <= 0:
                        result = {"error": "设备编号无效"}
                    else:
                        result = get_device_statistics(device_id)

                except (ValueError, TypeError):
                    result = {"error": "工具参数格式错误"}

            else:
                result = {"error": "不支持的工具"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    result,
                    ensure_ascii=False
                )
            })

        # 第二次请求：让DeepSeek根据查询结果回答
        final_response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages
        )

        return {
            "reply": (
                final_response.choices[0].message.content
                or "AI没有返回分析结果"
            )
        }

    except OpenAIError as e:
        print("DeepSeek API调用失败：", type(e).__name__)
        raise HTTPException(
            status_code=502,
            detail="DeepSeek服务调用失败"
        )



# AI Agent工具：根据数据库设备类型分析最近50条历史数据
def get_device_statistics(device_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        device = conn.execute("""
            SELECT id, name, device_type
            FROM device_info WHERE id = ?
        """, (device_id,)).fetchone()
        if device is None:
            return {"error": "设备不存在", "device_id": device_id}

        device_type = device["device_type"]
        if device_type == "smoke":
            rows = conn.execute("""
                SELECT smoke_value, status, timestamp
                FROM smoke_history WHERE device_id = ?
                ORDER BY id DESC LIMIT 50
            """, (device_id,)).fetchall()
        elif device_type == "temperature_humidity":
            rows = conn.execute("""
                SELECT temperature, humidity, status, timestamp
                FROM device_history WHERE device_id = ?
                ORDER BY id DESC LIMIT 50
            """, (device_id,)).fetchall()
        else:
            return {"error": "暂不支持该设备类型", "device_type": device_type}

    if not rows:
        return {"error": "该设备暂无历史数据", "device_id": device_id}

    common = {
        "device_id": device_id,
        "device_name": device["name"],
        "device_type": device_type,
        "record_count": len(rows),
        "warning_count": sum(1 for r in rows if r["status"] == "warning"),
        "latest_timestamp": rows[0]["timestamp"],
        "note": "warning_count表示最近50条中的异常采样次数，不是告警记录条数；数据均为模拟值"
    }

    if device_type == "smoke":
        values = [r["smoke_value"] for r in rows]
        common.update({
            "max_smoke_value": max(values),
            "min_smoke_value": min(values),
            "avg_smoke_value": round(sum(values) / len(values), 2),
            "latest_smoke_value": values[0],
            "warning_threshold": 80,
            "critical_threshold": 90,
            "threshold_note": "仅供演示，不代表真实消防报警标准"
        })
    else:
        temperatures = [r["temperature"] for r in rows]
        humidities = [r["humidity"] for r in rows]
        common.update({
            "max_temperature": max(temperatures),
            "min_temperature": min(temperatures),
            "avg_temperature": round(sum(temperatures) / len(temperatures), 2),
            "latest_temperature": temperatures[0],
            "max_humidity": max(humidities),
            "avg_humidity": round(sum(humidities) / len(humidities), 2),
            "latest_humidity": humidities[0]
        })
    return common


# AI Agent工具：查询当前未处理的所有类型设备告警
def get_pending_alerts():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT a.id, a.device_id, a.alert_type, a.alert_level,
                   a.alert_message, a.status, a.created_at,
                   COALESCE(d.name, '未知设备') AS device_name
            FROM device_alerts AS a
            LEFT JOIN device_info AS d ON d.id = a.device_id
            WHERE a.status = 'pending'
            ORDER BY CASE WHEN a.alert_level = 'critical' THEN 0 ELSE 1 END,
                     a.created_at DESC, a.id DESC
            LIMIT 50
        """).fetchall()

    result = [dict(row) for row in rows]
    return {
        "pending_count": len(result),
        "alerts": result,
        "note": "最多返回50条未处理告警，严重告警优先；烟雾告警阈值仅用于模拟演示"
    }


# 新增设备请求模型
from typing import Literal

class DeviceCreate(BaseModel):
    name: str = Field(min_length=1)
    location: str = ""
    description: str = ""
    device_type: Literal["temperature_humidity", "smoke"] = "temperature_humidity"

# 新增设备接口
@app.post("/devices/create")
def create_device(device: DeviceCreate):
    name = device.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="设备名称不能为空"
        )

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("""
              INSERT INTO device_info
             (name, location, description, device_type, created_at)
             VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            device.location,
            device.description,
            device.device_type,
            datetime.now().astimezone().isoformat()
        ))

        device_id = cursor.lastrowid

    return {
        "message": "设备创建成功",
        "device_id": device_id,
        "name": name
    }


# 查询数据库中的所有设备
@app.get("/devices/manage")
def get_managed_devices():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT
                id,
                name,
                location,
                description,
                device_type,
                created_at
            FROM device_info
            ORDER BY id
        """).fetchall()

    return [dict(row) for row in rows]


# 修改设备信息请求模型
class DeviceUpdate(BaseModel):
    name: str = Field(min_length=1)
    location: str = ""
    description: str = ""
    device_type: Literal["temperature_humidity", "smoke"] = "temperature_humidity"


# 修改设备信息接口
@app.put("/devices/manage/{device_id}")
def update_device(device_id: int, device: DeviceUpdate):
    name = device.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="设备名称不能为空"
        )

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("""
              UPDATE device_info
              SET name = ?, location = ?, description = ?, device_type = ?
              WHERE id = ?
        """, (
            name,
            device.location,
            device.description,
            device.device_type,
            device_id
        ))

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="设备不存在"
            )

    return {
        "message": "设备信息修改成功",
        "device_id": device_id,
        "name": name
    }


# 删除设备接口
@app.delete("/devices/manage/{device_id}")
def delete_device(device_id: int):

    # 暂时保护原来的3台监控设备
    if device_id in (1, 2, 3):
        raise HTTPException(
            status_code=400,
            detail="原始监控设备暂不允许删除"
        )

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(
            "DELETE FROM device_info WHERE id = ?",
            (device_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="设备不存在"
            )

    return {
        "message": "设备删除成功",
        "device_id": device_id
    }


# 检查烟雾异常：同设备只保留一条未处理烟雾告警
# 阈值仅供模拟演示，不代表消防报警标准
def check_smoke_alert(device_id, smoke_value, timestamp):
    if smoke_value < 80:
        return

    level = "critical" if smoke_value >= 90 else "warning"
    message = f"设备{device_id}烟雾指数异常：{smoke_value}，请及时检查设备运行情况"

    with sqlite3.connect(DB_NAME) as conn:
        existing = conn.execute("""
            SELECT id FROM device_alerts
            WHERE device_id = ? AND alert_type = 'smoke'
              AND status = 'pending'
            LIMIT 1
        """, (device_id,)).fetchone()
        if existing is not None:
            return
        # 原表温湿度字段为 NOT NULL，使用0作为不适用的占位值
        conn.execute("""
            INSERT INTO device_alerts
            (device_id, alert_type, alert_level, alert_message,
             temperature, humidity, status, created_at)
            VALUES (?, 'smoke', ?, ?, 0, 0, 'pending', ?)
        """, (device_id, level, message, timestamp))

# 模拟烟雾传感器数据，并保存历史记录
def generate_smoke_data(device):
    smoke_value = round(random.uniform(0, 100), 1)

    # 演示用阈值，不代表真实消防报警标准
    status = "warning" if smoke_value >= 80 else "normal"

    timestamp = datetime.now().astimezone().isoformat()

    # 保存烟雾历史数据
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO smoke_history (
                device_id,
                smoke_value,
                status,
                timestamp
            )
            VALUES (?, ?, ?, ?)
        """, (
            device["id"],
            smoke_value,
            status,
            timestamp
        ))

    # 将超阈值烟雾数据同步到统一告警表
    check_smoke_alert(device["id"], smoke_value, timestamp)

    return {
        "device_id": device["id"],
        "name": device["name"],
        "device_type": "smoke",
        "smoke_value": smoke_value,
        "status": status,
        "timestamp": timestamp
    }


# 查询烟雾传感器历史数据
@app.get("/smoke/history/{device_id}")
def get_smoke_history(device_id: int):

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        # 检查设备是否存在且属于烟雾传感器
        device = conn.execute("""
            SELECT id
            FROM device_info
            WHERE id = ? AND device_type = 'smoke'
        """, (device_id,)).fetchone()

        if device is None:
            raise HTTPException(
                status_code=404,
                detail="烟雾传感器不存在"
            )

        # 查询最近50条记录
        rows = conn.execute("""
            SELECT id, device_id, smoke_value,
                   status, timestamp
            FROM smoke_history
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT 50
        """, (device_id,)).fetchall()

    return [dict(row) for row in reversed(rows)]