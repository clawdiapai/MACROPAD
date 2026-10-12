import ctypes
import io
import json
import logging
import os
import socket
import sys
import subprocess
import time
import webbrowser
from typing import Optional, List
import threading

# Ensure UTF-8 encoding on Windows (especially under pythonw.exe when Discord channel names contain emojis)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
elif hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")
elif hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import paho.mqtt.client as mqtt
from pynput import keyboard

# SYSTEM TRAY CONTROLLER (PYSTRAY)
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except Exception as e:
    TRAY_AVAILABLE = False

try:
    from dotenv import load_dotenv, find_dotenv
    # Look for .env in current working dir, pc_app dir, or parent repo root
    _env_path = find_dotenv(usecwd=True)
    if not _env_path:
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        for _candidate in [os.path.join(_script_dir, ".env"), os.path.join(os.path.dirname(_script_dir), ".env")]:
            if os.path.exists(_candidate):
                _env_path = _candidate
                break
    if _env_path:
        load_dotenv(_env_path)
except ImportError:
    pass

try:
    from pc_app.discord_rpc import DiscordVoiceRPC
except ImportError:
    from discord_rpc import DiscordVoiceRPC

try:
    from pc_app.radial_menu import RadialMenuOverlay
except ImportError:
    from radial_menu import RadialMenuOverlay

# PYCAW AUDIO CONTROLLER
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    PYCAW_AVAILABLE = True
except Exception as e:
    PYCAW_AVAILABLE = False
    print(f"Warning: pycaw audio initialization failed: {e}")

# WINDOWS POLICY CONFIG (COM DEFAULT AUDIO ENDPOINT SWITCHER)
try:
    import comtypes
    from comtypes import CLSCTX_ALL
    CLSID_PolicyConfigClient = comtypes.GUID('{870AF99C-171D-4F9E-AF0D-E63Df40c2BC9}')
    IID_IPolicyConfig = comtypes.GUID('{F8679F50-850A-41CF-9C72-430F290290C8}')

    class IPolicyConfig(comtypes.IUnknown):
        _iid_ = IID_IPolicyConfig
        _methods_ = [
            comtypes.COMMETHOD([], comtypes.HRESULT, 'GetMixFormat'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'GetDeviceFormat'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'ResetDeviceFormat'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'SetDeviceFormat'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'GetProcessingPeriod'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'SetProcessingPeriod'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'GetShareMode'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'SetShareMode'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'GetPropertyValue'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'SetPropertyValue'),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'SetDefaultEndpoint',
                               (['in'], ctypes.c_wchar_p, 'pwstrDeviceId'),
                               (['in'], ctypes.c_uint, 'role')),
            comtypes.COMMETHOD([], comtypes.HRESULT, 'SetEndpointVisibility')
        ]
    POLICY_CONFIG_AVAILABLE = True
except Exception as e:
    POLICY_CONFIG_AVAILABLE = False
    print(f"Warning: PolicyConfig COM setup failed: {e}")

# TUYA DEVICE CONTROLLER (OPTIONAL)
try:
    import tinytuya
    TINAP_AVAILABLE = True
except Exception:
    TINAP_AVAILABLE = False

# ==============================================================================
# CONFIGURATION (.env supported)
# ==============================================================================
MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.1.62")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC_INPUT = os.getenv("TOPIC_INPUT", "macropad/input")
TOPIC_DISPLAY = os.getenv("TOPIC_DISPLAY", "macropad/display")
TOPIC_STATUS = os.getenv("TOPIC_STATUS", "macropad/status")

# TUYA DEVICE CONFIGURATION (IF DIRECT TUYA CONTROL IS USED)
TUYA_DEVICE_ID = os.getenv("TUYA_DEVICE_ID", "YOUR_TUYA_DEVICE_ID")
TUYA_IP = os.getenv("TUYA_IP", "YOUR_TUYA_DEVICE_IP")
TUYA_LOCAL_KEY = os.getenv("TUYA_LOCAL_KEY", "YOUR_TUYA_LOCAL_KEY")
TUYA_VERSION = float(os.getenv("TUYA_VERSION", "3.3"))

# DISCORD VOICE RPC CONFIGURATION (100% RELIABLE LIVE MUTE SYNC)
# Set in .env file:
# DISCORD_CLIENT_ID=...
# DISCORD_CLIENT_SECRET=...
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "").strip()
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "").strip()
discord_rpc_client: Optional[DiscordVoiceRPC] = None

# DISCORD MUTE HOTKEY (CTRL+SHIFT+])
# VK codes: VK_CONTROL = 0x11, VK_SHIFT = 0x10, VK_OEM_6 = 0xDD (']')
# Hardware Scan Codes (Set 1): Left Ctrl = 0x1D, Left Shift = 0x2A, Close Bracket ']' = 0x1B
DISCORD_HOTKEY_ENABLED = True
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_CLOSE_BRACKET = 0xDD
SCAN_LCTRL = 0x1D
SCAN_LSHIFT = 0x2A
SCAN_CLOSE_BRACKET = 0x1B

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [('wVk', ctypes.c_ushort),
                ('wScan', ctypes.c_ushort),
                ('dwFlags', ctypes.c_ulong),
                ('time', ctypes.c_ulong),
                ('dwExtraInfo', PUL)]
class HardwareInput(ctypes.Structure):
    _fields_ = [('uMsg', ctypes.c_ulong),
                ('wParamL', ctypes.c_short),
                ('wParamH', ctypes.c_ushort)]
class MouseInput(ctypes.Structure):
    _fields_ = [('dx', ctypes.c_long),
                ('dy', ctypes.c_long),
                ('mouseData', ctypes.c_ulong),
                ('dwFlags', ctypes.c_ulong),
                ('time', ctypes.c_ulong),
                ('dwExtraInfo', PUL)]
class Input_I(ctypes.Union):
    _fields_ = [('ki', KeyBdInput),
                ('mi', MouseInput),
                ('hi', HardwareInput)]
class Input(ctypes.Structure):
    _fields_ = [('type', ctypes.c_ulong),
                ('ii', Input_I)]

