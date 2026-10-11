import asyncio
import collections
import datetime
import json
import logging
import os
import sqlite3
import sys
import threading
import time
from typing import List, Dict, Any, Optional

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel

# ==============================================================================
# CONFIGURATION
# ==============================================================================
MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.1.62")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_INPUT = "macropad/input"
TOPIC_DISPLAY = "macropad/display"
TOPIC_STATUS = "macropad/status"
TOPIC_DEBUG = "macropad/debug"
TOPIC_WILDCARD = "macropad/#"

DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

# Persistent SQLite Battery Database
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "battery_history.db")

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS battery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                time_str TEXT,
                vbat REAL,
                batt_pct INTEGER,
                rssi INTEGER,
                state TEXT
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_battery_time ON battery_logs (timestamp)')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing SQLite database: {e}")

init_db()

def log_battery_to_db(vbat: float, batt_pct: int, rssi: int, state: str):
    try:
        now = time.time()
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH, timeout=2.0)
        c = conn.cursor()
        c.execute('''
            INSERT INTO battery_logs (timestamp, time_str, vbat, batt_pct, rssi, state)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (now, time_str, vbat, batt_pct, rssi, state))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

# ==============================================================================
# STATE & LOG BUFFER
# ==============================================================================
MAX_LOG_HISTORY = 1000
log_buffer = collections.deque(maxlen=MAX_LOG_HISTORY)

device_state: Dict[str, Any] = {
    "connected": False,
    "state": "unknown",         # "online", "sleeping", "offline"
    "last_seen": 0,
    "last_seen_str": "Never",
    "vbat": 0.0,
    "batt_pct": 0,
    "rssi": 0,
    "heap": 0,
    "min_heap": 0,
    "uptime_ms": 0,
    "uptime_str": "0s",
    "bank": 1,
    "slot": 1,
    "layer": 1,
    "modifier": False,
    "reset_reason": "Unknown",
    "screen_msg": "",
    "grid_labels": ["ACT 1", "ACT 2", "ACT 3", "ACT 4", "ACT 5", "ACT 6", "LT SLP", "SLEEP", "WOL PC"],
    "last_action": None,
    "encoder_states": {"1": 0, "2": 0, "3": 0},
    "key_matrix": {str(i): False for i in range(1, 17)}
}

# ==============================================================================
# BATTERY CAPACITY BENCHMARK STATE
# ==============================================================================
benchmark_state: Dict[str, Any] = {
    "active": False,
    "status": "idle",           # "idle", "running", "completed", "cancelled"
    "start_time": 0,
    "start_time_str": "None",
    "start_vbat": 0.0,
    "current_vbat": 0.0,
    "current_ma": 36.0,
    "elapsed_seconds": 0,
    "elapsed_str": "0m",
    "computed_mah": 0.0,
    "target_cutoff_v": 3.30,
    "data_points": []           # List of {"time": str, "elapsed_mins": float, "vbat": float, "mah": float}
}

# Active WebSocket subscribers
ws_clients: List[WebSocket] = []
async_loop: Optional[asyncio.AbstractEventLoop] = None

# ==============================================================================
# FASTAPI APPLICATION
# ==============================================================================
app = FastAPI(title="MacroPad Unified Hub & Bridge")

class PopupRequest(BaseModel):
    message: str

class LayerRequest(BaseModel):
    layer: Optional[int] = None
    bank: Optional[int] = None

class PublishRequest(BaseModel):
    topic: str
    payload: Dict[str, Any]

class NotificationRequest(BaseModel):
    type: str = "call"                  # "call", "message", "alert", "custom"
    source: str = "whatsapp"            # "whatsapp", "discord", "hass", "pc"
    sender: str = "Unknown"
    message: Optional[str] = ""
    duration_ms: Optional[int] = 4000
    led_effect: Optional[str] = None    # "pulse_green", "pulse_cyan", "pulse_amber"

class BenchmarkStartRequest(BaseModel):
    current_ma: float = 36.0
    cutoff_v: float = 3.30

class HassActionRequest(BaseModel):
    action: str                         # "light_toggle", "preset_recall", "wakeonlan", "audio_switch"
    index: Optional[int] = 1
    target: Optional[str] = None

# Helper to format timestamp
def get_iso_timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

def format_uptime(ms: int) -> str:
    secs = ms // 1000
    mins = secs // 60
    hours = mins // 60
    if hours > 0:
        return f"{hours}h {mins % 60}m {secs % 60}s"
    elif mins > 0:
        return f"{mins}m {secs % 60}s"
    else:
        return f"{secs}s"

def add_log_entry(level: str, tag: str, message: str, raw_topic: str = "", raw_payload: Any = None):
    entry = {
        "id": int(time.time() * 1000),
        "time": get_iso_timestamp(),
        "level": level.upper(),
        "tag": tag.upper(),
        "msg": message,
        "topic": raw_topic,
        "payload": raw_payload
    }
    log_buffer.append(entry)
    
    # Broadcast to WebSockets
    if async_loop and ws_clients:
        msg_json = json.dumps({"type": "log", "data": entry})
        for client in list(ws_clients):
            try:
                asyncio.run_coroutine_threadsafe(client.send_text(msg_json), async_loop)
            except Exception:
                pass

def broadcast_state():
    if async_loop and ws_clients:
        msg_json = json.dumps({
            "type": "state", 
            "data": device_state,
            "benchmark": benchmark_state
        })
        for client in list(ws_clients):
            try:
                asyncio.run_coroutine_threadsafe(client.send_text(msg_json), async_loop)
            except Exception:
                pass

# ==============================================================================
# BENCHMARK ENGINE
# ==============================================================================
def update_benchmark_point(vbat: float):
    if not benchmark_state["active"]:
        return
    now = time.time()
    elapsed = now - benchmark_state["start_time"]
    benchmark_state["elapsed_seconds"] = elapsed
    mins = elapsed / 60.0
    hours = elapsed / 3600.0
    
    # Format elapsed string
    h = int(hours)
    m = int((elapsed % 3600) // 60)
    benchmark_state["elapsed_str"] = f"{h}h {m}m" if h > 0 else f"{m}m"
    
    # Computed mAh
    computed_mah = hours * benchmark_state["current_ma"]
    benchmark_state["computed_mah"] = round(computed_mah, 1)
    benchmark_state["current_vbat"] = round(vbat, 3)

    # Record data point if 1 minute passed or first point
    pts = benchmark_state["data_points"]
    if not pts or (mins - pts[-1]["elapsed_mins"] >= 1.0):
        point = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "elapsed_mins": round(mins, 1),
            "vbat": round(vbat, 3),
            "mah": round(computed_mah, 1)
        }
        pts.append(point)
        # Limit in-memory points
        if len(pts) > 5000:
            benchmark_state["data_points"] = pts[-5000:]

    # Check for cutoff completion
    if vbat > 0.5 and vbat <= benchmark_state["target_cutoff_v"]:
        benchmark_state["active"] = False
        benchmark_state["status"] = "completed"
        add_log_entry("SYSTEM", "BENCHMARK", f"🎉 Battery Benchmark COMPLETED! Total Measured Capacity: {benchmark_state['computed_mah']} mAh ({benchmark_state['elapsed_str']})")

# ==============================================================================
# HOME ASSISTANT MQTT DISCOVERY
# ==============================================================================
def publish_ha_discovery():
    """Publishes Home Assistant MQTT Discovery payloads for MacroPad Battery & Telemetry"""
    if not mqtt_client.is_connected():
        return
    
    device_info = {
        "identifiers": ["macropad_c3_01"],
        "name": "MacroPad Controller",
        "model": "ESP32-S2 E-Ink MacroPad",
        "manufacturer": "Custom / Uzzo",
        "sw_version": "2.4.0"
    }

    # 1. Battery Percentage Sensor
    sensor_pct_config = {
        "name": "MacroPad Battery",
        "unique_id": "macropad_battery_pct",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "state_topic": TOPIC_STATUS,
        "value_template": "{{ value_json.batt_pct }}",
        "device": device_info
    }
    mqtt_client.publish("homeassistant/sensor/macropad/battery/config", json.dumps(sensor_pct_config), retain=True)

    # 2. Battery Voltage Sensor
    sensor_vbat_config = {
        "name": "MacroPad Battery Voltage",
        "unique_id": "macropad_battery_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "state_topic": TOPIC_STATUS,
        "value_template": "{{ value_json.vbat }}",
        "device": device_info
    }
    mqtt_client.publish("homeassistant/sensor/macropad/voltage/config", json.dumps(sensor_vbat_config), retain=True)

    # 3. Wi-Fi RSSI Sensor
    sensor_rssi_config = {
        "name": "MacroPad Signal Strength",
        "unique_id": "macropad_wifi_rssi",
        "device_class": "signal_strength",
        "state_class": "measurement",
        "unit_of_measurement": "dBm",
        "state_topic": TOPIC_STATUS,
        "value_template": "{{ value_json.rssi }}",
        "entity_category": "diagnostic",
        "device": device_info
    }
    mqtt_client.publish("homeassistant/sensor/macropad/rssi/config", json.dumps(sensor_rssi_config), retain=True)

    # 4. Device State / Power Status Sensor
    sensor_state_config = {
        "name": "MacroPad Power State",
        "unique_id": "macropad_power_state",
        "state_topic": TOPIC_STATUS,
        "value_template": "{{ value_json.state }}",
        "icon": "mdi:keyboard",
        "device": device_info
    }
    mqtt_client.publish("homeassistant/sensor/macropad/state/config", json.dumps(sensor_state_config), retain=True)
    add_log_entry("HASS", "MQTT", "Published Home Assistant Auto-Discovery entities for Battery, Voltage & RSSI")

# ==============================================================================
# MQTT CLIENT
# ==============================================================================
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        add_log_entry("SYSTEM", "MQTT", f"Connected to broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(TOPIC_WILDCARD)
        add_log_entry("SYSTEM", "MQTT", f"Subscribed to topic pattern: {TOPIC_WILDCARD}")
        publish_ha_discovery()
    else:
        add_log_entry("ERROR", "MQTT", f"Failed to connect to broker, return code: {rc}")

def on_mqtt_disconnect(client, userdata, flags, rc, properties=None):
    add_log_entry("WARN", "MQTT", f"Disconnected from broker (rc={rc})")

def on_mqtt_message(client, userdata, msg):
    topic = msg.topic
    now = time.time()
    device_state["last_seen"] = now
    device_state["last_seen_str"] = datetime.datetime.now().strftime("%H:%M:%S")

    try:
        payload_str = msg.payload.decode('utf-8')
        payload = json.loads(payload_str)
    except Exception:
        add_log_entry("INFO", "RAW", f"[{topic}] {msg.payload}", raw_topic=topic)
        return

    # 1. INPUT MESSAGES
    if topic == TOPIC_INPUT:
        action = payload.get("action", "unknown")
        device_state["last_action"] = payload
        modifier = payload.get("modifier", False)
        device_state["modifier"] = modifier
        if "layer" in payload:
            device_state["layer"] = payload["layer"]
            device_state["bank"] = ((payload["layer"] - 1) // 4) + 1
            device_state["slot"] = ((payload["layer"] - 1) % 4) + 1

        if action == "macro":
            idx = payload.get("index")
            lbl = payload.get("label", "")
            add_log_entry("INPUT", "KEY", f"Dynamic Macro Key #{idx} pressed -> '{lbl}' (Layer {payload.get('layer')})", raw_topic=topic, raw_payload=payload)
        
        elif action == "light_toggle":
            add_log_entry("INPUT", "KEY", "Key 5 tapped: Room Light Toggle triggered", raw_topic=topic, raw_payload=payload)
        
        elif action == "sleep":
            add_log_entry("INPUT", "KEY", "ACT 8 tapped: Instant Deep Sleep triggered", raw_topic=topic, raw_payload=payload)

        elif action == "wifi_sleep_toggle":
            enabled = payload.get("enabled", False)
            mode_str = "MODEM SLEEP (DTIM Listen)" if enabled else "FULL POWER (115mA)"
            add_log_entry("INPUT", "PWR", f"ACT 7 tapped: Switched WiFi mode to {mode_str}", raw_topic=topic, raw_payload=payload)

        elif action == "encoder_scroll":
            enc_id = payload.get("id")
            delta = payload.get("delta")
            mod_tag = " [MODIFIER ACTIVE]" if modifier else ""
            add_log_entry("INPUT", "ENCODER", f"Encoder {enc_id} rotated: delta={delta:+d}{mod_tag}", raw_topic=topic, raw_payload=payload)
        
        elif action == "encoder_click":
            enc_id = payload.get("id")
            mod_tag = " [MODIFIER ACTIVE]" if modifier else ""
            add_log_entry("INPUT", "ENCODER", f"Encoder {enc_id} CLICKED{mod_tag}", raw_topic=topic, raw_payload=payload)

        elif action == "preset_recall":
            idx = payload.get("index")
            add_log_entry("INPUT", "PRESET", f"Modifier + Tap Key #{idx} -> RECALL PRESET {idx}", raw_topic=topic, raw_payload=payload)

        elif action == "preset_save":
            idx = payload.get("index")
            add_log_entry("INPUT", "PRESET", f"Modifier + Hold Key #{idx} (>600ms) -> SAVED PRESET {idx}", raw_topic=topic, raw_payload=payload)

        elif action == "wakeonlan":
            mac = payload.get("mac", "d4:93:90:3b:f0:89")
            add_log_entry("INPUT", "WOL", f"Wake-on-LAN Magic Packet sent to {mac}", raw_topic=topic, raw_payload=payload)

        elif action == "notification_ack":
            add_log_entry("NOTIF", "ACK", "🔔 MacroPad alert acknowledged by user", raw_topic=topic, raw_payload=payload)
            try:
                import urllib.request
                req = urllib.request.Request("http://127.0.0.1:5001/api/ack", data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')
                urllib.request.urlopen(req, timeout=1.5)
            except Exception as e:
                pass

        else:
            add_log_entry("INPUT", action.upper(), f"Action: {action} -> {json.dumps(payload)}", raw_topic=topic, raw_payload=payload)

        broadcast_state()

    # 2. STATUS / HEARTBEAT MESSAGES
    elif topic == TOPIC_STATUS:
        state = payload.get("state", "online")
        device_state["state"] = state
        device_state["connected"] = (state == "online")

        if "vbat" in payload:
            v = float(payload["vbat"])
            device_state["vbat"] = v
            update_benchmark_point(v)

        if "batt_pct" in payload:
            device_state["batt_pct"] = int(payload["batt_pct"])
        if "rssi" in payload:
            device_state["rssi"] = int(payload["rssi"])
        if "heap" in payload:
            device_state["heap"] = int(payload["heap"])
        if "min_heap" in payload:
            device_state["min_heap"] = int(payload["min_heap"])
        if "uptime" in payload:
            device_state["uptime_ms"] = int(payload["uptime"])
            device_state["uptime_str"] = format_uptime(int(payload["uptime"]))
        if "bank" in payload:
            device_state["bank"] = int(payload["bank"])
        if "slot" in payload:
            device_state["slot"] = int(payload["slot"])
        if "layer" in payload:
            device_state["layer"] = int(payload["layer"])
        if "reset_reason" in payload:
            device_state["reset_reason"] = str(payload["reset_reason"])

        # Persist battery telemetry to SQLite DB
        if "vbat" in payload and float(payload["vbat"]) > 0.5:
            log_battery_to_db(float(payload["vbat"]), device_state.get("batt_pct", 0), device_state.get("rssi", 0), state)

        if state == "deep_sleeping":
            reason = payload.get("reason", "idle")
            add_log_entry("SYSTEM", "SLEEP", f"MacroPad entered DEEP SLEEP (Reason: {reason}, Vbat: {device_state['vbat']:.2f}V)", raw_topic=topic, raw_payload=payload)
        elif payload.get("event") == "wake":
            cause = payload.get("cause", "unknown")
            add_log_entry("SYSTEM", "WAKE", f"MacroPad WOKE UP from deep sleep (Wake cause: {cause})", raw_topic=topic, raw_payload=payload)
        else:
            add_log_entry("SYSTEM", "HEARTBEAT", f"Heartbeat: Vbat={device_state['vbat']:.2f}V ({device_state.get('batt_pct', 0)}%), RSSI={device_state['rssi']}dBm, Heap={device_state['heap']//1024}KB, Layer={device_state['layer']}", raw_topic=topic, raw_payload=payload)

        broadcast_state()

    # 3. DEBUG / DIAGNOSTIC LOGS
    elif topic == TOPIC_DEBUG:
        level = payload.get("level", "INFO")
        tag = payload.get("tag", "DEVICE")
        msg = payload.get("msg", json.dumps(payload))
        add_log_entry(level, tag, msg, raw_topic=topic, raw_payload=payload)

    # 4. DISPLAY / SCREEN UPDATES
    elif topic == TOPIC_DISPLAY:
        if "popup" in payload:
            device_state["screen_msg"] = payload["popup"]
            add_log_entry("DISPLAY", "POPUP", f"Screen Popup: \"{payload['popup']}\"", raw_topic=topic, raw_payload=payload)
        if "notification" in payload:
            n = payload["notification"]
            add_log_entry("NOTIFY", n.get("type", "ALERT").upper(), f"Push Alert [{n.get('source', 'app').upper()}]: {n.get('sender', '')} - {n.get('message', '')}", raw_topic=topic, raw_payload=payload)
        if "labels" in payload and isinstance(payload["labels"], list):
            device_state["grid_labels"] = payload["labels"][:9]
            add_log_entry("DISPLAY", "LABELS", f"Screen Labels Updated: {payload['labels'][:9]}", raw_topic=topic, raw_payload=payload)
        if "bank" in payload:
            device_state["bank"] = int(payload["bank"])
        if "layer" in payload:
            device_state["layer"] = int(payload["layer"])
            device_state["bank"] = ((payload["layer"] - 1) // 4) + 1
            device_state["slot"] = ((payload["layer"] - 1) % 4) + 1
        broadcast_state()

    else:
        add_log_entry("INFO", "MQTT", f"[{topic}] {payload_str}", raw_topic=topic, raw_payload=payload)

# MacroPad Stay-Awake Enforcer
def ensure_macropad_stay_awake():
    try:
        import urllib.request
        req = urllib.request.Request("http://192.168.1.58/api/status", headers={"User-Agent": "MacroPadHub"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            device_state["stay_awake"] = data.get("stay_awake", False)
            if not data.get("stay_awake", False):
                toggle_req = urllib.request.Request("http://192.168.1.58/api/toggle_stay_awake", data=b"", headers={"User-Agent": "MacroPadHub"}, method="POST")
                with urllib.request.urlopen(toggle_req, timeout=1.5) as t_resp:
                    res_str = t_resp.read().decode()
                    device_state["stay_awake"] = (res_str == "ON")
                    add_log_entry("SYSTEM", "POWER", "MacroPad stay-awake mode enforced (Sleep disabled 24/7)")
    except Exception:
        pass

# Background liveness watchdog
def liveness_watchdog():
    last_stay_awake_check = 0
    while True:
        time.sleep(5)
        now = time.time()
        last = device_state.get("last_seen", 0)
        curr_state = device_state.get("state")
        
        # Periodically ensure MacroPad stay-awake is active
        if curr_state == "online" and (now - last_stay_awake_check > 25):
            last_stay_awake_check = now
            ensure_macropad_stay_awake()

        # Periodic update for benchmark timer while active
        if benchmark_state["active"]:
            elapsed = now - benchmark_state["start_time"]
            benchmark_state["elapsed_seconds"] = elapsed
            hours = elapsed / 3600.0
            h = int(hours)
            m = int((elapsed % 3600) // 60)
            benchmark_state["elapsed_str"] = f"{h}h {m}m" if h > 0 else f"{m}m"
            benchmark_state["computed_mah"] = round(hours * benchmark_state["current_ma"], 1)

        if last > 0 and (now - last > 75) and curr_state not in ("deep_sleeping", "offline"):
            device_state["state"] = "offline"
            device_state["connected"] = False
            add_log_entry("WARN", "WATCHDOG", f"No signal from MacroPad for {int(now - last)}s - marking as OFFLINE/SLEEPING")
            broadcast_state()

# ==============================================================================
# REST API ENDPOINTS
# ==============================================================================
@app.get("/api/status")
async def get_status():
    return {
        "device": device_state,
        "benchmark": benchmark_state
    }

@app.get("/api/logs")
async def get_logs():
    return list(log_buffer)

@app.get("/api/export_logs")
async def export_logs():
    lines = []
    for l in log_buffer:
        lines.append(f"[{l['time']}] [{l['level']:<5}] [{l['tag']:<8}] {l['msg']}")
    return PlainTextResponse("\n".join(lines), media_type="text/plain", headers={"Content-Disposition": "attachment; filename=macropad_debug.log"})

# Universal Notification Dispatcher (WhatsApp / Home Assistant / PC Alerts)
@app.post("/api/macropad/toggle_stay_awake")
async def toggle_macropad_stay_awake():
    try:
        import urllib.request
        toggle_req = urllib.request.Request("http://192.168.1.58/api/toggle_stay_awake", data=b"", headers={"User-Agent": "MacroPadHub"}, method="POST")
        with urllib.request.urlopen(toggle_req, timeout=2.0) as t_resp:
            res_str = t_resp.read().decode().strip()
            device_state["stay_awake"] = (res_str == "ON")
            add_log_entry("SYSTEM", "POWER", f"MacroPad Stay Awake toggled -> {res_str}")
            broadcast_state()
            return {"status": "ok", "stay_awake": device_state["stay_awake"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/notify")
async def send_notification(req: NotificationRequest):
    led_eff = req.led_effect
    if not led_eff:
        if req.type == "call":
            led_eff = "pulse_green"
        elif req.type == "message":
            led_eff = "pulse_cyan"
        else:
            led_eff = "pulse_amber"

    type_upper = req.type.upper()
    popup_text = f"{type_upper}:\n{req.sender}"
    if req.message and len(req.message) <= 12:
        popup_text = f"{req.sender}:\n{req.message}"

    payload = {
        "popup": popup_text,
        "notification": {
            "type": req.type,
            "source": req.source,
            "sender": req.sender,
            "message": req.message
        },
        "led_effect": led_eff,
        "duration": req.duration_ms or 4000
    }
    mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload))
    add_log_entry("NOTIFY", req.source.upper(), f"Dispatched {req.type.upper()} alert from '{req.sender}': {req.message}")
# WhatsApp 24/7 Bridge Endpoints
WHATSAPP_DIR = "/home/uzzo/MACROPAD/whatsapp_bridge"
WHATSAPP_STATUS_FILE = os.path.join(WHATSAPP_DIR, "qr_status.json")
WHATSAPP_CONFIG_FILE = os.path.join(WHATSAPP_DIR, "config.json")

@app.get("/api/whatsapp/status")
async def get_whatsapp_status():
    if os.path.exists(WHATSAPP_STATUS_FILE):
        try:
            with open(WHATSAPP_STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            return {"connected": False, "status": f"Error reading state: {e}", "qr_image": None}
    return {"connected": False, "status": "Initializing WhatsApp Bridge...", "qr_image": None}

@app.get("/api/whatsapp/config")
async def get_whatsapp_config():
    if os.path.exists(WHATSAPP_CONFIG_FILE):
        try:
            with open(WHATSAPP_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "vip_contacts": [
            {"name": "Mom", "phone": "", "aliases": ["mom", "mamma", "mother"]},
            {"name": "Dad", "phone": "", "aliases": ["dad", "papa", "father"]},
            {"name": "Sister", "phone": "", "aliases": ["sister", "sis"]}
        ],
        "trigger_keywords": ["!call", "!urgent", "!alert", "call", "urgent", "🚨", "📞", "ring"],
        "any_vip_message_triggers": False,
        "incoming_call_triggers": True,
        "send_ack_reaction": False,
        "ack_reaction_emoji": "✅"
    }
# WhatsApp Recent Chats & Contacts Lookup
WHATSAPP_RECENT_CHATS_FILE = os.path.join(WHATSAPP_DIR, "recent_chats.json")

@app.get("/api/whatsapp/recent_chats")
async def get_whatsapp_recent_chats():
    if os.path.exists(WHATSAPP_RECENT_CHATS_FILE):
        try:
            with open(WHATSAPP_RECENT_CHATS_FILE, "r") as f:
                chats = json.load(f)
            # Filter out groups and broadcasts
            return [
                c for c in chats 
                if c and not any(g in c.get("jid", "") for g in ["@g.us", "@broadcast", "@newsletter", "genio"])
            ]
        except Exception as e:
            return []
    return []

# Battery Long-term History API (SQLite)
@app.get("/api/battery/history")
async def get_battery_history(hours: int = 48):
    try:
        since = time.time() - (hours * 3600)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            SELECT time_str, vbat, batt_pct, rssi, state, timestamp 
            FROM battery_logs 
            WHERE timestamp >= ? 
            ORDER BY timestamp ASC
        ''', (since,))
        rows = c.fetchall()
        conn.close()
        
        # Subsample if too many rows for smooth charting
        step = max(1, len(rows) // 300)
        downsampled = rows[::step]

        return [
            {
                "time": r[0],
                "vbat": round(r[1], 2),
                "batt_pct": r[2],
                "rssi": r[3],
                "state": r[4],
                "ts": r[5]
            }
            for r in downsampled
        ]
    except Exception as e:
        return []

@app.post("/api/whatsapp/config")
async def save_whatsapp_config(data: Dict[str, Any]):
    try:
        with open(WHATSAPP_CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
        add_log_entry("SYSTEM", "WHATSAPP", "Updated WhatsApp VIP contacts & trigger rules")
        return {"status": "saved", "config": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Battery Capacity Benchmark Endpoints
@app.post("/api/benchmark/start")
async def start_benchmark(req: BenchmarkStartRequest):
    benchmark_state["active"] = True
    benchmark_state["status"] = "running"
    benchmark_state["start_time"] = time.time()
    benchmark_state["start_time_str"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    benchmark_state["start_vbat"] = device_state["vbat"]
    benchmark_state["current_vbat"] = device_state["vbat"]
    benchmark_state["current_ma"] = req.current_ma
    benchmark_state["target_cutoff_v"] = req.cutoff_v
    benchmark_state["elapsed_seconds"] = 0
    benchmark_state["elapsed_str"] = "0m"
    benchmark_state["computed_mah"] = 0.0
    benchmark_state["data_points"] = [{
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "elapsed_mins": 0.0,
        "vbat": device_state["vbat"],
        "mah": 0.0
    }]
    add_log_entry("SYSTEM", "BENCHMARK", f"Started Battery Capacity Test @ {req.current_ma} mA (Cutoff: {req.cutoff_v}V, Start Vbat: {device_state['vbat']}V)")
    broadcast_state()
    return {"status": "started", "benchmark": benchmark_state}

@app.post("/api/benchmark/stop")
async def stop_benchmark():
    benchmark_state["active"] = False
    benchmark_state["status"] = "cancelled"
    add_log_entry("SYSTEM", "BENCHMARK", f"Battery Capacity Test stopped manually. Logged: {benchmark_state['computed_mah']} mAh over {benchmark_state['elapsed_str']}.")
    broadcast_state()
    return {"status": "stopped", "benchmark": benchmark_state}

@app.post("/api/benchmark/reset")
async def reset_benchmark():
    benchmark_state["active"] = False
    benchmark_state["status"] = "idle"
    benchmark_state["start_time"] = 0
    benchmark_state["start_time_str"] = "None"
    benchmark_state["computed_mah"] = 0.0
    benchmark_state["elapsed_seconds"] = 0
    benchmark_state["elapsed_str"] = "0m"
    benchmark_state["data_points"] = []
    add_log_entry("SYSTEM", "BENCHMARK", "Battery benchmark data cleared.")
    broadcast_state()
    return {"status": "reset"}

@app.get("/api/benchmark/data")
async def get_benchmark_data():
    return benchmark_state

# Home Assistant / Device Quick Actions
@app.post("/api/hass/action")
async def hass_action(req: HassActionRequest):
    payload = {}
    if req.action == "light_toggle":
        payload = {"action": "light_toggle"}
        mqtt_client.publish(TOPIC_INPUT, json.dumps(payload))
    elif req.action == "preset_recall":
        payload = {"action": "preset_recall", "index": req.index, "modifier": True}
        mqtt_client.publish(TOPIC_INPUT, json.dumps(payload))
    elif req.action == "wakeonlan":
        payload = {"action": "wakeonlan", "mac": "d4:93:90:3b:f0:89"}
        mqtt_client.publish(TOPIC_INPUT, json.dumps(payload))
    elif req.action == "audio_switch":
        target = req.target or "headphones"
        payload = {"action": "audio_device_select", "target": target}
        mqtt_client.publish(TOPIC_INPUT, json.dumps(payload))
    
    add_log_entry("HASS", "ACTION", f"Executed Quick Action: {req.action} ({json.dumps(payload)})")
    return {"status": "executed", "payload": payload}

@app.post("/api/send_popup")
async def send_popup(req: PopupRequest):
    payload = {"popup": req.message}
    mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload))
    add_log_entry("DISPLAY", "POPUP", f"Web Dashboard sent popup: \"{req.message}\"")
    return {"status": "sent", "payload": payload}

@app.post("/api/set_layer")
async def set_layer(req: LayerRequest):
    payload = {}
    if req.layer is not None:
        payload["layer"] = req.layer
    elif req.bank is not None:
        payload["bank"] = req.bank
    if payload:
        mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload))
        add_log_entry("DISPLAY", "CONFIG", f"Web Dashboard sent layer config: {payload}")
    return {"status": "sent", "payload": payload}

