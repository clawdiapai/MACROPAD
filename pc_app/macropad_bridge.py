import ctypes
import json
import logging
import time
from typing import Optional, List
import paho.mqtt.client as mqtt

# PYCAW AUDIO CONTROLLER
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    PYCAW_AVAILABLE = True
except Exception as e:
    PYCAW_AVAILABLE = False
    print(f"Warning: pycaw audio initialization failed: {e}")

# TUYA DEVICE CONTROLLER (OPTIONAL)
try:
    import tinytuya
    TINAP_AVAILABLE = True
except Exception:
    TINAP_AVAILABLE = False

# ==============================================================================
# CONFIGURATION
# ==============================================================================
MQTT_BROKER = "192.168.1.62"
MQTT_PORT = 1883
TOPIC_INPUT = "macropad/input"
TOPIC_DISPLAY = "macropad/display"

# TUYA DEVICE CONFIGURATION (IF DIRECT TUYA CONTROL IS USED)
TUYA_DEVICE_ID = "YOUR_TUYA_DEVICE_ID"
TUYA_IP = "YOUR_TUYA_DEVICE_IP"
TUYA_LOCAL_KEY = "YOUR_TUYA_LOCAL_KEY"
TUYA_VERSION = 3.3

# DISCORD MUTE HOTKEY (DEFAULT: CTRL+SHIFT+M)
# VK codes: VK_CONTROL = 0x11, VK_SHIFT = 0x10, VK_M = 0x4D
DISCORD_HOTKEY_ENABLED = True
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_M = 0x4D
KEYEVENTF_KEYUP = 0x0002

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
        mqtt_client.publish(TOPIC_DISPLAY, json.dumps(payload))

def trigger_discord_mute_hotkey():
    """Simulates pressing Ctrl+Shift+M (Discord's default toggle mute hotkey)"""
    try:
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_M, 0, 0, 0)
        time.sleep(0.02)
        ctypes.windll.user32.keybd_event(VK_M, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        logger.info("Sent Discord toggle mute hotkey (Ctrl+Shift+M)")
    except Exception as e:
        logger.error(f"Failed to send Discord hotkey: {e}")

def toggle_microphone_mute():
    """Toggles default recording microphone mute state and Discord hotkey"""
    if not PYCAW_AVAILABLE:
        logger.warning("pycaw is not available")
        return

    try:
        mic = AudioUtilities.GetMicrophone()
        if not mic:
            logger.warning("No default microphone found")
            return
        
        vol_interface = cast(mic.Activate(IAudioEndpointVolume._iid_, 7, None), POINTER(IAudioEndpointVolume))
        current_mute = vol_interface.GetMute()
        new_mute = not current_mute
        vol_interface.SetMute(new_mute, None)

        if DISCORD_HOTKEY_ENABLED:
            trigger_discord_mute_hotkey()

        status_str = "MIC MUTED" if new_mute else "MIC LIVE"
        logger.info(f">>> Microphone Mute: {status_str}")
        publish_popup(status_str)
        publish_mic_state(new_mute)
    except Exception as e:
        logger.error(f"Error toggling microphone: {e}")

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

# ==============================================================================
# MQTT HANDLERS
# ==============================================================================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}")
        client.subscribe(TOPIC_INPUT)
        logger.info(f"Subscribed to topic: {TOPIC_INPUT}")
    else:
        logger.error(f"MQTT connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
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

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def main():
    global mqtt_client
    logger.info("==================================================================")
    logger.info("  MacroPad Windows PC Audio & Discord Controller Bridge Live")
    logger.info("==================================================================")

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