def _send_scancode_key(vk: int, scan_code: int, is_up: bool = False):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if is_up else 0)
    ii_.ki = KeyBdInput(vk, scan_code, flags, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

INPUT_MOUSE = 0
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_UNICODE = 0x0004

VK_MAP = {
    "ESC": 0x1B,
    "ENTER": 0x0D,
    "SPACE": 0x20,
    "TAB": 0x09,
    "BACKSPACE": 0x08,
    "DELETE": 0x2E,
    "CTRL": 0x11,
    "CONTROL": 0x11,
    "SHIFT": 0x10,
    "ALT": 0x12,
    "WIN": 0x5B,
    "[": 0xDB,
    "]": 0xDD,
    "-": 0xBD,
    "=": 0xBB,
    ",": 0xBC,
    ".": 0xBE,
    "/": 0xBF,
    ";": 0xBA,
    "'": 0xDE,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

def ensure_default_desktop():
    """Ensures the current thread is attached to the active interactive user desktop."""
    try:
        hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            ctypes.windll.user32.SetThreadDesktop(hdesk)
            ctypes.windll.user32.CloseDesktop(hdesk)
    except Exception:
        pass

def get_foreground_window_info():
    """Returns (exe_basename_lower, window_title) of the currently focused Windows application."""
    try:
        ensure_default_desktop()
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return "", ""
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

        pid = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe_name = ""
        if pid.value:
            hproc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if hproc:
                try:
                    path_buf = ctypes.create_unicode_buffer(512)
                    sz = ctypes.c_ulong(512)
                    if ctypes.windll.kernel32.QueryFullProcessImageNameW(hproc, 0, path_buf, ctypes.byref(sz)):
                        exe_name = os.path.basename(path_buf.value).lower()
                finally:
                    ctypes.windll.kernel32.CloseHandle(hproc)
        return exe_name, title
    except Exception:
        return "", ""

def get_foreground_window_title() -> str:
    """Returns the lowercase title of the currently focused Windows application."""
    _, title = get_foreground_window_info()
    return title.lower()

def send_vk_tap(vk: int, hold_sec: float = 0.02):
    """Taps a virtual key code with its hardware scan code using Windows keybd_event."""
    scan_code = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    ctypes.windll.user32.keybd_event(vk, scan_code, 0, 0)
    if hold_sec > 0:
        time.sleep(hold_sec)
    ctypes.windll.user32.keybd_event(vk, scan_code, 2, 0)  # 2 = KEYEVENTF_KEYUP

MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

def send_vk_state(vk: int, is_up: bool = False):
    """Presses or releases a virtual key code on Windows using keybd_event."""
    scan_code = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    flags = 2 if is_up else 0  # 2 = KEYEVENTF_KEYUP
    ctypes.windll.user32.keybd_event(vk, scan_code, flags, 0)

def send_middle_mouse_state(is_up: bool = False):
    """Presses or releases the Middle Mouse Button (scroll wheel click) for Pan/Orbit clutches."""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    flags = MOUSEEVENTF_MIDDLEUP if is_up else MOUSEEVENTF_MIDDLEDOWN
    ii_.mi = MouseInput(0, 0, 0, flags, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

DEFAULT_TOP_MODIFIERS = {
    "1": "SHIFT",
    "2": "CTRL",
    "3": "ALT",
    "4": "ORBIT_CLUTCH"
}
active_held_top_mods = {}

def hold_top_modifier(slot: int):
    """Holds down the configured keyboard modifier or mouse clutch for Top-Row Key 1..4."""
    top_cfg = synced_app_rules.get("top_modifiers") or DEFAULT_TOP_MODIFIERS
    mod_type = top_cfg.get(str(slot), DEFAULT_TOP_MODIFIERS.get(str(slot), "SHIFT")).upper()
    active_held_top_mods[slot] = mod_type
    logger.info(f">>> [Top-Row Mod HOLD] Key #{slot} -> {mod_type}")

    if mod_type == "SHIFT":
        send_vk_state(VK_MAP["SHIFT"], is_up=False)
    elif mod_type == "CTRL":
        send_vk_state(VK_MAP["CTRL"], is_up=False)
    elif mod_type == "ALT":
        send_vk_state(VK_MAP["ALT"], is_up=False)
    elif mod_type == "SPACE":
        send_vk_state(VK_MAP["SPACE"], is_up=False)
    elif mod_type == "ORBIT_CLUTCH":
        send_vk_state(VK_MAP["SHIFT"], is_up=False)
        time.sleep(0.01)
        send_middle_mouse_state(is_up=False)
    elif mod_type == "PAN_CLUTCH":
        send_middle_mouse_state(is_up=False)

def release_top_modifier(slot: int):
    """Releases the held keyboard modifier or mouse clutch for Top-Row Key 1..4."""
    top_cfg = synced_app_rules.get("top_modifiers") or DEFAULT_TOP_MODIFIERS
    mod_type = active_held_top_mods.pop(slot, top_cfg.get(str(slot), DEFAULT_TOP_MODIFIERS.get(str(slot), "SHIFT"))).upper()
    logger.info(f">>> [Top-Row Mod RELEASE] Key #{slot} -> {mod_type}")

    if mod_type == "SHIFT":
        send_vk_state(VK_MAP["SHIFT"], is_up=True)
    elif mod_type == "CTRL":
        send_vk_state(VK_MAP["CTRL"], is_up=True)
    elif mod_type == "ALT":
        send_vk_state(VK_MAP["ALT"], is_up=True)
    elif mod_type == "SPACE":
        send_vk_state(VK_MAP["SPACE"], is_up=True)
    elif mod_type == "ORBIT_CLUTCH":
        send_middle_mouse_state(is_up=True)
        time.sleep(0.01)
        send_vk_state(VK_MAP["SHIFT"], is_up=True)
    elif mod_type == "PAN_CLUTCH":
        send_middle_mouse_state(is_up=True)

def send_esc_cancel():
    """Sends a double ESC tap (^C^C) to reliably back out of any active CAD tool or dialog."""
    send_vk_tap(VK_MAP["ESC"], 0.02)
    time.sleep(0.025)
    send_vk_tap(VK_MAP["ESC"], 0.02)

def send_ctrl_combo(char_key: str):
    """Sends Ctrl + <char_key> (e.g., Ctrl+Z, Ctrl+Y, Ctrl+S, Ctrl+P)."""
    send_hotkey_combo(f"CTRL+{char_key}")

def send_hotkey_combo(combo_str: str):
    """Sends a single key or multi-modifier shortcut (e.g., 'CTRL+SHIFT+Z', 'ALT+SHIFT+CTRL+S', 'B', '[')."""
    parts = [p.strip().upper() for p in combo_str.split("+") if p.strip()]
    if not parts:
        return
    vks = []
    for p in parts:
        if p in VK_MAP:
            vks.append(VK_MAP[p])
        elif len(p) == 1:
            vks.append(ord(p))
    if not vks:
        return

    # Press all keys in order
    for vk in vks:
        scan_code = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        ctypes.windll.user32.keybd_event(vk, scan_code, 0, 0)
        time.sleep(0.015)
    time.sleep(0.025)
    # Release all keys in reverse order
    for vk in reversed(vks):
        scan_code = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
        ctypes.windll.user32.keybd_event(vk, scan_code, 2, 0)  # 2 = KEYEVENTF_KEYUP
        time.sleep(0.012)

def send_mouse_wheel(delta: int):
    """Simulates mouse wheel scroll for CAD Zoom In / Out."""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    wheel_amount = int(delta * 120)
    ii_.mi = MouseInput(0, 0, ctypes.c_ulong(wheel_amount & 0xFFFFFFFF).value, MOUSEEVENTF_WHEEL, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def send_cad_command(cmd_str: str, cancel_first: bool = True):
    """Types an AutoCAD command string followed by Enter (cancelling any active command first like ^C^C)."""
    if cancel_first:
        send_esc_cancel()
        time.sleep(0.04)
    for ch in cmd_str:
        if ch == " " or ch == "\n":
            time.sleep(0.03)
            send_vk_tap(VK_MAP["ENTER"], 0.02)
            time.sleep(0.03)
        else:
            vk = ord(ch.upper())
            send_vk_tap(vk, 0.02)
            time.sleep(0.025)
    time.sleep(0.035)
    send_vk_tap(VK_MAP["ENTER"], 0.02)

FUSION_ADDIN_HOST = "127.0.0.1"
FUSION_ADDIN_PORT = 36042

def send_fusion_addin_command(target: str, action: str = "command", cancel_first: bool = True) -> bool:
    """Sends a native API command over localhost UDP to MacroPadFusionBridge running inside Fusion 360.
    Returns True if the Add-In acknowledged the packet (<40ms), or False if the Add-In is not running."""
    payload = json.dumps({
        "action": action,
        "target": target,
        "cancel_first": cancel_first
    }).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.045)
    try:
        sock.sendto(payload, (FUSION_ADDIN_HOST, FUSION_ADDIN_PORT))
        data, _ = sock.recvfrom(256)
        return b'"ok"' in data
    except Exception:
        return False
    finally:
        sock.close()

def send_fusion_search_command(query: str):
    """Fallback: Opens Fusion 360's 'S' Shortcuts search box if the native Add-In is not running."""
    if send_fusion_addin_command(query, action="command", cancel_first=True):
        return
    send_esc_cancel()
    time.sleep(0.04)
    # Press 'S' to open Fusion 360 Design Shortcuts search box
    send_vk_tap(ord("S"), 0.025)
    time.sleep(0.10)  # Wait for search popup input box to focus
    for ch in query:
        if ch == " ":
            send_vk_tap(VK_MAP["SPACE"], 0.015)
        else:
            send_vk_tap(ord(ch.upper()), 0.015)
        time.sleep(0.012)
    time.sleep(0.08)  # Let search results filter
    send_vk_tap(VK_MAP["ENTER"], 0.025)

# ==============================================================================
# LIVE UNIFIED HUB STORE SYNC (LAYERS, ACTIONS, RADIAL SLICES & APP RULES)
# ==============================================================================
synced_layers_store = {}
synced_icons_library = {}
synced_app_rules = {
    "auto_app_mode": False,
    "untracked_behavior": "stay",
    "fallback_layer": 1,
    "rules": []
}

def sync_config_from_hub():
    """Fetches the latest layers, button actions, radial pie slices, icons, and auto-app rules from the Pi Hub."""
    global synced_layers_store, synced_icons_library, synced_app_rules
    try:
        import urllib.request
        url = f"http://{MQTT_BROKER}:5000/api/layers"
        with urllib.request.urlopen(url, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "layers" in data:
                synced_layers_store = data["layers"]
            if "icons" in data:
                synced_icons_library = data["icons"]
            if "app_rules_config" in data:
                synced_app_rules = data["app_rules_config"]
            logger.info(f"[Hub Sync] Loaded {len(synced_layers_store)} layers, {len(synced_icons_library)} icons & {len(synced_app_rules.get('rules', []))} app rules (auto_app_mode={synced_app_rules.get('auto_app_mode')})")
    except Exception as e:
        logger.warning(f"[Hub Sync] Could not fetch config from {MQTT_BROKER}:5000: {e}")

# Native Fusion 360 Add-In target mapping for CAD commands across Layers 5..13
FUSION_ADDIN_MAP = {
    # Layer 5: Draw
    "L": ("command", "line"),
    "PL": ("command", "line"),
    "REC": ("command", "rect_2pt"),
    "C": ("command", "circle_center"),
    "A": ("command", "arc_3pt"),
    "POL": ("command", "poly_circum"),
    "SPL": ("command", "spline_fit"),
    "H": ("command", "hole"),
    # Layer 6: Modify
    "M": ("command", "move"),
    "CO": ("command", "move"),
    "RO": ("command", "move"),
    "TR": ("command", "trim"),
    "EX": ("command", "extend"),
    "O": ("command", "offset"),
    "MI": ("command", "mirror"),
    "SC": ("command", "scale"),
    # Layer 7: Construct
    "F": ("command", "fillet"),
    "CHA": ("command", "chamfer"),
    "J": ("command", "joint"),
    "X": ("command", "construction"),
    "BR": ("command", "trim"),
    "AL": ("command", "align"),
    "AR": ("command", "rect_pattern"),
    "E": ("command", "extrude"),
    # Layer 9: Annotate
    "DIM": ("command", "dimension"),
    "DLI": ("command", "dimension"),
    "DAL": ("command", "dimension"),
    "DAN": ("command", "dimension"),
    "DRA": ("command", "dimension"),
    "MLEADER": ("command", "text"),
    "MT": ("command", "text"),
    "TB": ("command", "parameters"),
    # Layer 11: Inspect
    "I": ("command", "Insert Mesh"),
    "DI": ("command", "measure"),
    "AA": ("command", "Properties"),
    # Layer 12: View
    "Z E": ("view", "fit"),
}

# FUSION 360 FALLBACK SHORTCUT MAP (used only if MacroPadFusionBridge Add-In is not running):
FUSION_SHORTCUT_MAP = {
    # Layer 5: Draw
    "L": ("key", "L"),                          # Line
    "PL": ("key", "L"),                         # Line (chained polyline in Fusion)
    "REC": ("key", "R"),                        # 2-Point Rectangle
    "C": ("key", "C"),                          # Center Diameter Circle
    "A": ("search", "3 Point Arc"),             # 3 Point Arc
    "POL": ("search", "Circumscribed Polygon"), # Polygon
    "SPL": ("search", "Fit Point Spline"),      # Fit Point Spline
    "H": ("key", "H"),                          # Hole
    # Layer 6: Modify
    "M": ("key", "M"),                          # Move/Copy
    "CO": ("key", "M"),                         # Move/Copy
    "RO": ("key", "M"),                         # Move/Copy (Rotate)
    "TR": ("key", "T"),                         # Trim
    "EX": ("search", "Extend"),                 # Extend
    "O": ("key", "O"),                          # Offset
    "MI": ("search", "Mirror"),                 # Mirror
    "SC": ("search", "Scale"),                  # Scale
    # Layer 7: Construct
    "F": ("key", "F"),                          # Fillet
    "CHA": ("search", "Chamfer"),               # Chamfer
    "J": ("key", "J"),                          # Joint
    "X": ("key", "X"),                          # Construction Toggle
    "BR": ("search", "Break"),                  # Break
    "AL": ("search", "Align"),                  # Align
    "AR": ("search", "Rectangular Pattern"),    # Rectangular Pattern / Array
    "E": ("key", "E"),                          # Extrude
    # Layer 9: Annotate
    "DIM": ("key", "D"),                        # Sketch Dimension
    "DLI": ("key", "D"),                        # Sketch Dimension
    "DAL": ("key", "D"),                        # Sketch Dimension
    "DAN": ("key", "D"),                        # Sketch Dimension
    "DRA": ("key", "D"),                        # Sketch Dimension
    "MLEADER": ("search", "Text"),              # Text
    "MT": ("search", "Text"),                   # Text
    "TB": ("search", "Change Parameters"),      # Parameters Table
    # Layer 11: Inspect
    "I": ("search", "Insert Mesh"),             # Insert
    "DI": ("key", "I"),                         # Measure / Inspect
    "AA": ("search", "Properties"),             # Area / Physical Properties
}

# AUTOCAD BANK 2 (LAYERS 5-8) & BANK 3 (LAYERS 9-12) ACTION MAP
# Note: Position 9 (bottom-right cell) is consistently ESC (Back Out / Cancel) across ALL layers 5..12!
AUTOCAD_LAYER_MAP = {
    # Layer 5 (Bank 2, Slot 1) — CAD: DRAW
    5: {
        1: ("cmd", "L"),          # LINE
        2: ("cmd", "PL"),         # PLINE
        3: ("cmd", "REC"),        # RECTANGLE
        4: ("cmd", "C"),          # CIRCLE
        5: ("cmd", "A"),          # ARC
        6: ("cmd", "POL"),        # POLYGON
        7: ("cmd", "SPL"),        # SPLINE
        8: ("cmd", "H"),          # HATCH
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    },
    # Layer 6 (Bank 2, Slot 2) — CAD: MODIFY
    6: {
        1: ("cmd", "M"),          # MOVE
        2: ("cmd", "CO"),         # COPY
        3: ("cmd", "RO"),         # ROTATE
        4: ("cmd", "TR"),         # TRIM
        5: ("cmd", "EX"),         # EXTEND
        6: ("cmd", "O"),          # OFFSET
        7: ("cmd", "MI"),         # MIRROR
        8: ("cmd", "SC"),         # SCALE
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    },
    # Layer 7 (Bank 2, Slot 3) — CAD: CONSTRUCT
    7: {
        1: ("cmd", "F"),          # FILLET
        2: ("cmd", "CHA"),        # CHAMFER
        3: ("cmd", "J"),          # JOIN
        4: ("cmd", "X"),          # EXPLODE
        5: ("cmd", "BR"),         # BREAK
        6: ("cmd", "AL"),         # ALIGN
        7: ("cmd", "AR"),         # ARRAY
        8: ("cmd", "E"),          # ERASE
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    },
    # Layer 8 (Bank 2, Slot 4) — CAD: PRECISION & SNAPS
    8: {
        1: ("key", "F3"),         # OSNAP
        2: ("key", "F8"),         # ORTHO
        3: ("key", "F10"),        # POLAR
        4: ("key", "F11"),        # OTRACK
        5: ("key", "F12"),        # DYN INPUT
        6: ("key", "F7"),         # GRID
        7: ("tcmd", "M2P"),       # MID BETWEEN 2 POINTS (Transparent inside command)
        8: ("tcmd", "FROM"),      # SNAP FROM (Transparent inside command)
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    },
    # Layer 9 (Bank 3, Slot 1) — CAD: ANNOTATE
    9: {
        1: ("cmd", "DIM"),        # SMART DIM
        2: ("cmd", "DLI"),        # DIMLINEAR
        3: ("cmd", "DAL"),        # DIMALIGNED
        4: ("cmd", "DAN"),        # DIMANGULAR
        5: ("cmd", "DRA"),        # DIMRADIUS
        6: ("cmd", "MLEADER"),    # MULTILEADER
        7: ("cmd", "MT"),         # MTEXT
        8: ("cmd", "TB"),         # TABLE
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    },
    # Layer 10 (Bank 3, Slot 2) — CAD: LAYERS
    10: {
        1: ("cmd", "LA"),         # LAYER MANAGER
        2: ("cmd", "LAYISO"),     # LAYER ISOLATE
        3: ("cmd", "LAYUNISO"),   # LAYER UNISOLATE
        4: ("cmd", "LAYOFF"),     # LAYER OFF
        5: ("cmd", "LAYON"),      # LAYER ON
        6: ("cmd", "LAYFRZ"),     # LAYER FREEZE
        7: ("cmd", "LAYMCUR"),    # MAKE CURRENT LAYER
        8: ("cmd", "MA"),         # MATCH PROPERTIES
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    },
    # Layer 11 (Bank 3, Slot 3) — CAD: BLOCKS & INQUIRY
    11: {
        1: ("cmd", "I"),          # INSERT BLOCK
        2: ("cmd", "B"),          # CREATE BLOCK
        3: ("cmd", "BE"),         # BLOCK EDITOR
        4: ("cmd", "W"),          # WRITE BLOCK (WBLOCK)
        5: ("cmd", "XR"),         # XREF MANAGER
        6: ("cmd", "DI"),         # DISTANCE
        7: ("cmd", "AA"),         # AREA
        8: ("cmd", "QSELECT"),    # QUICK SELECT
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    },
    # Layer 12 (Bank 3, Slot 4) — CAD: VIEW & OUTPUT
    12: {
        1: ("cmd", "Z E"),        # ZOOM EXTENTS
        2: ("cmd", "Z W"),        # ZOOM WINDOW
        3: ("cmd", "Z P"),        # ZOOM PREVIOUS
        4: ("cmd", "RE"),         # REGEN
        5: ("cmd", "PU"),         # PURGE
        6: ("cmd", "AUDIT Y"),    # AUDIT & FIX
        7: ("ctrl", "P"),         # PLOT / PRINT (Ctrl+P)
        8: ("ctrl", "S"),         # QSAVE (Ctrl+S)
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    },
    # Layer 13 (Bank 4, Slot 1) — FUSION 360: SPACEMOUSE RADIAL (Short-Tap Defaults)
    13: {
        1: ("cmd", "L"),          # SKETCH: Quick Tap = Line (L), Hold = Sketch Primitives Radial
        2: ("cmd", "REC"),        # SHAPES: Quick Tap = 2-Pt Rect (R), Hold = Rect/Poly/Slot Radial
        3: ("cmd", "DIM"),        # 2D EDIT: Quick Tap = Sketch Dim (D), Hold = Offset/Trim/Constraint Radial
        4: ("cmd", "E"),          # 3D SOLID: Quick Tap = Extrude (E), Hold = Extrude/Revolve/Sweep/Loft/Hole Radial
        5: ("cmd", "F"),          # MODIFY: Quick Tap = Fillet (F), Hold = Fillet/Chamfer/Shell/Combine/Split Radial
        6: ("cmd", "M"),          # PATTERN: Quick Tap = Move/Copy (M), Hold = Rect/Circ/Path Pattern & Mirror Radial
        7: ("cmd", "J"),          # PLANE/JNT: Quick Tap = Joint (J), Hold = Offset/Mid/Angle Plane & Assembly Radial
        8: ("cmd", "DI"),         # INSPECT: Quick Tap = Measure (I), Hold = Section/Params/Fit/Hide/3D Print Radial
        9: ("key", "ESC"),        # ESC (Back Out / Cancel)
    }
}

# 3DCONNEXION-STYLE HOLD RADIAL MENUS FOR LAYER 13 (BANK 4, SLOT 1)
# Slices are ordered clockwise starting from North (Top = index 0)
RADIAL_MENU_MAP = {
    13: {
        # Key 1: SKETCH PRIMITIVES (8-slice radial menu)
        1: ("SKETCH", [
            {"label": "Line\n(L)", "type": "fusion", "val": "line", "fb_type": "fkey", "fb_val": "L"},
            {"label": "Create\nSketch", "type": "fusion", "val": "create_sketch", "fb_type": "search", "fb_val": "Create Sketch"},
            {"label": "Circle\n(C)", "type": "fusion", "val": "circle_center", "fb_type": "fkey", "fb_val": "C"},
            {"label": "3-Point\nArc", "type": "fusion", "val": "arc_3pt", "fb_type": "search", "fb_val": "3 Point Arc"},
            {"label": "Fit Point\nSpline", "type": "fusion", "val": "spline_fit", "fb_type": "search", "fb_val": "Fit Point Spline"},
            {"label": "Project\n(P)", "type": "fusion", "val": "project", "fb_type": "fkey", "fb_val": "P"},
            {"label": "Construct\nLine (X)", "type": "fusion", "val": "construction", "fb_type": "fkey", "fb_val": "X"},
            {"label": "Finish\nSketch", "type": "fusion", "val": "finish_sketch", "fb_type": "search", "fb_val": "Finish Sketch"},
        ]),
        # Key 2: SHAPES — RECTANGLES, POLYGONS & SLOTS (6-slice radial menu)
        2: ("SHAPES", [
            {"label": "Center\nRect", "type": "fusion", "val": "rect_center", "fb_type": "search", "fb_val": "Center Rectangle"},
            {"label": "2-Point\nRect (R)", "type": "fusion", "val": "rect_2pt", "fb_type": "fkey", "fb_val": "R"},
            {"label": "3-Point\nRect", "type": "fusion", "val": "rect_3pt", "fb_type": "search", "fb_val": "3-Point Rectangle"},
            {"label": "Circumscr.\nPolygon", "type": "fusion", "val": "poly_circum", "fb_type": "search", "fb_val": "Circumscribed Polygon"},
            {"label": "Inscribed\nPolygon", "type": "fusion", "val": "poly_inscr", "fb_type": "search", "fb_val": "Inscribed Polygon"},
            {"label": "Center\nSlot", "type": "fusion", "val": "slot_center", "fb_type": "search", "fb_val": "Center to Center Slot"},
        ]),
        # Key 3: 2D EDIT & CONSTRAINTS (6-slice radial menu)
        3: ("2D EDIT", [
            {"label": "Dimension\n(D)", "type": "fusion", "val": "dimension", "fb_type": "fkey", "fb_val": "D"},
            {"label": "Offset\n(O)", "type": "fusion", "val": "offset", "fb_type": "fkey", "fb_val": "O"},
            {"label": "Trim\n(T)", "type": "fusion", "val": "trim", "fb_type": "fkey", "fb_val": "T"},
            {"label": "Extend", "type": "fusion", "val": "extend", "fb_type": "search", "fb_val": "Extend"},
            {"label": "2D Mirror", "type": "fusion", "val": "sketch_mirror", "fb_type": "search", "fb_val": "Mirror"},
            {"label": "Coincident", "type": "fusion", "val": "coincident", "fb_type": "search", "fb_val": "Coincident"},
        ]),
        # Key 4: 3D SOLID CREATE (8-slice radial menu)
        4: ("3D SOLID", [
            {"label": "Extrude\n(E)", "type": "fusion", "val": "extrude", "fb_type": "fkey", "fb_val": "E"},
            {"label": "Revolve", "type": "fusion", "val": "revolve", "fb_type": "search", "fb_val": "Revolve"},
            {"label": "Sweep", "type": "fusion", "val": "sweep", "fb_type": "search", "fb_val": "Sweep"},
            {"label": "Loft", "type": "fusion", "val": "loft", "fb_type": "search", "fb_val": "Loft"},
            {"label": "Hole\n(H)", "type": "fusion", "val": "hole", "fb_type": "fkey", "fb_val": "H"},
            {"label": "Thread", "type": "fusion", "val": "thread", "fb_type": "search", "fb_val": "Thread"},
            {"label": "Press Pull\n(Q)", "type": "fusion", "val": "press_pull", "fb_type": "fkey", "fb_val": "Q"},
            {"label": "Rib", "type": "fusion", "val": "rib", "fb_type": "search", "fb_val": "Rib"},
        ]),
        # Key 5: 3D MODIFY & REFINE (6-slice radial menu)
        5: ("MODIFY", [
            {"label": "Fillet\n(F)", "type": "fusion", "val": "fillet", "fb_type": "fkey", "fb_val": "F"},
            {"label": "Chamfer", "type": "fusion", "val": "chamfer", "fb_type": "search", "fb_val": "Chamfer"},
            {"label": "Shell", "type": "fusion", "val": "shell", "fb_type": "search", "fb_val": "Shell"},
            {"label": "Combine", "type": "fusion", "val": "combine", "fb_type": "search", "fb_val": "Combine"},
            {"label": "Split\nBody", "type": "fusion", "val": "split_body", "fb_type": "search", "fb_val": "Split Body"},
            {"label": "Scale", "type": "fusion", "val": "scale", "fb_type": "search", "fb_val": "Scale"},
        ]),
        # Key 6: PATTERN, MIRROR & MOVE (6-slice radial menu)
        6: ("PATTERN", [
            {"label": "Move/Copy\n(M)", "type": "fusion", "val": "move", "fb_type": "fkey", "fb_val": "M"},
            {"label": "Rect\nPattern", "type": "fusion", "val": "rect_pattern", "fb_type": "search", "fb_val": "Rectangular Pattern"},
            {"label": "Circular\nPattern", "type": "fusion", "val": "circ_pattern", "fb_type": "search", "fb_val": "Circular Pattern"},
            {"label": "Pattern\non Path", "type": "fusion", "val": "path_pattern", "fb_type": "search", "fb_val": "Pattern on Path"},
            {"label": "Mirror", "type": "fusion", "val": "mirror", "fb_type": "search", "fb_val": "Mirror"},
            {"label": "Align", "type": "fusion", "val": "align", "fb_type": "search", "fb_val": "Align"},
        ]),
        # Key 7: CONSTRUCTION PLANES & ASSEMBLY (6-slice radial menu)
        7: ("PLANE / ASSY", [
            {"label": "Offset\nPlane", "type": "fusion", "val": "offset_plane", "fb_type": "search", "fb_val": "Offset Plane"},
            {"label": "Midplane", "type": "fusion", "val": "midplane", "fb_type": "search", "fb_val": "Midplane"},
            {"label": "Plane at\nAngle", "type": "fusion", "val": "angle_plane", "fb_type": "search", "fb_val": "Plane at Angle"},
            {"label": "Joint\n(J)", "type": "fusion", "val": "joint", "fb_type": "fkey", "fb_val": "J"},
            {"label": "Rigid\nGroup", "type": "fusion", "val": "rigid_group", "fb_type": "search", "fb_val": "Rigid Group"},
            {"label": "New\nComponent", "type": "fusion", "val": "new_component", "fb_type": "search", "fb_val": "New Component"},
        ]),
        # Key 8: INSPECT, VIEW & EXPORT (6-slice radial menu)
        8: ("INSPECT / VIEW", [
            {"label": "Measure\n(I)", "type": "fusion", "val": "measure", "fb_type": "fkey", "fb_val": "I"},
            {"label": "Section\nAnalysis", "type": "fusion", "val": "section_analysis", "fb_type": "search", "fb_val": "Section Analysis"},
            {"label": "Parameters\n(fx)", "type": "fusion", "val": "parameters", "fb_type": "search", "fb_val": "Change Parameters"},
            {"label": "Fit View\n(F6)", "type": "fusion_view", "val": "fit", "fb_type": "vkey", "fb_val": "F6"},
            {"label": "Home\nView", "type": "fusion_view", "val": "home", "fb_type": "fkey", "fb_val": "V"},
            {"label": "3D Print\n(STL)", "type": "fusion", "val": "3d_print", "fb_type": "search", "fb_val": "3D Print"},
        ]),
    }
}

radial_menu_overlay: Optional[RadialMenuOverlay] = None

def execute_action_string(action_str: str, label: str = "") -> bool:
    """Universal action dispatcher for Unified Hub actions:
    Supports 'fusion:<id>', 'fusion_view:<orient>', 'cad_cmd:<cmd>', 'cad_tcmd:<cmd>',
    'cad_key:<key>', 'hotkey:<combo>', or 'wakeonlan'."""
    if not action_str or action_str.startswith("macro_"):
        return False
    exe_name, win_title = get_foreground_window_info()
    is_fusion = ("fusion" in exe_name) or ("fusion" in win_title.lower())

    if ":" in action_str:
        prefix, val = action_str.split(":", 1)
        prefix = prefix.strip().lower()
        val = val.strip()
    else:
        prefix, val = action_str.strip().lower(), ""

    logger.info(f">>> [Universal Action] {label} -> {prefix}:{val} (app={exe_name})")

    if prefix == "fusion":
        if send_fusion_addin_command(val, action="command", cancel_first=True):
            logger.info(f"    [MacroPadFusionBridge] Executed '{val}' natively via Fusion API")
            return True
        time.sleep(0.03)
        send_fusion_search_command(val.replace("_", " "))
        return True

    elif prefix == "fusion_view":
        if send_fusion_addin_command(val, action="view", cancel_first=False):
            logger.info(f"    [MacroPadFusionBridge] Set viewport '{val}' natively via Fusion API")
            return True
        time.sleep(0.03)
        send_vk_tap(VK_MAP["F6"], 0.025)
        return True

    elif prefix == "cad_key":
        if val.upper() == "ESC":
            if is_fusion and send_fusion_addin_command("", action="cancel", cancel_first=True):
                return True
            send_esc_cancel()
        else:
            send_hotkey_combo(val)
        return True

    elif prefix in ("cad_cmd", "cad_tcmd"):
        cancel_first = (prefix == "cad_cmd")
        if is_fusion:
            addin_entry = FUSION_ADDIN_MAP.get(val.upper(), ("command", val))
            if send_fusion_addin_command(addin_entry[1], action=addin_entry[0], cancel_first=cancel_first):
                return True
        send_cad_command(val, cancel_first=cancel_first)
        return True

    elif prefix == "hotkey":
        time.sleep(0.02)
        send_hotkey_combo(val)
        return True

    elif prefix in ("discord_mic_mute", "mic_mute_toggle"):
        toggle_microphone_mute()
        return True

    elif prefix == "discord_deafen":
        toggle_discord_deafen()
        return True

    elif prefix == "discord_vol_down":
        adjust_discord_volume(-5)
        return True

    elif prefix == "discord_vol_up":
        adjust_discord_volume(5)
        return True

    elif prefix == "discord_vol_reset":
        reset_discord_volume(100)
        return True

    elif prefix == "audio_headphones":
        switch_default_playback_device("headphones")
        return True

    elif prefix == "audio_speakers":
        switch_default_playback_device("speakers")
        return True

    elif prefix == "discord_sync_call":
        sync_discord_voice_call_manual()
        return True

    elif prefix == "discord_demo_call":
        toggle_discord_demo_call()
        return True

    return False

def get_synced_cell_config(layer: int, index: int) -> Optional[dict]:
    """Returns the cell dict from synced_layers_store for (layer, index 1..9) if present."""
    layer_obj = synced_layers_store.get(str(layer))
    if not layer_obj:
        return None
    for cell in layer_obj.get("cells", []):
        if int(cell.get("index", 0)) == index:
            return cell
    return None

def get_radial_menu_for_cell(layer: int, index: int):
    """Returns (title, slices_list) for (layer, index) from synced Hub store or fallback RADIAL_MENU_MAP."""
    cell = get_synced_cell_config(layer, index)
    if cell and cell.get("hold_enabled") and cell.get("radial_slices"):
        title = cell.get("radial_title") or cell.get("label") or f"KEY {index}"
        formatted_slices = []
        for s in cell["radial_slices"]:
            lbl = s.get("label", "Slice")
            sub = s.get("sub", "")
            disp = f"{lbl}\n({sub})" if sub and sub not in lbl else lbl
            formatted_slices.append({
                "label": disp,
                "type": "action_str",
                "val": s.get("action", "")
            })
        if formatted_slices:
            return title, formatted_slices

    layer_radials = RADIAL_MENU_MAP.get(layer, {})
    if index in layer_radials:
        return layer_radials[index]
    return None

def on_radial_slice_selected(act_type: str, act_val: str, act_label: str):
    """Callback invoked when a user selects a slice from the on-screen Radial Menu."""
    logger.info(f">>> [Radial Menu Selected] {act_label} -> {act_type.upper()}: {act_val}")
    if act_type == "action_str":
        time.sleep(0.025)
        execute_action_string(act_val, act_label)
        return
    elif act_type == "fusion":
        if send_fusion_addin_command(act_val, action="command", cancel_first=True):
            logger.info(f"    [MacroPadFusionBridge] Executed '{act_val}' natively via Fusion API")
            return
        # Fallback if Add-In not running yet
        time.sleep(0.03)
        send_fusion_search_command(act_val.replace("_", " "))
        return
    elif act_type == "fusion_view":
        if send_fusion_addin_command(act_val, action="view", cancel_first=False):
            logger.info(f"    [MacroPadFusionBridge] Set viewport '{act_val}' natively via Fusion API")
            return
        time.sleep(0.03)
        send_vk_tap(VK_MAP["F6"], 0.025)
        return

    time.sleep(0.03)  # Allow CAD window focus restoration
    if act_type == "fkey":
        send_esc_cancel()
        time.sleep(0.03)
        send_vk_tap(ord(act_val.upper()), 0.025)
    elif act_type == "vkey":
        vk = VK_MAP.get(act_val.upper())
        if vk:
            send_vk_tap(vk, 0.025)
    elif act_type == "search":
        send_fusion_search_command(act_val)
    elif act_type == "cmd":
        send_cad_command(act_val, cancel_first=True)

def execute_autocad_action(layer: int, index: int, label: str = ""):
    """Executes the mapped button action from the Unified Hub store (or fallback AUTOCAD_LAYER_MAP)."""
    if radial_menu_overlay and radial_menu_overlay.is_visible:
        radial_menu_overlay.close_menu()
        if index == 9:
            return

    # 1. Check dynamic Unified Hub store first (Zero-Reflash customizable actions on ANY layer!)
    cell = get_synced_cell_config(layer, index)
    if cell and cell.get("action") and not str(cell.get("action")).startswith("macro_"):
        if execute_action_string(str(cell["action"]), label or cell.get("label", "")):
            return

    # 2. Fallback to hardcoded AUTOCAD_LAYER_MAP
    layer_map = AUTOCAD_LAYER_MAP.get(layer)
    if not layer_map or index not in layer_map:
        return
    act_type, val = layer_map[index]
    fg_title = get_foreground_window_title()
    is_fusion = "fusion" in fg_title or layer == 13

    logger.info(f">>> [CAD L{layer} K{index}] {label} -> {act_type.upper()}: {val} (window='{fg_title}')")
    if act_type == "key":
        if val.upper() == "ESC":
            if is_fusion and send_fusion_addin_command("", action="cancel", cancel_first=True):
                logger.info("    [MacroPadFusionBridge] Cancelled active command via Fusion API")
                return
            send_esc_cancel()
        else:
            vk = VK_MAP.get(val.upper())
            if vk:
                send_vk_tap(vk, 0.02)
    elif act_type == "ctrl":
        send_ctrl_combo(val)
    elif act_type in ("cmd", "tcmd"):
        if is_fusion:
            # 1. Try native Fusion 360 Add-In Bridge first (<2ms direct API execution, zero search popup)
            addin_entry = FUSION_ADDIN_MAP.get(val, ("command", val))
            if send_fusion_addin_command(addin_entry[1], action=addin_entry[0], cancel_first=(act_type == "cmd")):
                logger.info(f"    [MacroPadFusionBridge] Executed {addin_entry[0]}='{addin_entry[1]}' natively via Fusion API")
                return
            # 2. Fallback if Add-In is not running yet
            if val in FUSION_SHORTCUT_MAP:
                f_mode, f_val = FUSION_SHORTCUT_MAP[val]
                if f_mode == "key":
                    send_esc_cancel()
                    time.sleep(0.03)
                    send_vk_tap(ord(f_val), 0.025)
                elif f_mode == "search":
                    send_fusion_search_command(f_val)
                return
        # AutoCAD command line execution (cancel_first=True for primary commands, False for transparent M2P/FROM)
        send_cad_command(val, cancel_first=(act_type == "cmd"))

# APP TARGET PROCESS GROUPS
APP_TARGETS = ["fortnite", "browser", "music"]
current_app_target_idx = 0

APP_PROCESS_MAP = {
    "fortnite": ["fortniteclient-win64-shipping.exe", "fortniteclient.exe", "fortnite.exe"],
    "browser": ["opera.exe", "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe", "vivaldi.exe"],
    "music": ["spotify.exe", "applemusic.exe", "music.ui.exe", "vlc.exe", "foobar2000.exe", "tidal.exe"]
}

# ==============================================================================
# LOGGING SETUP
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("MacroPadAudioBridge")

# ==============================================================================
# AUDIO CONTROLLER (WINDOWS PYCAW)
# ==============================================================================
mqtt_client = None

def publish_popup(text: str):
    global mqtt_client
    if mqtt_client and mqtt_client.is_connected():
        payload = {"popup": text}
        mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload))

def publish_mic_state(is_muted: bool):
    global mqtt_client
    if mqtt_client and mqtt_client.is_connected():
        payload = {"mic_muted": is_muted}
        mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload), retain=False)

