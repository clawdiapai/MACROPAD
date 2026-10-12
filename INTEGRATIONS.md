# 🧩 MacroPad Comprehensive Application Integrations Catalog

This document provides the complete reference of all **native API bridges**, **multi-layer static application profiles**, and **312 multi-source peripheral driver presets** (3Dconnexion, Loupedeck, TourBox, Wacom, PowerUser) built into the MacroPad ecosystem.

---

## 📊 Integration Ecosystem at a Glance

| Metric | Count | Description |
| :--- | :---: | :--- |
| **Total Application Profiles** | **312** | Pre-configured application definitions across CAD, Creative Suite, Coding, Streaming & Productivity |
| **Hardware Driver Presets** | **398** | Hardware profiles harvested across 3Dconnexion, Loupedeck, TourBox, Wacom & PowerUser |
| **Multi-Source Preset Apps** | **70** | Applications with selectable presets (e.g. choose between 3Dx, Loupedeck, TourBox, Wacom, or PowerUser) |
| **Executable Actions & Macros** | **2,810** | Ready-to-use `hotkey:...`, `keyseq:...`, and `cad_cmd:...` actions available in Unified Studio |
| **On-Screen Radial Pie Menus** | **427** | 4-slice and 8-slice long-press radial pie menus (`radial_menu.py`) |
| **24×24 1-Bit E-Ink Icons** | **3,560** | Dithered monochrome hardware icons compiled into `icon_library.py` |
| **Dedicated Static Hardware Layers** | **16** | 4 Banks × 4 Slots (`Layer 1` – `Layer 16`) stored in `layers_store.json` |

---

## 🔀 Multi-Source Hardware Presets & Source Selector

MacroPad unifies driver presets from **5 different hardware ecosystems**:
1. **🧊 3Dconnexion (`3DxWare`)**: Precision CAD/CAM, 3D DCC, and 3D printing slicer navigation and command macros.
2. **🎛️ Loupedeck (v5.9)**: Video editing, timeline cutting, color grading, photo retouching, and audio live-mixing macros.
3. **🎮 TourBox Console (v5.11)**: Digital illustration, raster manipulation, and RAW darkroom hotkey mappings.
4. **✒️ Wacom Tablet Driver (v6.4)**: Keystroke gestures, stylus buttons, and canvas navigation mappings.
5. **⚡ MacroPad Power-User Curated**: 50 high-impact productivity, development, gaming, and engineering integrations.

For applications supported across multiple drivers (e.g. **Blender**, **Adobe Photoshop**, **Adobe Lightroom**, **Adobe Premiere Pro**, **Adobe After Effects**, **Adobe Illustrator**, **Capture One**, **Ableton Live**, **SolidWorks**, **Fusion 360**), presets are grouped under a single canonical identity. In the **Unified Web Studio (`http://192.168.1.62:5000/`)**, you can:
- 🔄 **Switch Preset Tabs**: Instant live preview of the 3×3 E-Ink button grid, radial pie menus, and hotkeys for each hardware source.
- ⭐ **Set Active Preset**: Choose which driver source acts as the default auto-loaded layout in Auto-App Mode.
- 🚀 **1-Click Import**: Deploy any specific preset source onto one of the 16 static hardware layers.

---

## 🏆 Tier 1: Deep Native & Multi-Layer Integrations

These flagship integrations combine dedicated hardware layers, bidirectional IPC/HTTP bridges, and live telemetry:

### 1. Autodesk Fusion 360 (`fusion360.exe`)
- **Native Python Add-In (`fusion_addin/MacroPadFusionBridge/`)**: Executes Fusion 360 commands directly via the internal Autodesk API over localhost port `18842` without relying on fragile keystroke simulation.
- **Assigned Hardware Layers**: **Layer 13** (Primary 3D Design Grid) + **Layers 5–12** (8-Layer CAD Bank covering Draw, Modify, Construct, Annotate, Inspect, and View).
- **Hold Radial Pie Menus**: Holding any key (`>= 250ms`) opens a transparent Qt radial pie menu centered at the mouse cursor (Sketch, Extrude/Solids, Modify, Construct, Inspect, Views, plus 3Dconnexion Menus).
- **3Dconnexion Library Expansion**: +21 additional harvested functions (`Home View`, `Perspective with Ortho Faces`, `Shaded with Visible Edges`, `Timeline Play`, etc.).

### 2. Discord Live Voice Call Controller (`discord.exe`)
- **Local IPC RPC Bridge (`pc_app/discord_rpc.py`)**: Authenticates directly with the local Discord client over Named Pipe `\\?\pipe\discord-ipc-0`.
- **Assigned Hardware Layer**: **Layer 2** (Automatically activates when Discord is focused or during an active voice call).
- **Live Per-User Volume Grid**: Keys 1–8 dynamically populate with the names, live volume percentages (`0%`–`200%`), and mute indicators of everyone in your current voice channel.
  - **Tap Member Key**: Selects that user for live rotary encoder volume adjustment.
  - **Long-Press Member Key**: Toggles local mute for that specific user.
  - **Key 9**: Toggles Discord Deafen (`DEAFEN CALL` / `UNDEAF CALL`).
  - **Dedicated Key 13**: Instant global Microphone Mute/Unmute with NeoPixel status indicator.

### 3. Autodesk AutoCAD (`acad.exe`)
- **Assigned Hardware Layers**: Full 8-Layer CAD Bank (**Layers 5–12**):
  - **Layer 5 (Draw)**: `LINE`, `PLINE`, `RECTANG`, `CIRCLE`, `ARC`, `POLYGON`, `SPLINE`, `HATCH`
  - **Layer 6 (Modify)**: `MOVE`, `COPY`, `ROTATE`, `TRIM`, `EXTEND`, `OFFSET`, `MIRROR`, `SCALE`
  - **Layer 7 (Construct)**: `FILLET`, `CHAMFER`, `JOIN`, `EXPLODE`, `BREAK`, `ALIGN`, `ARRAY`, `EXTRUDE`
  - **Layer 8 (Layers)**: `LAYER`, `LAYISO`, `LAYUNISO`, `LAYOFF`, `LAYON`, `LAYFRZ`, `LAYMCUR`, `MATCHPROP`
  - **Layer 9 (Annotate)**: `DIM`, `DIMLINEAR`, `DIMALIGNED`, `DIMANGULAR`, `DIMRADIUS`, `MLEADER`, `MTEXT`, `TABLE`
  - **Layer 10 (Snaps & Grid)**: `OSNAP`, `ORTHO`, `GRID`, `SNAP`, `DYNMODE`, `POLAR`, `ISODRAFT`, `QP`
  - **Layer 11 (Blocks & Inspect)**: `INSERT`, `BLOCK`, `WBLOCK`, `XREF`, `DIST`, `AREA`, `ID`, `PURGE`
  - **Layer 12 (View & Plot)**: `ZOOM EXTENTS`, `ZOOM WINDOW`, `PAN`, `REGEN`, `PLOT`, `PSA`, `VIEW`, `3DORBIT`
- **3Dconnexion Library Expansion**: +34 harvested functions and **8 Radial Pie Menus**.

### 4. Home Assistant & Smart Room Control (`home_assistant/`)
- **MQTT Native Discovery**: Publishes real-time key events, encoder turns, and battery telemetry (`vbat`, `batt_pct`, `rssi`, `state`) to `192.168.1.62:1883`.
- **Dedicated Key 5**: Tap to toggle smart room lighting; hold for `MOD` lighting scenes.
- **Assigned Hardware Layer**: **Layer 3** (Smart Home & Room Automation scenes).

