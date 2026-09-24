import asyncio
import collections
import datetime
import json
import logging
import os
import sys
import threading
import time
from typing import List, Dict, Any, Optional

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

# ==============================================================================
# CONFIGURATION
# ==============================================================================
MQTT_BROKER = "192.168.1.62"
MQTT_PORT = 1883
TOPIC_INPUT = "macropad/input"
TOPIC_DISPLAY = "macropad/display"
TOPIC_STATUS = "macropad/status"
TOPIC_DEBUG = "macropad/debug"
TOPIC_WILDCARD = "macropad/#"

DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

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
    "grid_labels": ["ACT 1", "ACT 2", "ACT 3", "ACT 4", "ACT 5", "ACT 6", "ACT 7", "ACT 8", "ACT 9"],
    "last_action": None,
    "encoder_states": {"1": 0, "2": 0, "3": 0},
    "key_matrix": {str(i): False for i in range(1, 17)}
}

# Active WebSocket subscribers
ws_clients: List[WebSocket] = []
async_loop: Optional[asyncio.AbstractEventLoop] = None

# ==============================================================================
# FASTAPI APPLICATION
# ==============================================================================
app = FastAPI(title="MacroPad Diagnostic Hub & Debugger")

class PopupRequest(BaseModel):
    message: str

class LayerRequest(BaseModel):
    layer: Optional[int] = None
    bank: Optional[int] = None

class PublishRequest(BaseModel):
    topic: str
    payload: Dict[str, Any]

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
        "level": level.upper(),     # INFO, WARN, ERROR, INPUT, SYSTEM, DISPLAY
        "tag": tag.upper(),         # KEY, ENC, SLEEP, WAKE, BOOT, MQTT, BATT
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
        msg_json = json.dumps({"type": "state", "data": device_state})
        for client in list(ws_clients):
            try:
                asyncio.run_coroutine_threadsafe(client.send_text(msg_json), async_loop)
            except Exception:
                pass

