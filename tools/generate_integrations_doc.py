import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

with open(ROOT / "pi_app" / "tdx_harvested.json", encoding="utf-8") as f:
    tdx = json.load(f)

apps = tdx["apps"]
stats = tdx["stats"]

apps_with_funcs = sorted(
    [a for a in apps if len(a.get("actions", [])) > 0],
    key=lambda x: x["name"].lower(),
)
apps_view_only = sorted(
    [a for a in apps if len(a.get("actions", [])) == 0],
    key=lambda x: x["name"].lower(),
)

lines = [
    "# 🧩 MacroPad Comprehensive Application Integrations Catalog",
    "",
    "This document provides the complete reference of all **native API bridges**, **multi-layer static application profiles**, and **260 harvested 3Dconnexion (`3DxWare`) application profiles** built into the MacroPad ecosystem.",
    "",
    "---",
    "",
    "## 📊 Integration Ecosystem at a Glance",
    "",
    "| Metric | Count | Description |",
    "| :--- | :---: | :--- |",
    f"| **Total Application Profiles** | **{stats['total_apps']}** | Pre-configured application definitions harvested from 3Dconnexion `3DxWinCore/Cfg/*.xml` + native MacroPad rules |",
    f"| **Action-Rich App Profiles** | **{stats['apps_with_actions']}** | Profiles containing decoded keyboard macros, multi-step sequences, or native CAD commands |",
    f"| **Executable Actions & Macros** | **{stats['total_actions']:,}** | Ready-to-use `hotkey:...`, `keyseq:...`, and `cad_cmd:...` actions available in the Unified Studio |",
    f"| **On-Screen Radial Pie Menus** | **{stats['total_radial_menus']}** | 4-slice and 8-slice long-press radial pie menus (`radial_menu.py`) |",
    f"| **24×24 1-Bit E-Ink Icons** | **{stats['total_icons']}** | Dithered monochrome hardware icons compiled into `icon_library.py` |",
    "| **Dedicated Static Hardware Layers** | **16** | 4 Banks × 4 Slots (`Layer 1` – `Layer 16`) stored in `layers_store.json` |",
    "",
    "---",
    "",
    "## 🏆 Tier 1: Deep Native & Multi-Layer Integrations",
    "",
    "These flagship integrations combine dedicated hardware layers, bidirectional IPC/HTTP bridges, and live telemetry:",
    "",
    "### 1. Autodesk Fusion 360 (`fusion360.exe`)",
    "- **Native Python Add-In (`fusion_addin/MacroPadFusionBridge/`)**: Executes Fusion 360 commands directly via the internal Autodesk API over localhost port `18842` without relying on fragile keystroke simulation.",
    "- **Assigned Hardware Layers**: **Layer 13** (Primary 3D Design Grid) + **Layers 5–12** (8-Layer CAD Bank covering Draw, Modify, Construct, Annotate, Inspect, and View).",
    "- **Hold Radial Pie Menus**: Holding any key (`>= 250ms`) opens a transparent Qt radial pie menu centered at the mouse cursor (Sketch, Extrude/Solids, Modify, Construct, Inspect, Views, plus 3Dconnexion Menus).",
    "- **3Dconnexion Library Expansion**: +21 additional harvested functions (`Home View`, `Perspective with Ortho Faces`, `Shaded with Visible Edges`, `Timeline Play`, etc.).",
    "",
    "### 2. Discord Live Voice Call Controller (`discord.exe`)",
    "- **Local IPC RPC Bridge (`pc_app/discord_rpc.py`)**: Authenticates directly with the local Discord client over Named Pipe `\\\\?\\pipe\\discord-ipc-0`.",
    "- **Assigned Hardware Layer**: **Layer 2** (Automatically activates when Discord is focused or during an active voice call).",
    "- **Live Per-User Volume Grid**: Keys 1–8 dynamically populate with the names, live volume percentages (`0%`–`200%`), and mute indicators of everyone in your current voice channel.",
    "  - **Tap Member Key**: Selects that user for live rotary encoder volume adjustment.",
    "  - **Long-Press Member Key**: Toggles local mute for that specific user.",
    "  - **Key 9**: Toggles Discord Deafen (`DEAFEN CALL` / `UNDEAF CALL`).",
    "  - **Dedicated Key 13**: Instant global Microphone Mute/Unmute with NeoPixel status indicator.",
    "",
    "### 3. Autodesk AutoCAD (`acad.exe`)",
    "- **Assigned Hardware Layers**: Full 8-Layer CAD Bank (**Layers 5–12**):",
    "  - **Layer 5 (Draw)**: `LINE`, `PLINE`, `RECTANG`, `CIRCLE`, `ARC`, `POLYGON`, `SPLINE`, `HATCH`",
    "  - **Layer 6 (Modify)**: `MOVE`, `COPY`, `ROTATE`, `TRIM`, `EXTEND`, `OFFSET`, `MIRROR`, `SCALE`",
    "  - **Layer 7 (Construct)**: `FILLET`, `CHAMFER`, `JOIN`, `EXPLODE`, `BREAK`, `ALIGN`, `ARRAY`, `EXTRUDE`",
    "  - **Layer 8 (Layers)**: `LAYER`, `LAYISO`, `LAYUNISO`, `LAYOFF`, `LAYON`, `LAYFRZ`, `LAYMCUR`, `MATCHPROP`",
    "  - **Layer 9 (Annotate)**: `DIM`, `DIMLINEAR`, `DIMALIGNED`, `DIMANGULAR`, `DIMRADIUS`, `MLEADER`, `MTEXT`, `TABLE`",
    "  - **Layer 10 (Snaps & Grid)**: `OSNAP`, `ORTHO`, `GRID`, `SNAP`, `DYNMODE`, `POLAR`, `ISODRAFT`, `QP`",
    "  - **Layer 11 (Blocks & Inspect)**: `INSERT`, `BLOCK`, `WBLOCK`, `XREF`, `DIST`, `AREA`, `ID`, `PURGE`",
    "  - **Layer 12 (View & Plot)**: `ZOOM EXTENTS`, `ZOOM WINDOW`, `PAN`, `REGEN`, `PLOT`, `PSA`, `VIEW`, `3DORBIT`",
    "- **3Dconnexion Library Expansion**: +34 harvested functions and **8 Radial Pie Menus**.",
    "",
    "### 4. Home Assistant & Smart Room Control (`home_assistant/`)",
    "- **MQTT Native Discovery**: Publishes real-time key events, encoder turns, and battery telemetry (`vbat`, `batt_pct`, `rssi`, `state`) to `192.168.1.62:1883`.",
    "- **Dedicated Key 5**: Tap to toggle smart room lighting; hold for `MOD` lighting scenes.",
    "- **Assigned Hardware Layer**: **Layer 3** (Smart Home & Room Automation scenes).",
    "",
    "### 5. Adobe Photoshop (`photoshop.exe`)",
    "- **Assigned Hardware Layer**: **Layer 14** (Brush, Eraser, Marquee, Lasso, Clone Stamp, New Layer, Free Transform, Undo, Deselect).",
    "- **3Dconnexion Library Expansion**: +22 harvested functions and **4 Radial Pie Menus** (`Fit on Screen`, `100% Zoom`, `Brush Size +/-`, `Toggle Rulers/Extras`).",
    "",
    "---",
    "",
    "## 💻 Tier 2: Installed Applications Wired on This Workstation",
    "",
    "In addition to the Tier 1 integrations above, the following applications **currently installed on this PC** automatically activate their tailored 3Dconnexion 9-key grid, 24×24 E-Ink icons, and Hold Radial Menus whenever focused in **Auto-App Mode**:",
    "",
    "| Application | Executable(s) | Auto-Loaded 9-Key Grid (`Key 1` – `Key 9`) | Radial Menus | Total Functions |",
    "| :--- | :--- | :--- | :---: | :---: |",
    "| **Bambu Studio** | `bambu-studio.exe` | `MOVE` (`M`) · `SCALE` (`S`) · `ROTATE` (`R`) · `LAY ON FA` (`F`) · `MESH BOOL` (`B`) · `TEXT SHAP` (`T`) · `CUT` (`Ctrl+X`) · `SUPPORTS` (`L`) · `SLICE PLA` (`Ctrl+R`) | 2 | 26 |",
    "| **OrcaSlicer** | `orca-slicer.exe` | `MOVE` (`M`) · `SCALE` (`S`) · `ROTATE` (`R`) · `LAY ON FA` (`F`) · `SUPPORT P` (`L`) · `SEAM PAIN` (`P`) · `CUT` (`C`) · `ARRANGE` (`A`) · `SLICE` (`Ctrl+R`) | 2 | 24 |",
    "| **KiCad 9.0 (Schematic & PCB)** | `kicad.exe`, `eeschema.exe`, `pcbnew.exe` | **Schematic**: `ESC` · `FIT` · `WIRE` · `BUS` · `JUNCTION` · `ADD SYMBO` · `ADD POWER` · `UNDO` · `REDO`<br>**PCB Editor**: `ESC` · `FIT` · `ROUTE TRA` · `ADD VIA` · `ADD FILLE` · `3D VIEWER` · `MEASURE` · `UNDO` · `REDO` | — | 18 |",
    "| **Microsoft Paint** | `mspaint.exe` | `NEW` · `SELECT` · `PENCIL` · `ERASER` · `TEXT` · `GRID` · `RULERS` · `IMAGE PRO` · `FULL SCRE` | — | 19 |",
    "| **Opera / Chrome / Edge** | `opera.exe`, `chrome.exe`, `msedge.exe` | `100%` · `HOME` · `REFRESH` · `BOTTOM` · `INPRIVATE` · `NEW TAB` · `FIND ON P` · `HISTORY` · `DOWNLOADS` | 4 | 22 |",
    "| **Windows File Explorer** | `explorer.exe` | `NEW FILE` · `RENAME` · `FULL SCRE` · `PROPERTIE` · `BACK` · `FORWARD` · `TASK MANA` · `SETTINGS` · `EMOJIS` | 1 | 25 |",
    "| **Windows Notepad** | `notepad.exe` | `FIND NEXT` · `TIME/DATE` · `NEW` · `FIND PREV` · `REPLACE` · `SELECT AL` · `OPEN` · `SAVE AS` · `PRINT` | — | 12 |",
    "| **Task Manager & Photo Viewer** | `taskmgr.exe`, `dllhost.exe` | Window & View controls (`Actual Size`, `Fit to Window`, `Rotate`, `Delete`, `Next/Prev`) | — | 6 |",
    "",
    "---",
    "",
    "## 🗂️ Tier 3: Complete 187 Action-Rich 3Dconnexion Application Profiles",
    "",
    "Every profile below is pre-compiled in [`pi_app/tdx_harvested.json`](pi_app/tdx_harvested.json). It will **auto-activate with zero configuration** when its executable is focused in Auto-App Mode, or can be imported onto any static hardware layer via the **📦 3Dconnexion Library** browser in the Unified Web Studio (`http://192.168.1.62:5000/`).",
    "",
    "| # | Application Name | Matched Executables | Actions | Radial Menus | Default Auto-Grid Preview (Top Keys) |",
    "| :-: | :--- | :--- | :---: | :---: | :--- |",
]