def publish_voice_call_state(in_call: Optional[bool] = None):
    global mqtt_client, discord_rpc_client
    if not mqtt_client or not mqtt_client.is_connected():
        return
    if in_call is None:
        in_call = is_in_voice_call()
    payload = {"in_call": bool(in_call)}
    mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload), retain=False)

is_discord_muted = False
is_discord_deafened = False
is_synthetic_send = False

# ==============================================================================
# DISCORD VOICE CALL MEMBERS & DYNAMIC LAYER 2 MIXER
# ==============================================================================
is_audio_mod_active = False
voice_page = 0
selected_voice_member_idx = 0
discord_demo_call_active = False
active_voice_members = []
normal_grid_labels = ["ACT 1", "ACT 2", "ACT 3", "ACT 4", "ACT 5", "ACT 6", "ACT 7", "ACT 8", "WOL PC"]

DEMO_VOICE_MEMBERS_TEMPLATE = [
    {"id": "demo_1", "name": "ALEX", "volume": 100, "is_self": False, "bot": False, "local_mute": False, "mute": False, "speaking": True},
    {"id": "demo_2", "name": "SARAH", "volume": 100, "is_self": False, "bot": False, "local_mute": False, "mute": False, "speaking": False},
    {"id": "demo_3", "name": "MARK", "volume": 85, "is_self": False, "bot": False, "local_mute": False, "mute": False, "speaking": False},
    {"id": "demo_4", "name": "CHRIS", "volume": 120, "is_self": False, "bot": False, "local_mute": False, "mute": False, "speaking": False},
    {"id": "demo_self", "name": "UZZO", "volume": 100, "is_self": True, "bot": False, "local_mute": False, "mute": False, "speaking": False},
]
demo_voice_members = [dict(m) for m in DEMO_VOICE_MEMBERS_TEMPLATE]

