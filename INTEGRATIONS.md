# 🧩 MacroPad Comprehensive Application Integrations Catalog

This document provides the complete reference of all **native API bridges**, **multi-layer static application profiles**, and **260 harvested 3Dconnexion (`3DxWare`) application profiles** built into the MacroPad ecosystem.

---

## 📊 Integration Ecosystem at a Glance

| Metric | Count | Description |
| :--- | :---: | :--- |
| **Total Application Profiles** | **260** | Pre-configured application definitions harvested from 3Dconnexion `3DxWinCore/Cfg/*.xml` + native MacroPad rules |
| **Action-Rich App Profiles** | **187** | Profiles containing decoded keyboard macros, multi-step sequences, or native CAD commands |
| **Executable Actions & Macros** | **2,664** | Ready-to-use `hotkey:...`, `keyseq:...`, and `cad_cmd:...` actions available in the Unified Studio |
| **On-Screen Radial Pie Menus** | **402** | 4-slice and 8-slice long-press radial pie menus (`radial_menu.py`) |
| **24×24 1-Bit E-Ink Icons** | **879** | Dithered monochrome hardware icons compiled into `icon_library.py` |
| **Dedicated Static Hardware Layers** | **16** | 4 Banks × 4 Slots (`Layer 1` – `Layer 16`) stored in `layers_store.json` |

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
| 4 | **3DEXPERIENCE** | `3dexperience.exe` | 7 | 0 | `PROPS` · `UNDO` · `REDO` · `ARC` · `EXTRUDE` · `REVOLVE` |
| 5 | **3DEXPERIENCE** | `3dexperience.exe` | 3 | 0 | `UNDO` · `REDO` · `WIREFRAME` · `SAVE` · `COPY` · `PASTE` |
| 6 | **3DF Zephyr** | `3df zephyr.exe` | 3 | 0 | `SAVE` · `UNDO` · `REDO` · `COPY` · `PASTE` · `DELETE` |
| 7 | **3ds Max** | `3dsmax.exe` | 8 | 4 | `WIREFRAME` · `SHADED` · `CHAMFER` · `MIRROR` · `BOX` · `SPHERE` |
| 8 | **3DxUnity3D Editor** | `unity.exe` | 14 | 3 | `MOVE` · `ROTATE` · `SCALE` · `ADD COMP` · `SHADED DR` · `WIREFRM D` |
| 9 | **3Shape ScanIt Dental** | `dentaldesktop.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 10 | **7-Zip** | `7zfm.exe` | 2 | 0 | `ALL` · `DESELECT` · `UNDO` · `REDO` · `SAVE` · `COPY` |
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
| 26 | **ARES Commander** | `aresc.exe` | 22 | 4 | `REDO` · `UNDO` · `MATCH LAY` · `LINE` · `POLYLINE` · `CIRCLE` |
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
| 43 | **CATIA** | `cnext.exe` | 9 | 0 | `PROPS` · `UNDO` · `REDO` · `LINE` · `ARC` · `EXTRUDE` |
| 44 | **CETOL MultiCAD** | `cetolmc.exe` | 13 | 0 | `NEW` · `OPEN` · `OPTIONS` · `SAVE` · `COPY` · `CUT` |
| 45 | **Chaos Vantage** | `vantage.exe` | 4 | 2 | `ROTATE` · `SCALE` · `REDO` · `UNDO` · `SAVE` · `COPY` |
| 46 | **CharacterCreator** | `charactercreator.exe` | 8 | 3 | `UNDO` · `REDO` · `MOVE` · `ROTATE` · `SCALE` · `WIREFRAME` |
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
| 61 | **Creo Parametric** | `xtop.exe` | 42 | 15 | `REPAINT` · `SHADE` · `UNHIDE` · `REFIT` · `APPLY CHA` · `HIDE` |
| 62 | **CreoView** | `productview.exe` | 15 | 1 | `FIT` · `TOP` · `RIGHT` · `FRONT` · `ZOOM ALL` · `LEFT` |
| 63 | **CST STUDIO SUITE** | `modeler.exe`, `3dviewer.exe`, `modeler_amd64.exe` *(+7)* | 10 | 0 | `FIT` · `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` |
| 64 | **CStudio** | `cstudio.exe` | 9 | 1 | `WHEEL 20` · `WHEEL 20` · `SAVE` · `UNDO` · `REDO` · `MOVE` |
| 65 | **Cube3D** | `cube3d.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 66 | **Cyclone 3DR** | `3drviewer.exe`, `3dr.exe` | 8 | 1 | `FLY` · `ORBIT PER` · `ORBIT ORT` · `PANORAMA` · `TOP` · `RIGHT` |
| 67 | **D5 Render** | `d5_launcher.exe` | 12 | 1 | `WHEEL 20` · `WHEEL 20` · `UNDO` · `REDO` · `SAVE` · `WIREFRAME` |
| 68 | **DELMIA** | `delmia.exe` | 8 | 0 | `PROPS` · `UNDO` · `REDO` · `LINE` · `ARC` · `EXTRUDE` |
| 69 | **Dental Wings Chairside CAD** | `javaw.exe` | 10 | 0 | `FIT` · `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` |
| 70 | **Dental Wings Easy Mode** | `javaw.exe` | 9 | 0 | `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` · `TABAPPLIC` |
| 71 | **DentalCAD** | `dentalcadapp.exe` | 15 | 2 | `FIT` · `MEASUREME` · `DISTANCE` · `CUT` · `ROLL MODE` · `ROLL MODE` |
| 72 | **Desktop** | `explorer.exe`, `searchapp.exe`, `cortana.exe` *(+1)* | 8 | 1 | `PROJECT` · `PASTE` · `COPY` · `TASKMANAG` · `SETTINGS` · `TABAPPLIC` |
| 73 | **Deswik.CAD** | `deswik.cad.exe` | 10 | 1 | `SNAP MODE` · `POLYLINE` · `DISTANCE` · `MOVE` · `UNDO` · `REDO` |
| 74 | **DraftSight** | `draftsight.exe` | 11 | 1 | `FIT` · `QUICKZOOM` · `LINE` · `RECTANGLE` · `DIM LINEA` · `MIRROR` |
| 75 | **DraftSight** | `draftsight.exe` | 8 | 1 | `LINE` · `POLYLINE` · `CIRCLE` · `ARC` · `MOVE` · `COPY` |
| 76 | **DWOS Client** | `javaw.exe` | 10 | 0 | `FIT` · `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` |
| 77 | **ENOVIA DMU** | `dmu.exe` | 8 | 0 | `PROPS` · `UNDO` · `REDO` · `LINE` · `ARC` · `EXTRUDE` |
| 78 | **Enscape Archicad** | `archicad.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 79 | **Enscape Revit** | `revit.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 80 | **Enscape Rhino** | `rhino.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 81 | **Enscape SketchUp** | `sketchup.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 82 | **Enscape Vectorworks** | `vectorworks.*.exe`, `enscape.rendererhost.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 83 | **ExoViewer 3D** | `exoviewer3d.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 84 | **Firefox** | `firefox.exe` | 22 | 4 | `100%` · `HOME KEY` · `REFRESH` · `GO TO BOT` · `IN PRIVAT` · `NEW TAB` |
| 85 | **FreeCAD** | `freecad.exe` | 29 | 25 | `SAVE` · `UNDO` · `REDO` · `NEW` · `OPEN` · `DIMENSION` |
| 86 | **Fusion Electronics** | `fusion360.exe`, `fusion.exe` | 7 | 4 | `SAVE` · `UNDO` · `REDO` · `LINE` · `TEXT` · `CIRCLE` |
| 87 | **GO2cam** | `go2cam.exe`, `go2camdemo.exe`, `lioncam.exe` | 4 | 0 | `OPEN` · `FIT` · `ZOOM IN` · `ZOOM OUT` · `UNDO` · `REDO` |
| 88 | **Google Earth** | `googleearth.exe` | 23 | 3 | `FULLSCREE` · `RESET TIL` · `RESET TIL` · `RESET NOR` · `PATH` · `GRID` |
| 89 | **GPlay** | `gplay.exe` | 3 | 0 | `FIT` · `ZOOM IN` · `ZOOM OUT` · `UNDO` · `REDO` · `SAVE` |
| 90 | **GstarCAD** | `gcad.exe` | 17 | 3 | `WHEEL 20` · `WHEEL 20` · `POLYLINE` · `CIRCLE` · `RECTANGLE` · `COPY` |
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
| 104 | **Inventor** | `inventor.exe` | 48 | 52 | `LINE` · `SPLINE` · `OFFSET` · `REDO` · `UNDO` · `CUT` |
| 105 | **Inventor LT** | `inventor.exe` | 6 | 0 | `QUICKZOOM` · `QUICKZOOM` · `OPEN` · `MEASURE` · `FIND` · `FIT` |
| 106 | **Inventor RO** | `invro.exe` | 6 | 0 | `QUICKZOOM` · `QUICKZOOM` · `OPEN` · `MEASURE` · `FIND` · `FIT` |
| 107 | **IRONCAD** | `ironcad.exe` | 1 | 0 | `KB ESC` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 108 | **IRONCAD COMPOSE** | `iccompose.exe` | 1 | 0 | `KB ESC` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 109 | **IRONCAD DRAFT** | `icdraft.exe` | 1 | 0 | `KB ESC` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 110 | **IRONCAD INOVATE** | `inovate.exe` | 1 | 0 | `KB ESC` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 111 | **K-Compare Revision 4.0** | `kcomparerevision.exe` | 3 | 0 | `WHEEL 20` · `WHEEL 20` · `ANGLE` · `UNDO` · `REDO` · `SAVE` |
| 112 | **K-Display View 4.0** | `kdisplayview.exe` | 8 | 1 | `WHEEL 20` · `WHEEL 20` · `MOVE` · `SHADED` · `WIREFRAME` · `PRINT` |
| 113 | **KeyCreator** | `kc.exe` | 16 | 0 | `CONSTRUCT` · `WIREFRAME` · `SHADED` · `TREE` · `LAYOUT TO` · `TOP` |
| 114 | **KiCad** | `kicad.exe`, `eeschema.exe` | 4 | 0 | `KB ESC` · `FIT` · `W` · `J` · `UNDO` · `REDO` |
| 115 | **KiCad** | `kicad.exe`, `pcbnew.exe` | 3 | 0 | `KB ESC` · `FIT` · `C` · `UNDO` · `REDO` · `SAVE` |
| 116 | **KiCad** | `kicad.exe`, `pcbnew.exe` | 3 | 0 | `KB ESC` · `FIT` · `ALT+3` · `UNDO` · `REDO` · `SAVE` |
| 117 | **KOMPAS-3D** | `kompas.exe` | 5 | 0 | `FIT` · `KB F9` · `SAVEAS` · `NEW` · `KB ESC` · `UNDO` |
| 118 | **LightWave** | `modeler.exe`, `layout.exe` | 9 | 0 | `FIT` · `RIGHT` · `COPY` · `CUT` · `PASTE` · `ALIGNWIND` |
| 119 | **Lychee Slicer** | `lycheeslicer.exe` | 1 | 0 | `GO HOME/F` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 120 | **Mastercam X** | `mastercam.exe` | 24 | 2 | `FIT` · `TOP` · `FRONT` · `BACK` · `BOTTOM` · `RIGHT` |
| 121 | **Mastercam X** | `mastercam.exe` | 19 | 2 | `ZOOM - TA` · `ZOOM -` · `UN-ZOOM 5` · `SHADE TOG` · `REDRAW` · `HIDE ENTI` |
| 122 | **Maya** | `maya.exe` | 4 | 1 | `EXTRUDE` · `FIT` · `ZOOM IN` · `ZOOM OUT` · `UNDO` · `REDO` |
| 123 | **Microsoft Edge** | `msedge.exe` | 8 | 0 | `PRINT` · `INPRIVATE` · `OPEN` · `NEWTAB` · `FINDONPAG` · `DUPTAB` |
| 124 | **Microsoft Edge** | `microsoftedge.exe`, `microsoftedgecp.exe` | 17 | 4 | `ZOOM 100%` · `ADD CURRE` · `A SEARCH` · `FIND ON P` · `HISTORY P` · `FAVORITES` |
| 125 | **Microsoft Excel** | `excel.exe` | 27 | 2 | `BOLD` · `ITALIC` · `UNDERLINE` · `STRIKETHR` · `FIND` · `REPLACE` |
| 126 | **Microsoft Paint** | `mspaint.exe` | 19 | 0 | `NEW` · `SELECT` · `PENCIL` · `ERASER` · `TEXT` · `GRID` |
| 127 | **Microsoft PowerPoint** | `powerpnt.exe` | 17 | 1 | `BOLD` · `ITALIC` · `UNDERLINE` · `STRIKETHR` · `THESAURUS` · `TRANSLATE` |
| 128 | **Microsoft Teams** | `teams.exe` | 1 | 0 | `MIC MUTE` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 129 | **Microsoft Word** | `winword.exe` | 21 | 2 | `BOLD` · `ITALIC` · `UNDERLINE` · `STRIKETHR` · `FIND` · `REPLACE` |
| 130 | **MicroStation** | `ustation.exe` | 12 | 0 | `FIT` · `CTRL ALT` · `CTRL ALT` · `CTRL ALT` · `CTRL ALT` · `CTRL ALT` |
| 131 | **MicroStation** | `microstation.exe` | 9 | 2 | `TOOLS Q` · `POPUPS` · `MOVE` · `COPY` · `ROTATE` · `SCALE` |
| 132 | **MicroStation CONNECT** | `microstation.exe` | 25 | 1 | `FIT` · `DIM LINEA` · `DIM ELEME` · `DIM ANGUL` · `PLACE TEX` · `PLACE TAB` |
| 133 | **MODO** | `modo.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 134 | **Notepad** | `notepad.exe` | 12 | 0 | `FIND NEXT` · `TIME/DATE` · `NEW` · `FIND PREV` · `REPLACE` · `ZOOM IN` |
| 135 | **NX** | `ugraf.exe` | 34 | 14 | `NEW` · `OPEN` · `SAVE` · `HOLE` · `SPHERE` · `MEASURE` |
| 136 | **Onshape** | `3dxnlserver.exe` | 21 | 9 | `LINE` · `POINT` · `TEXT` · `TRIM` · `MIRROR` · `EXTEND` |
| 137 | **OrcaSlicer** | `orca-slicer.exe` | 24 | 2 | `MOVE` · `SCALE` · `ROTATE` · `LAY ON FA` · `SUPPORT P` · `SLICE PLA` |
| 138 | **Outlook** | `outlook.exe` | 14 | 1 | `BOLD` · `ITALIC` · `UNDERLINE` · `BULLETS` · `FIND` · `REPLACE` |
| 139 | **PhotoModeler** | `photomodeler.*.exe` | 2 | 0 | `PROPS` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 140 | **Photoshop** | `photoshop.exe` | 120 | 9 | `CANCEL` · `FIT ON SC` · `STEP BACK` · `STEP FORW` · `PAN` · `CREATE A` |
| 141 | **Plasticity** | `plasticity.exe` | 19 | 1 | `FRONT` · `RIGHT` · `TOP` · `BOTTOM` · `BACK` · `LEFT` |
| 142 | **PreForm** | `preform.exe` | 1 | 0 | `HOME VIEW` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 143 | **Procore** | `3dxnlserver.exe` | 9 | 1 | `MEASURE T` · `SECTION T` · `OBJECT TR` · `PROPS` · `X-RAY` · `FULL SCRE` |
| 144 | **ProgeCAD** | `pcad.exe` | 23 | 5 | `NEW` · `OPEN` · `LINE` · `RECTANGLE` · `POLYLINE` · `COPY` |
| 145 | **PrusaSlicer** | `prusa-slicer.exe` | 34 | 2 | `MOVE` · `SCALE` · `ROTATE` · `PLACE ON` · `CUT` · `SEAM PAIN` |
| 146 | **Quartis** | `quartis.exe` | 11 | 1 | `ZOOM ON C` · `DISPLAY O` · `TOP` · `LEFT` · `RIGHT` · `FRONT` |
| 147 | **Revizto** | `revizto5.exe` | 9 | 1 | `RULER` · `SECTION` · `NEW ISSUE` · `STAMP` · `OBJECT TR` · `VIEWPOINT` |
| 148 | **Rhinoceros** | `rhino.exe` | 18 | 0 | `WHEEL 20` · `WHEEL 20` · `ZOOMEXTEN` · `MAXIMIZE` · `SHADE` · `SHADESELE` |
| 149 | **Rhinoceros** | `rhino.exe`, `revit.exe` | 136 | 5 | `UNDO` · `REDO` · `RENDER` · `TRIM` · `POLYLINE` · `CYLINDER` |
| 150 | **Rhinoceros 4** | `rhino4.exe` | 22 | 0 | `FIT` · `ZOOM EXTE` · `MAXIMIZE` · `SHADE` · `SHADE SEL` · `UNDO` |
| 151 | **RhinoNL** | `rhino.exe`, `revit.exe` | 133 | 4 | `POLYLINE` · `CYLINDER` · `TRIM` · `LOFT` · `REVOLVE` · `MOVE` |
| 152 | **SDK MCAD Demo** | `mcad.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 153 | **Shapr3D** | `spacemousebridge.exe` | 10 | 1 | `ARC` · `LINE` · `RECTANGLE` · `EXTRUDE` · `REVOLVE` · `LOFT` |
| 154 | **ShellDesigner** | `shelldesigner.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 155 | **Shining3D** | `exscan s.exe`, `exscan hx.exe`, `exscan pro.exe` *(+3)* | 5 | 2 | `UNDO` · `ALL` · `DELETE` · `REDO` · `FIT` · `SAVE` |
| 156 | **SketchUp for Web** | `3dxnlserver.exe` | 30 | 3 | `SELECT` · `PUSH/PULL` · `OFFSET` · `SEARCH` · `LINE` · `RECTANGLE` |
| 157 | **SOFTIMAGE/XSI** | `xsi.exe` | 4 | 1 | `FIT` · `REDO` · `UNDO` · `KB ESC` · `SAVE` · `COPY` |
| 158 | **Solid Edge** | `edge.exe` | 29 | 22 | `SAVE` · `UNDO` · `REDO` · `NEW` · `OPEN` · `OPTIONS` |
| 159 | **SOLIDWORKS** | `sldworks.exe` | 22 | 15 | `HIDE` · `SHOW` · `UNDO` · `SHADED` · `MIRROR` · `LINE` |
| 160 | **SOLIDWORKS Visualize** | `sldworksvisualize.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 161 | **Substance 3D Painter** | `adobe substance 3d painter.*.exe` | 54 | 2 | `PROJECT` · `CLOSE PRO` · `SAVE PROJ` · `NEW PROJE` · `SHOW/HIDE` · `INCREASE` |
| 162 | **Task Manager** | `taskmgr.exe` | 2 | 0 | `OPEN` · `SAVE` · `UNDO` · `REDO` · `COPY` · `PASTE` |
| 163 | **Teamcenter** | `visview.exe`, `visview_ng.exe` | 20 | 0 | `FIT ALL` · `PART COLO` · `EXPLODED` · `LEFT` · `BOTTOM` · `BACK` |
| 164 | **Tebis** | `tebis.exe` | 25 | 1 | `FIT` · `FRONT` · `TOP` · `SIDE VIEW` · `SIDE VIEW` · `BOTTOM` |
| 165 | **Tekla Structures** | `teklastructures.exe` | 10 | 0 | `COPY` · `CUT` · `PASTE` · `ALIGNWIND` · `ALIGNWIND` · `TABAPPLIC` |
| 166 | **test_action_interface** | `test_action_interface.exe` | 7 | 2 | `NEW` · `OPEN` · `SAVE` · `UNDO` · `REDO` · `COPY` |
| 167 | **TopSolid** | `topsolid.exe` | 9 | 2 | `CIRCLE` · `RECTANGLE` · `DIMENSION` · `GROUP` · `LINE` · `TEXT` |
| 168 | **TopSolid Cam NC Operator** | `topsolid.cam.nc.operator.exe` | 10 | 0 | `OPTIONS` · `RET.ARR` · `7` · `ECHAP` · `F1` · `F2` |
| 169 | **Trimble SketchUp** | `sketchup.exe` | 19 | 8 | `EXPORT 3D` · `WIREFRAME` · `SHADED` · `TEXT` · `UNDO` · `REDO` |
| 170 | **Twinmotion** | `twinmotion.*.exe` | 2 | 1 | `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` · `DELETE` |
| 171 | **UltiMaker Cura** | `ultimaker-cura.exe` | 12 | 1 | `MOVE` · `SCALE` · `ROTATE` · `MIRROR` · `SUPPORT B` · `SLICE` |
| 172 | **Unreal Editor** | `ue4editor.*.exe`, `unrealeditor.*.exe` | 2 | 0 | `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` · `DELETE` |
| 173 | **Unreal Editor (Asset & Play-in-Editor)** | `ue4editor.*.exe`, `unrealeditor.*.exe` | 1 | 0 | `SNIPPINGT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 174 | **Vectorworks** | `vectorworks201[5-9].exe|vectorworks202[0-6].exe` | 12 | 0 | `MODIFY` · `CUT` · `MERGE` · `MIRROR` · `ROTATE` · `FILLET` |
| 175 | **Vectorworks** | `vectorworks202[6-9].exe` | 3 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 176 | **Viewer Demo** | `s3dm_viewer.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 177 | **Windows Explorer** | `explorer.exe` | 25 | 1 | `NEW FILE` · `RENAME` · `FULL SCRE` · `PROPS` · `BACK` · `FORWARD` |
| 178 | **WindowsMediaCenter** | `ehshell.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 179 | **Windowsshellexperience** | `shellui.exe` | 9 | 1 | `PASTE` · `COPY` · `CUT` · `ALIGNWIND` · `ALIGNWIND` · `TABAPPLIC` |
| 180 | **WYSIWYG** | `wyg.exe` | 1 | 0 | `FIT` · `UNDO` · `REDO` · `SAVE` · `COPY` · `PASTE` |
| 181 | **XVL Studio** | `xvlstudio2.exe` | 4 | 0 | `FIT` · `UNDO` · `REDO` · `KB ESC` · `SAVE` · `COPY` |
| 182 | **ZBrush** | `zbrush.exe` | 5 | 2 | `REDO` · `SYMMETRY` · `FIT TO ME` · `UNDO` · `REDO` · `SAVE` |
| 183 | **ZBrushCore** | `zbrushcore.exe` | 7 | 2 | `WHEEL 20` · `WHEEL 20` · `REDO` · `UNDO` · `REDO` · `FIT` |
| 184 | **ZBrushCoreMini** | `zbrushcoremini.exe` | 5 | 1 | `FIT` · `REDO` · `UNDO` · `OPEN` · `ZINTENSIT` · `SAVE` |
| 185 | **ZW3D** | `zw3d.exe` | 3 | 1 | `FIT` · `REDO` · `UNDO` · `SAVE` · `COPY` · `PASTE` |
| 186 | **ZW3D_NavLib** | `zw3d.exe` | 38 | 25 | `WHEEL 20` · `WHEEL 20` · `EXTRUDE` · `REVOLVE` · `SWEEP` · `LOFT` |
| 187 | **ZWCAD** | `zwcad.exe` | 15 | 4 | `RECTANGLE` · `HATCH` · `COPY` · `TRIM` · `ROTATE` · `MIRROR` |

---

## 🛰️ Tier 4: Additional 73 Tracked 3D/CAD Application Profiles

These 73 profiles from the 3Dconnexion library provide executable detection and inherit the global 3Dconnexion standard view/navigation macro set (or Universal productivity controls):

| # | Application Name | Matched Executables | Profile ID |
| :-: | :--- | :--- | :--- |
| 1 | **3DViewStation** | `3dviewstation.exe` | `3dviewstation` |
| 2 | **3DxUnity3D PlayMode** | `unity.exe` | `3dxunity3d_pm` |
| 3 | **3Shape 3D Viewer** | `3shape_3dviewer.exe` | `3shape_3d_viewer` |
| 4 | **3Shape DentalDesigner** | `dentaldesigner.exe` | `3shape_dentaldesigner` |
| 5 | **3Shape ModelBuilder** | `modelbuilder.exe` | `3shape_modelbuilder` |
| 6 | **3Shape ScanItLibrary** | `scanitlibrary.exe` | `3shape_scanitlibrary` |
| 7 | **AC3D** | `ac3d.exe` | `ac3d` |
| 8 | **Alibre Design** | `alibre design.exe` | `alibre_design_v2` |
| 9 | **Altair EDEM** | `edem.exe` | `altair_edem` |
| 10 | **Ansys Discovery** | `discovery.exe` | `ansys_discovery` |
| 11 | **ApplianceDesigner** | `appliancedesigner.exe` | `appliancedesigner` |
| 12 | **Arc** | `arc.exe` | `arcbrowser` |
| 13 | **ArcGIS Pro** | `arcgispro.exe` | `arcgis_pro` |
| 14 | **Autodesk Netfabb** | `netfabb.exe` | `autodesk_netfabb` |
| 15 | **Avogadro2** | `avogadro2.exe` | `avogadro2` |
| 16 | **Calculator** | `calculator.exe`, `calculatorapp.exe` | `mscalc` |
| 17 | **Chicken** | `chicken.exe` | `chicken` |
| 18 | **Civil 3D** | `acad.exe` | `autocad_civil_3d` |
| 19 | **CloudCompare** | `cloudcompare.exe` | `cloudcompare` |
| 20 | **coDiagnostiX** | `codiagnostix.exe` | `straumann_codiagnostix` |
| 21 | **Cognition Master Professional Suite** | `cognitionmasterprofessionalsuite.exe` | `vmscope_cmps` |
| 22 | **DesignSpark Mechanical Creator** | `spaceclaim.exe` | `designspark_mechanical_creator` |
| 23 | **DesignSpark Mechanical Engineer** | `spaceclaim.exe` | `designspark_mechanical_engineer` |
| 24 | **DesignSpark Mechanical Explorer** | `spaceclaim.exe` | `designspark_mechanical_explorer` |
| 25 | **DezignWorks for SOLIDWORKS** | `sldworks.exe` | `dezignworks` |
| 26 | **EarMouldDesigner** | `earmoulddesigner.exe` | `earmoulddesigner` |
| 27 | **Enscape 3D Client** | `enscapeclient.exe`, `enscapeclientglfw.exe`, `enscape.hostlauncher.exe` | `enscape_3d` |
| 28 | **EPLAN Pro Panel** | `eplan.exe` | `eplan_pro_panel` |
| 29 | **EXModel** | `quicksurface.exe` | `exmodel` |
| 30 | **fe.screen-sim Client Simulation** | `fe.screen-sim client.exe` | `fe_screen_sim_client_simulation` |
| 31 | **FlexSim** | `flexsim.exe` | `flexsim` |
| 32 | **FreeCAD** | `freecad.exe` | `freecad` |
| 33 | **GrabCAD Print** | `3dxnlserver.exe` | `grabcad_print` |
| 34 | **hyperCAD-S** | `hmc.exe` | `hypercad` |
| 35 | **HyperWorks** | `hw_.exe` | `hyperworks` |
| 36 | **iCAD SX** | `icadx4j.exe` | `icad_sx` |
| 37 | **Jet Demo** | `jet.exe` | `jet` |
| 38 | **KeyShot** | `keyshot.exe` | `keyshot` |
| 39 | **KiCad** | `kicad.exe` | `kicad` |
| 40 | **Magics** | `magics.exe` | `materialise_magics` |
| 41 | **MEDIT Link** | `medit_link.exe` | `medit_link` |
| 42 | **MoI** | `moi.exe` | `moi` |
| 43 | **OneCNC** | `onecnc_x64.exe` | `onecnc` |
| 44 | **OnyxCeph³** | `onyxceph.exe`, `onyxview.exe`, `onyxreport.exe` | `onyxceph` |
| 45 | **OrthoAnalyzer** | `orthoanalyzer.exe` | `orthoanalyzer` |
| 46 | **Palette CAD** | `plan3d.exe` | `palette_cad` |
| 47 | **ParaView** | `paraview.exe` | `paraview` |
| 48 | **Photos** | `photos.exe` | `msphotos` |
| 49 | **PowerToys Settings** | `powertoys.settings.exe` | `mspowertoys` |
| 50 | **QUICKSURFACE** | `quicksurface.exe` | `quicksurface` |
| 51 | **Revu** | `revu.exe` | `bluebeam_revu` |
| 52 | **ROBOGUIDE** | `roboguidecore.exe` | `roboguide` |
| 53 | **Secret Ear Builder** | `sebuilder.exe` | `sebuilder` |
| 54 | **Secret Ear Designer** | `sedesigner.exe` | `sedesigner` |
| 55 | **Secret Ear Viewer** | `seviewer.exe` | `seviewer` |
| 56 | **SmartCAM Production Turning** | `pturn.exe` | `smartcam_pturn` |
| 57 | **SolidCAM** | `solidcam.exe` | `solidcam_machinesimulation` |
| 58 | **SpaceClaim** | `spaceclaim.exe` | `spaceclaim` |
| 59 | **SpinFire** | `spinfire.viewer.exe` | `spinfire` |
| 60 | **STRAKON Cube** | `plan-x64.exe` | `strakon_cube` |
| 61 | **Straumann Nova** | `javaw.exe` | `straumann_nova` |
| 62 | **TopSolid Pdm Explorer** | `topsolid.pdm.explorer.exe` | `topsolidpdmexplorer` |
| 63 | **TopSolid Viewer** | `topsolid.viewer.exe` | `topsolidviewer` |
| 64 | **Trimble Business Center** | `trimblebusinesscenter.exe` | `trimblebusinesscenter` |
| 65 | **TrueMap** | `truemap[0-9]+.exe` | `truemap` |
| 66 | **TurboCAD** | `tcw[1-9]+.exe` | `turbocad` |
| 67 | **Vectorworks Viewer** | `vectorworks[0-9]*viewer.exe` | `vectorworksviewer` |
| 68 | **Visi** | `visi.exe` | `visi` |
| 69 | **VISI Qt** | `visiqt.exe` | `visiqt` |
| 70 | **Windows Photo Viewer** | `dllhost.exe` | `windowsphotoviewer` |
| 71 | **WinRAR** | `winrar.exe` | `winrar` |
| 72 | **ZEISS CALYPSO** | `acis35.exe` | `zeiss_calypso` |
| 73 | **ZEISS INSPECT** | `zeiss_inspect.exe` | `zeiss_inspect` |

---

## 🛠️ Re-Harvesting or Updating Profiles

To re-harvest profiles after updating 3DxWare drivers or adding custom user `.xml` configs:

```bash
python tools/harvest_3dconnexion.py
```

This regenerates `pi_app/tdx_harvested.json` with all decoded USB HID scan-code macros, multi-step sequences, radial pie menus, and 24×24 1-bit E-Ink icons.
