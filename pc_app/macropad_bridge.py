import ctypes
import json
import logging
import os
import time
from typing import Optional, List
import threading
import paho.mqtt.client as mqtt
from pynput import keyboard

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
        mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload), retain=True)

is_discord_muted = False
is_synthetic_send = False

# ==============================================================================
# DISCORD VOICE CALL MEMBERS & GRID MANAGEMENT
# ==============================================================================
is_audio_mod_active = False
voice_page = 0
active_voice_members = []
normal_grid_labels = ["ACT 1", "ACT 2", "ACT 3", "ACT 4", "ACT 5", "ACT 6", "ACT 7", "ACT 8", "ACT 9"]

def build_voice_labels(members: list, page: int):
    """Formats voice call members into 3x3 matrix labels with pagination"""
    total = len(members)
    labels = [""] * 9
    if total == 0:
        return labels, 1

    if total <= 9:
        total_pages = 1
        for i in range(min(9, total)):
            m = members[i]
            prefix = "*" if m.get("speaking") else ""
            vol = m.get("volume", 100)
            name = m.get("name", "User")
            if m.get("is_self"):
                labels[i] = f"{name}\nYOU"
            else:
                labels[i] = f"{prefix}{name}\n{vol}%"
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
                m = page_members[i]
                prefix = "*" if m.get("speaking") else ""
                vol = m.get("volume", 100)
                name = m.get("name", "User")
                if m.get("is_self"):
                    labels[i] = f"{name}\nYOU"
                else:
                    labels[i] = f"{prefix}{name}\n{vol}%"
            else:
                labels[i] = ""
        # Last 2 buttons for page down / page up
        labels[7] = f"P{page+1}/{total_pages} <"
        labels[8] = f"P{page+1}/{total_pages} >"
        return labels, total_pages

def publish_voice_grid(page_changed: bool = False):
    """Publishes current voice call members to the 3x3 matrix on the MacroPad"""
    global active_voice_members, voice_page
    if not discord_rpc_client or not discord_rpc_client.is_authenticated:
        return
    channel = discord_rpc_client.voice_channel
    if not channel or not channel.get("members"):
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.publish(TOPIC_DISPLAY, json.dumps({"in_call": False}), retain=True)
        return

    active_voice_members = channel["members"]
    labels, total_pages = build_voice_labels(active_voice_members, voice_page)
    payload = {
        "labels": labels,
        "in_call": True,
        "fast": True
    }
    if mqtt_client and mqtt_client.is_connected():
        mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload), retain=True)
        logger.info(f"Published voice member grid ({len(active_voice_members)} members, page {voice_page + 1}/{total_pages})")

def on_voice_channel_update(voice_channel):
    """Callback fired when voice call membership or status changes"""
    global is_audio_mod_active
    ch_name = voice_channel.get('name') if voice_channel else 'No call'
    logger.info(f"[Discord Voice Event] Channel update: {ch_name}")
    if is_audio_mod_active:
        publish_voice_grid()

def on_discord_rpc_mute_change(is_muted: bool):
    """Callback fired in real time whenever Discord voice settings change (from Discord app, hotkeys, or RPC)"""
    global is_discord_muted
    is_discord_muted = is_muted
    status_str = "MIC MUTED" if is_discord_muted else "MIC LIVE"
    logger.info(f"[Discord RPC Event] Live Mute State: {status_str}")
    publish_popup(status_str)
    publish_mic_state(is_discord_muted)

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
    publish_popup(status_str)
    publish_mic_state(is_discord_muted)

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
        return None

# ==============================================================================
# MQTT HANDLERS
# ==============================================================================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}")
        client.subscribe([(TOPIC_INPUT, 0), (TOPIC_STATUS, 0)])
        logger.info(f"Subscribed to topics: {TOPIC_INPUT}, {TOPIC_STATUS}")
        # Sync current mic status to MacroPad on connect (retained so device gets it whenever it powers on)
        publish_mic_state(is_discord_muted)
    else:
        logger.error(f"MQTT connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        # MacroPad status / heartbeat topic (fires when device powers on, reconnects, or wakes up)
        if msg.topic == TOPIC_STATUS:
            logger.info("MacroPad device presence detected -> syncing mic mute state")
            publish_mic_state(is_discord_muted)
            return

        payload = json.loads(msg.payload.decode('utf-8'))
        action = payload.get("action")
        modifier = payload.get("modifier", False)

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
                    channel = discord_rpc_client.voice_channel
                    if channel and channel.get("members"):
                        voice_page = 0
                        publish_voice_grid()
                    else:
                        if mqtt_client and mqtt_client.is_connected():
                            mqtt_client.publish(TOPIC_DISPLAY, json.dumps({"in_call": False}), retain=True)
            else:
                # Modifier released -> restore normal layer's grid labels
                if mqtt_client and mqtt_client.is_connected():
                    mqtt_client.publish(TOPIC_DISPLAY, json.dumps({
                        "labels": normal_grid_labels,
                        "in_call": False,
                        "fast": True
                    }), retain=True)

        elif action == "discord_page_down":
            if active_voice_members and len(active_voice_members) > 9:
                page_size = 7
                total_pages = (len(active_voice_members) + page_size - 1) // page_size
                voice_page = max(0, voice_page - 1)
                publish_voice_grid(page_changed=True)
                publish_popup(f"PAGE {voice_page + 1}/{total_pages}")

        elif action == "discord_page_up":
            if active_voice_members and len(active_voice_members) > 9:
                page_size = 7
                total_pages = (len(active_voice_members) + page_size - 1) // page_size
                voice_page = min(total_pages - 1, voice_page + 1)
                publish_voice_grid(page_changed=True)
                publish_popup(f"PAGE {voice_page + 1}/{total_pages}")

        elif action == "discord_user_volume":
            user_idx = payload.get("user_index", 1)  # 1 to 9
            delta = payload.get("delta", 0)
            if len(active_voice_members) <= 9:
                m_idx = user_idx - 1
            else:
                m_idx = (voice_page * 7) + (user_idx - 1)
            
            if 0 <= m_idx < len(active_voice_members):
                member = active_voice_members[m_idx]
                uid = member["id"]
                curr_vol = member.get("volume", 100)
                step = 5 * delta # 5% per encoder tick
                new_vol = max(0, min(200, curr_vol + step))
                member["volume"] = new_vol
                if discord_rpc_client and discord_rpc_client.is_authenticated:
                    discord_rpc_client.set_user_volume(uid, new_vol)
                logger.info(f">>> User {member['name']} Volume -> {new_vol}% (delta={delta})")
                publish_popup(f"{member['name'].upper()}:\n{new_vol}%")
                publish_voice_grid()

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

    except Exception as e:
        logger.error(f"Error handling message: {e}")

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
# MAIN ENTRY POINT
# ==============================================================================
def main():
    global mqtt_client
    logger.info("==================================================================")
    logger.info("  MacroPad Windows PC Audio & Discord Controller Bridge Live")
    logger.info("==================================================================")

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

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        logger.error(f"Could not connect to MQTT broker: {e}")
        return

    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user.")

if __name__ == "__main__":
    main()
