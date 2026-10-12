# MacroPad 1-Bit E-Ink Icon & Layer Specification Manifest

This document provides the complete technical specification for creating, encoding, and registering custom 1-bit monochrome icons and layers for the MacroPad 200×200 E-Ink display.

---

## 1. Display & Cell Geometry

* **Display Hardware:** 1.54" Monochrome E-Ink (`200 × 200` pixels, `GxEPD2_BW`)
* **Top Status Bar:** `200 × 16` pixels (`Y: 0..16`)
* **3×3 Key Grid Area:** `200 × 184` pixels (`Y: 16..200`)
* **Individual Cell Size:** **`66 × 61` pixels**
* **Cell Layout when Icon is Active:**
  * **Icon Position:** Horizontally centered at `cellX + (66 - w) / 2`, vertically placed at `cellY + 5`.
  * **Label Position:** Drawn automatically centered beneath the icon (`iconY + iconH + 6`), max **9 characters** (`5×7` pixel font).

### Supported Icon Dimensions
| Format | Dimensions (`W × H`) | Bytes per Row | Total Bytes | Hex String Length | Best Used For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard (Recommended)** | **`24 × 24`** | `3 bytes` | `72 bytes` | **`144 hex chars`** | App logos, media controls, tools |
| **Wide Banner** | **`32 × 16`** | `4 bytes` | `64 bytes` | **`128 hex chars`** | Wide badges, text-stylized logos |
| **Large Icon (Max)** | **`32 × 32`** | `4 bytes` | `128 bytes` | **`256 hex chars`** | Full-cell hero icons (minimal label) |

*(Note: Width should ideally be a multiple of 8 (`16`, `24`, `32`). Maximum buffer size per cell on the ESP32 is `128 bytes`).*

---

## 2. How to Author Icons (2 Methods)

### Method A: ASCII Art in `pi_app/icon_library.py` (Recommended for AI Agents)
The easiest and most visual way to author icons is using a 24×24 ASCII grid inside [`pi_app/icon_library.py`](file:///c:/Users/Uzzo/Desktop/MACROPAD/pi_app/icon_library.py), where:
* `.` = White background pixel (`0`)
* `#` = Black ink pixel (`1`)

Add your icon entry to `BUILTIN_ICONS_24X24` in `pi_app/icon_library.py`:

```python
    "spotify": [
        "........................",
        ".......##########.......",
        ".....##############.....",
        "....################....",
        "...##################...",
        "..#####..........#####..",
        "..###..##########..###..",
        ".###..############..###.",
        ".###................###.",
        ".###...#########....###.",
        ".###..###########...###.",
        ".###................###.",
        "..###..########....###..",
        "..####..########..####..",
        "...##################...",
        "....################....",
        ".....##############.....",
        ".......##########.......",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................",
        "........................"
    ],
```

`get_compiled_icons_library()` automatically compiles every 24×24 ASCII array into its 144-character hex string at startup.

---

### Method B: Raw Hex Bitmap Encoding (`Adafruit_GFX` Standard)
If converting from PNG/SVG or generating programmatically:
* **Bit Order:** **MSB First** (Leftmost pixel of each 8-pixel horizontal chunk is Bit 7 `0x80`; rightmost is Bit 0 `0x01`).
* **Row Order:** Top-to-bottom (`y = 0` to `h - 1`), left-to-right (`x = 0` to `w - 1`).
* **Row Padding:** Each row is padded to a full byte boundary: `bytes_per_row = (w + 7) // 8`.
* **Pixel Polarity:** `1` = Black ink (`GxEPD_BLACK`), `0` = White background.

#### Python Conversion Snippet (Pillow Image -> Hex String)
```python
from PIL import Image

def image_to_macropad_hex(img_path: str, w: int = 24, h: int = 24) -> str:
    img = Image.open(img_path).convert("L").resize((w, h))
    bytes_per_row = (w + 7) // 8
    out_bytes = []
    for y in range(h):
        for b in range(bytes_per_row):
            byte_val = 0
            for bit in range(8):
                x = b * 8 + bit
                if x < w:
                    # Darker than threshold -> black pixel (1)
                    if img.getpixel((x, y)) < 128:
                        byte_val |= (1 << (7 - bit))
            out_bytes.append(byte_val)
    return bytes(out_bytes).hex()
```

---

## 3. Registering Icons & Layers via REST API (Raspberry Pi Hub)

The Raspberry Pi Hub (`http://192.168.1.62:5000`) hosts the persistent Layer & Icon Store (`pi_app/layers_store.json`).

### 1. Register a Custom Icon
* **Endpoint:** `POST http://192.168.1.62:5000/api/icons`
* **Body:**
```json
{
  "name": "chrome",
  "w": 24,
  "h": 24,
  "hex": "0000000003c0000ff0003ffc007ffe007ffe00f00f00e00700c3c300c7e300c7e300c3c300e00700f00f007ffe007ffe003ffc000ff00003c0000000000000000000000000"
}
```

### 2. Create or Update a Layer
* **Endpoint:** `POST http://192.168.1.62:5000/api/layers/{layer_id}`
* **Body:**
```json
{
  "id": 5,
  "name": "OBS Studio",
  "bank": 2,
  "slot": 1,
  "cells": [
    {"index": 1, "label": "STREAM", "icon": "play", "action": "obs_stream_toggle"},
    {"index": 2, "label": "RECORD", "icon": "stop", "action": "obs_record_toggle"},
    {"index": 3, "label": "SCENE 1", "icon": "terminal", "action": "obs_scene_1"},
    {"index": 4, "label": "SCENE 2", "icon": "terminal", "action": "obs_scene_2"},
    {"index": 5, "label": "MUTE", "icon": "mute", "action": "mic_mute_toggle"},
    {"index": 6, "label": "CAM", "icon": "light", "action": "obs_cam_toggle"},
    {"index": 7, "label": "CLIP", "icon": "next", "action": "obs_replay_save"},
    {"index": 8, "label": "BRB", "icon": "sleep", "action": "obs_scene_brb"},
    {"index": 9, "label": "END", "icon": "power", "action": "obs_stream_stop"}
  ]
}
```

### 3. Push Layer to MacroPad E-Ink Display
* **Endpoint:** `POST http://192.168.1.62:5000/api/layers/{layer_id}/apply`

---

## 4. Direct MQTT Protocol (`macropad/display`)

If publishing directly to the MQTT broker (`192.168.1.62:1883`, topic `macropad/display`):

### Full 9-Cell Grid Update
```json
{
  "labels": ["PLAY", "PAUSE", "NEXT", "PREV", "LIGHT", "VOL+", "LT SLP", "SLEEP", "WOL PC"],
  "icons": ["<hex_0>", "<hex_1>", "<hex_2>", "<hex_3>", "<hex_4>", "<hex_5>", "<hex_6>", "<hex_7>", "<hex_8>"],
  "icon_w": 24,
  "icon_h": 24,
  "fast": false
}
```
*(Pass `""` in the `icons` array for any cell that should render text-only).*

### Single-Cell Update
```json
{
  "cell": 0,
  "label": "SPOTIFY",
  "icon": "<144_char_hex>",
  "w": 24,
  "h": 24,
  "fast": true
}
```

### Clear All Icons (Revert to Large Text Mode)
```json
{
  "clear_icons": true,
  "labels": ["ACT 1", "ACT 2", "ACT 3", "ACT 4", "ACT 5", "ACT 6", "ACT 7", "ACT 8", "ACT 9"]
}
```