def get_active_call_members() -> list:
    """Returns real Discord voice channel members if in a call, or demo members if Demo Call mode is active."""
    global active_voice_members
    if discord_rpc_client and discord_rpc_client.is_authenticated and discord_rpc_client.voice_channel:
        ch_members = discord_rpc_client.voice_channel.get("members") or []
        if ch_members:
            active_voice_members = ch_members
            return active_voice_members
    if discord_demo_call_active:
        active_voice_members = demo_voice_members
        return active_voice_members
    active_voice_members = []
    return []

def is_in_voice_call() -> bool:
    return len(get_active_call_members()) > 0

def format_voice_member_cell(m: dict, is_selected: bool) -> str:
    """Formats a single voice member into a 2-line MacroPad cell label with selection (>) and mute indicators."""
    name = m.get("name", "User")[:5] if is_selected else m.get("name", "User")[:6]
    sel_tag = ">" if is_selected else ""
    is_muted = bool(m.get("local_mute") or m.get("mute") or (m.get("is_self") and is_discord_muted))
    line1 = f"{sel_tag}{name}"
    if m.get("is_self"):
        line2 = "MUTED" if is_muted else "YOU"
    elif is_muted:
        line2 = "MUTED"
    else:
        line2 = f"{m.get('volume', 100)}%"
    return f"{line1}\n{line2}"

def build_voice_labels(members: list, page: int):
    """Formats voice call members into 3x3 matrix labels with pagination, selection cursor (>), and mute state."""
    global selected_voice_member_idx
    total = len(members)
    labels = [""] * 9
    if total == 0:
        return labels, 1

    if selected_voice_member_idx >= total or selected_voice_member_idx < 0:
        selected_voice_member_idx = 0

    if total <= 8:
        total_pages = 1
        for i in range(total):
            labels[i] = format_voice_member_cell(members[i], i == selected_voice_member_idx)
        # Slot 9 is EXIT DEMO (if in demo mode) or DEAFEN toggle (in real call)
        if discord_demo_call_active and not (discord_rpc_client and discord_rpc_client.voice_channel):
            labels[8] = "EXIT\nDEMO"
        else:
            labels[8] = "UNDEAF\nCALL" if is_discord_deafened else "DEAFEN\nCALL"
        return labels, total_pages
    elif total == 9:
        total_pages = 1
        for i in range(9):
            labels[i] = format_voice_member_cell(members[i], i == selected_voice_member_idx)
        return labels, total_pages
    else:
        # More than 9 members: use first 7 slots for users, last 2 slots for pagination
        page_size = 7
        total_pages = (total + page_size - 1) // page_size
        page = max(0, min(total_pages - 1, page))
        start = page * page_size
        page_members = members[start:start + page_size]
        for i in range(7):
            if i < len(page_members):
                global_idx = start + i
                labels[i] = format_voice_member_cell(page_members[i], global_idx == selected_voice_member_idx)
            else:
                labels[i] = ""
        labels[7] = f"P{page+1}/{total_pages} <"
        labels[8] = f"P{page+1}/{total_pages} >"
        return labels, total_pages

def publish_voice_grid(page_changed: bool = False, include_layer: Optional[int] = None, fast: bool = True):
    """Publishes current voice call members to the 3x3 matrix on the MacroPad"""
    global voice_page
    members = get_active_call_members()
    if not members:
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.publish(TOPIC_DISPLAY, json.dumps({"in_call": False}), retain=False)
        return

    labels, total_pages = build_voice_labels(members, voice_page)
    payload = {
        "clear_icons": True,
        "hold_mask": 511,
        "labels": labels,
        "in_call": True,
        "fast": fast
    }
    if include_layer is not None:
        payload["layer"] = int(include_layer)
    if mqtt_client and mqtt_client.is_connected():
        mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload), retain=False)
        logger.info(f"Published voice member grid ({len(members)} members, selected=#{selected_voice_member_idx + 1}, page {voice_page + 1}/{total_pages})")

