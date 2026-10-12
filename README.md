# MacroPad: Wireless ESP32-C3 E-Ink Mechanical Macro Controller

A custom, battery-powered 16-key mechanical macropad featuring an ultra-low-power **1.54" E-Ink display**, **18 addressable RGB NeoPixels**, **3 rotary encoders**, and seamless **MQTT integration** with Windows, Autodesk Fusion 360, Discord, Home Assistant, and **260+ pre-configured 3D/CAD/Creative applications** via the harvested 3Dconnexion library.

> 📖 **See [`INTEGRATIONS.md`](INTEGRATIONS.md)** for the complete catalog of **260 application profiles**, **2,810 actions/macros**, **427 on-screen radial pie menus**, and **3,560 24×24 E-Ink icons**.

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
|  Automations, Scenes, |                                |  - pycaw & Discord RPC|
|  Room Lights, Toggles |                                |  - Auto-App Watcher   |
+-----------------------+                                |  - Qt Radial Overlay  |
            ^                                            |  - Fusion 360 Bridge  |
            |                                            +-----------------------+
            +------------------+                                     |
                               |                                     v
                      +--------+-----------------+       +-----------------------+
                      |       Pi Unified Studio   |       |  Autodesk Fusion 360  |
                      |   Layer Store & Icon Mgr |       |  Native Python Add-in |
                      |    FastAPI (Port 5000)   |       +-----------------------+
                      +--------------------------+
```

---

## 📂 Repository Structure

```
MACROPAD/
├── firmware/
│   └── MACROPAD/
│       ├── MACROPAD.ino           # ESP32-C3 core firmware (I2C, E-Ink, NeoPixels, MQTT, OTA)
│       └── dashboard_html.h       # On-device embedded HTTP diagnostics, mode switch & OTA web server
├── pc_app/
│   ├── macropad_bridge.py        # Windows companion bridge (pycaw, Discord RPC, Auto-App watcher, 3Dx engine)
│   ├── discord_rpc.py            # Local Discord Voice RPC IPC client (mute/deafen/channel sync)
│   ├── radial_menu.py            # Transparent Qt on-screen radial pie menus (3Dconnexion-style)
│   ├── notification_bridge.py    # Windows toast notification interceptor (WhatsApp VIP, Phone Link)
│   ├── start_audio_bridge.bat    # 1-click Windows bridge runner
│   ├── install_startup.bat       # Configures silent Windows background startup via pythonw
│   └── requirements.txt          # Python dependencies for Windows bridge
├── fusion_addin/
│   └── MacroPadFusionBridge/
│       ├── MacroPadFusionBridge.py       # Native Fusion 360 Python API command bridge
│       └── MacroPadFusionBridge.manifest # Autodesk Fusion Add-In manifest
├── pi_app/
│   ├── app.py                    # Unified Studio web server (FastAPI, WebSockets, REST APIs)
│   ├── studio_ui.py              # Visual Layer Editor, Icon Picker, 3Dx Library Browser & App Rules Studio
│   ├── backlight_ui.py           # Interactive RGB NeoPixel Backlight & Animation Studio
│   ├── layer_manager.py          # Dynamic 16-layer store and rule matcher
│   ├── layers_store.json         # Persistent JSON layer configuration store
│   ├── tdx_harvested.json        # 260 harvested 3Dconnexion app profiles, 2,664 macros, 402 radial menus & 879 icons
│   ├── icon_library.py           # 24x24 1-bit monochrome bitmap icon compiler
│   └── macropad-dashboard.service# Systemd service unit for 24/7 background running on Pi
├── tools/
│   ├── harvest_3dconnexion.py    # XML parser & icon converter for 3Dconnexion 3DxWare Cfg profiles
│   └── generate_integrations_doc.py # Generates INTEGRATIONS.md from tdx_harvested.json
├── home_assistant/
│   ├── ha_configuration.yaml     # MQTT sensors & device discovery
│   ├── ha_automations.yaml       # Layer and macro automations
│   └── ha_scripts.yaml           # Preset execution scripts
├── ota_upload.py                 # Automated 1-click Wi-Fi OTA firmware flashing utility
├── INTEGRATIONS.md               # Comprehensive catalog of all 260+ integrated applications & macros
├── ICON_SPEC_MANIFEST.md         # Bitmap specifications for E-Ink icons
└── .gitignore                    # Build artifacts, tokens, logs, and database exclusions
```

---

## 🕹️ Operating Modes

The MacroPad supports three distinct operating modes, selectable from the **Unified Studio** (`http://192.168.1.62:5000/`) or the **On-Device Web Dashboard** (`http://192.168.1.58/`):

1. **🤖 Auto-App Mode (`automode`)** *(Default)*:
   - The PC bridge monitors the focused Windows application in real-time.
   - **Tier 1 Static Layer Rules**:
     - **Autodesk Fusion 360** $\rightarrow$ Layer 13 (Native API Bridge + 8 CAD Layers + Hold Radial Menus)
     - **Autodesk AutoCAD** $\rightarrow$ Layers 5–12 (Draw, Modify, Construct, Layers, Annotate, Snaps, Blocks, View)
     - **Adobe Photoshop** $\rightarrow$ Layer 14 (Tools, Brushes, Layers, Adjustments)
     - **Discord** $\rightarrow$ Layer 2 (Live Voice Call Member Volume Grid)
   - **Zero-Config 3Dconnexion Profiles (260 Apps)**:
     - Focusing any of the **260 supported 3Dconnexion apps** (e.g., **Bambu Studio**, **OrcaSlicer**, **KiCad**, **Blender**, **SolidWorks**, **Rhino**, **ZBrush**, **Unreal Engine**, **Paint**, **Chrome/Opera/Edge**, **File Explorer**) automatically loads its tailored 9-key grid, custom 24×24 E-Ink icons, and long-press radial pie menus. See **[`INTEGRATIONS.md`](INTEGRATIONS.md)** for the full list.
   - **Untracked Applications**: Displays **Universal Controls** (App name on Cell 1, plus `COPY`, `PASTE`, `CUT`, `UNDO`, `REDO`, `FIND`, `SAVE`, and `ESC`).
