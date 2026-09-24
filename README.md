# MacroPad: Wireless ESP32-C3 E-Ink Mechanical Macro Controller

A custom, battery-powered 16-key mechanical macropad featuring an ultra-low-power **1.54" E-Ink display**, **18 addressable RGB NeoPixels**, **3 rotary encoders**, and seamless **MQTT integration** with Home Assistant and Windows desktop audio control.

---

## 🏗️ Architecture Overview

```
                      +-----------------------------------+
                      |      ESP32-C3 MacroPad Device     |
                      |  16 Keys | 3 Encoders | 18 LEDs   |
                      |   1.54" E-Ink | 4000mAh Battery   |
                      +-----------------+-----------------+
                                        |  Wi-Fi (MQTT + HTTP)
                                        v
                      +-----------------------------------+
                      |      Raspberry Pi MQTT Broker     |
                      |       (192.168.1.62:1883)         |
                      +--------+-----------------+--------+
                               |                 |
            +------------------+                 +-------------------+
            v                                                        v
+-----------------------+                                +-----------------------+
|  Home Assistant (HA)  |                                |   Windows PC Bridge   |
|  Automations, Scenes, |                                |  pycaw Audio Control, |
|  Room Lights, Toggles |                                |  Discord Mute, Hotkeys|
+-----------------------+                                +-----------------------+
            ^                                                        ^
            |                                                        |
            +------------------+                 +-------------------+
                               |                 |
                      +--------+-----------------+--------+
                      |       Pi / PC Web Dashboard       |
                      |    FastAPI + WebSockets (Port 5000)|
                      +-----------------------------------+
```

---

## 📂 Repository Structure

```
MACROPAD/
├── firmware/
│   └── MACROPAD/
│       ├── MACROPAD.ino           # ESP32-C3 core firmware (I2C, E-Ink, NeoPixels, MQTT, OTA)
│       └── dashboard_html.h       # On-device embedded HTTP diagnostics & OTA web server
├── pc_app/
│   ├── macropad_bridge.py        # Windows audio controller (pycaw, Discord mic mute, volume)
│   ├── start_audio_bridge.bat    # 1-click Windows runner
│   └── requirements.txt          # Python dependencies for Windows bridge
├── pi_app/
│   ├── app.py                    # Real-time WebSocket terminal & diagnostic web dashboard
│   ├── start_dashboard.bat       # Windows runner
│   ├── start_dashboard.sh        # Linux / Raspberry Pi runner
│   ├── macropad-dashboard.service# Systemd service unit for 24/7 background running on Pi
│   └── requirements.txt          # Python dependencies for dashboard server
├── home_assistant/
│   ├── ha_configuration.yaml     # MQTT sensors & device discovery
│   ├── ha_automations.yaml       # Layer and macro automations
│   └── ha_scripts.yaml           # Preset execution scripts
└── .gitignore                    # Build artifact and temporary file exclusions
```

---

## ⚡ Hardware & Pinout

### Microcontroller: ESP32-C3 SuperMini (RISC-V 160MHz, 4MB Flash)

| Function | ESP32-C3 GPIO | Notes |
| :--- | :--- | :--- |
| **Matrix SDA** | `GPIO 4` | I2C Data (`PCF_MATRIX` @ `0x20`, `PCF_ENCODERS` @ `0x24`) |
| **Matrix SCL** | `GPIO 5` | I2C Clock (100kHz standard mode) |
| **Matrix INT** | `GPIO 3` | RTC domain GPIO with hardware interrupt & deep sleep wake |
| **NeoPixels** | `GPIO 1` | WS2812B data line (18 LEDs total) |
| **Encoder 1 CLK** | `GPIO 6` | Hardware interrupt (CHANGE) |
| **Encoder 1 DT** | `GPIO 7` | Hardware interrupt (CHANGE) |
| **Encoder 1 SW** | `GPIO 10` | Push switch (active LOW) |
| **E-Ink BUSY** | `GPIO 8` | Busy status indicator from E-Ink panel |
| **E-Ink DC** | `GPIO 2` | Data / Command select line |
| **E-Ink CS** | `GPIO 20` | SPI Chip Select |
| **E-Ink RST** | `-1` | Tied to hardware reset / unused |
| **Battery ADC** | `GPIO 0` | Resistor voltage divider (Divider ratio: `2.0455026`) |