def toggle_discord_deafen():
    """Toggles Discord deafen state via RPC (or Ctrl+Shift+D fallback)"""
    global is_discord_deafened
    if discord_rpc_client and discord_rpc_client.is_authenticated:
        is_discord_deafened = discord_rpc_client.toggle_deafen()
    else:
        is_discord_deafened = not is_discord_deafened
        send_hotkey_combo("CTRL+SHIFT+D")
    publish_popup("DISCORD:\nDEAFENED" if is_discord_deafened else "DISCORD:\nUNDEAFENED")
    if current_active_layer == 2 and is_in_voice_call():
        publish_voice_grid()

def sync_discord_voice_call_manual():
    """Manually refreshes Discord voice call status from Layer 2 button 8"""
    if discord_rpc_client and discord_rpc_client.is_authenticated:
        discord_rpc_client.refresh_voice_channel()
        time.sleep(0.15)
        if is_in_voice_call():
            publish_voice_grid(include_layer=2, fast=False)
            publish_popup("VOICE CALL:\nSYNCED")
            return
    publish_popup("DISCORD:\nNO ACTIVE CALL")

def toggle_discord_demo_call():
    """Toggles a 5-member simulated Discord voice call on Layer 2 for instant testing"""
    global discord_demo_call_active, demo_voice_members, selected_voice_member_idx, voice_page
    discord_demo_call_active = not discord_demo_call_active
    if discord_demo_call_active:
        demo_voice_members = [dict(m) for m in DEMO_VOICE_MEMBERS_TEMPLATE]
        selected_voice_member_idx = 0
        voice_page = 0
        logger.info(">>> Started Discord 5-Member Demo Call on Layer 2")
        publish_voice_grid(include_layer=2, fast=False)
        publish_popup("DEMO CALL ON:\nTAP=MUTE KNOB=VOL")
    else:
        logger.info(">>> Ended Discord Demo Call on Layer 2")
        publish_voice_call_state(False)
        apply_layer_via_hub(2, force_static=True)
        publish_popup("DEMO CALL:\nENDED")

def handle_layer2_voice_key_tap(idx: int) -> bool:
    """Quick Tap (<220ms) on Layer 2 in a call: Selects the target user (>) for volume adjustment."""
    global voice_page, selected_voice_member_idx, discord_demo_call_active
    members = get_active_call_members()
    if not members:
        return False

    total = len(members)
    if total > 9:
        page_size = 7
        total_pages = (total + page_size - 1) // page_size
        if idx == 8:
            voice_page = max(0, voice_page - 1)
            publish_voice_grid(page_changed=True)
            publish_popup(f"PAGE {voice_page + 1}/{total_pages}")
            return True
        elif idx == 9:
            voice_page = min(total_pages - 1, voice_page + 1)
            publish_voice_grid(page_changed=True)
            publish_popup(f"PAGE {voice_page + 1}/{total_pages}")
            return True
        m_idx = (voice_page * 7) + (idx - 1)
    else:
        if total <= 8 and idx == 9:
            if discord_demo_call_active and not (discord_rpc_client and discord_rpc_client.voice_channel):
                toggle_discord_demo_call()
            else:
                toggle_discord_deafen()
            return True
        m_idx = idx - 1

    if 0 <= m_idx < total:
        selected_voice_member_idx = m_idx
        member = members[m_idx]
        name = member.get("name", "User").upper()
        if member.get("is_self"):
            status_txt = "MUTED" if is_discord_muted else "YOU"
        elif member.get("local_mute") or member.get("mute"):
            status_txt = "MUTED"
        else:
            status_txt = f"{member.get('volume', 100)}%"
        logger.info(f">>> [Discord Call Tap] Selected Target User #{m_idx + 1}: {name} ({status_txt})")
        publish_popup(f"TARGET:\n{name} ({status_txt})")
        publish_voice_grid()
        return True

    return True

def handle_layer2_voice_key_hold(idx: int) -> bool:
    """Hold (>=220ms) on Layer 2 in a call: Toggles Mute / Unmute for that member (and selects them)."""
    global voice_page, selected_voice_member_idx
    members = get_active_call_members()
    if not members:
        return False

    total = len(members)
    if total > 9:
        if idx in (8, 9):
            return True
        m_idx = (voice_page * 7) + (idx - 1)
    else:
        if total <= 8 and idx == 9:
            toggle_discord_deafen()
            return True
        m_idx = idx - 1

    if 0 <= m_idx < total:
        selected_voice_member_idx = m_idx
        member = members[m_idx]
        uid = str(member.get("id", ""))
        name = member.get("name", "User").upper()

        if member.get("is_self"):
            toggle_microphone_mute()
            member["mute"] = is_discord_muted
            publish_voice_grid()
            return True

        new_mute = not bool(member.get("local_mute") or member.get("mute"))
        member["local_mute"] = new_mute
        member["mute"] = new_mute
        if discord_rpc_client and discord_rpc_client.is_authenticated and not uid.startswith("demo_"):
            discord_rpc_client.set_user_mute(uid, new_mute)

        vol = member.get("volume", 100)
        status_txt = "MUTED" if new_mute else f"LIVE ({vol}%)"
        logger.info(f">>> [Discord Call Hold] Toggled Mute on Member #{m_idx + 1} ({name}) -> {status_txt}")
        publish_popup(f"{name}:\n{status_txt}")
        publish_voice_grid()
        return True

    return True

def adjust_selected_voice_member_volume(delta: int, explicit_idx: Optional[int] = None):
    """Adjusts the volume (0%..200%) of the currently selected (>) or held voice call member."""
    global selected_voice_member_idx
    members = get_active_call_members()
    if not members:
        return
    if explicit_idx is not None:
        m_idx = explicit_idx
        selected_voice_member_idx = m_idx
    else:
        if selected_voice_member_idx >= len(members) or selected_voice_member_idx < 0:
            selected_voice_member_idx = 0
        m_idx = selected_voice_member_idx

    if 0 <= m_idx < len(members):
        member = members[m_idx]
        uid = str(member.get("id", ""))
        name = member.get("name", "User").upper()
        if member.get("is_self"):
            adjust_discord_volume(delta)
            return
        curr_vol = int(member.get("volume", 100))
        new_vol = max(0, min(200, curr_vol + (5 * delta)))
        member["volume"] = new_vol
        if new_vol > 0 and (member.get("local_mute") or member.get("mute")):
            member["local_mute"] = False
            member["mute"] = False
            if discord_rpc_client and discord_rpc_client.is_authenticated and not uid.startswith("demo_"):
                discord_rpc_client.set_user_mute(uid, False)
        if discord_rpc_client and discord_rpc_client.is_authenticated and not uid.startswith("demo_"):
            discord_rpc_client.set_user_volume(uid, new_vol)
        logger.info(f">>> [Discord Call] Member {name} Volume -> {new_vol}% (delta={delta:+d})")
        publish_popup(f"{name}:\nVOL {new_vol}%")
        publish_voice_grid()

def reset_selected_voice_member_volume(target_pct: int = 80):
    """Resets the currently selected (>) voice call member's volume to target_pct (default 80%)."""
    global selected_voice_member_idx
    members = get_active_call_members()
    if not members:
        reset_discord_volume(target_pct)
        return
    if selected_voice_member_idx >= len(members) or selected_voice_member_idx < 0:
        selected_voice_member_idx = 0
    m = members[selected_voice_member_idx]
    if m.get("is_self"):
        reset_discord_volume(target_pct)
        return
    m["volume"] = target_pct
    if m.get("local_mute") or m.get("mute"):
        m["local_mute"] = False
        m["mute"] = False
    uid = str(m.get("id", ""))
    if discord_rpc_client and discord_rpc_client.is_authenticated and not uid.startswith("demo_"):
        discord_rpc_client.set_user_mute(uid, False)
        discord_rpc_client.set_user_volume(uid, target_pct)
    name = m.get("name", "USER").upper()
    logger.info(f">>> [Discord Call] Reset Member {name} Volume -> {target_pct}%")
    publish_popup(f"{name}:\nVOL {target_pct}%")
    publish_voice_grid()

def cycle_selected_voice_member():
    """Cycles the (>) active volume target across call members without muting them."""
    global selected_voice_member_idx
    members = get_active_call_members()
    if not members:
        return
    selected_voice_member_idx = (selected_voice_member_idx + 1) % len(members)
    m = members[selected_voice_member_idx]
    name = m.get("name", "User").upper()
    vol = "YOU" if m.get("is_self") else ("MUTED" if (m.get("local_mute") or m.get("mute")) else f"{m.get('volume', 100)}%")
    logger.info(f">>> [Discord Call] Selected Volume Target -> {name} ({vol})")
    publish_popup(f"TARGET:\n{name} ({vol})")
    publish_voice_grid()

def on_voice_channel_update(voice_channel):
    """Callback fired when voice call membership or status changes"""
    global is_audio_mod_active, current_active_layer, universal_app_overlay_active
    ch_name = voice_channel.get('name') if voice_channel else 'No call'
    in_call = bool(voice_channel and voice_channel.get("id")) or discord_demo_call_active
    logger.info(f"[Discord Voice Event] Channel update: {ch_name} (in_call={in_call})")
    publish_voice_call_state(in_call)
    # ONLY push Discord voice grid if we are actually on Discord layer or holding Key 13 audio mod, and NOT currently displaying a universal app grid
    if not universal_app_overlay_active and (is_audio_mod_active or current_active_layer == 2):
        if in_call:
            publish_voice_grid()
        elif current_active_layer == 2:
            apply_layer_via_hub(2, force_static=True)

def on_discord_rpc_mute_change(is_muted: bool):
    """Callback fired in real time whenever Discord voice settings change (from Discord app, hotkeys, or RPC)"""
    global is_discord_muted, current_active_layer, universal_app_overlay_active
    is_discord_muted = is_muted
    status_str = "MIC MUTED" if is_discord_muted else "MIC LIVE"
    logger.info(f"[Discord RPC Event] Live Mute State: {status_str}")
    publish_mic_state(is_discord_muted)
    if not universal_app_overlay_active and current_active_layer == 2 and is_in_voice_call():
        publish_voice_grid()
    update_tray_icon()

def on_keyboard_hotkey():
    global is_synthetic_send, is_discord_muted, discord_rpc_client
    if is_synthetic_send:
        return
    # If Discord Voice RPC is connected, Discord natively handles the hotkey and emits an RPC event
    if discord_rpc_client and discord_rpc_client.is_authenticated:
        return
    logger.info("Physical keyboard hotkey [Ctrl+Shift+] detected (Fallback)")
    is_discord_muted = not is_discord_muted
    status_str = "MIC MUTED" if is_discord_muted else "MIC LIVE"
    publish_mic_state(is_discord_muted)
    update_tray_icon()

def trigger_discord_mute_hotkey():
    """Simulates pressing Ctrl+Shift+] using hardware scan codes via SendInput"""
    global is_synthetic_send
    is_synthetic_send = True
    try:
        # Key down sequence: Ctrl -> Shift -> ]
        _send_scancode_key(VK_CONTROL, SCAN_LCTRL, False)
        time.sleep(0.02)
        _send_scancode_key(VK_SHIFT, SCAN_LSHIFT, False)
        time.sleep(0.02)
        _send_scancode_key(VK_CLOSE_BRACKET, SCAN_CLOSE_BRACKET, False)
        time.sleep(0.06)
        # Key up sequence: ] -> Shift -> Ctrl
        _send_scancode_key(VK_CLOSE_BRACKET, SCAN_CLOSE_BRACKET, True)
        time.sleep(0.02)
        _send_scancode_key(VK_SHIFT, SCAN_LSHIFT, True)
        time.sleep(0.02)
        _send_scancode_key(VK_CONTROL, SCAN_LCTRL, True)
        logger.info("Sent Discord toggle mute hotkey (Ctrl+Shift+]) via SendInput scan codes")
    except Exception as e:
        logger.error(f"Failed to send Discord hotkey: {e}")
    finally:
        time.sleep(0.05)
        is_synthetic_send = False

def toggle_microphone_mute():
    """Toggles Discord mute state (via native RPC if available, fallback to hotkey)"""
    global is_discord_muted, discord_rpc_client

    if discord_rpc_client and discord_rpc_client.is_authenticated:
        logger.info(">>> Toggling Discord mute via RPC...")
        discord_rpc_client.toggle_mute()
        return

    # Fallback to hotkey simulation if RPC is not connected/configured
    is_discord_muted = not is_discord_muted

    if DISCORD_HOTKEY_ENABLED:
        trigger_discord_mute_hotkey()

    if PYCAW_AVAILABLE:
        try:
            mic = AudioUtilities.GetMicrophone()
            if mic:
                vol_interface = cast(mic.Activate(IAudioEndpointVolume._iid_, 7, None), POINTER(IAudioEndpointVolume))
                vol_interface.SetMute(is_discord_muted, None)
        except Exception as e:
            logger.debug(f"OS microphone mute sync: {e}")

    status_str = "MIC MUTED" if is_discord_muted else "MIC LIVE"
    logger.info(f">>> Microphone Mute (Fallback): {status_str}")
    publish_popup(status_str)
    publish_mic_state(is_discord_muted)