2. **🎛️ Manual Mode (`manual`)**:
   - Disables automatic switching. The pad operates statically across 16 layers (4 Banks $\times$ 4 Slots).
3. **🛠️ Debug Mode (`debug`)**:
   - Dedicated hardware diagnostics mode: screen test, battery ADC, stay-awake toggle, modem sleep, deep sleep, and Wake-on-LAN testing.

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
- **Key 5**: Room Light Toggle (Tap) / Modifier Hold (`MOD` - magenta presets).
- **Key 9**: **Status & Battery HUD Peek**: Tap or hold ($\ge 420\text{ms}$) to peek live battery voltage, Wi-Fi RSSI, and layer info.
- **Key 13**: **Discord Mic Mute / Audio Modifier**: Short tap toggles microphone mute; holding enables per-user Discord volume controls.
- **Keys 6–8, 10–12, 14–16**: 3×3 Dynamic Macro Grid mirroring the E-Ink display labels.

### Rotary Encoders
1. **HW Encoder (Top Right - GPIO 6/7/10)**:
   - Rotate: Master System Volume Up / Down.
   - Click: Reset Master Volume to 80%.
2. **Encoder 2 (Bottom Left - PCF8574)**:
   - Rotate: Selected Discord Call Member Volume (in voice call) / Application Volume.
   - Click: Mute / Unmute selected voice member.
3. **Encoder 3 (Top Left - PCF8574)**:
   - Rotate: Discord Master Volume / CAD Scroll.
   - Click: Reset Discord Master Volume to 80%.

---

## 🎙️ Dynamic Discord Voice Call Controller

When connected to Discord via local IPC RPC:
- When a voice call is active, Keys 1–8 automatically populate with **live call members**, their volumes (e.g. `60%`), and mute states.
- **Tap Member Key**: Sets the member as the active adjustment target (`>` indicator and popup toast).
- **Turn Bottom-Left Encoder**: Smoothly adjusts that targeted member's volume in Discord (0% to 200%).
- **Long Press Member Key ($\ge 250\text{ms}$)**: Toggles local mute for that specific member.
- **Key 9 (Cell 9)**: Toggles Discord Deafen (`DEAFEN CALL` / `UNDEAF CALL`).

---

## 📐 Autodesk Fusion 360 & Radial Menus

- **Native Fusion Add-In**: Connects directly to Autodesk Fusion 360 via `MacroPadFusionBridge.py`, bypassing unreliable simulated keystrokes for instant tool invocation (Sketch, Extrude, Revolve, Sweep, Loft, Fillet, Hole, etc.).
- **3Dconnexion-Style Radial Menus**: Holding any CAD macro key ($\ge 250\text{ms}$) displays an on-screen semi-transparent radial pie menu centered around your cursor with live tool selection.

---

## 🔋 Power Management & Battery Life

The pad is powered by a **4000 mAh Li-Po single-cell** battery.

- **Awake Consumption**: $\approx 45\text{–}65\,\text{mA}$ with NeoPixels dimmed.
- **Light Sleep Mode**: Triggers after **10 minutes** of idle inactivity. Drops current to $\approx 3.5\,\text{mA}$.
- **Deep Sleep Protection**: Automatically engages when battery voltage drops below **`3.30V`**.
  - E-Ink displays `! LOW BATT SLEEP !` (image persists indefinitely at $0.0\,\mu\text{A}$).
  - All NeoPixels shut off; radio powers down ($\approx 10\text{–}15\,\mu\text{A}$).
  - Wakes up via any matrix key press (`MATRIX_INT` GPIO 3) or by plugging in USB-C power ($\ge 4.3\text{V}$).
- **Estimated Battery Life**: ~18 to 25 days of regular desktop use on a single charge.

---

## 🚀 Getting Started

### 1. Firmware OTA Flash (`ota_upload.py`)

Firmware can be compiled and flashed over Wi-Fi without unplugging the device:
```bash
# Compile firmware
arduino-cli compile --fqbn esp32:esp32:esp32c3 firmware/MACROPAD --output-dir build

# 1-click Wi-Fi OTA Flash
python ota_upload.py
```

### 2. PC Companion Bridge (`pc_app`)

```bash
cd pc_app
pip install -r requirements.txt
python macropad_bridge.py
# Or run pc_app/install_startup.bat to run silently in background on boot
```

### 3. Raspberry Pi Studio Dashboard (`pi_app`)

```bash
cd pi_app
pip install -r requirements.txt
python app.py
# Access Web Studio at http://192.168.1.62:5000/
```

To enable as a permanent system service on Raspberry Pi:
```bash
sudo cp pi_app/macropad-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now macropad-dashboard.service
```

---

## 📡 MQTT Topic Specification

| Topic | Payload Type | Description |
| :--- | :--- | :--- |
| `macropad/input` | JSON | Published on key press, release, encoder turn, or click |
| `macropad/status` | JSON | Periodic heartbeat (battery voltage, RSSI, heap, layer, mode) |
| `macropad/display` | JSON | Subscribe topic for updating 3×3 screen labels, icons, or popups |
| `macropad/config_sync` | JSON | Broadcast topic for live layer & app rule synchronization |

---

## 📄 License
Private & Proprietary. All rights reserved by @clawdiapai.
