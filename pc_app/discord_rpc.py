import json
import logging
import os
import struct
import threading
import time
import uuid
from typing import Callable, Optional
import requests

logger = logging.getLogger("DiscordRPC")

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "discord_token.json")
RPC_PIPE_PATTERN = r"\\.\pipe\discord-ipc-{}"

class DiscordVoiceRPC:
    r"""
    Native Discord IPC Client for real-time voice settings (Mute/Deafen state)
    Uses the local named pipe \\.\pipe\discord-ipc-0 with OAuth2 RPC scopes.
    """
    def __init__(self, client_id: str, client_secret: str, on_mute_change: Optional[Callable[[bool], None]] = None):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.on_mute_change = on_mute_change
        
        self.pipe = None
        self.access_token: Optional[str] = None
        self.is_connected = False
        self.is_authenticated = False
        self.is_muted = False
        
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
        self._pending_requests = {}
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Finds and connects to the active Discord IPC named pipe"""
        self.close()
        self.is_connected = False
        self.is_authenticated = False
        for i in range(10):
            pipe_path = RPC_PIPE_PATTERN.format(i)
            try:
                self.pipe = open(pipe_path, "r+b", buffering=0)
                logger.info(f"Connected to Discord IPC pipe: {pipe_path}")
                self.is_connected = True
                break
            except Exception:
                continue

        if not self.is_connected:
            logger.error("Could not connect to Discord IPC. Is Discord desktop app running?")
            return False

        # 1. Send Handshake (Opcode 0)
        handshake_payload = {"v": 1, "client_id": self.client_id}
        self._send_raw(0, handshake_payload)

        # Read Handshake Response
        op, data = self._read_raw()
        if op != 1 or data.get("evt") != "READY":
            logger.error(f"Handshake failed: {data}")
            return False

        logger.info(f"Discord RPC Handshake successful. Connected to user: {data.get('data', {}).get('user', {}).get('username')}")

        # Start RX listener thread
        self._running = True
        self._rx_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._rx_thread.start()

        # 2. Authenticate
        if not self._authenticate():
            logger.error("Discord RPC Authentication failed.")
            return False

        # 3. Fetch initial voice state & subscribe to real-time events
        self._init_voice_subscription()
        return True

    def _send_raw(self, opcode: int, data: dict):
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("<II", opcode, len(payload))
        with self._lock:
            self.pipe.write(header + payload)

    def _read_raw(self):
        header = self.pipe.read(8)
        if len(header) < 8:
            return None, None
        opcode, length = struct.unpack("<II", header)
        data = self.pipe.read(length)
        return opcode, json.loads(data.decode("utf-8"))

    def _call(self, cmd: str, args: Optional[dict] = None, timeout: float = 5.0) -> Optional[dict]:
        nonce = str(uuid.uuid4())
        req = {"cmd": cmd, "nonce": nonce}
        if args is not None:
            req["args"] = args

        event = threading.Event()
        self._pending_requests[nonce] = (event, None)
        self._send_raw(1, req)

        if event.wait(timeout):
            _, res = self._pending_requests.pop(nonce, (None, None))
            return res
        self._pending_requests.pop(nonce, None)
        logger.warning(f"RPC call {cmd} timed out")
        return None

    def _authenticate(self) -> bool:
        # Check saved token
        token = self._load_saved_token()
        if token and self._try_token(token):
            self.access_token = token
            self.is_authenticated = True
            logger.info("Authenticated using stored Discord OAuth2 token.")
            return True

        # Need new authorization: Trigger Discord prompt
        logger.info("Prompting user to authorize MacroPad in Discord desktop app...")
        res = self._call("AUTHORIZE", {
            "client_id": self.client_id,
            "scopes": ["rpc", "rpc.voice.read", "rpc.voice.write"]
        }, timeout=30.0)

        if not res or res.get("evt") == "ERROR":
            logger.error(f"Authorization request rejected or failed: {res}")
            return False

        code = res.get("data", {}).get("code")
        if not code:
            logger.error(f"No authorization code returned: {res}")
            return False

        # Exchange code for access_token
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
        res = self._call("AUTHENTICATE", {"access_token": token}, timeout=5.0)
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

    def _init_voice_subscription(self):
        # 1. Subscribe to real-time VOICE_SETTINGS_UPDATE events
        nonce = str(uuid.uuid4())
        self._send_raw(1, {"cmd": "SUBSCRIBE", "evt": "VOICE_SETTINGS_UPDATE", "nonce": nonce})
        logger.info("Subscribed to Discord VOICE_SETTINGS_UPDATE events.")

        # 2. Query initial voice settings
        settings = self.get_voice_settings()
        if settings:
            self.is_muted = settings.get("mute", False)
            logger.info(f"Initial Discord Mute State: {'MUTED (True)' if self.is_muted else 'LIVE (False)'}")
            if self.on_mute_change:
                self.on_mute_change(self.is_muted)

    def get_voice_settings(self) -> Optional[dict]:
        res = self._call("GET_VOICE_SETTINGS", timeout=4.0)
        if res and "data" in res:
            return res["data"]
        return None

    def set_mute(self, muted: bool) -> bool:
        """Explicitly sets Discord mute state to True or False"""
        res = self._call("SET_VOICE_SETTINGS", {"mute": muted}, timeout=3.0)
        if res and "data" in res:
            self.is_muted = res["data"].get("mute", muted)
            return True
        return False

    def toggle_mute(self) -> bool:
        """Toggles the current Discord mute state"""
        target = not self.is_muted
        logger.info(f"Toggling Discord Mute via RPC: {self.is_muted} -> {target}")
        return self.set_mute(target)

    def _listen_loop(self):
        while self._running:
            try:
                opcode, msg = self._read_raw()
                if opcode is None:
                    break

                # Dispatch events
                if msg.get("cmd") == "DISPATCH" and msg.get("evt") == "VOICE_SETTINGS_UPDATE":
                    data = msg.get("data", {})
                    new_mute = data.get("mute", False)
                    if new_mute != self.is_muted:
                        self.is_muted = new_mute
                        logger.info(f"Discord event: Mute state changed -> {'MUTED' if new_mute else 'LIVE'}")
                        if self.on_mute_change:
                            self.on_mute_change(self.is_muted)

                # Resolve pending request nonces
                nonce = msg.get("nonce")
                if nonce and nonce in self._pending_requests:
                    event, _ = self._pending_requests[nonce]
                    self._pending_requests[nonce] = (event, msg)
                    event.set()

            except Exception as e:
                if self._running:
                    logger.debug(f"IPC read error: {e}")
                break

    def close(self):
        self._running = False
        if self.pipe:
            try:
                self.pipe.close()
            except Exception:
                pass