def adjust_master_volume(delta: int):
    """Adjusts Windows master volume up/down"""
    if not PYCAW_AVAILABLE:
        return
    try:
        speakers = AudioUtilities.GetSpeakers()
        vol = speakers.EndpointVolume
        current = vol.GetMasterVolumeLevelScalar()
        step = 0.02 * delta  # 2% per tick
        new_vol = max(0.0, min(1.0, current + step))
        vol.SetMasterVolumeLevelScalar(new_vol, None)
        pct = round(new_vol * 100)
        logger.info(f">>> Master Volume: {pct}% (delta={delta})")
        publish_popup(f"MASTER: {pct}%")
    except Exception as e:
        logger.error(f"Error adjusting master volume: {e}")

def reset_master_volume(target_pct: int = 80):
    """Resets master volume to 80%"""
    if not PYCAW_AVAILABLE:
        return
    try:
        speakers = AudioUtilities.GetSpeakers()
        vol = speakers.EndpointVolume
        vol.SetMasterVolumeLevelScalar(target_pct / 100.0, None)
        logger.info(f">>> Master Volume Reset to {target_pct}%")
        publish_popup(f"MASTER: {target_pct}%")
    except Exception as e:
        logger.error(f"Error resetting master volume: {e}")

def find_session(process_names: List[str]):
    """Finds an active audio session matching any of the process names"""
    if not PYCAW_AVAILABLE:
        return None
    try:
        sessions = AudioUtilities.GetAllSessions()
        for s in sessions:
            if s.Process:
                pname = s.Process.name().lower()
                for name in process_names:
                    if name.lower() in pname:
                        return s
    except Exception:
        pass
    return None

def adjust_discord_volume(delta: int):
    """Adjusts Discord application volume"""
    session = find_session(["discord.exe"])
    if session:
        try:
            curr = session.SimpleAudioVolume.GetMasterVolume()
            new_vol = max(0.0, min(1.0, curr + (delta * 0.02)))
            session.SimpleAudioVolume.SetMasterVolume(new_vol, None)
            pct = round(new_vol * 100)
            logger.info(f">>> Discord Volume: {pct}%")
            publish_popup(f"DISCORD: {pct}%")
        except Exception as e:
            logger.error(f"Error adjusting Discord volume: {e}")
    else:
        logger.warning("Discord process not found in audio mixer")
        publish_popup("DISCORD: N/A")

def reset_discord_volume(target_pct: int = 80):
    """Resets Discord application volume to 80%"""
    session = find_session(["discord.exe"])
    if session:
        try:
            session.SimpleAudioVolume.SetMasterVolume(target_pct / 100.0, None)
            logger.info(f">>> Discord Volume Reset to {target_pct}%")
            publish_popup(f"DISCORD: {target_pct}%")
        except Exception as e:
            logger.error(f"Error resetting Discord volume: {e}")
    else:
        logger.warning("Discord process not found in audio mixer")
        publish_popup("DISCORD: N/A")

def cycle_app_target():
    """Toggles active application volume target between Fortnite, Browser, and Music"""
    global current_app_target_idx
    current_app_target_idx = (current_app_target_idx + 1) % len(APP_TARGETS)
    target = APP_TARGETS[current_app_target_idx]
    
    session = find_session(APP_PROCESS_MAP[target])
    if session:
        try:
            pct = round(session.SimpleAudioVolume.GetMasterVolume() * 100)
            status = f"APP: {target.upper()} ({pct}%)"
        except Exception:
            status = f"APP: {target.upper()}"
    else:
        status = f"APP: {target.upper()} (N/A)"
    
    logger.info(f">>> Switched Audio Target: {status}")
    publish_popup(status)

def adjust_app_volume(delta: int):
    """Adjusts volume for the currently selected target (Fortnite / Browser / Music)"""
    target = APP_TARGETS[current_app_target_idx]
    session = find_session(APP_PROCESS_MAP[target])
    if session:
        try:
            curr = session.SimpleAudioVolume.GetMasterVolume()
            new_vol = max(0.0, min(1.0, curr + (delta * 0.02)))
            session.SimpleAudioVolume.SetMasterVolume(new_vol, None)
            pct = round(new_vol * 100)
            logger.info(f">>> {target.upper()} Volume: {pct}%")
            publish_popup(f"{target.upper()}: {pct}%")
        except Exception as e:
            logger.error(f"Error adjusting {target} volume: {e}")
    else:
        logger.warning(f"No active audio session found for {target.upper()}")
        publish_popup(f"{target.upper()}: N/A")

def switch_default_playback_device(target: str) -> Optional[str]:
    """Switches Windows default audio playback endpoint between Headphones and Speakers"""
    if not POLICY_CONFIG_AVAILABLE:
        logger.warning("PolicyConfig COM interface is not available")
        return None

    if target == "toggle":
        try:
            spk = AudioUtilities.GetSpeakers()
            curr_name = getattr(spk, 'FriendlyName', '')
            if "g321" in curr_name.lower():
                target = "speakers"
            else:
                target = "headphones"
        except Exception:
            target = "headphones"

    keyword = "G321" if target == "headphones" else "EDIFIER"
    label = "Logitech G321" if target == "headphones" else "Edifier Speakers"
    
    try:
        policy = comtypes.CoCreateInstance(CLSID_PolicyConfigClient, IPolicyConfig, CLSCTX_ALL)
        for d in AudioUtilities.GetAllDevices():
            name = getattr(d, 'FriendlyName', '')
            dev_id = getattr(d, 'id', '')
            state = str(getattr(d, 'state', ''))
            # Filter for active playback endpoints matching keyword
            if keyword.lower() in name.lower() and 'Active' in state and dev_id.startswith('{0.0.0.'):
                logger.info(f">>> Switching Default Audio to: {name} ({dev_id})")
                for role in (0, 1, 2): # Console (0), Multimedia (1), Communications (2)
                    policy.SetDefaultEndpoint(dev_id, role)
                publish_popup(f"AUDIO:\n{label.upper()}")
                return name
        logger.warning(f"Audio device matching '{keyword}' not found or not active")
        publish_popup(f"{keyword}:\nNOT ACTIVE")
        return None
    except Exception as e:
        logger.error(f"Error switching audio device: {e}")
def send_wake_on_lan(mac_address: str = "d4:93:90:3b:f0:89"):
    """Broadcasts Wake-on-LAN magic packet over UDP to wake target machine"""
    try:
        clean_mac = mac_address.replace(":", "").replace("-", "")
        if len(clean_mac) != 12:
            logger.error(f"Invalid MAC address for WoL: {mac_address}")
            return
        data = bytes.fromhex("FFFFFFFFFFFF" + (clean_mac * 16))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(data, ("255.255.255.255", 9))
            s.sendto(data, ("192.168.1.255", 9))
        logger.info(f">>> Sent Wake-on-LAN magic packet to {mac_address}")
        publish_popup("WOL SENT:\nPC WAKE")
    except Exception as e:
        logger.error(f"Failed to send Wake-on-LAN packet: {e}")

# ==============================================================================
# MQTT HANDLERS
# ==============================================================================
TOPIC_CONFIG_SYNC = "macropad/config_sync"
TOPIC_PC_TELEMETRY = "macropad/pc_telemetry"
force_app_reeval = False

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}")
        client.subscribe([(TOPIC_INPUT, 0), (TOPIC_STATUS, 0), (TOPIC_CONFIG_SYNC, 0)])
        logger.info(f"Subscribed to topics: {TOPIC_INPUT}, {TOPIC_STATUS}, {TOPIC_CONFIG_SYNC}")
        # Sync current mic status, voice call status, and Unified Hub config store
        publish_mic_state(is_discord_muted)
        publish_voice_call_state()
        threading.Thread(target=sync_config_from_hub, daemon=True).start()
    else:
        logger.error(f"MQTT connection failed with code {rc}")

current_active_layer = 1
voice_grid_displayed = False
universal_app_overlay_active = False
universal_app_name = ""