# ==============================================================================
# MQTT CLIENT
# ==============================================================================
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        add_log_entry("SYSTEM", "MQTT", f"Connected to broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(TOPIC_WILDCARD)
        add_log_entry("SYSTEM", "MQTT", f"Subscribed to topic pattern: {TOPIC_WILDCARD}")
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

        elif action == "fixed_key":
            kid = payload.get("id")
            add_log_entry("INPUT", "KEY", f"Fixed Key {kid} tapped", raw_topic=topic, raw_payload=payload)

        else:
            add_log_entry("INPUT", action.upper(), f"Action: {action} -> {json.dumps(payload)}", raw_topic=topic, raw_payload=payload)

        broadcast_state()

    # 2. STATUS / HEARTBEAT MESSAGES
    elif topic == TOPIC_STATUS:
        state = payload.get("state", "online")
        device_state["state"] = state
        device_state["connected"] = (state == "online")

        if "vbat" in payload:
            device_state["vbat"] = float(payload["vbat"])
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

        if state == "sleeping":
            reason = payload.get("reason", "idle")
            add_log_entry("SYSTEM", "SLEEP", f"MacroPad entered LIGHT SLEEP (Reason: {reason}, Vbat: {device_state['vbat']:.2f}V)", raw_topic=topic, raw_payload=payload)
        elif payload.get("event") == "wake":
            cause = payload.get("cause", "unknown")
            add_log_entry("SYSTEM", "WAKE", f"MacroPad WOKE UP from light sleep (Wake cause: {cause})", raw_topic=topic, raw_payload=payload)
        else:
            add_log_entry("SYSTEM", "HEARTBEAT", f"Heartbeat: Vbat={device_state['vbat']:.2f}V, RSSI={device_state['rssi']}dBm, Heap={device_state['heap']//1024}KB, Layer={device_state['layer']}", raw_topic=topic, raw_payload=payload)

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

# Background task to monitor device offline watchdog
def liveness_watchdog():
    while True:
        time.sleep(5)
        now = time.time()
        last = device_state.get("last_seen", 0)
        curr_state = device_state.get("state")
        
        # If no message for > 75 seconds and not marked sleeping, mark offline
        if last > 0 and (now - last > 75) and curr_state not in ("sleeping", "offline"):
            device_state["state"] = "offline"
            device_state["connected"] = False
            add_log_entry("WARN", "WATCHDOG", f"No signal from MacroPad for {int(now - last)}s - marking device as OFFLINE/SLEEPING")
            broadcast_state()

# ==============================================================================
# REST API ENDPOINTS
# ==============================================================================
@app.get("/api/status")
async def get_status():
    return device_state

@app.get("/api/logs")
async def get_logs():
    return list(log_buffer)

@app.get("/api/export_logs")
async def export_logs():
    lines = []
    for l in log_buffer:
        lines.append(f"[{l['time']}] [{l['level']:<5}] [{l['tag']:<8}] {l['msg']}")
    return PlainTextResponse("\n".join(lines), media_type="text/plain", headers={"Content-Disposition": "attachment; filename=macropad_debug.log"})

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
        # Send initial full state and recent log backlog
        await websocket.send_text(json.dumps({"type": "state", "data": device_state}))
        recent_logs = list(log_buffer)[-150:]
        await websocket.send_text(json.dumps({"type": "history", "data": recent_logs}))
        while True:
            data = await websocket.receive_text()
            # Handle incoming ping / client events if needed
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
<title>MacroPad Terminal Debugger & Hub</title>
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

  /* MAIN CONTENT LAYOUT */
  main {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 360px;
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
    width: 170px;
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
  .log-msg.error-msg { color: var(--accent-red); font-weight: 600; }

  /* SIDEBAR SECTION */
  .sidebar-section {
    background: var(--bg-secondary);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 16px;
    gap: 16px;
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
    height: 48px;
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
  .matrix-key .key-num { font-size: 9px; color: #555; }
  .matrix-key .key-lbl { font-size: 10px; font-weight: 600; color: #aaa; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 100%; }
  
  /* Key States */
  .matrix-key.top-slot-active { border-color: var(--accent-green); background: rgba(0,255,102,0.12); }
  .matrix-key.top-slot-active .key-lbl { color: var(--accent-green); }
  .matrix-key.key-modifier { border-color: var(--accent-amber); }
  .matrix-key.key-modifier.active { background: rgba(0,243,255,0.3); border-color: var(--accent-cyan); box-shadow: 0 0 10px var(--accent-cyan); }
  .matrix-key.flash-pressed { background: var(--accent-cyan) !important; color: #000 !important; transform: scale(0.95); }

  /* ENCODERS */
  .encoder-group {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }
  .encoder-box {
    background: #111822;
    border: 1px solid #232b36;
    border-radius: 4px;
    padding: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .encoder-knob {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 2px dashed #444;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    transition: transform 0.2s ease, border-color 0.2s ease;
  }
  .encoder-box.rotate-cw .encoder-knob { border-color: var(--accent-green); transform: rotate(45deg); }
  .encoder-box.rotate-ccw .encoder-knob { border-color: var(--accent-cyan); transform: rotate(-45deg); }
  .encoder-box.clicked .encoder-knob { background: var(--accent-magenta); color: #fff; }

  /* VIRTUAL E-INK SCREEN */
  .eink-screen {
    background: #e8eaed;
    color: #111;
    border-radius: 4px;
    padding: 10px;
    font-family: var(--font-mono);
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-height: 120px;
    border: 2px solid #333;
    box-shadow: inset 0 0 6px rgba(0,0,0,0.15);
  }
  .eink-bar {
    display: flex;
    justify-content: space-between;
    font-size: 9px;
    font-weight: 700;
    border-bottom: 1px solid #999;
    padding-bottom: 3px;
  }
  .eink-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    flex: 1;
  }
  .eink-cell {
    background: #fff;
    border: 1px solid #aaa;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    text-align: center;
    padding: 4px 2px;
  }
  .eink-popup {
    background: #111;
    color: #fff;
    padding: 6px;
    font-size: 10px;
    font-weight: 700;
    text-align: center;
    border-radius: 2px;
  }

  /* QUICK CONTROLS */
  .control-row {
    display: flex;
    gap: 6px;
  }
  .control-input {
    flex: 1;
    background: #111822;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    color: #fff;
    padding: 6px 8px;
    font-size: 12px;
  }
  .control-btn {
    background: #1f293d;
    border: 1px solid #334155;
    color: #fff;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 12px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .control-btn:hover { background: #2a3952; }
  .btn-accent { background: rgba(0,243,255,0.2); border-color: var(--accent-cyan); color: var(--accent-cyan); }
  .btn-accent:hover { background: rgba(0,243,255,0.3); }

  /* DIAGNOSTIC BANNER */
  .diag-banner {
    background: rgba(255,51,68,0.1);
    border: 1px solid var(--accent-red);
    color: var(--accent-red);
    padding: 8px 10px;
    border-radius: 4px;
    font-size: 11px;
    display: none;
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
      <span class="metric-label">Battery</span>
      <span class="metric-val green" id="metric-vbat">-- V</span>
    </div>
    <div class="metric-item">
      <span class="metric-label">WiFi RSSI</span>
      <span class="metric-val cyan" id="metric-rssi">-- dBm</span>
    </div>
    <div class="metric-item">
      <span class="metric-label">Free Heap</span>
      <span class="metric-val" id="metric-heap">-- KB</span>
    </div>
    <div class="metric-item">
      <span class="metric-label">Active Layer</span>
      <span class="metric-val amber" id="metric-layer">Bank 1 | L1</span>
    </div>
    <div class="metric-item">
      <span class="metric-label">Last Reset Reason</span>
      <span class="metric-val" id="metric-reset" style="font-size:11px; color:#aaa;">Waiting...</span>
    </div>
  </div>
</header>

<main>
  <!-- LEFT: REAL-TIME TERMINAL DEBUGGER -->
  <section class="terminal-section">
    <div class="terminal-header">
      <div class="filter-group">
        <button class="filter-btn active" data-filter="ALL" onclick="setFilter('ALL')">ALL</button>
        <button class="filter-btn" data-filter="INPUT" onclick="setFilter('INPUT')">INPUTS</button>
        <button class="filter-btn" data-filter="SYSTEM" onclick="setFilter('SYSTEM')">SYSTEM / SLEEP</button>
        <button class="filter-btn" data-filter="DISPLAY" onclick="setFilter('DISPLAY')">DISPLAY</button>
        <button class="filter-btn" data-filter="ERROR" onclick="setFilter('ERROR')">ERRORS</button>
      </div>

      <input type="text" id="log-search" class="terminal-search" placeholder="Search logs (grep)..." oninput="applyFilters()">

      <div class="terminal-actions">
        <button id="btn-autoscroll" class="btn-icon active" onclick="toggleAutoScroll()" title="Toggle Auto Scroll">Auto-Scroll</button>
        <button class="btn-icon" onclick="clearLogs()" title="Clear Screen">Clear</button>
        <button class="btn-icon" onclick="exportLogs()" title="Download Logs">Export</button>
      </div>
    </div>

    <div id="log-container" class="log-container">
      <!-- Live logs injected here -->
    </div>
  </section>

  <!-- RIGHT: DEVICE VISUALIZER & CONFIG -->
  <section class="sidebar-section">

    <!-- Brownout / Crash Alert Banner -->
    <div id="diag-banner" class="diag-banner">
      ⚠️ <strong>CRASH DIAGNOSTIC:</strong> <span id="diag-banner-text"></span>
    </div>

    <!-- 4x4 MATRIX VISUALIZER -->
    <div class="card">
      <div class="card-title">
        <span>4×4 Matrix Status</span>
        <span id="modifier-badge" style="font-size:10px; color:#666;">MODIFIER: OFF</span>
      </div>
      <div class="matrix-grid" id="matrix-grid">
        <!-- 16 keys populated dynamically -->
      </div>
    </div>

    <!-- 3 ROTARY ENCODERS -->
    <div class="card">
      <div class="card-title">Rotary Encoders</div>
      <div class="encoder-group">
        <div class="encoder-box" id="enc-box-1">
          <div class="encoder-knob">1</div>
          <span style="font-size:10px; color:#888;">Volume/Dim</span>
        </div>
        <div class="encoder-box" id="enc-box-2">
          <div class="encoder-knob">2</div>
          <span style="font-size:10px; color:#888;">Colors</span>
        </div>
        <div class="encoder-box" id="enc-box-3">
          <div class="encoder-knob">3</div>
          <span style="font-size:10px; color:#888;">Anims/Bank</span>
        </div>
      </div>
    </div>

    <!-- VIRTUAL E-INK DISPLAY PREVIEW -->
    <div class="card">
      <div class="card-title">E-Ink 1.54" Live Mirror</div>
      <div class="eink-screen">
        <div class="eink-bar">
          <span id="eink-title">BANK 1: MACROS</span>
          <span id="eink-batt">BAT: 3.8V</span>
        </div>
        <div class="eink-grid" id="eink-grid">
          <!-- 3x3 cells -->
        </div>
        <div class="eink-popup" id="eink-popup" style="display:none;"></div>
      </div>
    </div>

    <!-- QUICK REMOTE ACTIONS -->
    <div class="card">
      <div class="card-title">Remote Test & Config</div>
      <div class="control-row">
        <input type="text" id="popup-input" class="control-input" placeholder="Type popup message..." value="TEST POPUP">
        <button class="control-btn btn-accent" onclick="sendPopup()">Send Popup</button>
      </div>

      <div class="control-row" style="margin-top:6px;">
        <button class="control-btn" style="flex:1" onclick="switchBank(1)">Bank 1</button>
        <button class="control-btn" style="flex:1" onclick="switchBank(2)">Bank 2</button>
        <button class="control-btn" style="flex:1" onclick="switchBank(3)">Bank 3</button>
        <button class="control-btn" style="flex:1" onclick="switchBank(4)">Bank 4</button>
      </div>
    </div>

  </section>
</main>

<script>
  let logs = [];
  let currentFilter = 'ALL';
  let autoScroll = true;
  let ws = null;

  // Initialize 4x4 matrix representation
  const matrixLabels = {
    1: "Slot 1", 2: "Slot 2", 3: "Slot 3", 4: "Slot 4",
    5: "LIGHT/MOD", 6: "ACT 1", 7: "ACT 2", 8: "ACT 3",
    9: "FIXED 9", 10: "ACT 4", 11: "ACT 5", 12: "ACT 6",
    13: "FIXED 13", 14: "ACT 7", 15: "ACT 8", 16: "ACT 9"
  };

  function initMatrixUI() {
    const grid = document.getElementById('matrix-grid');
    grid.innerHTML = '';
    for (let id = 1; id <= 16; id++) {
      const key = document.createElement('div');
      key.id = `key-btn-${id}`;
      key.className = 'matrix-key';
      if (id === 5) key.classList.add('key-modifier');
      key.innerHTML = `<span class="key-num">${id}</span><span class="key-lbl">${matrixLabels[id]}</span>`;
      grid.appendChild(key);
    }
  }

  function initEInkGrid(labels) {
    const grid = document.getElementById('eink-grid');
    grid.innerHTML = '';
    for (let i = 0; i < 9; i++) {
      const cell = document.createElement('div');
      cell.className = 'eink-cell';
      cell.innerText = (labels && labels[i]) ? labels[i] : `ACT ${i+1}`;
      grid.appendChild(cell);
    }
  }

  // Connect to WebSocket
  function connectWS() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => {
      console.log("WebSocket connected to MacroPad hub");
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'log') {
        logs.push(msg.data);
        if (logs.length > 1000) logs.shift();
        appendLogDOM(msg.data);
        handleKeyFlashFromLog(msg.data);
      } else if (msg.type === 'history') {
        logs = msg.data;
        renderAllLogs();
      } else if (msg.type === 'state') {
        updateStateUI(msg.data);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected, reconnecting in 2s...");
      setTimeout(connectWS, 2000);
    };
  }

  function updateStateUI(s) {
    const badge = document.getElementById('device-badge');
    const badgeTxt = document.getElementById('state-text');
    badge.className = 'badge-state';

    if (s.state === 'online') {
      badge.classList.add('state-online');
      badgeTxt.innerText = 'ONLINE';
    } else if (s.state === 'sleeping') {
      badge.classList.add('state-sleeping');
      badgeTxt.innerText = 'LIGHT SLEEP';
    } else {
      badge.classList.add('state-offline');
      badgeTxt.innerText = 'OFFLINE';
    }

    if (s.vbat > 0) document.getElementById('metric-vbat').innerText = `${s.vbat.toFixed(2)} V`;
    if (s.rssi) document.getElementById('metric-rssi').innerText = `${s.rssi} dBm`;
    if (s.heap) document.getElementById('metric-heap').innerText = `${Math.round(s.heap / 1024)} KB`;
    if (s.layer) document.getElementById('metric-layer').innerText = `Bank ${s.bank || 1} | L${s.layer}`;
    if (s.reset_reason) {
      document.getElementById('metric-reset').innerText = s.reset_reason;
      if (s.reset_reason.includes('BROWNOUT') || s.reset_reason.includes('Panic') || s.reset_reason.includes('Watchdog')) {
        const banner = document.getElementById('diag-banner');
        banner.style.display = 'block';
        document.getElementById('diag-banner-text').innerText = `${s.reset_reason} detected! Check battery level or code watchdog.`;
      }
    }

    // Top slot highlight
    for (let slot = 1; slot <= 4; slot++) {
      const el = document.getElementById(`key-btn-${slot}`);
      if (el) {
        if (slot === s.slot) el.classList.add('top-slot-active');
        else el.classList.remove('top-slot-active');
      }
    }

    // Modifier
    const modEl = document.getElementById('key-btn-5');
    const modBadge = document.getElementById('modifier-badge');
    if (s.modifier) {
      modEl.classList.add('active');
      modBadge.innerText = 'MODIFIER: HELD';
      modBadge.style.color = 'var(--accent-cyan)';
    } else {
      modEl.classList.remove('active');
      modBadge.innerText = 'MODIFIER: OFF';
      modBadge.style.color = '#666';
    }

    // Update E-Ink mirror
    if (s.grid_labels) initEInkGrid(s.grid_labels);
    document.getElementById('eink-title').innerText = `BANK ${s.bank || 1}: LAYER ${s.layer || 1}`;
    if (s.vbat) document.getElementById('eink-batt').innerText = `BAT: ${s.vbat.toFixed(2)}V`;

    const popupEl = document.getElementById('eink-popup');
    if (s.screen_msg) {
      popupEl.innerText = s.screen_msg;
      popupEl.style.display = 'block';
    } else {
      popupEl.style.display = 'none';
    }
  }

  function handleKeyFlashFromLog(entry) {
    if (entry.level !== 'INPUT') return;
    const p = entry.payload || {};
    
    // Matrix key flash
    if (p.action === 'macro' && p.index) {
      const idxToKey = [0, 6, 7, 8, 10, 11, 12, 14, 15, 16];
      const keyId = idxToKey[p.index];
      flashKey(keyId);
    } else if (p.action === 'light_toggle') {
      flashKey(5);
    } else if (p.action === 'fixed_key' && p.id) {
      flashKey(p.id);
    }

    // Encoder flash
    if (p.action === 'encoder_scroll' && p.id) {
      const encBox = document.getElementById(`enc-box-${p.id}`);
      if (encBox) {
        encBox.classList.remove('rotate-cw', 'rotate-ccw');
        encBox.classList.add(p.delta > 0 ? 'rotate-cw' : 'rotate-ccw');
        setTimeout(() => encBox.classList.remove('rotate-cw', 'rotate-ccw'), 200);
      }
    } else if (p.action === 'encoder_click' && p.id) {
      const encBox = document.getElementById(`enc-box-${p.id}`);
      if (encBox) {
        encBox.classList.add('clicked');
        setTimeout(() => encBox.classList.remove('clicked'), 250);
      }
    }
  }

  function flashKey(keyId) {
    const el = document.getElementById(`key-btn-${keyId}`);
    if (!el) return;
    el.classList.add('flash-pressed');
    setTimeout(() => el.classList.remove('flash-pressed'), 180);
  }

  function setFilter(filter) {
    currentFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(btn => {
      if (btn.dataset.filter === filter) btn.classList.add('active');
      else btn.classList.remove('active');
    });
    applyFilters();
  }

  function applyFilters() {
    renderAllLogs();
  }

  function renderAllLogs() {
    const container = document.getElementById('log-container');
    container.innerHTML = '';
    const search = document.getElementById('log-search').value.toLowerCase();

    const filtered = logs.filter(l => {
      if (currentFilter !== 'ALL') {
        if (currentFilter === 'INPUT' && l.level !== 'INPUT') return false;
        if (currentFilter === 'SYSTEM' && l.level !== 'SYSTEM') return false;
        if (currentFilter === 'DISPLAY' && l.level !== 'DISPLAY') return false;
        if (currentFilter === 'ERROR' && l.level !== 'ERROR' && l.level !== 'WARN') return false;
      }
      if (search && !l.msg.toLowerCase().includes(search) && !l.tag.toLowerCase().includes(search)) {
        return false;
      }
      return true;
    });

    filtered.forEach(appendLogDOM);
    if (autoScroll) container.scrollTop = container.scrollHeight;
  }

  function appendLogDOM(entry) {
    const container = document.getElementById('log-container');
    const search = document.getElementById('log-search').value.toLowerCase();
    
    // Check if passes current filter
    if (currentFilter !== 'ALL') {
      if (currentFilter === 'INPUT' && entry.level !== 'INPUT') return;
      if (currentFilter === 'SYSTEM' && entry.level !== 'SYSTEM') return;
      if (currentFilter === 'DISPLAY' && entry.level !== 'DISPLAY') return;
      if (currentFilter === 'ERROR' && entry.level !== 'ERROR' && entry.level !== 'WARN') return;
    }
    if (search && !entry.msg.toLowerCase().includes(search) && !entry.tag.toLowerCase().includes(search)) {
      return;
    }

    const row = document.createElement('div');
    row.className = 'log-line';
    row.innerHTML = `
      <span class="log-time">${entry.time}</span>
      <span class="log-level lvl-${entry.level}">${entry.level}</span>
      <span class="log-tag">[${entry.tag}]</span>
      <span class="log-msg ${entry.level === 'ERROR' ? 'error-msg' : ''}">${escapeHtml(entry.msg)}</span>
    `;
    container.appendChild(row);

    if (autoScroll) {
      container.scrollTop = container.scrollHeight;
    }
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function toggleAutoScroll() {
    autoScroll = !autoScroll;
    const btn = document.getElementById('btn-autoscroll');
    if (autoScroll) btn.classList.add('active');
    else btn.classList.remove('active');
  }

  function clearLogs() {
    logs = [];
    document.getElementById('log-container').innerHTML = '';
  }

  function exportLogs() {
    window.location.href = '/api/export_logs';
  }

  function sendPopup() {
    const msg = document.getElementById('popup-input').value;
    if (!msg) return;
    fetch('/api/send_popup', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg})
    });
  }

  function switchBank(b) {
    fetch('/api/set_layer', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({bank: b})
    });
  }

  // Run on startup
  initMatrixUI();
  initEInkGrid(["ACT 1", "ACT 2", "ACT 3", "ACT 4", "ACT 5", "ACT 6", "ACT 7", "ACT 8", "ACT 9"]);
  connectWS();
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
    
    # Set async event loop reference for MQTT callbacks
    config = uvicorn.Config(app=app, host=DASHBOARD_HOST, port=DASHBOARD_PORT, log_level="warning")
    server = uvicorn.Server(config)
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)
    async_loop.run_until_complete(server.serve())

if __name__ == "__main__":
    main()