### Key Matrix Layout (4×4 PCF8574 Expander)
- **Top Row (Keys 1–4)**: Quick Layer Slots (1 to 4) within the active Bank.
- **Key 5**: Room Light Toggle (Tap) / Modifier Hold (`MOD`).
- **Key 9**: Fixed system function.
- **Key 13**: Discord Mic Mute (Short tap) / App Audio Target Modifier (Hold $\ge 500\text{ms}$).
- **Keys 6–8, 10–12, 14–16**: 3×3 Dynamic Macro Grid mirroring the E-Ink display labels.

### Rotary Encoders
1. **HW Encoder (Top Right - GPIO 6/7/10)**:
   - Rotate: Master Volume Up / Down (with acceleration).
   - Click: Reset Master Volume to 50%.
2. **Encoder 2 (Top Left - PCF8574)**:
   - Rotate: Target App Volume (when audio modifier held) / Layer cycle.
   - Click: Cycle active target application.
   - Long Press ($\ge 500\text{ms}$): Quick Return to Bank 1 Layer 1 (`HOME`).
3. **Encoder 1 (Bottom Left - PCF8574)**:
   - Rotate: Discord Volume Up / Down.
   - Click: Reset Discord Volume to 100%.

---

## 🔋 Power Management & Battery Life

The pad is powered by a **4000 mAh Li-Po single-cell** battery.

- **Awake Consumption**: $\approx 45\text{–}65\,\text{mA}$ with NeoPixels dimmed.
- **Light Sleep Mode**: Triggers after **10 minutes** of idle inactivity. Powers down display rails and drops current to $\approx 3.5\,\text{mA}$.
- **Deep Sleep Protection**: Automatically engages when battery voltage drops below **`3.30V`**.
  - E-Ink updates to `! LOW BATT SLEEP !` (image persists indefinitely at $0.0\,\mu\text{A}$).
  - All NeoPixels shut off.
  - Radio powers down.
  - ESP32-C3 enters deep sleep ($\approx 10\text{–}15\,\mu\text{A}$).
  - Wakes up via matrix key press (`MATRIX_INT` GPIO 3) or by plugging in USB power ($\ge 4.3\text{V}$).
- **Estimated Battery Life**: ~18 to 22 days of regular daily desktop use on a single charge.

---

## 🚀 Getting Started

### 1. Firmware (`firmware/MACROPAD`)

#### Using Arduino CLI:
```bash
# Compile firmware
arduino-cli compile --fqbn esp32:esp32:esp32c3 firmware/MACROPAD

# Flash over USB (replace COM7 with your port)
arduino-cli upload -p COM7 --fqbn esp32:esp32:esp32c3 firmware/MACROPAD
```

#### Wireless HTTP OTA Update:
Once connected to your local network, updates can be flashed over Wi-Fi without plugging in USB:
```bash
curl -F "update=@firmware/MACROPAD/build/MACROPAD.ino.bin" http://<DEVICE_IP>/update
```

---

### 2. PC Windows Audio Bridge (`pc_app`)

Provides native Windows Master Volume, Discord Mic Muting, and individual application volume control via `pycaw`.

```bash
cd pc_app
pip install -r requirements.txt
python macropad_bridge.py
# Or double-click start_audio_bridge.bat
```

---

### 3. Raspberry Pi Web Dashboard (`pi_app`)

Real-time browser-based telemetry terminal and device debugger using FastAPI and WebSockets.

```bash
cd pi_app
pip install -r requirements.txt
python app.py
# Or run bash start_dashboard.sh
```

To install as a permanent system service on Raspberry Pi:
```bash
sudo cp pi_app/macropad-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now macropad-dashboard.service
```

---

### 4. Home Assistant Integration (`home_assistant`)

Copy the YAML configurations into your Home Assistant `/config/` directory:
- `ha_configuration.yaml`: Sets up MQTT device status sensor, battery monitor, and uptime.
- `ha_automations.yaml`: Handles incoming matrix button clicks and encoder events.
- `ha_scripts.yaml`: Provides helper scripts for screen label updates and preset changing.

---

## 📡 MQTT Topic Specification

| Topic | Payload Type | Description |
| :--- | :--- | :--- |
| `macropad/input` | JSON | Published on key press, release, encoder turn, or click |
| `macropad/status` | JSON | Periodic heartbeat (battery voltage, RSSI, heap, layer) |
| `macropad/display` | JSON | Subscribe topic for updating 3×3 screen labels or popups |
| `macropad/debug` | JSON | Real-time device ring buffer debug logs |

### Example Input Payload:
```json
{
  "device": "macropad",
  "layer": 1,
  "action": "macro",
  "index": 1,
  "label": "ACT 1"
}
```

---

## 📄 License
Private & Proprietary. All rights reserved by @clawdiapai.