def on_message(client, userdata, msg):
    global is_audio_mod_active, voice_page, current_active_layer, voice_grid_displayed, force_app_reeval, universal_app_overlay_active
    try:
        # Live config sync broadcast from Unified Web Hub when user saves layers or app rules
        if msg.topic == TOPIC_CONFIG_SYNC:
            try:
                cfg_msg = json.loads(msg.payload.decode("utf-8"))
                if "auto_app_mode" in cfg_msg:
                    synced_app_rules["auto_app_mode"] = bool(cfg_msg["auto_app_mode"])
                    force_app_reeval = True
            except Exception:
                pass
            threading.Thread(target=sync_config_from_hub, daemon=True).start()
            return

        # MacroPad status / heartbeat topic (fires when device powers on, reconnects, or wakes up)
        if msg.topic == TOPIC_STATUS:
            try:
                st = json.loads(msg.payload.decode('utf-8'))
                if "layer" in st:
                    current_active_layer = int(st["layer"])
                if "auto_app_mode" in st:
                    synced_app_rules["auto_app_mode"] = bool(st["auto_app_mode"])
            except Exception:
                pass
            logger.info("MacroPad device presence detected -> syncing mic mute and call state")
            publish_mic_state(is_discord_muted)
            publish_voice_call_state()
            return

        try:
            payload = json.loads(msg.payload.decode('utf-8', errors='replace'), strict=False)
        except Exception as e:
            logger.warning(f"Error parsing MQTT JSON: {e}")
            return
        action = payload.get("action")
        modifier = payload.get("modifier", False)
        if "layer" in payload:
            current_active_layer = int(payload["layer"])

        # ----------------------------------------------------------------------
        # 0. KEY 9 SHORT TAP: 3-WAY MODE TOGGLE (AUTOMODE / MANUAL / DEBUG)
        # ----------------------------------------------------------------------
        if action == "mode_change":
            new_mode = payload.get("mode", "automode")
            is_auto = (new_mode == "automode")
            synced_app_rules["auto_app_mode"] = is_auto
            synced_app_rules["device_mode"] = new_mode
            force_app_reeval = True
            logger.info(f">>> Mode Changed: {new_mode.upper()} (Auto-App={is_auto})")
            return

        elif action == "auto_app_mode":
            active = bool(payload.get("enabled", payload.get("active", False)))
            synced_app_rules["auto_app_mode"] = active
            force_app_reeval = True
            logger.info(f">>> Key 9 Mode Toggle: Auto-App Mode = {'ON' if active else 'MANUAL'}")
            return

        elif action == "top_mod_hold":
            slot = int(payload.get("slot", 1))
            hold_top_modifier(slot)
            return

        elif action == "top_mod_release":
            slot = int(payload.get("slot", 1))
            release_top_modifier(slot)
            return

        # ----------------------------------------------------------------------
        # 1. KEY 13 ACTIONS: DISCORD MIC MUTE & AUDIO MODIFIER
        # ----------------------------------------------------------------------
        if action == "mic_mute_toggle":
            logger.info(">>> Key 13 short tap: Toggle Discord Mic Mute")
            toggle_microphone_mute()

        # 13 + HW Encoder (ID 1): Master Output Control
        elif action == "audio_master_volume":
            delta = payload.get("delta", 0)
            adjust_master_volume(delta)

        elif action == "audio_master_reset":
            reset_master_volume(payload.get("volume", 80))

        # 13 + Encoder 1 (Code ID 2): Discord Volume Control
        elif action == "audio_discord_volume":
            delta = payload.get("delta", 0)
            adjust_discord_volume(delta)

        elif action == "audio_discord_reset":
            reset_discord_volume(payload.get("volume", 80))

        # 13 + Encoder 2 (Code ID 3): App Target Toggle & App Volume
        elif action == "audio_app_toggle":
            cycle_app_target()

        elif action == "audio_app_volume":
            delta = payload.get("delta", 0)
            adjust_app_volume(delta)

        # 13 + Matrix Keys 7 & 8: Default Audio Output Switcher (Headphones vs Speakers)
        elif action == "audio_device_select":
            target = payload.get("target")
            logger.info(f">>> Key 13 Audio Modifier + Key: Output Switch -> {target}")
            switch_default_playback_device(target)

        elif action in ("layer_change", "layer_reset"):
            universal_app_overlay_active = False
            if current_active_layer == 2 and is_in_voice_call():
                publish_voice_grid(include_layer=2, fast=True)
            return

        # ----------------------------------------------------------------------
        # DISCORD VOICE CALL MEMBER CONTROLS (AUDIO MODIFIER + 3x3 MATRIX)
        # ----------------------------------------------------------------------
        elif action == "audio_modifier":
            active = payload.get("active", False)
            is_audio_mod_active = active
            logger.info(f">>> Key 13 Audio Modifier state: {'HELD' if active else 'RELEASED'}")
            if active:
                if discord_rpc_client and discord_rpc_client.is_authenticated:
                    discord_rpc_client.refresh_voice_channel()
                if is_in_voice_call():
                    voice_page = 0
                    voice_grid_displayed = True
                    publish_voice_grid()
                else:
                    if mqtt_client and mqtt_client.is_connected():
                        mqtt_client.publish(TOPIC_DISPLAY, json.dumps({"in_call": False}), retain=False)
            else:
                # Modifier released -> restore active layer's grid & icons if voice grid was displayed on a non-Discord layer
                if voice_grid_displayed:
                    voice_grid_displayed = False
                    if current_active_layer == 2 and is_in_voice_call():
                        publish_voice_grid()
                    else:
                        apply_layer_via_hub(current_active_layer, force_static=True)

        elif action == "discord_page_down":
            members = get_active_call_members()
            if members and len(members) > 9:
                page_size = 7
                total_pages = (len(members) + page_size - 1) // page_size
                voice_page = max(0, voice_page - 1)
                publish_voice_grid(page_changed=True)
                publish_popup(f"PAGE {voice_page + 1}/{total_pages}")

        elif action == "discord_page_up":
            members = get_active_call_members()
            if members and len(members) > 9:
                page_size = 7
                total_pages = (len(members) + page_size - 1) // page_size
                voice_page = min(total_pages - 1, voice_page + 1)
                publish_voice_grid(page_changed=True)
                publish_popup(f"PAGE {voice_page + 1}/{total_pages}")

        elif action == "discord_user_volume":
            user_idx = int(payload.get("user_index", 1))  # 1 to 9
            delta = int(payload.get("delta", 0))
            members = get_active_call_members()
            if len(members) <= 9:
                m_idx = user_idx - 1
            else:
                m_idx = (voice_page * 7) + (user_idx - 1)
            adjust_selected_voice_member_volume(delta, explicit_idx=m_idx)

        # ----------------------------------------------------------------------
        # 2. KEY 5 ACTIONS: ROOM LIGHTING & PRESETS
        # ----------------------------------------------------------------------
        elif action == "light_toggle":
            logger.info(">>> Key 5 short tap: Room Light Toggle")
            # Handled directly by Home Assistant automation

        elif action == "preset_recall":
            logger.info(f">>> Modifier + Preset Recall: Preset {payload.get('index')}")

        elif action == "preset_save":
            logger.info(f">>> Modifier + Preset Save: Preset {payload.get('index')}")

        elif action == "wakeonlan":
            mac = payload.get("mac", "d4:93:90:3b:f0:89")
            logger.info(f">>> Wake-on-LAN triggered for {mac}")
            send_wake_on_lan(mac)

        # ----------------------------------------------------------------------
        # 3. UNIVERSAL LAYER BUTTONS, RADIAL PIE MENUS & ENCODERS
        # ----------------------------------------------------------------------
        elif action == "macro":
            layer = int(payload.get("layer", current_active_layer))
            idx = int(payload.get("index", 0))
            lbl = payload.get("label", "")
            # 1. Unsupported App Universal Mode: Execute universal shortcut or show app name
            if universal_app_overlay_active:
                if handle_universal_app_key_tap(idx):
                    return

            # 2. Discord Voice Call Member Grid (ONLY on Layer 2 or holding Audio Mod)
            if (layer == 2 or is_audio_mod_active) and is_in_voice_call():
                if handle_layer2_voice_key_tap(idx):
                    return

            if layer == 1 and idx == 9:
                cell = get_synced_cell_config(1, 9)
                if not cell or cell.get("action") in ("", "wakeonlan", "macro_9"):
                    send_wake_on_lan(payload.get("mac", "d4:93:90:3b:f0:89"))
                    return
            execute_autocad_action(layer, idx, lbl)

        elif action == "macro_hold":
            layer = int(payload.get("layer", current_active_layer))
            idx = int(payload.get("index", 0))
            if (layer == 2 or is_audio_mod_active) and is_in_voice_call():
                handle_layer2_voice_key_hold(idx)
                return
            menu_data = get_radial_menu_for_cell(layer, idx)
            if menu_data and radial_menu_overlay:
                title, slices = menu_data
                logger.info(f">>> [Radial Menu OPEN] Layer {layer} Key {idx} ({title})")
                radial_menu_overlay.show_menu(title, slices)

        elif action == "macro_release":
            if radial_menu_overlay and radial_menu_overlay.is_visible:
                logger.info(f">>> [Radial Menu RELEASE] Layer {payload.get('layer')} Key {payload.get('index')}")
                radial_menu_overlay.release_hold()

        elif action == "encoder_scroll":
            layer = int(payload.get("layer", current_active_layer))
            enc_id = payload.get("id")
            delta = int(payload.get("delta", 0))
            if universal_app_overlay_active:
                if enc_id == 1:
                    adjust_master_volume(delta)
                elif enc_id == 2:
                    if delta > 0:
                        send_ctrl_combo("Y")
                    elif delta < 0:
                        send_ctrl_combo("Z")
                elif enc_id == 3:
                    send_mouse_wheel(delta)
            elif layer == 2:
                # Right Encoder (1): System Master Volume
                # Bottom-Left Encoder (2): Selected (>) User Volume (or Discord Volume if not in call)
                # Top-Left Encoder (3): Discord Master Volume
                if enc_id == 1:
                    adjust_master_volume(delta)
                elif enc_id == 2:
                    if is_in_voice_call():
                        adjust_selected_voice_member_volume(delta)
                    else:
                        adjust_discord_volume(delta)
                elif enc_id == 3:
                    adjust_discord_volume(delta)
            elif layer in AUTOCAD_LAYER_MAP or layer >= 5:
                if enc_id == 2:
                    # Bottom Left Encoder: Undo (CCW) / Redo (CW)
                    if delta > 0:
                        logger.info(">>> [CAD Enc 2] Redo (Ctrl+Y)")
                        send_ctrl_combo("Y")
                    elif delta < 0:
                        logger.info(">>> [CAD Enc 2] Undo (Ctrl+Z)")
                        send_ctrl_combo("Z")
                elif enc_id in (1, 3):
                    # Top Left / Main Encoder: Zoom In / Out (Mouse Wheel)
                    logger.info(f">>> [CAD Enc {enc_id}] Zoom Wheel (delta={delta:+d})")
                    send_mouse_wheel(delta)

        elif action == "encoder_click":
            layer = int(payload.get("layer", current_active_layer))
            enc_id = payload.get("id")
            if universal_app_overlay_active:
                if enc_id == 1:
                    reset_master_volume(80)
                elif enc_id == 2:
                    send_vk_tap(VK_MAP["SPACE"])
                elif enc_id == 3:
                    send_vk_tap(VK_MAP["ESC"])
            elif layer == 2:
                # Right Encoder Click (1): Reset System Master Volume to 80%
                # Bottom-Left Encoder Click (2): Reset Selected (>) User Volume to 80%
                # Top-Left Encoder Click (3): Reset Discord Master Volume to 80%
                if enc_id == 1:
                    reset_master_volume(80)
                elif enc_id == 2:
                    if is_in_voice_call():
                        reset_selected_voice_member_volume(80)
                    else:
                        reset_discord_volume(80)
                elif enc_id == 3:
                    reset_discord_volume(80)
            elif layer in AUTOCAD_LAYER_MAP or layer >= 5:
                if enc_id == 2:
                    # Bottom Left Encoder Click: Space (Repeat Last Command)
                    logger.info(">>> [CAD Enc 2 Click] Repeat Last Command (SPACE)")
                    send_vk_tap(VK_MAP["SPACE"])
                elif enc_id == 3 and modifier:
                    # Top Left Encoder Click with Modifier: ESC (Cancel)
                    logger.info(">>> [CAD Enc 3 Mod+Click] Cancel (ESC)")
                    send_vk_tap(VK_MAP["ESC"])

        # ----------------------------------------------------------------------
        # 4. LAYER 4 POWER CONTROLS: SHUTDOWN & RESTART TIMERS
        # ----------------------------------------------------------------------
        elif action == "shutdown_timer_start":
            duration = payload.get("duration", 20)
            logger.warning(f">>> Layer 4 ACT 9: Windows Shutdown timer started ({duration}s)")
            os.system(f'shutdown /s /t {duration} /c "MacroPad: Shutdown in {duration}s. Tap ACT 9 to cancel."')

        elif action == "restart_timer_start":
            duration = payload.get("duration", 20)
            logger.warning(f">>> Layer 4 ACT 9: Windows Restart timer started ({duration}s)")
            os.system(f'shutdown /r /t {duration} /c "MacroPad: Restart in {duration}s. Tap ACT 9 to cancel."')

        elif action == "power_timer_cancel":
            logger.info(">>> Layer 4 ACT 9: Windows Power Timer CANCELLED")
            os.system("shutdown /a")

        elif action == "pc_shutdown":
            logger.warning(">>> Layer 4 ACT 9: Executing immediate Windows Shutdown...")
            os.system("shutdown /s /t 0 /f")

        elif action == "pc_restart":
            logger.warning(">>> Layer 4 ACT 9: Executing immediate Windows Restart...")
            os.system("shutdown /r /t 0 /f")

    except Exception as e:
        logger.error(f"Error handling message: {e}")

# ==============================================================================
# FOREGROUND WINDOWS APP WATCHER (KEY 9 DYNAMIC AUTO-APP SWITCHER)
# ==============================================================================
IGNORED_TRANSIENT_EXES = {
    "pythonw.exe", "python.exe", "searchhost.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "applicationframehost.exe", "lockapp.exe"
}

FRIENDLY_APP_NAMES = {
    "chrome.exe": "CHROME",
    "msedge.exe": "EDGE",
    "firefox.exe": "FIREFOX",
    "brave.exe": "BRAVE",
    "opera.exe": "OPERA",
    "explorer.exe": "FILES",
    "code.exe": "VSCODE",
    "antigravity.exe": "AGY IDE",
    "cursor.exe": "CURSOR",
    "spotify.exe": "SPOTIFY",
    "notepad.exe": "NOTEPAD",
    "windowsterminal.exe": "TERM",
    "powershell.exe": "PWSH",
    "cmd.exe": "CMD",
    "vlc.exe": "VLC",
    "obs64.exe": "OBS",
    "steam.exe": "STEAM",
    "taskmgr.exe": "TASKMGR",
    "excel.exe": "EXCEL",
    "winword.exe": "WORD",
    "powerpnt.exe": "PPT",
}

UNIVERSAL_APP_CELLS = [
    {"index": 1, "label": "APP",   "icon": "",           "hotkey": ""},
    {"index": 2, "label": "COPY",  "icon": "cad_copy",   "hotkey": "CTRL+C"},
    {"index": 3, "label": "PASTE", "icon": "cad_offset", "hotkey": "CTRL+V"},
    {"index": 4, "label": "CUT",   "icon": "cad_trim",   "hotkey": "CTRL+X"},
    {"index": 5, "label": "UNDO",  "icon": "cad_rotate", "hotkey": "CTRL+Z"},
    {"index": 6, "label": "REDO",  "icon": "next",       "hotkey": "CTRL+Y"},
    {"index": 7, "label": "FIND",  "icon": "cad_zoom",   "hotkey": "CTRL+F"},
    {"index": 8, "label": "SAVE",  "icon": "cad_save",   "hotkey": "CTRL+S"},
    {"index": 9, "label": "ESC",   "icon": "cad_esc",    "hotkey": "ESC"},
]

def get_clean_app_name(exe_name: str) -> str:
    exe_l = (exe_name or "").lower().strip()
    if exe_l in FRIENDLY_APP_NAMES:
        return FRIENDLY_APP_NAMES[exe_l]
    base = exe_l[:-4] if exe_l.endswith(".exe") else exe_l
    clean = "".join(c for c in base if c.isalnum() or c in " -_").upper().strip()
    return clean[:6] if clean else "APP"