@app.post("/api/publish")
async def publish_custom(req: PublishRequest):
    mqtt_client.publish(req.topic, json.dumps(req.payload))
    add_log_entry("MQTT", "PUBLISH", f"Published to {req.topic}: {json.dumps(req.payload)}")
    return {"status": "published"}

# ==============================================================================
# WEBSOCKET STREAM
# ==============================================================================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    try:
        await websocket.send_text(json.dumps({
            "type": "state", 
            "data": device_state,
            "benchmark": benchmark_state
        }))
        recent_logs = list(log_buffer)[-150:]
        await websocket.send_text(json.dumps({"type": "history", "data": recent_logs}))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
    except Exception:
        if websocket in ws_clients:
            ws_clients.remove(websocket)

# ==============================================================================
# EMBEDDED DASHBOARD FRONTEND HTML
# ==============================================================================
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MacroPad Unified Hub & Pi Bridge</title>
<style>
  :root {
    --bg-primary: #0a0e14;
    --bg-secondary: #131924;
    --bg-card: #182234;
    --bg-terminal: #070a0f;
    --accent-cyan: #00f3ff;
    --accent-green: #00ff66;
    --accent-amber: #ffb800;
    --accent-magenta: #ff007f;
    --accent-blue: #3a86ff;
    --accent-red: #ff3344;
    --accent-purple: #b5179e;
    --text-main: #e6edf3;
    --text-dim: #7d8590;
    --border-color: #21262d;
    --font-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg-primary);
    color: var(--text-main);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* TOP TELEMETRY NAVBAR */
  header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 10px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-shrink: 0;
  }
  .title-group {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .brand-icon {
    font-size: 20px;
    filter: drop-shadow(0 0 8px var(--accent-cyan));
  }
  h1 {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .badge-state {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    text-transform: uppercase;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .state-online { background: rgba(0,255,102,0.15); color: var(--accent-green); border: 1px solid var(--accent-green); }
  .state-sleeping { background: rgba(255,184,0,0.15); color: var(--accent-amber); border: 1px solid var(--accent-amber); }
  .state-offline { background: rgba(255,51,68,0.15); color: var(--accent-red); border: 1px solid var(--accent-red); }
  .pulse-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 1.5s infinite;
  }
  @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } }

  .telemetry-row {
    display: flex;
    align-items: center;
    gap: 20px;
  }
  .metric-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .metric-label {
    font-size: 10px;
    color: var(--text-dim);
    text-transform: uppercase;
    font-weight: 600;
  }
  .metric-val {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 600;
    color: #fff;
  }
  .metric-val.cyan { color: var(--accent-cyan); }
  .metric-val.green { color: var(--accent-green); }
  .metric-val.amber { color: var(--accent-amber); }
  .metric-val.magenta { color: var(--accent-magenta); }

  /* MAIN CONTENT LAYOUT */
  main {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 380px;
    overflow: hidden;
  }

  /* TERMINAL SECTION */
  .terminal-section {
    display: flex;
    flex-direction: column;
    background: var(--bg-terminal);
    border-right: 1px solid var(--border-color);
    position: relative;
    overflow: hidden;
  }
  .terminal-header {
    background: #0d1219;
    padding: 8px 14px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-shrink: 0;
  }
  .filter-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .filter-btn {
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-dim);
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .filter-btn:hover { color: #fff; border-color: #444d56; }
  .filter-btn.active {
    background: rgba(0, 243, 255, 0.15);
    color: var(--accent-cyan);
    border-color: var(--accent-cyan);
  }
  .terminal-search {
    background: #161b22;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    color: #fff;
    padding: 4px 10px;
    font-size: 11px;
    font-family: var(--font-mono);
    width: 150px;
  }
  .terminal-search:focus { outline: none; border-color: var(--accent-cyan); }
  
  .terminal-actions {
    display: flex;
    gap: 8px;
  }
  .btn-icon {
    background: #161b22;
    border: 1px solid var(--border-color);
    color: var(--text-dim);
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }
  .btn-icon:hover { color: #fff; border-color: #555; }
  .btn-icon.active { background: rgba(0,255,102,0.15); color: var(--accent-green); border-color: var(--accent-green); }

  /* LOG WINDOW */
  .log-container {
    flex: 1;
    overflow-y: auto;
    padding: 12px 14px;
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 1.5;
  }
  .log-line {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 2px 0;
    border-bottom: 1px solid rgba(255,255,255,0.02);
  }
  .log-line:hover { background: rgba(255,255,255,0.02); }
  .log-time { color: #484f58; flex-shrink: 0; }
  .log-level {
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 10px;
    flex-shrink: 0;
  }
  .lvl-INFO { background: rgba(58,134,255,0.15); color: var(--accent-blue); }
  .lvl-INPUT { background: rgba(0,255,102,0.15); color: var(--accent-green); }
  .lvl-SYSTEM { background: rgba(0,243,255,0.15); color: var(--accent-cyan); }
  .lvl-DISPLAY { background: rgba(255,0,127,0.15); color: var(--accent-magenta); }
  .lvl-NOTIFY { background: rgba(181,23,158,0.25); color: var(--accent-magenta); border: 1px solid var(--accent-magenta); }
  .lvl-WARN { background: rgba(255,184,0,0.15); color: var(--accent-amber); }
  .lvl-ERROR { background: rgba(255,51,68,0.25); color: var(--accent-red); font-weight: 800; }
  
  .log-tag {
    color: #8b949e;
    font-size: 11px;
    flex-shrink: 0;
    width: 65px;
  }
  .log-msg {
    color: var(--text-main);
    word-break: break-all;
    flex: 1;
  }

  /* SIDEBAR SECTION */
  .sidebar-section {
    background: var(--bg-secondary);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 14px;
    gap: 14px;
  }
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .card-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  /* HARDWARE VISUALIZER: 4x4 MATRIX */
  .matrix-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
  }
  .matrix-key {
    background: #111822;
    border: 1px solid #232b36;
    border-radius: 4px;
    height: 44px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    cursor: default;
    transition: all 0.1s ease;
    user-select: none;
    text-align: center;
    padding: 2px;
  }
  .matrix-key .key-num { font-size: 8px; color: #555; }
  .matrix-key .key-lbl { font-size: 9px; font-weight: 600; color: #aaa; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 100%; }
  .matrix-key.top-slot-active { border-color: var(--accent-green); background: rgba(0,255,102,0.12); }
  .matrix-key.top-slot-active .key-lbl { color: var(--accent-green); }
  .matrix-key.flash-pressed { background: var(--accent-cyan) !important; color: #000 !important; transform: scale(0.95); }

  /* BATTERY BENCHMARK CARD */
  .bench-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    background: #101622;
    padding: 10px;
    border-radius: 4px;
    border: 1px solid #212d40;
  }
  .bench-stat-item { display: flex; flex-direction: column; gap: 2px; }
  .bench-stat-label { font-size: 9px; color: var(--text-dim); text-transform: uppercase; font-weight: 600; }
  .bench-stat-val { font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: var(--accent-cyan); }
  .bench-stat-val.green { color: var(--accent-green); }
  
  /* SVG CHART */
  .chart-box {
    background: #0d131d;
    border: 1px solid #1e293b;
    border-radius: 4px;
    padding: 6px;
    position: relative;
    height: 100px;
    width: 100%;
  }
  svg.discharge-chart {
    width: 100%;
    height: 100%;
    overflow: visible;
  }

  /* BUTTONS & CONTROLS */
  .btn-row { display: flex; gap: 6px; flex-wrap: wrap; }
  .btn {
    background: #1f293d;
    border: 1px solid #334155;
    color: #fff;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 10px;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .btn:hover { background: #2a3952; border-color: #475569; }
  .btn-cyan { background: rgba(0,243,255,0.15); border-color: var(--accent-cyan); color: var(--accent-cyan); }
  .btn-cyan:hover { background: rgba(0,243,255,0.25); }
  .btn-green { background: rgba(0,255,102,0.15); border-color: var(--accent-green); color: var(--accent-green); }
  .btn-green:hover { background: rgba(0,255,102,0.25); }
  .btn-magenta { background: rgba(255,0,127,0.15); border-color: var(--accent-magenta); color: var(--accent-magenta); }
  .btn-magenta:hover { background: rgba(255,0,127,0.25); }
  .btn-amber { background: rgba(255,184,0,0.15); border-color: var(--accent-amber); color: var(--accent-amber); }
  .btn-amber:hover { background: rgba(255,184,0,0.25); }
  .btn-red { background: rgba(255,51,68,0.15); border-color: var(--accent-red); color: var(--accent-red); }

  .input-field {
    background: #111822;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    color: #fff;
    padding: 5px 8px;
    font-size: 11px;
    font-family: var(--font-mono);
    width: 100%;
  }
</style>
</head>
<body>

<header>
  <div class="title-group">
    <div class="brand-icon">⚡</div>
    <div>
      <h1>MacroPad Hub <span id="device-badge" class="badge-state state-offline"><span class="pulse-dot"></span><span id="state-text">OFFLINE</span></span></h1>
    </div>
  </div>

  <div class="telemetry-row">
    <div class="metric-item">
      <span class="metric-label">Battery Voltage</span>
      <span class="metric-val green" id="metric-vbat">-- V</span>
    </div>
    <div class="metric-item">
      <span class="metric-label">Estimated SoC</span>
      <span class="metric-val cyan" id="metric-pct">-- %</span>
    </div>
    <div class="metric-item">
      <span class="metric-label">WiFi RSSI</span>
      <span class="metric-val" id="metric-rssi">-- dBm</span>
    </div>
    <div class="metric-item">
      <span class="metric-label">Active Layer</span>
      <span class="metric-val amber" id="metric-layer">Bank 1 | L1</span>
    </div>
    <div class="metric-item">
      <span class="metric-label">Uptime</span>
      <span class="metric-val" id="metric-uptime">0s</span>
    </div>
    <div class="metric-item" onclick="toggleStayAwake()" style="cursor:pointer;" title="Click to toggle Stay Awake / Sleep mode">
      <span class="metric-label">Power Mode</span>
      <span class="metric-val green" id="metric-stay-awake">⚡ AWAKE 24/7</span>
    </div>
  </div>
</header>

<main>
  <!-- REAL-TIME CONSOLE TERMINAL -->
  <section class="terminal-section">
    <div class="terminal-header">
      <div class="filter-group">
        <button class="filter-btn active" data-filter="ALL">ALL</button>
        <button class="filter-btn" data-filter="INPUT">INPUT</button>
        <button class="filter-btn" data-filter="NOTIFY">NOTIFY</button>
        <button class="filter-btn" data-filter="SYSTEM">SYSTEM</button>
        <button class="filter-btn" data-filter="DISPLAY">DISPLAY</button>
        <button class="filter-btn" data-filter="WARN">WARNS</button>
      </div>

      <div class="terminal-actions">
        <input type="text" id="terminal-search" class="terminal-search" placeholder="Filter logs...">
        <button class="btn-icon" id="btn-autoscroll" title="Auto-scroll toggle">⚡ Scroll: ON</button>
        <button class="btn-icon" id="btn-clear" title="Clear view">Clear</button>
        <a href="/api/export_logs" class="btn-icon" style="text-decoration:none;" download>Export</a>
      </div>
    </div>

    <div class="log-container" id="log-container">
      <!-- Live log stream injected here -->
    </div>
  </section>

  <!-- SIDEBAR CONTROLS & BENCHMARK -->
  <aside class="sidebar-section">

    <!-- 1. BATTERY CAPACITY BENCHMARKER -->
    <div class="card">
      <div class="card-title">
        <span>🔋 Battery Capacity Benchmarker</span>
        <span id="bench-status-badge" class="badge-state state-offline" style="font-size:9px; padding:1px 5px;">IDLE</span>
      </div>

      <div class="bench-stats">
        <div class="bench-stat-item">
          <span class="bench-stat-label">Measured Capacity</span>
          <span class="bench-stat-val green" id="bench-mah">0.0 mAh</span>
        </div>
        <div class="bench-stat-item">
          <span class="bench-stat-label">Elapsed Time</span>
          <span class="bench-stat-val" id="bench-elapsed">0m</span>
        </div>
        <div class="bench-stat-item">
          <span class="bench-stat-label">Start Voltage</span>
          <span class="bench-stat-val cyan" id="bench-start-v">-- V</span>
        </div>
        <div class="bench-stat-item">
          <span class="bench-stat-label">Current Voltage</span>
          <span class="bench-stat-val" id="bench-curr-v">-- V</span>
        </div>
      </div>

      <!-- Live Discharge Slope Chart -->
      <div class="chart-box">
        <svg class="discharge-chart" id="chart-svg" viewBox="0 0 340 90" preserveAspectRatio="none">
          <defs>
            <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#00f3ff" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="#00f3ff" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          <path id="chart-area" d="" fill="url(#chartGrad)"/>
          <path id="chart-line" d="" fill="none" stroke="#00f3ff" stroke-width="2"/>
          <text x="5" y="15" fill="#556" font-size="9" font-family="monospace">4.20V</text>
          <text x="5" y="85" fill="#556" font-size="9" font-family="monospace">3.30V</text>
        </svg>
      </div>

      <div class="btn-row">
        <button class="btn btn-cyan" id="btn-bench-start-36">▶ Start @ 36mA</button>
        <button class="btn btn-amber" id="btn-bench-start-115">▶ Start @ 115mA</button>
        <button class="btn btn-red" id="btn-bench-stop">⏹ Stop</button>
        <button class="btn" id="btn-bench-reset">Reset</button>
      </div>
    </div>

    <!-- 2. WHATSAPP 24/7 LINKED DEVICE BRIDGE -->
    <div class="card" id="whatsapp-card">
      <div class="card-title">
        <span>📱 WhatsApp 24/7 Bridge</span>
        <span id="wa-status-badge" class="badge-state state-offline" style="font-size:9px; padding:1px 5px;">CHECKING</span>
      </div>

      <div id="wa-qr-box" style="display:none; text-align:center; padding:10px; background:#101622; border-radius:4px; border:1px dashed var(--accent-cyan);">
        <div style="font-size:11px; color:#fff; font-weight:600; margin-bottom:6px;">Scan to Pair (WhatsApp Linked Devices):</div>
        <img id="wa-qr-img" src="" alt="WhatsApp QR Code" style="max-width:180px; border-radius:6px; background:#fff; padding:4px;">
        <div style="font-size:10px; color:#888; margin-top:4px;">WhatsApp &gt; Settings &gt; Linked Devices &gt; Link Device</div>
      </div>

      <div id="wa-connected-box" style="display:none; padding:8px 10px; background:rgba(0,255,102,0.08); border-radius:4px; border:1px solid var(--accent-green);">
        <div style="font-size:11px; color:var(--accent-green); font-weight:700;">✓ WhatsApp Linked &amp; Active 24/7</div>
        <div style="font-size:10px; color:#aaa; margin-top:2px;">Listening for Mom, Dad, Sister and !call triggers.</div>
      </div>

      <!-- Quick Triggers Config Accordion -->
      <details style="font-size:11px; color:#888; cursor:pointer;" id="wa-config-details" open>
        <summary style="font-weight:600; color:var(--text-main); margin-bottom:6px;">⚙️ VIP Triggers &amp; Settings</summary>
        <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
          
          <!-- Recent WhatsApp Conversations Quick Selector -->
          <div style="background:#0d131d; border:1px solid #1e293b; border-radius:4px; padding:6px 8px;">
            <div style="font-size:10px; color:var(--accent-cyan); font-weight:700; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
              <span>⚡ Quick Add from Recent Conversations:</span>
              <button class="btn" style="padding:2px 6px; font-size:9px;" onclick="loadRecentWhatsAppChats()">🔄 Refresh</button>
            </div>
            <select id="wa-recent-dropdown" class="input-field" style="cursor:pointer; margin-bottom:4px;">
              <option value="">-- Select a recent WhatsApp conversation --</option>
            </select>
            <div style="display:flex; gap:4px;">
              <button class="btn btn-cyan" style="flex:1; padding:3px 6px; font-size:10px;" onclick="fillVipFromRecent('mom')">+ Set Mom</button>
              <button class="btn btn-cyan" style="flex:1; padding:3px 6px; font-size:10px;" onclick="fillVipFromRecent('dad')">+ Set Dad</button>
              <button class="btn btn-cyan" style="flex:1; padding:3px 6px; font-size:10px;" onclick="fillVipFromRecent('sis')">+ Set Sister</button>
            </div>
          </div>

          <div style="display:flex; gap:4px; align-items:center;">
            <span style="width:45px; font-size:10px; color:#aaa; font-weight:600;">Mom:</span>
            <input type="text" id="wa-mom-phone" class="input-field" placeholder="Mom's Phone (e.g. +39340...)">
          </div>
          <div style="display:flex; gap:4px; align-items:center;">
            <span style="width:45px; font-size:10px; color:#aaa; font-weight:600;">Dad:</span>
            <input type="text" id="wa-dad-phone" class="input-field" placeholder="Dad's Phone (e.g. +39340...)">
          </div>
          <div style="display:flex; gap:4px; align-items:center;">
            <span style="width:45px; font-size:10px; color:#aaa; font-weight:600;">Sister:</span>
            <input type="text" id="wa-sis-phone" class="input-field" placeholder="Sister's Phone (e.g. +39340...)">
          </div>
          <div style="display:flex; gap:4px; align-items:center;">
            <span style="width:45px; font-size:10px; color:#aaa; font-weight:600;">Triggers:</span>
            <input type="text" id="wa-keywords" class="input-field" placeholder="Keywords (e.g. !call, urgent, 🚨, ring)">
          </div>
          
          <div style="display:flex; align-items:center; gap:8px; margin-top:3px; background:#111822; padding:5px 8px; border-radius:4px; border:1px solid var(--border-color);">
            <input type="checkbox" id="wa-ack-reaction" style="accent-color:var(--accent-green); cursor:pointer;">
            <label for="wa-ack-reaction" style="font-size:11px; color:#ccc; cursor:pointer; flex:1;">Send WhatsApp reaction on MacroPad ack</label>
            <input type="text" id="wa-ack-emoji" class="input-field" value="✅" style="width:36px; text-align:center; padding:2px;" placeholder="✅">
          </div>

          <button class="btn btn-green" onclick="saveWhatsAppConfig()">Save VIP Settings</button>
        </div>
      </details>
    </div>

    <!-- 3. BATTERY DISCHARGE HISTORY & SQLITE DATABASE -->
    <div class="card">
      <div class="card-title">
        <span>📈 Battery History &amp; Discharge Trend</span>
        <button class="btn" style="padding:2px 6px; font-size:9px;" onclick="loadBatteryHistory()">🔄 Refresh</button>
      </div>
      <div style="font-size:10px; color:#888; margin-bottom:6px;">Persistent SQLite Telemetry (Past 48 Hours)</div>

      <div class="chart-box" style="height:110px;">
        <svg class="discharge-chart" id="hist-chart-svg" viewBox="0 0 340 90" preserveAspectRatio="none">
          <defs>
            <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#00ff66" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="#00ff66" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          <path id="hist-chart-area" d="" fill="url(#histGrad)"/>
          <path id="hist-chart-line" d="" fill="none" stroke="#00ff66" stroke-width="2"/>
          <text x="5" y="15" fill="#556" font-size="9" font-family="monospace">4.20V</text>
          <text x="5" y="85" fill="#556" font-size="9" font-family="monospace">3.30V</text>
        </svg>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:9px; color:#666; font-family:var(--font-mono); margin-top:2px;">
        <span id="hist-start-time">--</span>
        <span id="hist-points-count">0 records</span>
        <span id="hist-end-time">Now</span>
      </div>
    </div>

    <!-- 3. WHATSAPP & PUSH NOTIFICATION DISPATCHER -->
    <div class="card">
      <div class="card-title">
        <span>💬 Manual Notification Dispatcher</span>
        <span style="font-size:9px; color:var(--accent-cyan);">Instant &lt;50ms</span>
      </div>
      <div style="font-size:11px; color:#888;">Triggers visual LED rotating effects & caller banner on MacroPad:</div>
      
      <div class="btn-row">
        <button class="btn btn-green" onclick="sendTestNotify('call', 'whatsapp', 'Mom', 'Incoming WhatsApp Call')">📞 WhatsApp Call</button>
        <button class="btn btn-cyan" onclick="sendTestNotify('message', 'whatsapp', 'Alex', 'Hey, you there?')">💬 WhatsApp Msg</button>
        <button class="btn btn-amber" onclick="sendTestNotify('alert', 'hass', 'Front Door', 'Motion Detected')">🚨 Doorbell / Alert</button>
      </div>

      <div style="display:flex; gap:6px; margin-top:4px;">
        <input type="text" id="custom-sender" class="input-field" placeholder="Sender name (e.g. John)" style="width:45%;">
        <input type="text" id="custom-msg" class="input-field" placeholder="Message / Title">
        <button class="btn btn-magenta" onclick="sendCustomNotify()">Send</button>
      </div>
    </div>

    <!-- 3. SMART HOME & HOME ASSISTANT QUICK ACTIONS -->
    <div class="card">
      <div class="card-title">
        <span>💡 Home Assistant & Quick Actions</span>
        <span style="font-size:9px; color:var(--accent-green);">HASS MQTT</span>
      </div>

      <div class="btn-row">
        <button class="btn btn-amber" onclick="sendHassAction('light_toggle')">💡 Toggle Ceiling Light</button>
        <button class="btn btn-cyan" onclick="sendHassAction('wakeonlan')">⚡ WOL PC</button>
        <button class="btn" onclick="sendHassAction('preset_recall', 1)">Preset 1</button>
        <button class="btn" onclick="sendHassAction('preset_recall', 2)">Preset 2</button>
        <button class="btn" onclick="sendHassAction('preset_recall', 3)">Preset 3</button>
      </div>
    </div>

    <!-- 4. HARDWARE 4x4 MATRIX VISUALIZER -->
    <div class="card">
      <div class="card-title">
        <span>🎛️ Live 4x4 Key Matrix</span>
        <span id="visualizer-layer-tag" style="font-size:9px; color:var(--accent-amber);">B1:L1</span>
      </div>
      <div class="matrix-grid" id="matrix-visualizer">
        <!-- 16 keys generated dynamically -->
      </div>
    </div>

  </aside>
</main>

<script>
  let ws;
  let autoScroll = true;
  let activeFilter = 'ALL';
  let searchTerm = '';
  let logsBacklog = [];
  let currentBenchmark = {};

  const keyLabels = {
    1: 'SLOT 1', 2: 'SLOT 2', 3: 'SLOT 3', 4: 'SLOT 4',
    5: 'MOD (LGT)', 6: 'ACT 1', 7: 'ACT 2', 8: 'ACT 3',
    9: 'HUD', 10: 'ACT 4', 11: 'ACT 5', 12: 'ACT 6',
    13: 'AUD MOD', 14: 'LT SLP', 15: 'SLEEP', 16: 'WOL PC'
  };

  function initMatrixVisualizer() {
    const container = document.getElementById('matrix-visualizer');
    container.innerHTML = '';
    for (let i = 1; i <= 16; i++) {
      const el = document.createElement('div');
      el.id = `key-btn-${i}`;
      el.className = 'matrix-key';
      el.innerHTML = `<span class="key-num">#${i}</span><span class="key-lbl">${keyLabels[i] || 'KEY'}</span>`;
      container.appendChild(el);
    }
  }

  function connectWebSocket() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onopen = () => {
      console.log('Connected to MacroPad Hub WebSocket');
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'state') {
        updateDeviceState(msg.data);
        if (msg.benchmark) updateBenchmarkState(msg.benchmark);
      } else if (msg.type === 'history') {
        logsBacklog = msg.data;
        renderLogs();
      } else if (msg.type === 'log') {
        logsBacklog.push(msg.data);
        if (logsBacklog.length > 1000) logsBacklog.shift();
        appendLogEntry(msg.data);
      }
    };

    ws.onclose = () => {
      setTimeout(connectWebSocket, 2000);
    };
  }

  function updateDeviceState(state) {
    const badge = document.getElementById('device-badge');
    const badgeText = document.getElementById('state-text');
    badge.className = `badge-state state-${state.state || 'offline'}`;
    badgeText.textContent = (state.state || 'OFFLINE').toUpperCase();

    document.getElementById('metric-vbat').textContent = state.vbat > 0 ? `${state.vbat.toFixed(2)} V` : '-- V';
    document.getElementById('metric-pct').textContent = state.batt_pct !== undefined ? `${state.batt_pct} %` : '-- %';
    document.getElementById('metric-rssi').textContent = state.rssi ? `${state.rssi} dBm` : '-- dBm';
    document.getElementById('metric-layer').textContent = `Bank ${state.bank || 1} | L${state.layer || 1}`;
    document.getElementById('metric-uptime').textContent = state.uptime_str || '0s';
    document.getElementById('visualizer-layer-tag').textContent = `B${state.bank || 1}:L${state.layer || 1}`;

    const stayEl = document.getElementById('metric-stay-awake');
    if (stayEl) {
      const isAwake = state.stay_awake !== false;
      stayEl.textContent = isAwake ? '⚡ AWAKE 24/7' : '💤 SLEEP ON';
      stayEl.className = `metric-val ${isAwake ? 'green' : 'amber'}`;
    }

    // Highlight active slot key (1..4)
    for (let k = 1; k <= 4; k++) {
      const el = document.getElementById(`key-btn-${k}`);
      if (el) {
        if (k === state.slot) el.classList.add('top-slot-active');
        else el.classList.remove('top-slot-active');
      }
    }
  }

  async function toggleStayAwake() {
    try {
      const res = await fetch('/api/macropad/toggle_stay_awake', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'ok') {
        const isAwake = data.stay_awake;
        const stayEl = document.getElementById('metric-stay-awake');
        if (stayEl) {
          stayEl.textContent = isAwake ? '⚡ AWAKE 24/7' : '💤 SLEEP ON';
          stayEl.className = `metric-val ${isAwake ? 'green' : 'amber'}`;
        }
      }
    } catch (e) {
      alert('Could not reach MacroPad: ' + e);
    }
  }

  function updateBenchmarkState(b) {
    currentBenchmark = b;
    const badge = document.getElementById('bench-status-badge');
    badge.className = `badge-state ${b.active ? 'state-online' : (b.status === 'completed' ? 'state-online' : 'state-offline')}`;
    badge.textContent = (b.status || 'IDLE').toUpperCase();

    document.getElementById('bench-mah').textContent = `${b.computed_mah || 0.0} mAh`;
    document.getElementById('bench-elapsed').textContent = b.elapsed_str || '0m';
    document.getElementById('bench-start-v').textContent = b.start_vbat > 0 ? `${b.start_vbat.toFixed(2)} V` : '-- V';
    document.getElementById('bench-curr-v').textContent = b.current_vbat > 0 ? `${b.current_vbat.toFixed(2)} V` : '-- V';

    renderChart(b.data_points || []);
  }

  function renderChart(pts) {
    if (!pts || pts.length < 2) {
      document.getElementById('chart-line').setAttribute('d', '');
      document.getElementById('chart-area').setAttribute('d', '');
      return;
    }
    const maxElapsed = Math.max(10, pts[pts.length - 1].elapsed_mins);
    const minV = 3.30;
    const maxV = 4.25;
    const w = 340, h = 90;

    let pathD = '';
    pts.forEach((p, idx) => {
      const x = (p.elapsed_mins / maxElapsed) * w;
      const normY = Math.max(0, Math.min(1, (p.vbat - minV) / (maxV - minV)));
      const y = h - (normY * h);
      if (idx === 0) pathD += `M ${x.toFixed(1)} ${y.toFixed(1)}`;
      else pathD += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    });

    document.getElementById('chart-line').setAttribute('d', pathD);
    const areaD = `${pathD} L ${w} ${h} L 0 ${h} Z`;
    document.getElementById('chart-area').setAttribute('d', areaD);
  }

  function renderLogs() {
    const container = document.getElementById('log-container');
    container.innerHTML = '';
    const filtered = logsBacklog.filter(matchesFilter);
    filtered.forEach(entry => appendLogDOM(entry, container));
    if (autoScroll) container.scrollTop = container.scrollHeight;
  }

  function matchesFilter(entry) {
    if (activeFilter !== 'ALL' && entry.level !== activeFilter) return false;
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      return entry.msg.toLowerCase().includes(s) || entry.tag.toLowerCase().includes(s);
    }
    return true;
  }

  function appendLogDOM(entry, container) {
    const div = document.createElement('div');
    div.className = 'log-line';
    div.innerHTML = `
      <span class="log-time">${entry.time}</span>
      <span class="log-level lvl-${entry.level}">${entry.level}</span>
      <span class="log-tag">[${entry.tag}]</span>
      <span class="log-msg">${escapeHtml(entry.msg)}</span>
    `;
    container.appendChild(div);
  }

  function appendLogEntry(entry) {
    if (matchesFilter(entry)) {
      const container = document.getElementById('log-container');
      appendLogDOM(entry, container);
      if (autoScroll) container.scrollTop = container.scrollHeight;
    }
  }

  function escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Quick Action Callbacks
  async function sendTestNotify(type, source, sender, message) {
    await fetch('/api/notify', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({type, source, sender, message, duration_ms: 4000})
    });
  }

  async function sendCustomNotify() {
    const sender = document.getElementById('custom-sender').value || 'Alert';
    const message = document.getElementById('custom-msg').value || 'Notification';
    await sendTestNotify('message', 'custom', sender, message);
  }

  async function sendHassAction(action, index = 1) {
    await fetch('/api/hass/action', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action, index})
    });
  }

  // Event Listeners
  document.getElementById('btn-bench-start-36').onclick = () => fetch('/api/benchmark/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({current_ma: 36.0, cutoff_v: 3.30})
  });

  document.getElementById('btn-bench-start-115').onclick = () => fetch('/api/benchmark/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({current_ma: 115.0, cutoff_v: 3.30})
  });

  document.getElementById('btn-bench-stop').onclick = () => fetch('/api/benchmark/stop', {method: 'POST'});
  document.getElementById('btn-bench-reset').onclick = () => fetch('/api/benchmark/reset', {method: 'POST'});

  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;
      renderLogs();
    };
  });

  document.getElementById('terminal-search').oninput = (e) => {
    searchTerm = e.target.value;
    renderLogs();
  };

  document.getElementById('btn-autoscroll').onclick = function() {
    autoScroll = !autoScroll;
    this.textContent = `⚡ Scroll: ${autoScroll ? 'ON' : 'OFF'}`;
    this.classList.toggle('active', autoScroll);
  };

  // WhatsApp 24/7 Bridge Handlers
  async function pollWhatsAppState() {
    try {
      const res = await fetch('/api/whatsapp/status');
      const data = await res.json();
      const badge = document.getElementById('wa-status-badge');
      const qrBox = document.getElementById('wa-qr-box');
      const qrImg = document.getElementById('wa-qr-img');
      const connBox = document.getElementById('wa-connected-box');

      if (data.connected) {
        badge.className = 'badge-state state-online';
        badge.textContent = 'CONNECTED';
        qrBox.style.display = 'none';
        connBox.style.display = 'block';
      } else if (data.qr_image) {
        badge.className = 'badge-state state-sleeping';
        badge.textContent = 'PAIRING (SCAN QR)';
        qrImg.src = data.qr_image;
        qrBox.style.display = 'block';
        connBox.style.display = 'none';
      } else {
        badge.className = 'badge-state state-offline';
        badge.textContent = 'INITIALIZING';
        qrBox.style.display = 'none';
        connBox.style.display = 'none';
      }
    } catch (e) {}
  }
  setInterval(pollWhatsAppState, 3000);

  async function loadWhatsAppConfig() {
    try {
      const res = await fetch('/api/whatsapp/config');
      const cfg = await res.json();
      if (cfg.vip_contacts) {
        cfg.vip_contacts.forEach(c => {
          if (c.name.toLowerCase() === 'mom') document.getElementById('wa-mom-phone').value = c.phone || '';
          if (c.name.toLowerCase() === 'dad') document.getElementById('wa-dad-phone').value = c.phone || '';
          if (c.name.toLowerCase() === 'sister') document.getElementById('wa-sis-phone').value = c.phone || '';
        });
      }
      if (cfg.trigger_keywords) {
        document.getElementById('wa-keywords').value = cfg.trigger_keywords.join(', ');
      }
      document.getElementById('wa-ack-reaction').checked = !!cfg.send_ack_reaction;
      if (cfg.ack_reaction_emoji) {
        document.getElementById('wa-ack-emoji').value = cfg.ack_reaction_emoji;
      }
    } catch (e) {}
  }

  let recentChatsList = [];

  async function loadRecentWhatsAppChats() {
    try {
      const res = await fetch('/api/whatsapp/recent_chats');
      recentChatsList = await res.json();
      const dropdown = document.getElementById('wa-recent-dropdown');
      dropdown.innerHTML = '<option value="">-- Select a recent WhatsApp conversation --</option>';
      recentChatsList.forEach((c, idx) => {
        const opt = document.createElement('option');
        opt.value = idx;
        const phoneLabel = c.phone ? ` (${c.phone})` : '';
        const msgSnippet = c.last_msg ? ` - "${c.last_msg}"` : '';
        opt.textContent = `${c.name}${phoneLabel}${msgSnippet} [${c.time_str}]`;
        dropdown.appendChild(opt);
      });
    } catch (e) {}
  }

  function fillVipFromRecent(role) {
    const dropdown = document.getElementById('wa-recent-dropdown');
    const idx = dropdown.value;
    if (idx === "" || !recentChatsList[idx]) {
      alert('Please select a contact from the dropdown first!');
      return;
    }
    const contact = recentChatsList[idx];
    const val = contact.phone || contact.name;
    if (role === 'mom') document.getElementById('wa-mom-phone').value = val;
    if (role === 'dad') document.getElementById('wa-dad-phone').value = val;
    if (role === 'sis') document.getElementById('wa-sis-phone').value = val;
  }

  async function loadBatteryHistory() {
    try {
      const res = await fetch('/api/battery/history?hours=48');
      const pts = await res.json();
      if (!pts || pts.length === 0) return;

      document.getElementById('hist-points-count').textContent = `${pts.length} records`;
      document.getElementById('hist-start-time').textContent = pts[0].time.split(' ')[1] || '';
      document.getElementById('hist-end-time').textContent = pts[pts.length - 1].time.split(' ')[1] || 'Now';

      const minV = 3.30;
      const maxV = 4.35;
      const w = 340, h = 90;

      let pathD = '';
      pts.forEach((p, idx) => {
        const x = (idx / (pts.length - 1)) * w;
        const normY = Math.max(0, Math.min(1, (p.vbat - minV) / (maxV - minV)));
        const y = h - (normY * h);
        if (idx === 0) pathD += `M ${x.toFixed(1)} ${y.toFixed(1)}`;
        else pathD += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
      });

      document.getElementById('hist-chart-line').setAttribute('d', pathD);
      const areaD = `${pathD} L ${w} ${h} L 0 ${h} Z`;
      document.getElementById('hist-chart-area').setAttribute('d', areaD);
    } catch (e) {}
  }

  async function saveWhatsAppConfig() {
    const momPhone = document.getElementById('wa-mom-phone').value.trim();
    const dadPhone = document.getElementById('wa-dad-phone').value.trim();
    const sisPhone = document.getElementById('wa-sis-phone').value.trim();
    const kwRaw = document.getElementById('wa-keywords').value.trim();
    const keywords = kwRaw ? kwRaw.split(',').map(s => s.trim()).filter(Boolean) : ['!call', 'urgent', '🚨'];
    const sendAckReaction = document.getElementById('wa-ack-reaction').checked;
    const ackReactionEmoji = document.getElementById('wa-ack-emoji').value.trim() || '✅';

    const payload = {
      vip_contacts: [
        { name: "Mom", phone: momPhone, aliases: ["mom", "mamma", "mother"] },
        { name: "Dad", phone: dadPhone, aliases: ["dad", "papa", "father"] },
        { name: "Sister", phone: sisPhone, aliases: ["sister", "sis"] }
      ],
      trigger_keywords: keywords,
      any_vip_message_triggers: false,
      incoming_call_triggers: true,
      send_ack_reaction: sendAckReaction,
      ack_reaction_emoji: ackReactionEmoji,
      dashboard_notify_url: "http://127.0.0.1:5000/api/notify"
    };

    try {
      const res = await fetch('/api/whatsapp/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) alert('✓ WhatsApp VIP settings saved!');
    } catch (e) {
      alert('Error saving config: ' + e);
    }
  }

  window.onload = () => {
    initMatrixVisualizer();
    connectWebSocket();
    pollWhatsAppState();
    loadWhatsAppConfig();
    loadRecentWhatsAppChats();
    loadBatteryHistory();
    setInterval(loadBatteryHistory, 30000);
  };
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return HTML_CONTENT

# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def main():
    global async_loop
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    # Start MQTT client
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_disconnect = on_mqtt_disconnect
    mqtt_client.on_message = on_mqtt_message

    print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Warning: Could not connect to MQTT broker ({e}). Will keep retrying...")

    # Start liveness watchdog thread
    watchdog_thread = threading.Thread(target=liveness_watchdog, daemon=True)
    watchdog_thread.start()

    print(f"Starting MacroPad Web Hub on http://localhost:{DASHBOARD_PORT}...")
    
    config = uvicorn.Config(app=app, host=DASHBOARD_HOST, port=DASHBOARD_PORT, log_level="warning")
    server = uvicorn.Server(config)
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)
    async_loop.run_until_complete(server.serve())

if __name__ == "__main__":
    main()