for idx, a in enumerate(apps_with_funcs, 1):
    name = a["name"].replace("|", "/")
    exes_list = a.get("exes", [])
    exes = ", ".join(f"`{e}`" for e in exes_list[:3])
    if len(exes_list) > 3:
        exes += f" *(+{len(exes_list) - 3})*"
    if not exes:
        exes = "*(Global / Template)*"
    f_cnt = len(a.get("actions", []))
    r_cnt = len(a.get("radial_menus", []))
    grid = a.get("recommended_cells", [])
    preview_labels = [g.get("label", "") for g in grid if g.get("label")][:6]
    if not preview_labels:
        preview_labels = [fn.get("label", "") for fn in a.get("actions", [])[:6]]
    preview_str = " · ".join(f"`{lbl}`" for lbl in preview_labels if lbl)
    lines.append(f"| {idx} | **{name}** | {exes} | {f_cnt} | {r_cnt} | {preview_str} |")

lines.extend([
    "",
    "---",
    "",
    "## 🛰️ Tier 4: Additional 73 Tracked 3D/CAD Application Profiles",
    "",
    "These 73 profiles from the 3Dconnexion library provide executable detection and inherit the global 3Dconnexion standard view/navigation macro set (or Universal productivity controls):",
    "",
    "| # | Application Name | Matched Executables | Profile ID |",
    "| :-: | :--- | :--- | :--- |",
])

for idx, a in enumerate(apps_view_only, 1):
    name = a["name"].replace("|", "/")
    exes_list = a.get("exes", [])
    exes = ", ".join(f"`{e}`" for e in exes_list[:4]) or "*(Inherited)*"
    pid = a.get("id", "")
    lines.append(f"| {idx} | **{name}** | {exes} | `{pid}` |")

lines.extend([
    "",
    "---",
    "",
    "## 🛠️ Re-Harvesting or Updating Profiles",
    "",
    "To re-harvest profiles after updating 3DxWare drivers or adding custom user `.xml` configs:",
    "",
    "```bash",
    "python tools/harvest_3dconnexion.py",
    "```",
    "",
    "This regenerates `pi_app/tdx_harvested.json` with all decoded USB HID scan-code macros, multi-step sequences, radial pie menus, and 24×24 1-bit E-Ink icons.",
    "",
])

out_path = ROOT / "INTEGRATIONS.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {out_path} with {len(lines)} lines.")