### 5. Adobe Photoshop (`photoshop.exe`)
- **Assigned Hardware Layer**: **Layer 14** (Brush, Eraser, Marquee, Lasso, Clone Stamp, New Layer, Free Transform, Undo, Deselect).
- **3Dconnexion Library Expansion**: +22 harvested functions and **4 Radial Pie Menus** (`Fit on Screen`, `100% Zoom`, `Brush Size +/-`, `Toggle Rulers/Extras`).

---

## 💻 Tier 2: Installed Applications Wired on This Workstation

In addition to the Tier 1 integrations above, the following applications **currently installed on this PC** automatically activate their tailored 3Dconnexion 9-key grid, 24×24 E-Ink icons, and Hold Radial Menus whenever focused in **Auto-App Mode**:

| Application | Executable(s) | Auto-Loaded 9-Key Grid (`Key 1` – `Key 9`) | Radial Menus | Total Functions |
| :--- | :--- | :--- | :---: | :---: |
| **Bambu Studio** | `bambu-studio.exe` | `MOVE` (`M`) · `SCALE` (`S`) · `ROTATE` (`R`) · `LAY ON FA` (`F`) · `MESH BOOL` (`B`) · `TEXT SHAP` (`T`) · `CUT` (`Ctrl+X`) · `SUPPORTS` (`L`) · `SLICE PLA` (`Ctrl+R`) | 2 | 26 |
| **OrcaSlicer** | `orca-slicer.exe` | `MOVE` (`M`) · `SCALE` (`S`) · `ROTATE` (`R`) · `LAY ON FA` (`F`) · `SUPPORT P` (`L`) · `SEAM PAIN` (`P`) · `CUT` (`C`) · `ARRANGE` (`A`) · `SLICE` (`Ctrl+R`) | 2 | 24 |
| **KiCad 9.0 (Schematic & PCB)** | `kicad.exe`, `eeschema.exe`, `pcbnew.exe` | **Schematic**: `ESC` · `FIT` · `WIRE` · `BUS` · `JUNCTION` · `ADD SYMBO` · `ADD POWER` · `UNDO` · `REDO`<br>**PCB Editor**: `ESC` · `FIT` · `ROUTE TRA` · `ADD VIA` · `ADD FILLE` · `3D VIEWER` · `MEASURE` · `UNDO` · `REDO` | — | 18 |
| **Microsoft Paint** | `mspaint.exe` | `NEW` · `SELECT` · `PENCIL` · `ERASER` · `TEXT` · `GRID` · `RULERS` · `IMAGE PRO` · `FULL SCRE` | — | 19 |
| **Opera / Chrome / Edge** | `opera.exe`, `chrome.exe`, `msedge.exe` | `100%` · `HOME` · `REFRESH` · `BOTTOM` · `INPRIVATE` · `NEW TAB` · `FIND ON P` · `HISTORY` · `DOWNLOADS` | 4 | 22 |
| **Windows File Explorer** | `explorer.exe` | `NEW FILE` · `RENAME` · `FULL SCRE` · `PROPERTIE` · `BACK` · `FORWARD` · `TASK MANA` · `SETTINGS` · `EMOJIS` | 1 | 25 |
| **Windows Notepad** | `notepad.exe` | `FIND NEXT` · `TIME/DATE` · `NEW` · `FIND PREV` · `REPLACE` · `SELECT AL` · `OPEN` · `SAVE AS` · `PRINT` | — | 12 |
| **Task Manager & Photo Viewer** | `taskmgr.exe`, `dllhost.exe` | Window & View controls (`Actual Size`, `Fit to Window`, `Rotate`, `Delete`, `Next/Prev`) | — | 6 |

---

## 🗂️ Tier 3: Complete 187 Action-Rich 3Dconnexion Application Profiles

Every profile below is pre-compiled in [`pi_app/tdx_harvested.json`](pi_app/tdx_harvested.json). It will **auto-activate with zero configuration** when its executable is focused in Auto-App Mode, or can be imported onto any static hardware layer via the **📦 3Dconnexion Library** browser in the Unified Web Studio (`http://192.168.1.62:5000/`).