def publish_universal_app_grid(exe_name: str):
    """Pushes a Universal App grid to the MacroPad showing the App Name in Cell 1 + 8 universal actions."""
    global universal_app_overlay_active, universal_app_name
    app_short = get_clean_app_name(exe_name)
    universal_app_name = app_short
    universal_app_overlay_active = True

    labels = [""] * 9
    icons = [""] * 9
    for i, c in enumerate(UNIVERSAL_APP_CELLS):
        if i == 0:
            labels[0] = f"{app_short[:6]}\n[APP]"
            icons[0] = ""
        else:
            labels[i] = c["label"]
            icon_key = c["icon"]
            if icon_key and icon_key in synced_icons_library:
                icons[i] = synced_icons_library[icon_key].get("hex", "")
            else:
                icons[i] = ""

    payload = {
        "labels": labels,
        "icons": icons,
        "icon_w": 24,
        "icon_h": 24,
        "hold_mask": 0,
        "in_call": False,
        "auto_app_mode": True,
        "fast": False
    }
    if mqtt_client and mqtt_client.is_connected():
        mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload), retain=False)
        logger.info(f"[Auto-App Universal] Displayed Universal Controls for unsupported app '{exe_name}' ({app_short})")

def handle_universal_app_key_tap(idx: int) -> bool:
    """Executes universal app actions when an unsupported app is active in Auto-App Mode."""
    if idx < 1 or idx > 9:
        return False
    if idx == 1:
        publish_popup(f"APP: {universal_app_name}\nUNIVERSAL")
        return True
    cell = UNIVERSAL_APP_CELLS[idx - 1]
    hk = cell.get("hotkey", "")
    if hk:
        logger.info(f">>> [Universal App Action] {universal_app_name} Key {idx} ({cell['label']}) -> {hk}")
        send_hotkey_combo(hk)
        return True
    return False

def match_app_rule(exe_name: str, win_title: str) -> Optional[dict]:
    """Checks synced_app_rules for a rule matching exe_name or win_title (supports pipe-delimited patterns)."""
    if not exe_name and not win_title:
        return None
    exe_l = exe_name.lower()
    title_l = win_title.lower()
    rules_list = synced_app_rules.get("rules") or synced_app_rules.get("app_rules") or []
    for rule in rules_list:
        if rule.get("enabled") is False:
            continue
        raw_pat = (rule.get("exe_match") or rule.get("match") or "").strip().lower()
        title_pat = (rule.get("title_match") or "").strip().lower()
        if raw_pat:
            parts = [p.strip() for p in raw_pat.replace(",", "|").split("|") if p.strip()]
            for p in parts:
                if p in exe_l or p in title_l:
                    return rule
        if title_pat:
            t_parts = [p.strip() for p in title_pat.replace(",", "|").split("|") if p.strip()]
            for p in t_parts:
                if p in title_l:
                    return rule
    return None

def apply_layer_via_hub(target_layer: int, force_static: bool = False):
    """Requests the Raspberry Pi Unified Hub to push target_layer to the MacroPad.
    If target_layer == 2 (Discord) and user is in a voice call (or Demo Call), pushes the dynamic call member grid."""
    global current_active_layer, universal_app_overlay_active
    current_active_layer = target_layer
    universal_app_overlay_active = False
    if target_layer == 2 and not force_static:
        if discord_rpc_client and discord_rpc_client.is_authenticated:
            discord_rpc_client.refresh_voice_channel()
        if is_in_voice_call():
            publish_voice_grid(include_layer=2, fast=False)
            logger.info("[Auto-App Switch] Switched MacroPad to Layer 2 (Discord Live Voice Call Grid)")
            return
    try:
        import urllib.request
        req = urllib.request.Request(
            f"http://{MQTT_BROKER}:5000/api/layers/{target_layer}/apply",
            data=b'{}',
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req, timeout=1.5)
        logger.info(f"[Auto-App Switch] Switched MacroPad to Layer {target_layer}")
    except Exception as e:
        logger.warning(f"[Auto-App Switch] Failed to switch to Layer {target_layer}: {e}")

def start_window_watcher():
    """Polls the active Windows foreground application every 250ms, publishes live telemetry
    to the Unified Web Dashboard, and auto-switches MacroPad layers when Auto-App Mode is active."""
    global force_app_reeval, current_active_layer, universal_app_overlay_active
    last_exe = ""
    last_title = ""
    last_matched_name = ""
    last_auto_target_layer = None
    last_universal_exe = ""
    last_telemetry_ts = 0.0
    last_discord_poll_ts = 0.0

    while True:
        try:
            # Skip if radial overlay is currently open so we don't treat the overlay as an app change
            if radial_menu_overlay and radial_menu_overlay.is_visible:
                time.sleep(0.25)
                continue

            exe_name, win_title = get_foreground_window_info()
            if exe_name in IGNORED_TRANSIENT_EXES or not exe_name:
                time.sleep(0.25)
                continue

            now = time.time()
            # Periodically refresh Discord voice call members when Discord is focused or Layer 2 is active
            if (exe_name == "discord.exe" or current_active_layer == 2) and (now - last_discord_poll_ts > 3.0):
                last_discord_poll_ts = now
                if discord_rpc_client and discord_rpc_client.is_authenticated:
                    discord_rpc_client.refresh_voice_channel()

            rule = match_app_rule(exe_name, win_title)
            t_layer = int(rule.get("target_layer") or rule.get("layer") or 1) if rule else None
            app_short = get_clean_app_name(exe_name)
            if rule:
                matched_name = f"{rule.get('name')} -> L{t_layer}"
            elif synced_app_rules.get("auto_app_mode", False):
                matched_name = f"{app_short} (Universal)"
            else:
                matched_name = ""

            changed = (exe_name != last_exe) or (win_title != last_title) or (matched_name != last_matched_name) or force_app_reeval

            if changed or (now - last_telemetry_ts > 8.0):
                last_exe = exe_name
                last_title = win_title
                last_matched_name = matched_name
                last_telemetry_ts = now
                if mqtt_client and mqtt_client.is_connected():
                    mqtt_client.publish(TOPIC_PC_TELEMETRY, json.dumps({
                        "exe": exe_name,
                        "title": win_title[:80],
                        "matched_rule": matched_name
                    }))

            # Auto-switch layer if Auto-App Mode (Key 9) is enabled
            if synced_app_rules.get("auto_app_mode", False):
                if rule and t_layer:
                    last_universal_exe = ""
                    if force_app_reeval or universal_app_overlay_active or (t_layer != current_active_layer and t_layer != last_auto_target_layer):
                        last_auto_target_layer = t_layer
                        force_app_reeval = False
                        apply_layer_via_hub(t_layer)
                else:
                    # Unsupported / Untracked App: Display App Name + Universal Functions!
                    last_auto_target_layer = None
                    if force_app_reeval or not universal_app_overlay_active or (exe_name != last_universal_exe):
                        last_universal_exe = exe_name
                        force_app_reeval = False
                        publish_universal_app_grid(exe_name)
            else:
                if universal_app_overlay_active:
                    universal_app_overlay_active = False
                    last_universal_exe = ""
                    apply_layer_via_hub(current_active_layer, force_static=True)
                last_auto_target_layer = None
                force_app_reeval = False

        except Exception as e:
            logger.debug(f"Window watcher error: {e}")

        time.sleep(0.25)

def start_discord_rpc():
    """Background worker that connects to Discord Voice RPC and maintains live sync"""
    global discord_rpc_client
    if not DISCORD_CLIENT_ID or DISCORD_CLIENT_ID == "YOUR_DISCORD_CLIENT_ID":
        logger.info("Discord RPC credentials not configured in .env. Using Ctrl+Shift+] hotkey fallback.")
        return

    logger.info("Starting Discord Voice RPC client...")
    discord_rpc_client = DiscordVoiceRPC(
        client_id=DISCORD_CLIENT_ID,
        client_secret=DISCORD_CLIENT_SECRET,
        on_mute_change=on_discord_rpc_mute_change,
        on_voice_channel_update=on_voice_channel_update
    )

    while True:
        try:
            if not discord_rpc_client.is_connected or not discord_rpc_client.is_authenticated:
                success = discord_rpc_client.connect()
                if success:
                    logger.info("Discord Voice RPC client connected and authenticated!")
                else:
                    logger.warning("Discord Voice RPC connection attempt failed. Retrying in 10s...")
            else:
                time.sleep(2)
        except Exception as e:
            logger.warning(f"Discord RPC background monitor error: {e}. Retrying in 10s...")
        time.sleep(10)

# ==============================================================================
# SYSTEM TRAY ICON (PYSTRAY)
# ==============================================================================
tray_icon = None

def create_tray_image(muted: bool = False):
    """Generates a crisp 32x32 RGBA icon for the Windows system tray."""
    img = Image.new('RGBA', (32, 32), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Background rounded square
    bg_color = (25, 28, 36, 255)
    border_color = (255, 60, 80, 255) if muted else (0, 230, 255, 255)
    d.rounded_rectangle([(1, 1), (30, 30)], radius=6, fill=bg_color, outline=border_color, width=2)
    
    # Status indicator circle
    dot_color = (255, 60, 80, 255) if muted else (0, 230, 255, 255)
    d.ellipse([(9, 9), (22, 22)], fill=dot_color)
    
    # Inner bright dot
    inner_dot = (255, 200, 210, 255) if muted else (210, 255, 255, 255)
    d.ellipse([(13, 13), (18, 18)], fill=inner_dot)
    return img

def on_tray_open_dashboard(icon, item):
    webbrowser.open("http://192.168.1.62:5000")

def on_tray_toggle_mute(icon, item):
    toggle_microphone_mute()

def on_tray_restart(icon, item):
    logger.info("Restarting MacroPad PC Bridge via Tray Icon...")
    if icon:
        try:
            icon.stop()
        except Exception:
            pass
    if mqtt_client:
        try:
            mqtt_client.disconnect()
        except Exception:
            pass
    time.sleep(0.3)
    # Relaunch the process without console window
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__)],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )
    os._exit(0)

def on_tray_exit(icon, item):
    logger.info("Quitting MacroPad PC Bridge via Tray Icon...")
    if icon:
        try:
            icon.stop()
        except Exception:
            pass
    if mqtt_client:
        try:
            mqtt_client.disconnect()
        except Exception:
            pass
    os._exit(0)

def update_tray_icon():
    global tray_icon
    if tray_icon and TRAY_AVAILABLE:
        try:
            tray_icon.icon = create_tray_image(is_discord_muted)
            tray_icon.title = f"MacroPad Bridge ({'MUTED' if is_discord_muted else 'LIVE'})"
        except Exception:
            pass

def setup_tray_icon():
    global tray_icon
    if not TRAY_AVAILABLE:
        return None
    menu = pystray.Menu(
        pystray.MenuItem("⚡ MacroPad Audio Bridge", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🌐 Open Web Dashboard", on_tray_open_dashboard),
        pystray.MenuItem(lambda text: "🎤 Mic: MUTED (Click to Unmute)" if is_discord_muted else "🎤 Mic: LIVE (Click to Mute)", on_tray_toggle_mute),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🔄 Restart Bridge", on_tray_restart),
        pystray.MenuItem("❌ Quit", on_tray_exit)
    )
    tray_icon = pystray.Icon("MacroPadBridge", create_tray_image(is_discord_muted), "MacroPad Audio Bridge", menu)
    return tray_icon

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def main():
    global mqtt_client, tray_icon, radial_menu_overlay
    logger.info("==================================================================")
    logger.info("  MacroPad Windows PC Audio, CAD & Auto-App Bridge Live")
    logger.info("==================================================================")

    # Initial sync of layers & auto-app rules from Unified Hub
    sync_config_from_hub()

    # Start 3Dconnexion-style On-Screen Radial Menu Overlay
    try:
        radial_menu_overlay = RadialMenuOverlay(on_radial_slice_selected)
        logger.info("On-Screen Radial Menu Overlay initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Radial Menu Overlay: {e}")

    # Start Foreground Windows App Watcher (Key 9 Auto-App Switcher + Live Dashboard Telemetry)
    watcher_thread = threading.Thread(target=start_window_watcher, daemon=True)
    watcher_thread.start()

    # Start Discord Voice RPC background worker thread
    rpc_thread = threading.Thread(target=start_discord_rpc, daemon=True)
    rpc_thread.start()

    # Start background listener for physical keyboard Ctrl+Shift+]
    try:
        hotkeys = keyboard.GlobalHotKeys({
            '<ctrl>+<shift>+]': on_keyboard_hotkey
        })
        hotkeys.daemon = True
        hotkeys.start()
        logger.info("Listening for physical keyboard [Ctrl+Shift+] hotkey...")
    except Exception as e:
        logger.warning(f"Could not start physical keyboard listener: {e}")

    # Launch System Tray Icon detached
    if TRAY_AVAILABLE:
        tray_icon = setup_tray_icon()
        if tray_icon:
            try:
                tray_icon.run_detached()
                logger.info("System Tray Icon active and detached.")
            except Exception as e:
                logger.error(f"Failed to start system tray icon: {e}")

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            break
        except Exception as e:
            logger.warning(f"Could not connect to MQTT broker ({e}). Retrying in 5 seconds...")
            time.sleep(5)

    # Keep process alive with MQTT message processing loop
    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user.")
        if tray_icon:
            tray_icon.stop()

if __name__ == "__main__":
    main()
