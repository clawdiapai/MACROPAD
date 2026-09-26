import ctypes
from ctypes import wintypes
import json
import logging
import os
import struct
import threading
import time
import uuid
from typing import Callable, Optional, List, Dict
import requests

logger = logging.getLogger("DiscordRPC")

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "discord_token.json")
RPC_PIPE_PATTERN = r"\\.\pipe\discord-ipc-{}"

k32 = ctypes.windll.kernel32
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = -1

class DiscordVoiceRPC:
    r"""
    Native Win32 Discord IPC Client for real-time voice settings (Mute/Deafen state)
    and Voice Channel Call Member control (User Volume, Paging, Member List).
    Uses \\.\pipe\discord-ipc-0 with Win32 API and non-blocking PeekNamedPipe polling.
    """
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        on_mute_change: Optional[Callable[[bool], None]] = None,
        on_voice_channel_update: Optional[Callable[[Optional[dict]], None]] = None
    ):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.on_mute_change = on_mute_change
        self.on_voice_channel_update = on_voice_channel_update
        
        self.handle = INVALID_HANDLE_VALUE
        self.access_token: Optional[str] = None
        self.current_user_id: Optional[str] = None
        self.is_connected = False
        self.is_authenticated = False
        self.is_muted = False
        self.voice_channel: Optional[dict] = None
        
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
        self._send_lock = threading.Lock()

    def connect(self) -> bool:
        """Finds and connects to the active Discord IPC named pipe"""
        self.close()
        self.is_connected = False
        self.is_authenticated = False

        for i in range(10):
            pipe_path = RPC_PIPE_PATTERN.format(i)
            h = k32.CreateFileW(
                pipe_path,
                GENERIC_READ | GENERIC_WRITE,
                0,
                None,
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL,
                None
            )
            if h != INVALID_HANDLE_VALUE and h != 0:
                self.handle = h
                logger.info(f"Connected to Discord IPC pipe: {pipe_path}")
                self.is_connected = True
                break

        if not self.is_connected:
            logger.warning("Could not connect to Discord IPC. Is Discord desktop app running?")
            return False

        # 1. Send Handshake (Opcode 0)
        handshake_payload = {"v": 1, "client_id": self.client_id}
        self._send_raw(0, handshake_payload)

        # Read Handshake Response
        op, data = self._read_raw()
        if op != 1 or not data or data.get("evt") != "READY":
            logger.error(f"Handshake failed: {data}")
            self.close()
            return False

        user_info = data.get("data", {}).get("user", {})
        self.current_user_id = str(user_info.get("id", ""))
        username = user_info.get("username", "Unknown")
        logger.info(f"Discord RPC Handshake successful. Connected to user: {username} (ID: {self.current_user_id})")

        # 2. Authenticate
        if not self._authenticate():
            logger.error("Discord RPC Authentication failed.")
            self.close()
            return False

        # 3. Query initial voice settings
        self._send_raw(1, {"cmd": "GET_VOICE_SETTINGS", "nonce": str(uuid.uuid4())})
        op, v_res = self._read_raw()
        if v_res and "data" in v_res:
            self.is_muted = v_res["data"].get("mute", False)
            status_str = "MUTED" if self.is_muted else "LIVE"
            logger.info(f"Initial Discord Mute State: {status_str}")
            if self.on_mute_change:
                self.on_mute_change(self.is_muted)

        # 4. Subscribe to real-time events
        # VOICE_SETTINGS_UPDATE
        self._send_raw(1, {
            "cmd": "SUBSCRIBE",
            "evt": "VOICE_SETTINGS_UPDATE",
            "nonce": str(uuid.uuid4())
        })
        self._read_raw()
        
        # VOICE_CHANNEL_SELECT (when joining or leaving a call)
        self._send_raw(1, {
            "cmd": "SUBSCRIBE",
            "evt": "VOICE_CHANNEL_SELECT",
            "nonce": str(uuid.uuid4())
        })
        self._read_raw()
        logger.info("Subscribed to Discord Voice Settings & Channel events.")

        # 5. Fetch initial voice call status
        self.refresh_voice_channel()

        # 6. Start background listener thread for continuous events
        self._running = True
        self._rx_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._rx_thread.start()

        return True

    def _send_raw(self, opcode: int, data: dict):
        if not self.is_connected or self.handle in (INVALID_HANDLE_VALUE, 0):
            return
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("<II", opcode, len(payload))
        buf = header + payload
        written = wintypes.DWORD()
        with self._send_lock:
            k32.WriteFile(self.handle, buf, len(buf), ctypes.byref(written), None)

    def _read_raw(self):
        if not self.is_connected or self.handle in (INVALID_HANDLE_VALUE, 0):
            return None, None
        hdr = ctypes.create_string_buffer(8)
        read_bytes = wintypes.DWORD()
        res = k32.ReadFile(self.handle, hdr, 8, ctypes.byref(read_bytes), None)
        if not res or read_bytes.value < 8:
            return None, None
        op, length = struct.unpack("<II", hdr.raw)
        data = ctypes.create_string_buffer(length)
        total = 0
        while total < length:
            chunk = ctypes.create_string_buffer(length - total)
            res = k32.ReadFile(self.handle, chunk, length - total, ctypes.byref(read_bytes), None)
            if not res or read_bytes.value == 0:
                break
            data.raw = data.raw[:total] + chunk.raw[:read_bytes.value] + data.raw[total + read_bytes.value:]
            total += read_bytes.value
        try:
            return op, json.loads(data.raw[:length].decode("utf-8"))
        except Exception as e:
            logger.warning(f"Error decoding Discord message: {e}")
            return None, None

    def _authenticate(self) -> bool:
        # Check saved token first
        token = self._load_saved_token()
        if token and self._try_token(token):
            self.access_token = token
            self.is_authenticated = True
            logger.info("Authenticated using stored Discord OAuth2 token.")
            return True

        # Need new authorization code
        logger.info("Requesting authorization from Discord...")
        self._send_raw(1, {
            "cmd": "AUTHORIZE",
            "args": {
                "client_id": self.client_id,
                "scopes": ["rpc", "rpc.voice.read", "rpc.voice.write", "identify"]
            },
            "nonce": str(uuid.uuid4())
        })
        op, res = self._read_raw()
        if not res or res.get("evt") == "ERROR":
            logger.error(f"Authorization request rejected or failed: {res}")
            return False

        code = res.get("data", {}).get("code")
        if not code:
            logger.error(f"No authorization code returned: {res}")
            return False

        logger.info("Exchanging authorization code for OAuth2 access token...")
        token = self._exchange_code_for_token(code)
        if not token:
            return False

        if self._try_token(token):
            self.access_token = token
            self._save_token(token)
            self.is_authenticated = True
            logger.info("Successfully authorized and authenticated with Discord RPC!")
            return True

        return False

    def _try_token(self, token: str) -> bool:
        self._send_raw(1, {
            "cmd": "AUTHENTICATE",
            "args": {"access_token": token},
            "nonce": str(uuid.uuid4())
        })
        op, res = self._read_raw()
        return bool(res and res.get("evt") != "ERROR")

    def _exchange_code_for_token(self, code: str) -> Optional[str]:
        try:
            resp = requests.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": "http://127.0.0.1"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0
            )
            data = resp.json()
            token = data.get("access_token")
            if not token:
                logger.error(f"Failed to get token from Discord API: {data}")
            return token
        except Exception as e:
            logger.error(f"Exception exchanging OAuth2 code: {e}")
            return None

    def _load_saved_token(self) -> Optional[str]:
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("access_token")
            except Exception:
                pass
        return None

    def _save_token(self, token: str):
        try:
            with open(TOKEN_FILE, "w") as f:
                json.dump({"access_token": token}, f)
        except Exception as e:
            logger.warning(f"Could not save token file: {e}")

    # =========================================================================
    # VOICE SETTINGS (MIC MUTE)
    # =========================================================================
    def set_mute(self, muted: bool) -> bool:
        """Explicitly sets Discord mute state to True or False"""
        if not self.is_authenticated:
            return False
        logger.info(f"Setting Discord Mute via RPC -> {muted}")
        self._send_raw(1, {
            "cmd": "SET_VOICE_SETTINGS",
            "args": {"mute": muted},
            "nonce": str(uuid.uuid4())
        })
        return True

    def toggle_mute(self) -> bool:
        """Toggles the current Discord mute state"""
        target = not self.is_muted
        return self.set_mute(target)

    # =========================================================================
    # VOICE CALL & CALL MEMBERS
    # =========================================================================
    def parse_members(self, channel_data: Optional[dict]) -> List[dict]:
        """Parses, sanitizes, and sorts voice call members for display on MacroPad"""
        if not channel_data or not channel_data.get("id"):
            return []

        states = channel_data.get("voice_states", [])
        members = []
        for s in states:
            u = s.get("user", {})
            uid = str(u.get("id", ""))
            raw_name = s.get("nick") or u.get("global_name") or u.get("username") or "User"
            # Sanitize for e-ink (alphanumeric + basic symbols, max 6 chars)
            clean_name = "".join(c for c in raw_name if c.isalnum() or c in " -_")[:6].strip()
            if not clean_name:
                clean_name = u.get("username", "User")[:6]

            vol = round(s.get("volume", 100))
            is_self = bool(self.current_user_id and uid == self.current_user_id)
            is_bot = u.get("bot", False)

            members.append({
                "id": uid,
                "name": clean_name,
                "volume": vol,
                "is_self": is_self,
                "bot": is_bot,
                "mute": s.get("mute", False) or s.get("voice_state", {}).get("mute", False) or s.get("voice_state", {}).get("self_mute", False),
                "speaking": False
            })

        # Sort order: other humans first, bots second, current user last
        members.sort(key=lambda m: (1 if m["is_self"] else 0, 1 if m["bot"] else 0, m["name"].lower()))
        return members

    def refresh_voice_channel(self) -> Optional[dict]:
        """Fetches the current voice channel and updates active members"""
        if not self.is_authenticated:
            return None
        self._send_raw(1, {
            "cmd": "GET_SELECTED_VOICE_CHANNEL",
            "nonce": str(uuid.uuid4())
        })
        # If the background listener is running, it will catch the response.
        # But if called before the listener starts, we read directly:
        if not self._running:
            op, res = self._read_raw()
            if res and res.get("data") and res["data"].get("id"):
                members = self.parse_members(res["data"])
                self.voice_channel = {
                    "id": res["data"]["id"],
                    "name": res["data"].get("name", "Voice Call"),
                    "members": members
                }
            else:
                self.voice_channel = None
            return self.voice_channel
        return self.voice_channel

    def set_user_volume(self, user_id: str, volume: float) -> Optional[int]:
        """Adjusts a specific Discord call member's volume (0% to 200%)"""
        if not self.is_authenticated:
            return None
        clamped_vol = max(0.0, min(200.0, float(volume)))
        target_int = round(clamped_vol)
        logger.info(f"Setting User {user_id} Discord Volume -> {target_int}%")
        self._send_raw(1, {
            "cmd": "SET_USER_VOICE_SETTINGS",
            "args": {"user_id": user_id, "volume": clamped_vol},
            "nonce": str(uuid.uuid4())
        })
        # Update local cache immediately
        if self.voice_channel and "members" in self.voice_channel:
            for m in self.voice_channel["members"]:
                if m["id"] == user_id:
                    m["volume"] = target_int
                    break
        return target_int

    # =========================================================================
    # EVENT LISTENER LOOP
    # =========================================================================
    def _listen_loop(self):
        while self._running and self.is_connected:
            try:
                # Non-blocking poll via PeekNamedPipe to prevent synchronous ReadFile from blocking WriteFile
                avail = wintypes.DWORD()
                if not k32.PeekNamedPipe(self.handle, None, 0, None, ctypes.byref(avail), None):
                    logger.debug("Discord IPC pipe disconnected")
                    break

                if avail.value < 8:
                    time.sleep(0.02)
                    continue

                opcode, msg = self._read_raw()
                if opcode is None or msg is None:
                    continue

                cmd = msg.get("cmd")
                evt = msg.get("evt")
                data = msg.get("data", {})

                # 1. Voice Settings Update (Mic Mute / Deafen)
                if cmd == "DISPATCH" and evt == "VOICE_SETTINGS_UPDATE":
                    new_mute = data.get("mute", False)
                    if new_mute != self.is_muted:
                        self.is_muted = new_mute
                        logger.info(f"Discord event: Mute state changed -> {'MUTED' if new_mute else 'LIVE'}")
                        if self.on_mute_change:
                            self.on_mute_change(self.is_muted)

                # 2. Voice Channel Select (User joined or left a voice channel)
                elif cmd == "DISPATCH" and evt == "VOICE_CHANNEL_SELECT":
                    channel_id = data.get("channel_id")
                    if channel_id:
                        logger.info(f"Discord joined voice channel: {channel_id}. Fetching members...")
                        # Query selected voice channel to get member list
                        self._send_raw(1, {"cmd": "GET_SELECTED_VOICE_CHANNEL", "nonce": str(uuid.uuid4())})
                    else:
                        logger.info("Discord left voice channel.")
                        self.voice_channel = None
                        if self.on_voice_channel_update:
                            self.on_voice_channel_update(None)

                # 3. Channel Info Response (from GET_SELECTED_VOICE_CHANNEL)
                elif cmd == "GET_SELECTED_VOICE_CHANNEL":
                    if data and data.get("id"):
                        members = self.parse_members(data)
                        self.voice_channel = {
                            "id": data["id"],
                            "name": data.get("name", "Voice Call"),
                            "members": members
                        }
                        logger.info(f"Voice call active: {self.voice_channel['name']} ({len(members)} members)")
                    else:
                        self.voice_channel = None
                    if self.on_voice_channel_update:
                        self.on_voice_channel_update(self.voice_channel)

                # 4. Voice Setting command acks
                elif cmd == "SET_VOICE_SETTINGS":
                    new_mute = data.get("mute", self.is_muted)
                    if new_mute != self.is_muted:
                        self.is_muted = new_mute
                        logger.info(f"Discord SET_VOICE_SETTINGS ack -> {'MUTED' if new_mute else 'LIVE'}")
                        if self.on_mute_change:
                            self.on_mute_change(self.is_muted)

                # 5. User Voice Setting ack
                elif cmd == "SET_USER_VOICE_SETTINGS":
                    uid = data.get("user_id")
                    vol = round(data.get("volume", 100))
                    if self.voice_channel and "members" in self.voice_channel:
                        for m in self.voice_channel["members"]:
                            if m["id"] == uid:
                                m["volume"] = vol
                                break

            except Exception as e:
                if self._running:
                    logger.debug(f"IPC read error: {e}")
                time.sleep(0.05)

    def close(self):
        self._running = False
        self.is_connected = False
        self.is_authenticated = False
        if self.handle not in (INVALID_HANDLE_VALUE, 0):
            try:
                k32.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = INVALID_HANDLE_VALUE