| # | Application Name | Matched Executables | Actions | Radial Menus | Default Auto-Grid Preview (Top Keys) |
| :-: | :--- | :--- | :---: | :---: | :--- |
| 1 | **3D Sprint** | `3dsprint.exe` | 8 | 1 | `TOP` · `FRONT` · `BACK` · `BOTTOM` · `LEFT` · `RIGHT` |
| 2 | **3DCoat** | `3dcoatgl64.exe` | 7 | 0 | `WHEEL 20` · `WHEEL 20` · `MOVE` · `UNDO` · `REDO` · `SAVE` |
| 3 | **3Dconnexion Viewer** | `sui_viewer.exe` | 4 | 0 | `FIT` · `OPEN` · `QUICKZOOM` · `QUICKZOOM` · `UNDO` · `REDO` |
| 4 | **3DEXPERIENCE** | `3dexperience.exe` | 9 | 0 | `PROPS` · `UNDO` · `REDO` · `LINE` · `ARC` · `EXTRUDE` |
| 5 | **3DEXPERIENCE** | `3dexperience.exe` | 3 | 0 | `UNDO` · `REDO` · `WIREFRAME` · `SAVE` · `COPY` · `PASTE` |
| 6 | **3DF Zephyr** | `3df zephyr.exe` | 3 | 0 | `SAVE` · `UNDO` · `REDO` · `COPY` · `PASTE` · `DELETE` |
| 7 | **3ds Max** | `3dsmax.exe` | 8 | 4 | `WIREFRAME` · `SHADED` · `CHAMFER` · `MIRROR` · `BOX` · `SPHERE` |
| 8 | **3DxUnity3D Editor** | `unity.exe` | 14 | 3 | `MOVE` · `ROTATE` · `SCALE` · `ADD COMP` · `SHADED DR` · `WIREFRM D` |
| 9 | **3Shape ScanIt Dental** | `dentaldesktop.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 10 | **7-Zip** | `7zfm.exe` | 3 | 0 | `OPTIONS` · `ALL` · `DESELECT` · `UNDO` · `REDO` · `SAVE` |
| 11 | **ABAQUS/CAE** | `abqcaeg.exe` | 9 | 2 | `FIT` · `MODEL TRE` · `QUERY` · `MOVIE` · `DATUM` · `CREATE PA` |
| 12 | **ABAQUS/Viewer** | `abqvwrg.exe` | 6 | 0 | `FIT` · `MODEL TRE` · `QUERY` · `DATUM` · `UNDO` · `REDO` |
| 13 | **Adobe Acrobat** | `acrobat.exe` | 4 | 0 | `FIT` · `FIRST PAG` · `LAST PAGE` · `FIND` · `UNDO` · `REDO` |
| 14 | **Adobe Reader** | `acrord32.exe`, `acrobat.exe` | 9 | 1 | `FIT` · `FIT PAGE` · `SEARCH` · `FULLSCREE` · `FIRST PAG` · `LAST PAGE` |
| 15 | **ALLPLAN** | `allplan_20(0[0-9]|1[0-9]|2[0-5]).exe` | 25 | 2 | `WALL` · `PROPS` · `LAYERS` · `MEASURE` · `DIM LINE` · `ELEVATION` |
| 16 | **ALLPLAN** | `allplan_20(2[6-9]|[3-9][0-9]).exe` | 25 | 2 | `WALL` · `PROPS` · `LAYERS` · `MEASURE` · `DIM LINE` · `ELEVATION` |
| 17 | **Altair SimSolid** | `simsolid.exe` | 3 | 0 | `WHEEL 20` · `WHEEL 20` · `FIT` · `UNDO` · `REDO` · `SAVE` |
| 18 | **Altium Designer** | `dxp.exe`, `x2.exe` | 13 | 3 | `FIT` · `3D BOARD` · `2D BOARD` · `BOARD PLA` · `BILL OF M` · `MEASURE D` |
| 19 | **Ansys CFD Viewer** | `pregui_ogl.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 20 | **Ansys ICEM CFD** | `med.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 21 | **Anycubic Slicer Next** | `anycubicslicernext.exe` | 24 | 2 | `MOVE` · `SCALE` · `ROTATE` · `LAY ON FA` · `CUT` · `ARRANGE A` |
| 22 | **AnycubicSlicer** | `anycubic-slicer.exe` | 7 | 1 | `ISO1` · `TOP` · `BOTTOM` · `FRONT` · `BACK` · `LEFT` |
| 23 | **ArcGISEarth** | `arcgisearth.exe` | 18 | 2 | `RESET NOR` · `RESET TIL` · `RESET TIL` · `SETTINGS` · `TABLE OF` · `ADD DATA` |
| 24 | **Archicad** | `archicad.exe` | 12 | 1 | `FLOOR PLA` · `3D WINDOW` · `KB END` · `KB PAGEDO` · `KB ENTER` · `KB HOME` |
| 25 | **ARCHLine.XP** | `archlinexp[0-9]+.bin` | 4 | 1 | `REDO` · `UNDO` · `DISTANCE` · `FIT` · `SAVE` · `COPY` |
| 26 | **ARES Commander** | `aresc.exe` | 23 | 4 | `REDO` · `UNDO` · `MATCH LAY` · `LINE` · `POLYLINE` · `CIRCLE` |
| 27 | **AutoCAD** | `acad.exe` | 53 | 8 | `ARC` · `POLYGON` · `PASTE` · `DIMENSION` · `MEASURE A` · `LENGTHEN` |
| 28 | **AutoCad LT** | `acadlt.exe` | 13 | 1 | `FIT` · `LINE` · `RECTANGLE` · `CIRCLE` · `ARC` · `POLYLINE` |
| 29 | **AutoCAD Start Tab** | `acwebbrowser.exe`, `msedgewebview2.exe` | 19 | 0 | `NEW DRAWI` · `DRAWING` · `NEW TAB` · `NEXT TAB` · `SAMPLES` · `APPLICATI` |
| 30 | **Autodesk 123D** | `123d.exe` | 5 | 0 | `FIT` · `PASTE` · `UNDO` · `REDO` · `KB DELETE` · `SAVE` |
| 31 | **Autodesk Fusion** | `fusion360.exe`, `fusion.exe` | 18 | 2 | `EXTRUDE` · `FILLET` · `HOLE` · `JOINT` · `MOVE` · `LINE` |
| 32 | **Autodesk Fusion** | `fusion360.exe`, `fusion.exe` | 24 | 2 | `SHADED` · `SHADED WI` · `WIREFRAME` · `LINE` · `MIRROR` · `FILLET` |
| 33 | **Autodesk Navisworks** | `roamer.exe` | 10 | 1 | `SHADED` · `WIREFRAME` · `ANGLE` · `FIT / RES` · `TOP` · `LEFT` |
| 34 | **Autodesk Navisworks** | `roamer.exe` | 3 | 1 | `ANGLE` · `SHADED` · `WIREFRAME` · `UNDO` · `REDO` · `SAVE` |
| 35 | **Autodesk Revit** | `revit.exe` | 11 | 1 | `FIT` · `PROPS` · `MOVE` · `ROTATE` · `TEXT` · `COPY` |
| 36 | **Autodesk Showcase** | `showcase.exe` | 69 | 0 | `DUPLICATE` · `ORGANIZER` · `TRANSFORM` · `COPY TRAN` · `PASTE TRA` · `REVERT TR` |
| 37 | **Bambu Studio** | `bambu-studio.exe` | 26 | 2 | `MOVE` · `SCALE` · `ROTATE` · `LAY ON FA` · `MESH BOOL` · `TEXT SHAP` |
| 38 | **BIMcollab Zoom** | `bimcollab zoom.exe` | 6 | 4 | `LINE` · `ELLIPSE` · `DIMENSION` · `RECTANGLE` · `TEXT` · `FIT` |
| 39 | **Blender** | `blender.exe`, `blender-app.exe` | 43 | 7 | `SET PAREN` · `TRANSFORM` · `INSERT KE` · `FRONT` · `RIGHT` · `TOP` |
| 40 | **BricsCAD** | `bricscad.exe` | 18 | 4 | `UNDO` · `REDO` · `LINE` · `POLYLINE` · `CIRCLE` · `RECTANGLE` |
| 41 | **Cadwork 3D** | `3d.exe` | 2 | 0 | `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` · `DELETE` |
| 42 | **Capture** | `capture [0-9]+.exe` | 19 | 2 | `WIREFRAME` · `PLOT` · `LIVE` · `BY LAYER` · `BY LOCATI` · `BY DRAWIN` |
| 43 | **CATIA** | `cnext.exe` | 11 | 0 | `PROPS` · `UNDO` · `REDO` · `LINE` · `ARC` · `EXTRUDE` |
| 44 | **CETOL MultiCAD** | `cetolmc.exe` | 13 | 0 | `NEW` · `OPEN` · `OPTIONS` · `SAVE` · `COPY` · `CUT` |
| 45 | **Chaos Vantage** | `vantage.exe` | 4 | 2 | `ROTATE` · `SCALE` · `REDO` · `UNDO` · `SAVE` · `COPY` |
| 46 | **CharacterCreator** | `charactercreator.exe` | 9 | 3 | `HOME` · `UNDO` · `REDO` · `MOVE` · `ROTATE` · `SCALE` |
| 47 | **Chief Architect** | `chief architect premier x[0-9]+.exe` | 18 | 3 | `FIT` · `OBJECT` · `PERSP FUL` · `ORTHO FUL` · `STRAIGHT` · `HINGED DO` |
| 48 | **CHITUBOX Basic** | `chitubox_basic.exe` | 12 | 1 | `MOVE` · `ROTATE` · `OPEN` · `SAVE` · `SCALE` · `UNDO` |
| 49 | **CHITUBOX Pro** | `chitubox pro.exe` | 19 | 2 | `MOVE` · `SCALE` · `ROTATE` · `ADD SUPPO` · `DELETE SU` · `EDIT SUPP` |
| 50 | **Chrome** | `chrome.exe` | 22 | 4 | `100%` · `HOME KEY` · `REFRESH` · `GO TO BOT` · `IN PRIVAT` · `NEW TAB` |
| 51 | **CINEMA 4D** | `cinema 4d.exe` | 29 | 2 | `FIT` · `PLAY FORW` · `MIRROR` · `STITCH AN` · `BEVEL` · `MATRIX EX` |
| 52 | **CINEMA 4D** | `cinema 4d.exe` | 9 | 2 | `COMMAND S` · `CYLINDER` · `SPHERE` · `POLYGON` · `TEXT` · `MOVE` |
| 53 | **CINEMA 4D 64 Bit** | `cinema 4d 64 bit.exe` | 28 | 2 | `FIT` · `PLAY FORW` · `MIRROR` · `STITCH AN` · `BEVEL` · `MATRIX EX` |
| 54 | **CINEMA 4D Demo** | `cinema 4d demo.exe` | 28 | 2 | `FIT` · `PLAY FORW` · `MIRROR` · `STITCH AN` · `BEVEL` · `MATRIX EX` |
| 55 | **CIROS Studio** | `ciros studio.donotship.rif.exe`, `ciros studio.exe`, `ciros studio festo.exe` *(+6)* | 11 | 1 | `FRONT` · `BACK` · `BOTTOM` · `TOP` · `LEFT` · `RIGHT` |
| 56 | **Citrix Receiver (read-only)** | `wfica32.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 57 | **CMM-Manager** | `cmmmgr.exe` | 3 | 0 | `POINT` · `LINE` · `CIRCLE` · `UNDO` · `REDO` · `SAVE` |
| 58 | **CMS IntelliCAD** | `cmsicad.exe` | 11 | 4 | `NEW` · `OPEN` · `OPTIONS` · `LINE` · `POLYLINE` · `COPY` |
| 59 | **Creality Print** | `crealityprint.exe` | 7 | 0 | `FIT` · `TOP` · `BOTTOM` · `FRONT` · `BACK` · `RIGHT` |
| 60 | **Creo Elements/Direct Modeling** | `soliddesigner.exe`, `solidd~1.exe` | 20 | 3 | `QUICKZOOM` · `QUICKZOOM` · `FULLSCREE` · `FIT TO` · `SHADED/WI` · `WP BORDER` |
| 61 | **Creo Parametric** | `xtop.exe` | 51 | 20 | `REPAINT` · `SHADE` · `UNHIDE` · `REFIT` · `APPLY CHA` · `HIDE` |
| 62 | **CreoView** | `productview.exe` | 15 | 1 | `FIT` · `TOP` · `RIGHT` · `FRONT` · `ZOOM ALL` · `LEFT` |
| 63 | **CST STUDIO SUITE** | `modeler.exe`, `3dviewer.exe`, `modeler_amd64.exe` *(+7)* | 10 | 0 | `FIT` · `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` |
| 64 | **CStudio** | `cstudio.exe` | 9 | 1 | `WHEEL 20` · `WHEEL 20` · `SAVE` · `UNDO` · `REDO` · `MOVE` |
| 65 | **Cube3D** | `cube3d.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 66 | **Cyclone 3DR** | `3drviewer.exe`, `3dr.exe` | 8 | 1 | `FLY` · `ORBIT PER` · `ORBIT ORT` · `PANORAMA` · `TOP` · `RIGHT` |
| 67 | **D5 Render** | `d5_launcher.exe` | 12 | 1 | `WHEEL 20` · `WHEEL 20` · `UNDO` · `REDO` · `SAVE` · `WIREFRAME` |
| 68 | **DELMIA** | `delmia.exe` | 10 | 0 | `PROPS` · `UNDO` · `REDO` · `LINE` · `ARC` · `EXTRUDE` |
| 69 | **Dental Wings Chairside CAD** | `javaw.exe` | 10 | 0 | `FIT` · `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` |
| 70 | **Dental Wings Easy Mode** | `javaw.exe` | 9 | 0 | `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` · `TABAPPLIC` |
| 71 | **DentalCAD** | `dentalcadapp.exe` | 15 | 2 | `FIT` · `MEASUREME` · `DISTANCE` · `CUT` · `ROLL MODE` · `ROLL MODE` |
| 72 | **Desktop** | `explorer.exe`, `searchapp.exe`, `cortana.exe` *(+1)* | 8 | 1 | `PROJECT` · `PASTE` · `COPY` · `TASKMANAG` · `SETTINGS` · `TABAPPLIC` |
| 73 | **Deswik.CAD** | `deswik.cad.exe` | 10 | 1 | `SNAP MODE` · `POLYLINE` · `DISTANCE` · `MOVE` · `UNDO` · `REDO` |
| 74 | **DraftSight** | `draftsight.exe` | 11 | 1 | `FIT` · `QUICKZOOM` · `LINE` · `RECTANGLE` · `DIM LINEA` · `MIRROR` |
| 75 | **DraftSight** | `draftsight.exe` | 8 | 1 | `LINE` · `POLYLINE` · `CIRCLE` · `ARC` · `MOVE` · `COPY` |
| 76 | **DWOS Client** | `javaw.exe` | 10 | 0 | `FIT` · `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` |
| 77 | **ENOVIA DMU** | `dmu.exe` | 10 | 0 | `PROPS` · `UNDO` · `REDO` · `LINE` · `ARC` · `EXTRUDE` |
| 78 | **Enscape Archicad** | `archicad.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 79 | **Enscape Revit** | `revit.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 80 | **Enscape Rhino** | `rhino.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 81 | **Enscape SketchUp** | `sketchup.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 82 | **Enscape Vectorworks** | `vectorworks.*.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 83 | **ExoViewer 3D** | `exoviewer3d.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 84 | **Firefox** | `firefox.exe` | 22 | 4 | `100%` · `HOME KEY` · `REFRESH` · `GO TO BOT` · `IN PRIVAT` · `NEW TAB` |
| 85 | **FreeCAD** | `freecad.exe` | 31 | 26 | `SAVE` · `UNDO` · `REDO` · `NEW` · `OPEN` · `DIMENSION` |
| 86 | **Fusion Electronics** | `fusion360.exe`, `fusion.exe` | 10 | 4 | `SAVE` · `UNDO` · `REDO` · `LINE` · `TEXT` · `CIRCLE` |
| 87 | **GO2cam** | `go2cam.exe`, `go2camdemo.exe`, `lioncam.exe` | 4 | 0 | `OPEN` · `FIT` · `ZOOM IN` · `ZOOM OUT` · `UNDO` · `REDO` |
| 88 | **Google Earth** | `googleearth.exe` | 23 | 3 | `FULLSCREE` · `RESET TIL` · `RESET TIL` · `RESET NOR` · `PATH` · `GRID` |
| 89 | **GPlay** | `gplay.exe` | 3 | 0 | `FIT` · `ZOOM IN` · `ZOOM OUT` · `UNDO` · `REDO` · `SAVE` |
| 90 | **GstarCAD** | `gcad.exe` | 18 | 3 | `WHEEL 20` · `WHEEL 20` · `POLYLINE` · `CIRCLE` · `RECTANGLE` · `HATCH` |
| 91 | **GUI Sync SDK Demo** | `guisync_sdk.exe` | 6 | 0 | `FIT` · `KB ESC` · `KB ENTER` · `KB DELETE` · `KB TAB` · `KB SPACE` |
| 92 | **HiCAD** | `hicad.exe` | 6 | 2 | `FILLET` · `CHAMFER` · `UNDO` · `REDO` · `KB ESC` · `FIT` |
| 93 | **HLibrary** | `hlibrary.exe` | 10 | 1 | `WHEEL 20` · `WHEEL 20` · `MOVE` · `ROTATE` · `SCALE` · `REDO` |
| 94 | **Home** | `adcefwebbrowser.exe` | 18 | 0 | `NEW DRAWI` · `DRAWING` · `NEW TAB` · `NEXT TAB` · `SAMPLES` · `APPLICATI` |
| 95 | **Houdini** | `houdini.exe`, `houdinifx.exe`, `hindie.exe` *(+2)* | 23 | 2 | `RM VIEW` · `RM MODELI` · `MOVE` · `ROTATE` · `SCALE` · `PLAY/PAUS` |
| 96 | **Houdini Core** | `houdinicore.exe`, `hescape.exe` | 23 | 2 | `RM VIEW` · `RM MODELI` · `MOVE` · `ROTATE` · `SCALE` · `PLAY/PAUS` |
| 97 | **HStudio** | `hstudio.exe` | 9 | 1 | `WHEEL 20` · `WHEEL 20` · `MOVE` · `ROTATE` · `SCALE` · `REDO` |
| 98 | **hyperMILL** | `hmc.exe` | 12 | 5 | `SAVE` · `REDO` · `UNDO` · `DIMENSION` · `TEXT` · `RECTANGLE` |
| 99 | **hypsoCAD** | `dentalcad.exe` | 3 | 0 | `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` · `DELETE` |
| 100 | **iClone** | `iclone.exe` | 19 | 0 | `MOVE` · `ROTATE` · `SCALE` · `UNDO` · `REDO` · `COPY` |
| 101 | **ideaMaker** | `ideamaker.exe` | 1 | 0 | `HOME VIEW` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 102 | **IntelliCAD** | `icad.exe` | 11 | 4 | `NEW` · `OPEN` · `OPTIONS` · `LINE` · `POLYLINE` · `COPY` |
| 103 | **Internet Explorer** | `iexplore.exe` | 20 | 3 | `OPEN` · `NEW TAB` · `FIND ON P` · `DUP TAB` · `NEW` · `CLOSE TAB` |
| 104 | **Inventor** | `inventor.exe` | 50 | 52 | `LINE` · `SPLINE` · `OFFSET` · `REDO` · `UNDO` · `CUT` |
| 105 | **Inventor LT** | `inventor.exe` | 6 | 0 | `QUICKZOOM` · `QUICKZOOM` · `OPEN` · `MEASURE` · `FIND` · `FIT` |
| 106 | **Inventor RO** | `invro.exe` | 6 | 0 | `QUICKZOOM` · `QUICKZOOM` · `OPEN` · `MEASURE` · `FIND` · `FIT` |
| 107 | **IRONCAD** | `ironcad.exe` | 1 | 0 | `KB ESC` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 108 | **IRONCAD COMPOSE** | `iccompose.exe` | 1 | 0 | `KB ESC` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 109 | **IRONCAD DRAFT** | `icdraft.exe` | 1 | 0 | `KB ESC` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 110 | **IRONCAD INOVATE** | `inovate.exe` | 1 | 0 | `KB ESC` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 111 | **K-Compare Revision 4.0** | `kcomparerevision.exe` | 3 | 0 | `WHEEL 20` · `WHEEL 20` · `ANGLE` · `UNDO` · `REDO` · `SAVE` |
| 112 | **K-Display View 4.0** | `kdisplayview.exe` | 8 | 1 | `WHEEL 20` · `WHEEL 20` · `MOVE` · `SHADED` · `WIREFRAME` · `PRINT` |
| 113 | **KeyCreator** | `kc.exe` | 16 | 0 | `CONSTRUCT` · `WIREFRAME` · `SHADED` · `TREE` · `LAYOUT TO` · `TOP` |
| 114 | **KiCad** | `kicad.exe` | 51 | 5 | `FOOTPRINT` · `ADD SYMBO` · `ROTATE CW` · `EDIT VALU` · `PCB EDITO` · `ADD WIRE` |
| 115 | **KiCad 3D** | `kicad.exe`, `pcbnew.exe` | 12 | 2 | `ORTHO` · `MEASURE` · `REFRESH` · `ROTATE X` · `ROTATE Y` · `ROTATE Z` |
| 116 | **KiCad PCB** | `kicad.exe`, `pcbnew.exe` | 20 | 3 | `SCHEMATIC` · `ROUTE TRA` · `3D VIEWER` · `SEARCH` · `DIFF PAIR` · `DRAW LINE` |
| 117 | **KiCad Schematic** | `kicad.exe`, `eeschema.exe` | 27 | 5 | `FOOTPRINT` · `ADD SYMBO` · `ROTATE CW` · `EDIT VALU` · `PCB EDITO` · `ADD WIRE` |
| 118 | **KOMPAS-3D** | `kompas.exe` | 5 | 0 | `FIT` · `KB F9` · `SAVEAS` · `NEW` · `KB ESC` · `UNDO` |
| 119 | **LightWave** | `modeler.exe`, `layout.exe` | 9 | 0 | `FIT` · `RIGHT` · `COPY` · `CUT` · `PASTE` · `ALIGNWIND` |
| 120 | **Lychee Slicer** | `lycheeslicer.exe` | 1 | 0 | `GO HOME/F` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 121 | **Mastercam X** | `mastercam.exe` | 24 | 2 | `FIT` · `TOP` · `FRONT` · `BACK` · `BOTTOM` · `RIGHT` |
| 122 | **Mastercam X** | `mastercam.exe` | 19 | 2 | `ZOOM - TA` · `ZOOM -` · `UN-ZOOM 5` · `SHADE TOG` · `REDRAW` · `HIDE ENTI` |
| 123 | **Maya** | `maya.exe` | 4 | 1 | `EXTRUDE` · `FIT` · `ZOOM IN` · `ZOOM OUT` · `UNDO` · `REDO` |
| 124 | **Microsoft Edge** | `msedge.exe` | 21 | 3 | `REFRESH` · `ADD TO FA` · `FAVORITES` · `NEW TAB` · `NEW` · `NEW INPRI` |
| 125 | **Microsoft Edge** | `microsoftedge.exe`, `microsoftedgecp.exe` | 17 | 4 | `ZOOM 100%` · `ADD CURRE` · `A SEARCH` · `FIND ON P` · `HISTORY P` · `FAVORITES` |
| 126 | **Microsoft Excel** | `excel.exe` | 27 | 2 | `BOLD` · `ITALIC` · `UNDERLINE` · `STRIKETHR` · `FIND` · `REPLACE` |
| 127 | **Microsoft Paint** | `mspaint.exe` | 19 | 0 | `NEW` · `SELECT` · `PENCIL` · `ERASER` · `TEXT` · `GRID` |
| 128 | **Microsoft PowerPoint** | `powerpnt.exe` | 17 | 1 | `BOLD` · `ITALIC` · `UNDERLINE` · `STRIKETHR` · `THESAURUS` · `TRANSLATE` |
| 129 | **Microsoft Teams** | `teams.exe` | 1 | 0 | `MIC MUTE` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 130 | **Microsoft Word** | `winword.exe` | 21 | 2 | `BOLD` · `ITALIC` · `UNDERLINE` · `STRIKETHR` · `FIND` · `REPLACE` |
| 131 | **MicroStation** | `ustation.exe` | 12 | 0 | `FIT` · `CTRL ALT` · `CTRL ALT` · `CTRL ALT` · `CTRL ALT` · `CTRL ALT` |
| 132 | **MicroStation** | `microstation.exe` | 9 | 2 | `TOOLS Q` · `POPUPS` · `MOVE` · `COPY` · `ROTATE` · `SCALE` |
| 133 | **MicroStation CONNECT** | `microstation.exe` | 25 | 1 | `FIT` · `DIM LINEA` · `DIM ELEME` · `DIM ANGUL` · `PLACE TEX` · `PLACE TAB` |
| 134 | **MODO** | `modo.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 135 | **Notepad** | `notepad.exe` | 12 | 0 | `FIND NEXT` · `TIME/DATE` · `NEW` · `FIND PREV` · `REPLACE` · `ZOOM IN` |
| 136 | **NX** | `ugraf.exe` | 35 | 15 | `NEW` · `OPEN` · `SAVE` · `HOLE` · `SPHERE` · `MEASURE` |
| 137 | **Onshape** | `3dxnlserver.exe` | 21 | 9 | `LINE` · `POINT` · `TEXT` · `TRIM` · `MIRROR` · `EXTEND` |
| 138 | **OrcaSlicer** | `orca-slicer.exe` | 24 | 2 | `MOVE` · `SCALE` · `ROTATE` · `LAY ON FA` · `SUPPORT P` · `SLICE PLA` |
| 139 | **Outlook** | `outlook.exe` | 14 | 1 | `BOLD` · `ITALIC` · `UNDERLINE` · `BULLETS` · `FIND` · `REPLACE` |
| 140 | **PhotoModeler** | `photomodeler.*.exe` | 2 | 0 | `PROPS` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 141 | **Photoshop** | `photoshop.exe` | 120 | 9 | `CANCEL` · `FIT ON SC` · `STEP BACK` · `STEP FORW` · `PAN` · `CREATE A` |
| 142 | **Plasticity** | `plasticity.exe` | 19 | 1 | `FRONT` · `RIGHT` · `TOP` · `BOTTOM` · `BACK` · `LEFT` |
| 143 | **PreForm** | `preform.exe` | 1 | 0 | `HOME VIEW` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 144 | **Procore** | `3dxnlserver.exe` | 9 | 1 | `MEASURE T` · `SECTION T` · `OBJECT TR` · `PROPS` · `X-RAY` · `FULL SCRE` |
| 145 | **ProgeCAD** | `pcad.exe` | 24 | 5 | `NEW` · `OPEN` · `HELP` · `LINE` · `RECTANGLE` · `POLYLINE` |
| 146 | **PrusaSlicer** | `prusa-slicer.exe` | 34 | 2 | `MOVE` · `SCALE` · `ROTATE` · `PLACE ON` · `CUT` · `SEAM PAIN` |
| 147 | **Quartis** | `quartis.exe` | 11 | 1 | `ZOOM ON C` · `DISPLAY O` · `TOP` · `LEFT` · `RIGHT` · `FRONT` |
| 148 | **Revizto** | `revizto5.exe` | 9 | 1 | `RULER` · `SECTION` · `NEW ISSUE` · `STAMP` · `OBJECT TR` · `VIEWPOINT` |
| 149 | **Rhinoceros** | `rhino.exe` | 18 | 0 | `WHEEL 20` · `WHEEL 20` · `ZOOMEXTEN` · `MAXIMIZE` · `SHADE` · `SHADESELE` |
| 150 | **Rhinoceros** | `rhino.exe`, `revit.exe` | 136 | 5 | `UNDO` · `REDO` · `RENDER` · `TRIM` · `POLYLINE` · `CYLINDER` |
| 151 | **Rhinoceros 4** | `rhino4.exe` | 22 | 0 | `FIT` · `ZOOM EXTE` · `MAXIMIZE` · `SHADE` · `SHADE SEL` · `UNDO` |
| 152 | **RhinoNL** | `rhino.exe`, `revit.exe` | 133 | 4 | `POLYLINE` · `CYLINDER` · `TRIM` · `LOFT` · `REVOLVE` · `MOVE` |
| 153 | **SDK MCAD Demo** | `mcad.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 154 | **Shapr3D** | `spacemousebridge.exe` | 10 | 1 | `ARC` · `LINE` · `RECTANGLE` · `EXTRUDE` · `REVOLVE` · `LOFT` |
| 155 | **ShellDesigner** | `shelldesigner.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 156 | **Shining3D** | `exscan s.exe`, `exscan hx.exe`, `exscan pro.exe` *(+3)* | 5 | 2 | `UNDO` · `ALL` · `DELETE` · `REDO` · `FIT` · `SAVE` |
| 157 | **SketchUp for Web** | `3dxnlserver.exe` | 30 | 3 | `SELECT` · `PUSH/PULL` · `OFFSET` · `SEARCH` · `LINE` · `RECTANGLE` |
| 158 | **SOFTIMAGE/XSI** | `xsi.exe` | 4 | 1 | `FIT` · `REDO` · `UNDO` · `KB ESC` · `SAVE` · `COPY` |
| 159 | **Solid Edge** | `edge.exe` | 29 | 22 | `SAVE` · `UNDO` · `REDO` · `NEW` · `OPEN` · `OPTIONS` |
| 160 | **SOLIDWORKS** | `sldworks.exe` | 22 | 15 | `HIDE` · `SHOW` · `UNDO` · `SHADED` · `MIRROR` · `LINE` |
| 161 | **SOLIDWORKS Visualize** | `sldworksvisualize.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 162 | **Substance 3D Painter** | `adobe substance 3d painter.*.exe` | 54 | 2 | `PROJECT` · `CLOSE PRO` · `SAVE PROJ` · `NEW PROJE` · `SHOW/HIDE` · `INCREASE` |
| 163 | **Task Manager** | `taskmgr.exe` | 4 | 0 | `OPEN` · `NEW` · `SAVE` · `FIND` · `UNDO` · `REDO` |
| 164 | **Teamcenter** | `visview.exe`, `visview_ng.exe` | 20 | 0 | `FIT ALL` · `PART COLO` · `EXPLODED` · `LEFT` · `BOTTOM` · `BACK` |
| 165 | **Tebis** | `tebis.exe` | 25 | 1 | `FIT` · `FRONT` · `TOP` · `SIDE VIEW` · `SIDE VIEW` · `BOTTOM` |
| 166 | **Tekla Structures** | `teklastructures.exe` | 10 | 0 | `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` · `TABAPPLIC` |
| 167 | **test_action_interface** | `test_action_interface.exe` | 7 | 2 | `NEW` · `OPEN` · `SAVE` · `UNDO` · `REDO` · `COPY` |
| 168 | **TopSolid** | `topsolid.exe` | 9 | 2 | `CIRCLE` · `RECTANGLE` · `DIMENSION` · `GROUP` · `LINE` · `TEXT` |
| 169 | **TopSolid Cam NC Operator** | `topsolid.cam.nc.operator.exe` | 10 | 0 | `OPTIONS` · `RET.ARR` · `7` · `ECHAP` · `F1` · `F2` |
| 170 | **Trimble SketchUp** | `sketchup.exe` | 19 | 8 | `EXPORT 3D` · `WIREFRAME` · `SHADED` · `TEXT` · `UNDO` · `REDO` |
| 171 | **Twinmotion** | `twinmotion.*.exe` | 2 | 1 | `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` · `DELETE` |
| 172 | **UltiMaker Cura** | `ultimaker-cura.exe` | 12 | 1 | `MOVE` · `SCALE` · `ROTATE` · `MIRROR` · `SUPPORT B` · `SLICE` |
| 173 | **Unreal Editor** | `ue4editor.*.exe`, `unrealeditor.*.exe` | 2 | 0 | `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` · `DELETE` |
| 174 | **Unreal Editor (Asset & Play-in-Editor)** | `ue4editor.*.exe`, `unrealeditor.*.exe` | 1 | 0 | `SNIPPINGT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 175 | **Vectorworks** | `vectorworks201[5-9].exe|vectorworks202[0-6].exe` | 12 | 0 | `MODIFY` · `CUT` · `MERGE` · `MIRROR` · `ROTATE` · `FILLET` |
| 176 | **Vectorworks** | `vectorworks202[6-9].exe` | 3 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 177 | **Viewer Demo** | `s3dm_viewer.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 178 | **Windows Explorer** | `explorer.exe` | 25 | 1 | `NEW FILE` · `RENAME` · `FULL SCRE` · `PROPS` · `BACK` · `FORWARD` |
| 179 | **WindowsMediaCenter** | `ehshell.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 180 | **Windowsshellexperience** | `shellui.exe` | 9 | 1 | `PASTE` · `COPY` · `CUT` · `ALIGNWIND` · `ALIGNWIND` · `TABAPPLIC` |
| 181 | **WYSIWYG** | `wyg.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 182 | **XVL Studio** | `xvlstudio2.exe` | 4 | 0 | `FIT` · `UNDO` · `REDO` · `KB ESC` · `SAVE` · `COPY` |
| 183 | **ZBrush** | `zbrush.exe` | 5 | 2 | `REDO` · `SYMMETRY` · `FIT TO ME` · `UNDO` · `REDO` · `SAVE` |
| 184 | **ZBrushCore** | `zbrushcore.exe` | 7 | 2 | `WHEEL 20` · `WHEEL 20` · `REDO` · `UNDO` · `REDO` · `FIT` |
| 185 | **ZBrushCoreMini** | `zbrushcoremini.exe` | 5 | 1 | `FIT` · `REDO` · `UNDO` · `OPEN` · `ZINTENSIT` · `SAVE` |
| 186 | **ZW3D** | `zw3d.exe` | 3 | 1 | `FIT` · `REDO` · `UNDO` · `SAVE` · `COPY` · `PASTE` |
| 187 | **ZW3D_NavLib** | `zw3d.exe` | 38 | 25 | `WHEEL 20` · `WHEEL 20` · `EXTRUDE` · `REVOLVE` · `SWEEP` · `LOFT` |
| 188 | **ZWCAD** | `zwcad.exe` | 16 | 4 | `EXTENTS` · `RECTANGLE` · `HATCH` · `COPY` · `TRIM` · `ROTATE` |

---

## 🛰️ Tier 4: Additional 73 Tracked 3D/CAD Application Profiles

These 73 profiles from the 3Dconnexion library provide executable detection and inherit the global 3Dconnexion standard view/navigation macro set (or Universal productivity controls):

| # | Application Name | Matched Executables | Profile ID |
| :-: | :--- | :--- | :--- |
| 1 | **1Password / Bitwarden** | `1password.exe`, `bitwarden.exe` | `bitwarden` |
| 2 | **3DViewStation** | `3dviewstation.exe` | `3dviewstation` |
| 3 | **3DxUnity3D PlayMode** | `unity.exe` | `3dxunity3d_pm` |
| 4 | **3Shape 3D Viewer** | `3shape_3dviewer.exe` | `3shape_3d_viewer` |
| 5 | **3Shape DentalDesigner** | `dentaldesigner.exe` | `3shape_dentaldesigner` |
| 6 | **3Shape ModelBuilder** | `modelbuilder.exe` | `3shape_modelbuilder` |
| 7 | **3Shape ScanItLibrary** | `scanitlibrary.exe` | `3shape_scanitlibrary` |
| 8 | **Ableton Live** | `ableton live.exe`, `abltonlive.exe` | `ableton_live` |
| 9 | **AC3D** | `ac3d.exe` | `ac3d` |
| 10 | **Adobe After Effects** | `afterfx.exe` | `adobe_after_effects` |
| 11 | **Adobe Bridge** | `bridge.exe` | `adobe_bridge` |
| 12 | **Adobe Illustrator** | `illustrator.exe` | `adobe_illustrator` |
| 13 | **Adobe InDesign** | `indesign.exe` | `adobe_indesign` |
| 14 | **Adobe Lightroom Classic** | `lightroom.exe` | `adobe_lightroom` |
| 15 | **Adobe Premiere Pro** | `premiereproc.exe` | `adobe_premiere_pro` |
| 16 | **Affinity Designer** | `designer.exe`, `affinity designer.exe` | `affinity_designer` |
| 17 | **Affinity Photo** | `photo.exe`, `affinity photo.exe` | `affinity_photo` |
| 18 | **Alibre Design** | `alibre design.exe` | `alibre_design_v2` |
| 19 | **Altair EDEM** | `edem.exe` | `altair_edem` |
| 20 | **Anki** | `anki.exe` | `anki` |
| 21 | **Ansys Discovery** | `discovery.exe` | `ansys_discovery` |
| 22 | **ApplianceDesigner** | `appliancedesigner.exe` | `appliancedesigner` |
| 23 | **Arc** | `arc.exe` | `arcbrowser` |
| 24 | **ArcGIS Pro** | `arcgispro.exe` | `arcgis_pro` |
| 25 | **Arduino IDE** | `arduino_debug.exe`, `arduino.exe` | `arduino_ide` |
| 26 | **Audacity** | `audacity.exe` | `audacity` |
| 27 | **Autodesk Alias** | `alias.exe` | `alias` |
| 28 | **Autodesk Netfabb** | `netfabb.exe` | `autodesk_netfabb` |
| 29 | **Avogadro2** | `avogadro2.exe` | `avogadro2` |
| 30 | **Calculator** | `calculator.exe`, `calculatorapp.exe` | `mscalc` |
| 31 | **Canva** | `canva.exe` | `canva` |
| 32 | **CapCut** | `capcut.exe` | `capcut` |
| 33 | **Capture One** | `captureone.exe` | `capture_one` |
| 34 | **Chicken** | `chicken.exe` | `chicken` |
| 35 | **Civil 3D** | `acad.exe` | `autocad_civil_3d` |
| 36 | **Clip Studio Paint** | `clipstudiopaint.exe` | `clip_studio_paint` |
| 37 | **CloudCompare** | `cloudcompare.exe` | `cloudcompare` |
| 38 | **coDiagnostiX** | `codiagnostix.exe` | `straumann_codiagnostix` |
| 39 | **Cognition Master Professional Suite** | `cognitionmasterprofessionalsuite.exe` | `vmscope_cmps` |
| 40 | **DaVinci Resolve** | `resolve.exe` | `davinci_resolve` |
| 41 | **DBeaver** | `dbeaver.exe` | `dbeaver` |
| 42 | **DesignSpark Mechanical Creator** | `spaceclaim.exe` | `designspark_mechanical_creator` |
| 43 | **DesignSpark Mechanical Engineer** | `spaceclaim.exe` | `designspark_mechanical_engineer` |
| 44 | **DesignSpark Mechanical Explorer** | `spaceclaim.exe` | `designspark_mechanical_explorer` |
| 45 | **DezignWorks for SOLIDWORKS** | `sldworks.exe` | `dezignworks` |
| 46 | **Docker Desktop** | `docker desktop.exe`, `dockerdesktop.exe` | `docker_desktop` |
| 47 | **EarMouldDesigner** | `earmoulddesigner.exe` | `earmoulddesigner` |
| 48 | **Enscape 3D Client** | `enscapeclient.exe`, `enscapeclientglfw.exe`, `enscape.hostlauncher.exe` | `enscape_3d` |
| 49 | **EPLAN Pro Panel** | `eplan.exe` | `eplan_pro_panel` |
| 50 | **EXModel** | `quicksurface.exe` | `exmodel` |
| 51 | **fe.screen-sim Client Simulation** | `fe.screen-sim client.exe` | `fe_screen_sim_client_simulation` |
| 52 | **Figma** | `figma.exe` | `figma` |
| 53 | **FlexSim** | `flexsim.exe` | `flexsim` |
| 54 | **FreeCAD** | `freecad.exe` | `freecad` |
| 55 | **GitHub Desktop** | `githubdesktop.exe`, `github desktop.exe` | `github_desktop` |
| 56 | **GrabCAD Print** | `3dxnlserver.exe` | `grabcad_print` |
| 57 | **HandBrake** | `handbrake.exe` | `handbrake` |
| 58 | **HWiNFO / Afterburner** | `hwinfo64.exe`, `msiafterburner.exe` | `hwinfo_afterburner` |
| 59 | **hyperCAD-S** | `hmc.exe` | `hypercad` |
| 60 | **HyperWorks** | `hw_.exe` | `hyperworks` |
| 61 | **iCAD SX** | `icadx4j.exe` | `icad_sx` |
| 62 | **Inkscape** | `inkscape.exe` | `inkscape` |
| 63 | **Jet Demo** | `jet.exe` | `jet` |
| 64 | **JetBrains IDE (IDEA / PyCharm)** | `idea64.exe`, `pycharm64.exe` | `jetbrains_idea` |
| 65 | **KeyShot** | `keyshot.exe` | `keyshot` |
| 66 | **Krita** | `krita.exe` | `krita` |
| 67 | **LightBurn** | `lightburn.exe` | `lightburn` |
| 68 | **LTspice / EDA Tools** | `ltspice.exe`, `ltspicexvii.exe` | `ltspice` |
| 69 | **Lychee Slicer** | `lychee slicer.exe`, `lychee.exe` | `lychee_slicer` |
| 70 | **Magics** | `magics.exe` | `materialise_magics` |
| 71 | **MEDIT Link** | `medit_link.exe` | `medit_link` |
| 72 | **MoI** | `moi.exe` | `moi` |
| 73 | **Notion** | `notion.exe` | `notion` |
| 74 | **NVIDIA GeForce Overlay** | `nvcontainer.exe`, `nvgexui.exe` | `nvidia_overlay` |
| 75 | **OBS Studio** | `obs64.exe`, `obs.exe` | `obs_studio` |
| 76 | **Obsidian** | `obsidian.exe` | `obsidian` |
| 77 | **OneCNC** | `onecnc_x64.exe` | `onecnc` |
| 78 | **OnyxCeph³** | `onyxceph.exe`, `onyxview.exe`, `onyxreport.exe` | `onyxceph` |
| 79 | **OpenSCAD** | `openscad.exe` | `openscad` |
| 80 | **OrthoAnalyzer** | `orthoanalyzer.exe` | `orthoanalyzer` |
| 81 | **Paint Tool SAI** | `sai.exe` | `paint_tool_sai` |
| 82 | **Palette CAD** | `plan3d.exe` | `palette_cad` |
| 83 | **ParaView** | `paraview.exe` | `paraview` |
| 84 | **Parsec / AnyDesk** | `parsecd.exe`, `anydesk.exe` | `parsec` |
| 85 | **Photos** | `photos.exe` | `msphotos` |
| 86 | **Postman** | `postman.exe` | `postman` |
| 87 | **PowerToys / ShareX** | `powertoys.exe`, `sharex.exe` | `powertoys` |
| 88 | **PowerToys Settings** | `powertoys.settings.exe` | `mspowertoys` |
| 89 | **PuTTY / WinSCP** | `putty.exe`, `winscp.exe` | `puTTY` |
| 90 | **QUICKSURFACE** | `quicksurface.exe` | `quicksurface` |
| 91 | **Reaper** | `reaper.exe` | `reaper` |
| 92 | **Revu** | `revu.exe` | `bluebeam_revu` |
| 93 | **ROBOGUIDE** | `roboguidecore.exe` | `roboguide` |
| 94 | **Secret Ear Builder** | `sebuilder.exe` | `sebuilder` |
| 95 | **Secret Ear Designer** | `sedesigner.exe` | `sedesigner` |
| 96 | **Secret Ear Viewer** | `seviewer.exe` | `seviewer` |
| 97 | **Sketchbook** | `sketchbook.exe` | `sketchbook` |
| 98 | **Slack** | `slack.exe` | `slack` |
| 99 | **SmartCAM Production Turning** | `pturn.exe` | `smartcam_pturn` |
| 100 | **SolidCAM** | `solidcam.exe` | `solidcam_machinesimulation` |
| 101 | **SpaceClaim** | `spaceclaim.exe` | `spaceclaim` |
| 102 | **SpinFire** | `spinfire.viewer.exe` | `spinfire` |
| 103 | **Spotify** | `spotify.exe` | `spotify` |
| 104 | **Steam** | `steam.exe` | `steam` |
| 105 | **STRAKON Cube** | `plan-x64.exe` | `strakon_cube` |
| 106 | **Straumann Nova** | `javaw.exe` | `straumann_nova` |
| 107 | **Telegram / WhatsApp** | `telegram.exe`, `whatsapp.exe` | `telegram_whatsapp` |
| 108 | **TopSolid Pdm Explorer** | `topsolid.pdm.explorer.exe` | `topsolidpdmexplorer` |
| 109 | **TopSolid Viewer** | `topsolid.viewer.exe` | `topsolidviewer` |
| 110 | **Trimble Business Center** | `trimblebusinesscenter.exe` | `trimblebusinesscenter` |
| 111 | **TrueMap** | `truemap[0-9]+.exe` | `truemap` |
| 112 | **TurboCAD** | `tcw[1-9]+.exe` | `turbocad` |
| 113 | **Vectorworks Viewer** | `vectorworks[0-9]*viewer.exe` | `vectorworksviewer` |
| 114 | **Visi** | `visi.exe` | `visi` |
| 115 | **VISI Qt** | `visiqt.exe` | `visiqt` |
| 116 | **Visual Studio** | `devenv.exe` | `visual_studio` |
| 117 | **VLC Media Player** | `vlc.exe` | `vlc` |
| 118 | **VS Code / Cursor** | `code.exe`, `cursor.exe` | `vs_code` |
| 119 | **Windows (Global)** | *(Inherited)* | `windows_global` |
| 120 | **Windows Photo Viewer** | `dllhost.exe` | `windowsphotoviewer` |
| 121 | **Windows Terminal** | `windowsterminal.exe` | `windows_terminal` |
| 122 | **WinRAR** | `winrar.exe` | `winrar` |
| 123 | **ZEISS CALYPSO** | `acis35.exe` | `zeiss_calypso` |
| 124 | **ZEISS INSPECT** | `zeiss_inspect.exe` | `zeiss_inspect` |

---

## 🛠️ Re-Harvesting or Updating Profiles

To re-harvest profiles after updating 3DxWare drivers or adding custom user `.xml` configs:

```bash
python tools/harvest_3dconnexion.py
```

This regenerates `pi_app/tdx_harvested.json` with all decoded USB HID scan-code macros, multi-step sequences, radial pie menus, and 24×24 1-bit E-Ink icons.
