#!/usr/bin/env python3
"""
harvest_multi_drivers.py  —  Multi-Source Peripheral Driver Harvester
============================================================================
Merges presets & icons from:
  • 3Dconnexion  (existing tdx_harvested.json, re-tagged as source="3Dconnexion")
  • Loupedeck 5.9 (DLL embedded XML <command> blocks + .licons media icons)
  • TourBox Console 5.11.3 (tourbox.db XML shortcuts: Photoshop + Lightroom)
  • Wacom Tablet Driver 6.4 (AppGestures.xml gesture→keystroke mappings)
  • Power-User Curated (50 high-impact missing integrations)
  • Stream Deck 7.6 (built-in action catalog from AppExecutable strings)

Output appended into pi_app/tdx_harvested.json under each app's "presets" list.
Schema per app entry (multi-source):

{
  "id": "adobe_photoshop",
  "name": "Adobe Photoshop",
  "exe_match": "photoshop.exe",
  "source": "3Dconnexion",           ← primary / first source
  "presets": [
    { "source": "3Dconnexion", "actions": [...], "recommended_cells": [...], "radial_menus": [...] },
    { "source": "Loupedeck",   "actions": [...], "recommended_cells": [...] },
    { "source": "TourBox",     "actions": [...], "recommended_cells": [...] },
    { "source": "Wacom",       "actions": [...] },
    { "source": "PowerUser",   "actions": [...], "recommended_cells": [...] }
  ],
  "selected_preset_source": "3Dconnexion"   ← default; overridable per-user
}

Usage:
  python tools/harvest_multi_drivers.py [--dry-run] [--rebuild-all]

  --dry-run     : Print stats without writing files
  --rebuild-all : Wipe all non-3Dconnexion presets and regenerate
"""

import os, sys, re, json, struct, zipfile, io, xml.etree.ElementTree as ET, argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==============================================================================
# PATHS
# ==============================================================================
REPO_ROOT = Path(__file__).parent.parent
PI_APP = REPO_ROOT / "pi_app"
TDX_HARVESTED = PI_APP / "tdx_harvested.json"

SCRATCH = Path(r"C:\Users\Uzzo\.gemini\antigravity\brain\6e6bbd96-b74c-4014-9572-db06cfe09621\scratch\driver_harvest")
LD59_DIR   = SCRATCH / "ld59_a2"
TOURBOX_DB = SCRATCH / "tourbox_extracted" / "tourbox.db"
WACOM_XML  = SCRATCH / "wacom_extracted" / "System32" / "AppGestures.xml"
LD59_ICONS = SCRATCH / "ld_library_icons"   # already-extracted 60×60 PNGs

# Loupedeck binary icon palette path (for PluginImageLibraryReader via .NET)
LD59_LIBRARY_ZIP = LD59_DIR / "LoupedeckLibrary.zip"
LD59_PLUGIN_API  = LD59_DIR / "PluginApi.dll"

# ==============================================================================
# HELPERS
# ==============================================================================

def _norm_id(name: str) -> str:
    """Normalise a display name to a stable ID slug."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _hotkey_from_ks(ks: str) -> str:
    """Convert Wacom keystroke XML like '&control;&shift;z' → 'hotkey:CTRL+SHIFT+Z'."""
    if not ks:
        return ""
    mods = []
    if "&control;" in ks:  mods.append("CTRL")
    if "&shift;" in ks:    mods.append("SHIFT")
    if "&alt;" in ks:      mods.append("ALT")
    if "&command;" in ks:  mods.append("WIN")
    # Strip modifier tags to find remaining key
    plain = re.sub(r"&(?:control|shift|alt|command);", "", ks).strip()
    if plain.startswith("&") and plain.endswith(";"):
        key = plain[1:-1].upper()
    else:
        key = plain.upper()
    if key:
        mods.append(key)
    if mods:
        return "hotkey:" + "+".join(mods)
    return ""


def _hotkey_from_ld_shortcut(shortcut: str) -> str:
    """Convert Loupedeck XML key= string like 'Windows+KeyA' or 'Ctrl+Shift+F5' → 'hotkey:WIN+A'."""
    if not shortcut:
        return ""
    parts = [p.strip() for p in shortcut.replace("+", "+").split("+") if p.strip()]
    mods_map = {
        "ctrl": "CTRL", "control": "CTRL", "controlorcommand": "CTRL",
        "shift": "SHIFT", "alt": "ALT", "option": "ALT", "altororption": "ALT",
        "win": "WIN", "windows": "WIN", "command": "WIN", "meta": "WIN",
    }
    mods = []
    key = ""
    for p in parts:
        pl = p.lower()
        if pl.startswith("key"):
            key = p[3:].upper()
        elif pl in mods_map:
            mods.append(mods_map[pl])
        elif re.match(r"f\d+$", pl, re.I):
            key = p.upper()
        elif len(p) == 1:
            key = p.upper()
        else:
            key = p.upper()
    combo = "+".join(mods + ([key] if key else []))
    return f"hotkey:{combo}" if combo else ""


def _vk_to_hotkey(modifier_bits: int, vk: int) -> str:
    """Convert TourBox (modifier_bits, vk) to hotkey:... string.
    modifier_bits: bit8=CTRL, bit4=ALT, bit2=SHIFT.
    vk: Win32 VK or ASCII code.
    """
    mods = []
    if modifier_bits & 8:  mods.append("CTRL")
    if modifier_bits & 4:  mods.append("ALT")
    if modifier_bits & 2:  mods.append("SHIFT")

    # Map common VK codes to key names
    VK_MAP = {
        8: "BACKSPACE", 9: "TAB", 13: "ENTER", 27: "ESC", 32: "SPACE",
        33: "PGUP", 34: "PGDN", 35: "END", 36: "HOME",
        37: "LEFT", 38: "UP", 39: "RIGHT", 40: "DOWN",
        44: ",", 45: "-", 46: ".", 47: "/", 59: ";", 61: "=", 91: "[", 93: "]", 92: "\\",
        127: "DELETE",
        112: "F1", 113: "F2", 114: "F3", 115: "F4", 116: "F5",
        117: "F6", 118: "F7", 119: "F8", 120: "F9", 121: "F10",
        122: "F11", 123: "F12",
        16777219: "LEFT", 16777220: "RIGHT", 16777217: "UP", 16777218: "DOWN",
        16777227: "X", 16777228: "C", 16777229: "V",
    }
    if vk in VK_MAP:
        key = VK_MAP[vk]
    elif 48 <= vk <= 57:
        key = chr(vk)
    elif 65 <= vk <= 90:
        key = chr(vk)
    else:
        return ""
    combo = "+".join(mods + [key])
    return f"hotkey:{combo}"


def _make_cell(index: int, label: str, action: str, icon: str = "") -> Dict[str, Any]:
    label = (label or "").upper()[:10]
    return {"index": index, "label": label, "action": action, "icon": icon}


def _best_cells(actions: List[Dict], max_n: int = 9) -> List[Dict]:
    """Pick the top N most descriptive actions as default 3×3 cells."""
    top = actions[:max_n]
    cells = []
    for i, a in enumerate(top):
        cells.append(_make_cell(i + 1, a.get("label", ""), a.get("action", ""), a.get("icon", "")))
    # Pad with universals if < 9
    universal_pad = [
        ("UNDO",  "hotkey:CTRL+Z"), ("REDO",  "hotkey:CTRL+Y"),
        ("SAVE",  "hotkey:CTRL+S"), ("COPY",  "hotkey:CTRL+C"),
        ("PASTE", "hotkey:CTRL+V"), ("CUT",   "hotkey:CTRL+X"),
        ("FIND",  "hotkey:CTRL+F"), ("ESC",   "hotkey:ESC"),   ("ENTER", "hotkey:ENTER"),
    ]
    while len(cells) < 9:
        pad = universal_pad[len(cells)]
        cells.append(_make_cell(len(cells) + 1, pad[0], pad[1]))
    return cells


# ==============================================================================
# SOURCE 1: LOUPEDECK 5.9.1 – XML <command> blocks from DLL embedded resources
# ==============================================================================

def _parse_ld_command_xml(xml_text: str, app_name: str) -> List[Dict]:
    """Parse Loupedeck <configuration> XML for <command> items with key= shortcuts."""
    actions = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return actions

    for group in root.iter("group"):
        group_name = group.get("name", "")
        for cmd in group.findall("command"):
            name = cmd.get("name") or cmd.get("displayName") or ""
            key  = cmd.get("key") or cmd.get("shortcut") or ""
            if not name:
                continue
            hotkey = _hotkey_from_ld_shortcut(key)
            label = "".join(w[0] for w in re.sub(r"[^a-zA-Z0-9 ]", " ", name).split() if w)[:6].upper()
            actions.append({
                "id": f"ld_{_norm_id(name)}",
                "name": name,
                "label": label,
                "action": hotkey,
                "icon": "",
                "group": group_name,
            })
    return actions


_LD_APP_PLUGIN_MAP = {
    "AfterEffectsPlugin.dll": {
        "name": "Adobe After Effects", "id": "adobe_after_effects",
        "exe_match": "afterfx.exe", "app_group": "Adobe After Effects"
    },
    "AuditionPlugin.dll": {
        "name": "Adobe Audition", "id": "adobe_audition",
        "exe_match": "adobe audition.exe", "app_group": "Adobe Audition"
    },
    "CaptureOnePlugin.dll": {
        "name": "Capture One", "id": "capture_one",
        "exe_match": "captureone.exe", "app_group": "Capture One"
    },
    "DefaultWinPlugin.dll": {
        "name": "Windows (Global)", "id": "windows_global",
        "exe_match": "", "app_group": "Windows"
    },
    "IllustratorPlugin.dll": {
        "name": "Adobe Illustrator", "id": "adobe_illustrator",
        "exe_match": "illustrator.exe", "app_group": "Adobe Illustrator"
    },
    "PremiereProPlugin.dll": {
        "name": "Adobe Premiere Pro", "id": "adobe_premiere_pro",
        "exe_match": "premiereproc.exe|adobe premiere pro.exe", "app_group": "Adobe Premiere Pro"
    },
    "ObsStudioPlugin.dll": {
        "name": "OBS Studio", "id": "obs_studio",
        "exe_match": "obs64.exe|obs.exe", "app_group": "OBS Studio"
    },
    "AbletonPlugin.dll": {
        "name": "Ableton Live", "id": "ableton_live",
        "exe_match": "ableton live.exe|abltonlive.exe", "app_group": "Ableton Live"
    },
    "LightroomPlugin.dll": {
        "name": "Adobe Lightroom Classic", "id": "adobe_lightroom",
        "exe_match": "lightroom.exe", "app_group": "Adobe Lightroom"
    },
    "PhotoshopUxpPlugin.dll": {
        "name": "Adobe Photoshop", "id": "adobe_photoshop",
        "exe_match": "photoshop.exe", "app_group": "Adobe Photoshop"
    },
}


def harvest_loupedeck_59(verbose: bool = False) -> List[Dict]:
    """Harvest Loupedeck 5.9.1 app presets from DLL embedded XML <command> blocks."""
    print("\n[Loupedeck 5.9] Scanning DLLs in:", LD59_DIR)
    presets = []

    if not LD59_DIR.exists():
        print("  [WARN] ld59_a2 folder not found, skipping Loupedeck harvesting.")
        return presets

    for dll_name, app_info in _LD_APP_PLUGIN_MAP.items():
        dll_path = LD59_DIR / dll_name
        if not dll_path.exists():
            # Try inside lplug4 unpacked subdir
            for sub in LD59_DIR.glob(f"unpacked_*/{dll_name}"):
                dll_path = sub
                break
        if not dll_path.exists():
            if verbose:
                print(f"  [SKIP] {dll_name} not found")
            continue

        with open(dll_path, "rb") as f:
            data = f.read()

        # 1. Extract all embedded XML <configuration> blocks
        xmls = re.findall(rb"<configuration[\s\S]*?</configuration>", data)
        all_actions: List[Dict] = []
        for raw_xml in xmls:
            txt = raw_xml.decode("utf-8", "ignore")
            acts = _parse_ld_command_xml(txt, app_info["name"])
            for a in acts:
                if a["action"] and a not in all_actions:
                    all_actions.append(a)

        # 2. Check profileActions & macroCommands from embedded ProfileInfo.json ZIPs
        pos = 0
        while True:
            idx = data.find(b"PK\x05\x06", pos)
            if idx == -1:
                break
            try:
                cd_size, cd_offset, clen = struct.unpack("<IIH", data[idx + 12:idx + 22])
                zstart = idx - cd_size - cd_offset
                if 0 <= zstart < idx and data[zstart:zstart + 4] == b"PK\x03\x04":
                    zf = zipfile.ZipFile(io.BytesIO(data[zstart:idx + 22 + clen]))
                    if "ProfileInfo.json" in zf.namelist():
                        pinfo = json.loads(zf.read("ProfileInfo.json").decode("utf-8", "ignore"))
                        # Scan profileActions (e.g. Photoshop Liquify, Swiss Shift, etc.)
                        for pa in (pinfo.get("profileActions") or []):
                            pa_name = pa.get("displayName", "")
                            if not pa_name:
                                continue
                            params = pa.get("actionParameters", {}).get("parameters", {})
                            kb_key = params.get("keyboardKey", "")
                            if kb_key:
                                raw_k = kb_key.split("___")[0]
                                hotkey = _hotkey_from_ld_shortcut(raw_k.replace("ControlOrCommand", "CTRL").replace("KeyboardKey", "").replace("AltOrOption", "ALT"))
                                if hotkey:
                                    label = "".join(w[0] for w in re.sub(r"[^a-zA-Z0-9 ]", " ", pa_name).split() if w)[:6].upper()
                                    entry = {
                                        "id": f"ld_{_norm_id(pa_name)}",
                                        "name": pa_name,
                                        "label": label,
                                        "action": hotkey,
                                        "icon": "",
                                        "group": pa.get("groupName", ""),
                                    }
                                    if entry not in all_actions:
                                        all_actions.append(entry)

                        # Scan macroCommands (e.g. After Effects Trim In/Out, Capture One adjustments, etc.)
                        for mc in (pinfo.get("macroCommands") or []):
                            mc_name = mc.get("displayName", "")
                            if not mc_name or mc_name == "___GROUP___":
                                continue
                            first_act = ""
                            for ar in (mc.get("actions") or []):
                                m = re.search(r"@KeyboardShortcut___(.+)$", ar)
                                if m:
                                    raw = m.group(1)
                                    first_act = _hotkey_from_ld_shortcut(raw.replace("ControlOrCommand", "CTRL").replace("KeyboardKey", "").replace("AltOrOption", "ALT"))
                                    break
                            if not first_act:
                                continue
                            label = "".join(w[0] for w in re.sub(r"[^a-zA-Z0-9 ]", " ", mc_name).split() if w)[:6].upper()
                            entry = {
                                "id": f"ld_{_norm_id(mc_name)}",
                                "name": mc_name,
                                "label": label,
                                "action": first_act,
                                "icon": "",
                                "group": mc.get("groupName", ""),
                            }
                            if entry not in all_actions:
                                all_actions.append(entry)
            except Exception:
                pass
            pos = idx + 4

        # 3. Add default suite actions for major video/design plugins
        if dll_name == "PremiereProPlugin.dll":
            prem_defaults = [
                ("Mark In", "IN", "hotkey:I"),
                ("Mark Out", "OUT", "hotkey:O"),
                ("Razor Tool", "CUT", "hotkey:C"),
                ("Selection Tool", "SEL", "hotkey:V"),
                ("Ripple Edit", "RIPPLE", "hotkey:B"),
                ("Add Edit", "SPLIT", "hotkey:CTRL+K"),
                ("Play / Stop", "PLAY", "hotkey:SPACE"),
                ("Export Media", "EXPRT", "hotkey:CTRL+M"),
                ("Go to In", "GOTO IN", "hotkey:SHIFT+I"),
                ("Go to Out", "GOTO OUT", "hotkey:SHIFT+O"),
                ("Audio Gain", "GAIN", "hotkey:G"),
                ("Speed / Duration", "SPEED", "hotkey:CTRL+R"),
            ]
            for n, l, a in prem_defaults:
                all_actions.append({
                    "id": f"ld_{_norm_id(n)}",
                    "name": n,
                    "label": l,
                    "action": a,
                    "icon": "",
                    "group": "Timeline",
                })
        elif dll_name == "IllustratorPlugin.dll" and len(all_actions) < 4:
            ill_defaults = [
                ("Selection Tool", "SEL", "hotkey:V"),
                ("Direct Select", "DIRECT", "hotkey:A"),
                ("Pen Tool", "PEN", "hotkey:P"),
                ("Shape Builder", "BUILD", "hotkey:SHIFT+M"),
                ("Group", "GROUP", "hotkey:CTRL+G"),
                ("Make Clipping Mask", "MASK", "hotkey:CTRL+7"),
                ("Create Outlines", "OUTLINE", "hotkey:CTRL+SHIFT+O"),
                ("Zoom to Fit", "FIT", "hotkey:CTRL+0"),
                ("Export for Screens", "EXPRT", "hotkey:CTRL+ALT+E"),
            ]
            for n, l, a in ill_defaults:
                all_actions.append({
                    "id": f"ld_{_norm_id(n)}",
                    "name": n,
                    "label": l,
                    "action": a,
                    "icon": "",
                    "group": "Tools",
                })

        if not all_actions:
            if verbose:
                print(f"  [SKIP] {dll_name}: no command shortcuts found")
            continue

        # Deduplicate by action
        seen_actions = set()
        deduped = []
        for a in all_actions:
            key_s = a["action"]
            if key_s not in seen_actions:
                seen_actions.add(key_s)
                deduped.append(a)

        preset = {
            "source": "Loupedeck",
            "id": app_info["id"],
            "name": app_info["name"],
            "app_group": app_info["app_group"],
            "exe_match": app_info["exe_match"],
            "action_count": len(deduped),
            "actions": deduped,
            "recommended_cells": _best_cells(deduped),
            "radial_menus": [],
        }
        presets.append(preset)
        print(f"  [Loupedeck] {app_info['name']:32s} → {len(deduped):3d} actions")

    return presets


# ==============================================================================
# SOURCE 2: TOURBOX CONSOLE 5.11.3 – tourbox.db XML
# ==============================================================================

_TOURBOX_APP_ENTRIES = [
    ("Adobe Photoshop", "adobe_photoshop", "photoshop.exe"),
    ("Adobe Lightroom", "adobe_lightroom", "lightroom.exe"),
]


def harvest_tourbox(verbose: bool = False) -> List[Dict]:
    """Decode tourbox.db <dictionaryMap> into shortcut presets for Photoshop & Lightroom."""
    print("\n[TourBox] Parsing:", TOURBOX_DB)
    presets = []

    if not TOURBOX_DB.exists():
        print("  [WARN] tourbox.db not found, skipping.")
        return presets

    try:
        tree = ET.parse(str(TOURBOX_DB))
    except ET.ParseError as e:
        print(f"  [ERROR] Failed to parse tourbox.db: {e}")
        return presets

    root = tree.getroot()
    entries = root.findall("./dictionaryMap/entry")

    for i, (app_name, app_id, exe_match) in enumerate(_TOURBOX_APP_ENTRIES):
        if i >= len(entries):
            break
        entry = entries[i]
        descs = entry.findall("./list/ShortDesc")
        actions = []
        for sd in descs:
            m_bits = int(sd.findtext("m") or "0")
            vk = int(sd.findtext("s") or "0")
            d_name = (sd.findtext("d") or "").strip()
            if not d_name or not vk:
                continue
            hotkey = _vk_to_hotkey(m_bits, vk)
            if not hotkey:
                continue
            label = "".join(w[0] for w in re.sub(r"[^a-zA-Z0-9 ]", " ", d_name).split() if w)[:6].upper()
            actions.append({
                "id": f"tb_{_norm_id(d_name)}",
                "name": d_name,
                "label": label,
                "action": hotkey,
                "icon": "",
            })

        print(f"  [TourBox] {app_name:32s} → {len(actions):3d} shortcuts")
        preset = {
            "source": "TourBox",
            "id": app_id,
            "name": app_name,
            "app_group": app_name,
            "exe_match": exe_match,
            "action_count": len(actions),
            "actions": actions,
            "recommended_cells": _best_cells(actions),
            "radial_menus": [],
        }
        presets.append(preset)

    return presets


# ==============================================================================
# SOURCE 3: WACOM TABLET DRIVER 6.4 – AppGestures.xml gesture→keystroke
# ==============================================================================

_WACOM_APP_MAP = {
    "photoshop":        ("Adobe Photoshop",          "adobe_photoshop",          "photoshop.exe"),
    "photoshp":         ("Adobe Photoshop",          "adobe_photoshop",          "photoshop.exe"),
    "AfterFX":          ("Adobe After Effects",      "adobe_after_effects",      "afterfx.exe"),
    "illustrator":      ("Adobe Illustrator",        "adobe_illustrator",        "illustrator.exe"),
    "indesign":         ("Adobe InDesign",           "adobe_indesign",           "indesign.exe"),
    "bridge":           ("Adobe Bridge",             "adobe_bridge",             "bridge.exe"),
    "lightroom":        ("Adobe Lightroom",          "adobe_lightroom",          "lightroom.exe"),
    "CaptureOne":       ("Capture One",              "capture_one",              "captureone.exe"),
    "Blender":          ("Blender",                  "blender",                  "blender.exe"),
    "krita":            ("Krita",                    "krita",                    "krita.exe"),
    "CLIPStudioPaint":  ("Clip Studio Paint",        "clip_studio_paint",        "clipstudiopaint.exe"),
    "ZBrush":           ("ZBrush",                   "zbrush",                   "zbrush.exe"),
    "ZBrushCore":       ("ZBrushCore",               "zbrushcore",               "zbrushcore.exe"),
    "Rhino":            ("Rhino",                    "rhino",                    "rhino.exe"),
    "maya":             ("Maya",                     "maya",                     "maya.exe"),
    "3dsMax":           ("3ds Max",                  "3ds_max",                  "3dsmax.exe"),
    "SketchBook":       ("Sketchbook",               "sketchbook",               "sketchbook.exe"),
    "sai":              ("Paint Tool SAI",           "paint_tool_sai",           "sai.exe"),
    "painter":          ("Corel Painter",            "corel_painter",            "painter.exe"),
    "Figma":            ("Figma",                    "figma",                    "figma.exe"),
    "fusion360":        ("Fusion 360",               "fusion360",                "fusion360.exe"),
    "sldworks":         ("SolidWorks",               "solidworks",               "sldworks.exe"),
    "Shapr3D":          ("Shapr3D",                  "shapr3d",                  "shapr3d.exe"),
    "Inventor":         ("Autodesk Inventor",        "inventor",                 "inventor.exe"),
    "Alias":            ("Autodesk Alias",           "alias",                    "alias.exe"),
    "CINEMA 4D":        ("Cinema 4D",                "cinema4d",                 "cinema 4d.exe"),
    "modo":             ("Modo",                     "modo",                     "modo.exe"),
    "Adobe Premiere Pro":("Adobe Premiere Pro",      "adobe_premiere_pro",       "premiereproc.exe"),
    "fresco":           ("Adobe Fresco",             "adobe_fresco",             "fresco.exe"),
}

_WACOM_GESTURE_NAMES = {
    "Undo": ("Undo", "hotkey:CTRL+Z"),
    "Redo": ("Redo", "hotkey:CTRL+SHIFT+Z"),
    "ZoomIn": ("Zoom In", "hotkey:CTRL+="),
    "ZoomOut": ("Zoom Out", "hotkey:CTRL+-"),
}


def _wacom_parse_element(elem: ET.Element) -> List[Dict]:
    """Extract keystroke-driven gestures from one <ArrayElement>."""
    actions = []
    for child in elem:
        tag = child.tag
        if tag in ("identifier", "auxidentifier", "displayname",
                   "useTapAssist", "AutoBehavior", "immersive", "flipInkPenRotation"):
            continue
        # Check for <keystroke> child
        ks = child.findtext("keystroke")
        if ks:
            hotkey = _hotkey_from_ks(ks)
            if not hotkey:
                continue
            friendly = tag
            # Use predefined friendly name if available
            if tag in _WACOM_GESTURE_NAMES:
                friendly = _WACOM_GESTURE_NAMES[tag][0]
            label = "".join(w[0] for w in re.sub(r"[^a-zA-Z0-9 ]", " ", tag).split() if w)[:6].upper()
            actions.append({
                "id": f"wacom_{_norm_id(tag)}",
                "name": friendly,
                "label": label,
                "action": hotkey,
                "icon": "",
            })
        # Check for <input type="string"> based gesture (mousebutton + modifier = pan/zoom)
        elif child.findtext("input") == "scrollwheelup" or child.findtext("input") == "scrollwheeldown":
            inp = child.findtext("input", "")
            mods = child.findtext("modifiers", "")
            if inp and tag:
                action_name = tag
                if "up" in inp.lower():
                    hotkey = "hotkey:CTRL+=" if "control" in mods else "hotkey:SCROLL_UP"
                else:
                    hotkey = "hotkey:CTRL+-" if "control" in mods else "hotkey:SCROLL_DOWN"
                label = tag[:6].upper()
                actions.append({
                    "id": f"wacom_{_norm_id(tag)}",
                    "name": action_name,
                    "label": label,
                    "action": hotkey,
                    "icon": "",
                })
    return actions


def harvest_wacom(verbose: bool = False) -> List[Dict]:
    """Harvest Wacom AppGestures.xml per-app keystroke gesture mappings."""
    print("\n[Wacom] Parsing:", WACOM_XML)
    presets = []

    if not WACOM_XML.exists():
        print("  [WARN] AppGestures.xml not found, skipping.")
        return presets

    try:
        tree = ET.parse(str(WACOM_XML))
    except ET.ParseError as e:
        print(f"  [ERROR] Failed to parse AppGestures.xml: {e}")
        return presets

    root = tree.getroot()
    for elem in root.findall("ArrayElement"):
        ident = elem.findtext("identifier") or ""
        if ident not in _WACOM_APP_MAP:
            continue
        app_name, app_id, exe_match = _WACOM_APP_MAP[ident]
        actions = _wacom_parse_element(elem)
        if not actions:
            if verbose:
                print(f"  [SKIP] Wacom {ident}: no keystroke actions")
            continue

        print(f"  [Wacom] {app_name:32s} → {len(actions):3d} gesture→keystroke mappings")
        preset = {
            "source": "Wacom",
            "id": app_id,
            "name": app_name,
            "app_group": app_name,
            "exe_match": exe_match,
            "action_count": len(actions),
            "actions": actions,
            "recommended_cells": _best_cells(actions),
            "radial_menus": [],
        }
        presets.append(preset)

    return presets


# ==============================================================================
# SOURCE 4: POWER-USER CURATED – 50 high-impact missing integrations
# ==============================================================================

def _pu(id: str, name: str, exe: str, group: str, actions: List[tuple]) -> Dict:
    """Helper to build a Power-User preset entry."""
    acts = []
    for (n, lbl, act, icon) in actions:
        acts.append({"id": f"pu_{_norm_id(n)}", "name": n, "label": lbl[:6].upper(), "action": act, "icon": icon})
    return {
        "source": "PowerUser",
        "id": id,
        "name": name,
        "app_group": group,
        "exe_match": exe,
        "action_count": len(acts),
        "actions": acts,
        "recommended_cells": _best_cells(acts),
        "radial_menus": [],
    }


def harvest_poweruser() -> List[Dict]:
    """Return curated Power-User preset list for 50 missing integrations."""
    print("\n[PowerUser] Building curated preset catalog...")
    presets = []

    presets.append(_pu("blender", "Blender", "blender.exe|blender-app.exe", "Blender", [
        ("Edit Mode",         "TAB",   "hotkey:TAB",          ""),
        ("Search (F3)",       "SRCH",  "hotkey:F3",           ""),
        ("Extrude (E)",       "EXTR",  "hotkey:E",            ""),
        ("Bevel (Ctrl+B)",    "BEVEL", "hotkey:CTRL+B",       ""),
        ("Loop Cut (Ctrl+R)", "LOOP",  "hotkey:CTRL+R",       ""),
        ("Shading (Z)",       "SHADE", "hotkey:Z",            ""),
        ("Render (F12)",      "RENDER","hotkey:F12",          ""),
        ("Front View (Num1)", "FRONT", "hotkey:NUM1",         ""),
        ("Top View (Num7)",   "TOP",   "hotkey:NUM7",         ""),
    ]))

    presets.append(_pu("photoshop", "Adobe Photoshop", "photoshop.exe", "Adobe Photoshop", [
        ("Free Transform",    "XFORM", "hotkey:CTRL+T",       ""),
        ("Brush Tool",        "BRUSH", "hotkey:B",            ""),
        ("Eraser Tool",       "ERASE", "hotkey:E",            ""),
        ("Duplicate Layer",   "DUP",   "hotkey:CTRL+J",       ""),
        ("New Layer",         "NEW",   "hotkey:CTRL+SHIFT+N", ""),
        ("Stamp Visible",     "STAMP", "hotkey:CTRL+SHIFT+ALT+E", ""),
        ("Curves",            "CURVE", "hotkey:CTRL+M",       ""),
        ("Levels",            "LEVEL", "hotkey:CTRL+L",       ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("adobe_premiere_pro", "Adobe Premiere Pro", "premiereproc.exe|adobe premiere pro.exe", "Adobe Premiere Pro", [
        ("Play / Stop",       "PLAY",  "hotkey:SPACE",        ""),
        ("Mark In (I)",       "IN",    "hotkey:I",            ""),
        ("Mark Out (O)",      "OUT",   "hotkey:O",            ""),
        ("Razor Tool (C)",    "CUT",   "hotkey:C",            ""),
        ("Selection Tool (V)","SEL",   "hotkey:V",            ""),
        ("Add Edit",          "SPLIT", "hotkey:CTRL+K",       ""),
        ("Ripple Delete",     "RDEL",  "hotkey:SHIFT+DELETE", ""),
        ("Ripple Edit (B)",   "RIPPLE","hotkey:B",            ""),
        ("Export Media",      "EXPRT", "hotkey:CTRL+M",       ""),
    ]))

    presets.append(_pu("adobe_after_effects", "Adobe After Effects", "afterfx.exe", "Adobe After Effects", [
        ("Play / Preview",    "PLAY",  "hotkey:SPACE",        ""),
        ("Trim In (Alt+[)",   "TRIM IN","hotkey:ALT+[",       ""),
        ("Trim Out (Alt+])",  "TRIM OUT","hotkey:ALT+]",      ""),
        ("Split Layer",       "SPLIT", "hotkey:CTRL+SHIFT+D", ""),
        ("Position (P)",      "POS",   "hotkey:P",            ""),
        ("Scale (S)",         "SCALE", "hotkey:S",            ""),
        ("Rotation (R)",      "ROT",   "hotkey:R",            ""),
        ("Opacity (T)",       "OPAC",  "hotkey:T",            ""),
        ("Easy Ease (F9)",    "EASE",  "hotkey:F9",           ""),
    ]))

    presets.append(_pu("adobe_illustrator", "Adobe Illustrator", "illustrator.exe", "Adobe Illustrator", [
        ("Selection (V)",     "SEL",   "hotkey:V",            ""),
        ("Direct Select (A)", "DIRECT","hotkey:A",            ""),
        ("Pen Tool (P)",      "PEN",   "hotkey:P",            ""),
        ("Shape Builder",     "BUILD", "hotkey:SHIFT+M",      ""),
        ("Group (Ctrl+G)",    "GROUP", "hotkey:CTRL+G",       ""),
        ("Clipping Mask",     "MASK",  "hotkey:CTRL+7",       ""),
        ("Create Outlines",   "OUTLINE","hotkey:CTRL+SHIFT+O",""),
        ("Zoom to Fit",       "FIT",   "hotkey:CTRL+0",       ""),
        ("Export",            "EXPRT", "hotkey:CTRL+ALT+E",   ""),
    ]))

    presets.append(_pu("vs_code", "VS Code / Cursor", "code.exe|cursor.exe", "VS Code", [
        ("Command Palette",   "CMD",   "hotkey:CTRL+SHIFT+P", ""),
        ("Quick Open File",   "OPEN",  "hotkey:CTRL+P",       ""),
        ("Toggle Terminal",   "TERM",  "hotkey:CTRL+GRAVE",   ""),
        ("Split Editor",      "SPLIT", "hotkey:CTRL+\\",      ""),
        ("Format Document",   "FMT",   "hotkey:SHIFT+ALT+F",  ""),
        ("Go To Definition",  "GO DEF","hotkey:F12",          ""),
        ("Rename Symbol",     "RENAME","hotkey:F2",           ""),
        ("Toggle Sidebar",    "SIDE",  "hotkey:CTRL+B",       ""),
        ("Run / Debug",       "RUN",   "hotkey:F5",           ""),
    ]))

    presets.append(_pu("windows_terminal", "Windows Terminal", "windowsterminal.exe", "Windows Terminal", [
        ("New Tab",           "NEW",   "hotkey:CTRL+SHIFT+T", ""),
        ("New Pane Vert",     "SPLIT", "hotkey:ALT+SHIFT+PLUS",""),
        ("Close Tab",         "CLOSE", "hotkey:CTRL+SHIFT+W", ""),
        ("Tab 1",             "TAB1",  "hotkey:CTRL+ALT+1",   ""),
        ("Find",              "FIND",  "hotkey:CTRL+SHIFT+F", ""),
        ("Copy",              "COPY",  "hotkey:CTRL+SHIFT+C", ""),
        ("Paste",             "PASTE", "hotkey:CTRL+SHIFT+V", ""),
        ("Zoom In",           "ZOOM+", "hotkey:CTRL+=",       ""),
        ("Zoom Out",          "ZOOM-", "hotkey:CTRL+-",       ""),
    ]))

    presets.append(_pu("davinci_resolve", "DaVinci Resolve", "resolve.exe", "DaVinci Resolve", [
        ("Play / Stop",       "PLAY",  "hotkey:SPACE",        ""),
        ("Mark In",           "IN",    "hotkey:I",            ""),
        ("Mark Out",          "OUT",   "hotkey:O",            ""),
        ("Razor at Playhead", "CUT",   "hotkey:CTRL+B",       ""),
        ("Split Clip",        "SPLIT", "hotkey:CTRL+\\",      ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Color Page",        "COLOR", "hotkey:SHIFT+5",      ""),
        ("Edit Page",         "EDIT",  "hotkey:SHIFT+4",      ""),
        ("Deliver",           "DELIVR","hotkey:SHIFT+8",      ""),
    ]))

    presets.append(_pu("capcut", "CapCut", "capcut.exe", "CapCut", [
        ("Play / Pause",      "PLAY",  "hotkey:SPACE",        ""),
        ("Split",             "SPLIT", "hotkey:CTRL+B",       ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Redo",              "REDO",  "hotkey:CTRL+SHIFT+Z", ""),
        ("Delete",            "DEL",   "hotkey:DELETE",       ""),
        ("Export",            "EXPORT","hotkey:CTRL+E",       ""),
        ("Zoom In",           "ZOOM+", "hotkey:CTRL+=",       ""),
        ("Zoom Out",          "ZOOM-", "hotkey:CTRL+-",       ""),
        ("Select All",        "ALL",   "hotkey:CTRL+A",       ""),
    ]))

    presets.append(_pu("obs_studio", "OBS Studio", "obs64.exe|obs.exe", "OBS Studio", [
        ("Start / Stop Stream","STREAM","hotkey:CTRL+F5",     ""),
        ("Start / Stop Record","REC",   "hotkey:CTRL+F6",     ""),
        ("Scene 1",           "SC1",   "hotkey:CTRL+1",       ""),
        ("Scene 2",           "SC2",   "hotkey:CTRL+2",       ""),
        ("Scene 3",           "SC3",   "hotkey:CTRL+3",       ""),
        ("Mute Mic",          "MIC",   "hotkey:CTRL+M",       ""),
        ("Take Screenshot",   "SNAP",  "hotkey:CTRL+SHIFT+S", ""),
        ("Pause Record",      "PAUSE", "hotkey:CTRL+SHIFT+P", ""),
        ("Stats",             "STATS", "hotkey:CTRL+SHIFT+W", ""),
    ]))

    presets.append(_pu("vlc", "VLC Media Player", "vlc.exe", "VLC", [
        ("Play / Pause",      "PLAY",  "hotkey:SPACE",        ""),
        ("Volume +",          "VOL+",  "hotkey:CTRL+UP",      ""),
        ("Volume -",          "VOL-",  "hotkey:CTRL+DOWN",    ""),
        ("Fullscreen",        "FULL",  "hotkey:F",            ""),
        ("Skip +10s",         "+10S",  "hotkey:ALT+RIGHT",    ""),
        ("Skip -10s",         "-10S",  "hotkey:ALT+LEFT",     ""),
        ("Next Track",        "NEXT",  "hotkey:N",            ""),
        ("Prev Track",        "PREV",  "hotkey:P",            ""),
        ("Snapshot",          "SNAP",  "hotkey:SHIFT+S",      ""),
    ]))

    presets.append(_pu("spotify", "Spotify", "spotify.exe", "Spotify", [
        ("Play / Pause",      "PLAY",  "hotkey:SPACE",        ""),
        ("Next Track",        "NEXT",  "hotkey:CTRL+RIGHT",   ""),
        ("Prev Track",        "PREV",  "hotkey:CTRL+LEFT",    ""),
        ("Volume +",          "VOL+",  "hotkey:CTRL+UP",      ""),
        ("Volume -",          "VOL-",  "hotkey:CTRL+DOWN",    ""),
        ("Shuffle",           "SHUF",  "hotkey:CTRL+S",       ""),
        ("Repeat",            "REP",   "hotkey:CTRL+R",       ""),
        ("Like Track",        "LIKE",  "hotkey:ALT+SHIFT+B",  ""),
        ("Search",            "SRCH",  "hotkey:CTRL+L",       ""),
    ]))

    presets.append(_pu("figma", "Figma", "figma.exe", "Figma", [
        ("Move Tool (V)",     "MOVE",  "hotkey:V",            ""),
        ("Frame Tool (F)",    "FRAME", "hotkey:F",            ""),
        ("Rectangle (R)",     "RECT",  "hotkey:R",            ""),
        ("Pen Tool (P)",      "PEN",   "hotkey:P",            ""),
        ("Text Tool (T)",     "TEXT",  "hotkey:T",            ""),
        ("Zoom to Fit",       "FIT",   "hotkey:SHIFT+1",      ""),
        ("Group (Ctrl+G)",    "GROUP", "hotkey:CTRL+G",       ""),
        ("Ungroup",           "UNGR",  "hotkey:CTRL+SHIFT+G", ""),
        ("Export",            "EXPRT", "hotkey:CTRL+SHIFT+E", ""),
    ]))

    presets.append(_pu("inkscape", "Inkscape", "inkscape.exe", "Inkscape", [
        ("Select (F1)",       "SEL",   "hotkey:F1",           ""),
        ("Node Tool (N)",     "NODE",  "hotkey:N",            ""),
        ("Pen Tool (P)",      "PEN",   "hotkey:P",            ""),
        ("Fill & Stroke",     "FILL",  "hotkey:SHIFT+CTRL+F", ""),
        ("XML Editor",        "XML",   "hotkey:CTRL+SHIFT+X", ""),
        ("Group (Ctrl+G)",    "GROUP", "hotkey:CTRL+G",       ""),
        ("Zoom Fit",          "FIT",   "hotkey:5",            ""),
        ("Export PNG",        "EXPRT", "hotkey:CTRL+SHIFT+E", ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("krita", "Krita", "krita.exe", "Krita", [
        ("Brush Tool (B)",    "BRUSH", "hotkey:B",            ""),
        ("Eraser (E)",        "ERASE", "hotkey:E",            ""),
        ("Transform (CTRL+T)","XFORM", "hotkey:CTRL+T",       ""),
        ("Fill (F)",          "FILL",  "hotkey:F",            ""),
        ("Zoom In (+)",       "ZOOM+", "hotkey:PLUS",         ""),
        ("Zoom Out (-)",      "ZOOM-", "hotkey:MINUS",        ""),
        ("Rotate View",       "ROT",   "hotkey:SHIFT+SPACE",  ""),
        ("Mirror Canvas",     "FLIP",  "hotkey:M",            ""),
        ("Flatten Image",     "FLAT",  "hotkey:CTRL+SHIFT+E", ""),
    ]))

    presets.append(_pu("clip_studio_paint", "Clip Studio Paint", "clipstudiopaint.exe", "Clip Studio Paint", [
        ("Brush (B)",         "BRUSH", "hotkey:B",            ""),
        ("Eraser (E)",        "ERASE", "hotkey:E",            ""),
        ("Lasso Select (M)",  "LASSO", "hotkey:M",            ""),
        ("Fill (G)",          "FILL",  "hotkey:G",            ""),
        ("Zoom In (CTRL++)",  "ZOOM+", "hotkey:CTRL+PLUS",    ""),
        ("Zoom Out (CTRL+-)", "ZOOM-", "hotkey:CTRL+MINUS",   ""),
        ("Rotate (R)",        "ROT",   "hotkey:R",            ""),
        ("Flip Canvas",       "FLIP",  "hotkey:CTRL+SHIFT+H", ""),
        ("Merge Layers",      "MERGE", "hotkey:CTRL+E",       ""),
    ]))

    presets.append(_pu("affinity_designer", "Affinity Designer", "designer.exe|affinity designer.exe", "Affinity", [
        ("Select (V)",        "SEL",   "hotkey:V",            ""),
        ("Node Edit (A)",     "NODE",  "hotkey:A",            ""),
        ("Pen Tool (P)",      "PEN",   "hotkey:P",            ""),
        ("Zoom Fit",          "FIT",   "hotkey:CTRL+0",       ""),
        ("Export",            "EXPRT", "hotkey:CTRL+ALT+E",   ""),
        ("Group (Ctrl+G)",    "GROUP", "hotkey:CTRL+G",       ""),
        ("Symbol Sync",       "SYNC",  "hotkey:CTRL+SHIFT+Y", ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Redo",              "REDO",  "hotkey:CTRL+Y",       ""),
    ]))

    presets.append(_pu("affinity_photo", "Affinity Photo", "photo.exe|affinity photo.exe", "Affinity", [
        ("Brush (B)",         "BRUSH", "hotkey:B",            ""),
        ("Healing Brush (J)", "HEAL",  "hotkey:J",            ""),
        ("Develop",           "DEVELOP","hotkey:CTRL+SHIFT+D",""),
        ("Tone Mapping",      "TONE",  "hotkey:CTRL+SHIFT+T", ""),
        ("Liquify",           "LIQ",   "hotkey:CTRL+SHIFT+X", ""),
        ("Levels",            "LEVEL", "hotkey:CTRL+L",       ""),
        ("Curves",            "CURVE", "hotkey:CTRL+M",       ""),
        ("Sharpen",           "SHARP", "hotkey:CTRL+SHIFT+S", ""),
        ("Export",            "EXPRT", "hotkey:CTRL+ALT+E",   ""),
    ]))

    presets.append(_pu("fl_studio", "FL Studio", "fl64.exe|fl studio.exe", "FL Studio", [
        ("Play / Pause",      "PLAY",  "hotkey:SPACE",        ""),
        ("Record",            "REC",   "hotkey:CTRL+R",       ""),
        ("Pattern Mode",      "PAT",   "hotkey:CTRL+P",       ""),
        ("Song Mode",         "SONG",  "hotkey:CTRL+H",       ""),
        ("Mixer",             "MIX",   "hotkey:CTRL+M",       ""),
        ("Piano Roll",        "PIANO", "hotkey:CTRL+E",       ""),
        ("Browser",           "BROWSER","hotkey:CTRL+B",      ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Zoom In",           "ZOOM+", "hotkey:CTRL+RIGHT",   ""),
    ]))

    presets.append(_pu("ableton_live", "Ableton Live", "ableton live.exe", "Ableton Live", [
        ("Play / Pause",      "PLAY",  "hotkey:SPACE",        ""),
        ("Record",            "REC",   "hotkey:F9",           ""),
        ("Session View",      "SESSION","hotkey:CTRL+ALT+2",  ""),
        ("Arrangement View",  "ARRNG", "hotkey:CTRL+ALT+1",   ""),
        ("Tap Tempo",         "TAP",   "hotkey:CTRL+ALT+SHIFT+T",""),
        ("New Scene",         "SCENE", "hotkey:CTRL+SHIFT+E", ""),
        ("Add MIDI Track",    "MIDI",  "hotkey:CTRL+SHIFT+T", ""),
        ("Add Audio Track",   "AUDIO", "hotkey:CTRL+T",       ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("reaper", "Reaper", "reaper.exe", "Reaper", [
        ("Play / Stop",       "PLAY",  "hotkey:SPACE",        ""),
        ("Record",            "REC",   "hotkey:CTRL+SHIFT+R", ""),
        ("Split at Cursor",   "SPLIT", "hotkey:S",            ""),
        ("Zoom In",           "ZOOM+", "hotkey:CTRL+PLUS",    ""),
        ("Zoom Out",          "ZOOM-", "hotkey:CTRL+MINUS",   ""),
        ("Mute Track",        "MUTE",  "hotkey:ALT+M",        ""),
        ("Solo Track",        "SOLO",  "hotkey:ALT+S",        ""),
        ("Mixdown",           "RENDER","hotkey:CTRL+ALT+R",   ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("audacity", "Audacity", "audacity.exe", "Audacity", [
        ("Play / Pause",      "PLAY",  "hotkey:SPACE",        ""),
        ("Record",            "REC",   "hotkey:R",            ""),
        ("Stop",              "STOP",  "hotkey:S",            ""),
        ("Normalize",         "NORM",  "hotkey:CTRL+SHIFT+N", ""),
        ("Export MP3",        "EXPRT", "hotkey:CTRL+SHIFT+E", ""),
        ("Zoom In",           "ZOOM+", "hotkey:CTRL+1",       ""),
        ("Zoom Out",          "ZOOM-", "hotkey:CTRL+3",       ""),
        ("Silence",           "SILNCE","hotkey:CTRL+L",       ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("lightburn", "LightBurn", "lightburn.exe", "LightBurn", [
        ("Start Job",         "START", "hotkey:CTRL+SHIFT+P", ""),
        ("Stop",              "STOP",  "hotkey:CTRL+SHIFT+H", ""),
        ("Frame",             "FRAME", "hotkey:CTRL+SHIFT+F", ""),
        ("Home",              "HOME",  "hotkey:CTRL+SHIFT+G", ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Zoom Fit",          "FIT",   "hotkey:CTRL+SHIFT+A", ""),
        ("New Layer",         "LAYER", "hotkey:CTRL+L",       ""),
        ("Material Library",  "MAT",   "hotkey:CTRL+SHIFT+L", ""),
        ("Settings",          "SETTINGS","hotkey:CTRL+COMMA", ""),
    ]))

    presets.append(_pu("lychee_slicer", "Lychee Slicer", "lychee slicer.exe|lychee.exe", "Lychee Slicer", [
        ("Slice",             "SLICE", "hotkey:CTRL+SHIFT+S", ""),
        ("Import",            "IMPORT","hotkey:CTRL+I",       ""),
        ("Export",            "EXPORT","hotkey:CTRL+E",       ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Rotate",            "ROT",   "hotkey:R",            ""),
        ("Scale",             "SCALE", "hotkey:S",            ""),
        ("Zoom Fit",          "FIT",   "hotkey:NUM5",         ""),
        ("Top View",          "TOP",   "hotkey:NUM7",         ""),
        ("Front View",        "FRONT", "hotkey:NUM1",         ""),
    ]))

    presets.append(_pu("openscad", "OpenSCAD", "openscad.exe", "OpenSCAD", [
        ("Render (F6)",       "RENDER","hotkey:F6",           ""),
        ("Preview (F5)",      "PREV",  "hotkey:F5",           ""),
        ("Export STL",        "EXPRT", "hotkey:CTRL+SHIFT+E", ""),
        ("Zoom Fit",          "FIT",   "hotkey:V",            ""),
        ("Top View",          "TOP",   "hotkey:7",            ""),
        ("Front View",        "FRONT", "hotkey:1",            ""),
        ("Right View",        "RIGHT", "hotkey:3",            ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("New",               "NEW",   "hotkey:CTRL+N",       ""),
    ]))

    presets.append(_pu("microsoft_teams", "Microsoft Teams", "teams.exe|ms-teams.exe", "Teams", [
        ("Mute (Ctrl+Shift+M)", "MUTE","hotkey:CTRL+SHIFT+M",""),
        ("Camera Toggle",     "CAM",   "hotkey:CTRL+SHIFT+O",""),
        ("Raise Hand",        "HAND",  "hotkey:CTRL+SHIFT+K",""),
        ("Open Chat",         "CHAT",  "hotkey:CTRL+SHIFT+C",""),
        ("Start Meeting",     "MEET",  "hotkey:CTRL+SHIFT+X",""),
        ("Screen Share",      "SHARE", "hotkey:CTRL+SHIFT+E",""),
        ("Accept Call",       "CALL",  "hotkey:CTRL+SHIFT+A",""),
        ("Reject Call",       "REJCT", "hotkey:CTRL+SHIFT+D",""),
        ("Files Tab",         "FILES", "hotkey:CTRL+SHIFT+F",""),
    ]))

    presets.append(_pu("zoom", "Zoom", "zoom.exe", "Zoom", [
        ("Mute / Unmute",     "MUTE",  "hotkey:ALT+A",        ""),
        ("Video Toggle",      "CAM",   "hotkey:ALT+V",        ""),
        ("Participants",      "PARTS", "hotkey:ALT+U",        ""),
        ("Screen Share",      "SHARE", "hotkey:ALT+SHIFT+S",  ""),
        ("Raise Hand",        "HAND",  "hotkey:ALT+Y",        ""),
        ("React",             "REACT", "hotkey:ALT+Y",        ""),
        ("Chat",              "CHAT",  "hotkey:ALT+H",        ""),
        ("Record",            "REC",   "hotkey:ALT+R",        ""),
        ("End Meeting",       "END",   "hotkey:ALT+Q",        ""),
    ]))

    presets.append(_pu("slack", "Slack", "slack.exe", "Slack", [
        ("Next Unread",       "NEXT",  "hotkey:ALT+SHIFT+DOWN",""),
        ("Prev Unread",       "PREV",  "hotkey:ALT+SHIFT+UP", ""),
        ("Quick Switcher",    "SWITCH","hotkey:CTRL+K",        ""),
        ("Search",            "SRCH",  "hotkey:CTRL+F",       ""),
        ("New Message",       "MSG",   "hotkey:CTRL+N",       ""),
        ("Mute Channel",      "MUTE",  "hotkey:CTRL+SHIFT+M", ""),
        ("All Unreads",       "ALL",   "hotkey:CTRL+SHIFT+A", ""),
        ("Direct Messages",   "DM",    "hotkey:CTRL+SHIFT+K", ""),
        ("Preferences",       "PREFS", "hotkey:CTRL+COMMA",   ""),
    ]))

    presets.append(_pu("obsidian", "Obsidian", "obsidian.exe", "Obsidian", [
        ("Quick Switcher",    "SWITCH","hotkey:CTRL+O",        ""),
        ("Command Palette",   "CMD",   "hotkey:CTRL+P",        ""),
        ("New Note",          "NEW",   "hotkey:CTRL+N",        ""),
        ("Toggle Edit/View",  "EDIT",  "hotkey:CTRL+E",        ""),
        ("Graph View",        "GRAPH", "hotkey:CTRL+G",        ""),
        ("Back",              "BACK",  "hotkey:ALT+LEFT",      ""),
        ("Forward",           "FWD",   "hotkey:ALT+RIGHT",     ""),
        ("Search In Files",   "SRCH",  "hotkey:CTRL+SHIFT+F",  ""),
        ("Toggle Left Panel", "PANEL", "hotkey:CTRL+SHIFT+L",  ""),
    ]))

    presets.append(_pu("notion", "Notion", "notion.exe", "Notion", [
        ("New Page",          "NEW",   "hotkey:CTRL+SHIFT+N",  ""),
        ("Search",            "SRCH",  "hotkey:CTRL+P",        ""),
        ("Toggle Dark Mode",  "DARK",  "hotkey:CTRL+SHIFT+L",  ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",        ""),
        ("Bold",              "BOLD",  "hotkey:CTRL+B",        ""),
        ("Italic",            "ITALIC","hotkey:CTRL+I",        ""),
        ("Heading 1",         "H1",    "hotkey:CTRL+ALT+1",    ""),
        ("Heading 2",         "H2",    "hotkey:CTRL+ALT+2",    ""),
        ("Toggle Sidebar",    "SIDE",  "hotkey:CTRL+SHIFT+\\", ""),
    ]))

    presets.append(_pu("steam", "Steam", "steam.exe", "Steam", [
        ("Open Library",      "LIB",   "hotkey:CTRL+SHIFT+L",  ""),
        ("Open Store",        "STORE", "hotkey:CTRL+SHIFT+S",  ""),
        ("Open Community",    "COMM",  "hotkey:CTRL+SHIFT+C",  ""),
        ("Friends List",      "FRND",  "hotkey:CTRL+SHIFT+F",  ""),
        ("Big Picture Mode",  "BIG",   "hotkey:CTRL+SHIFT+B",  ""),
        ("Take Screenshot",   "SNAP",  "hotkey:F12",           ""),
        ("Steam Overlay",     "OVRLY", "hotkey:SHIFT+TAB",     ""),
        ("Close Game",        "CLOSE", "hotkey:ALT+F4",        ""),
        ("Refresh",           "REFR",  "hotkey:F5",            ""),
    ]))

    presets.append(_pu("nvidia_overlay", "NVIDIA GeForce Overlay", "nvcontainer.exe|nvgexui.exe", "NVIDIA", [
        ("Instant Replay",    "REPLAY","hotkey:ALT+SHIFT+F10", ""),
        ("Record Toggle",     "REC",   "hotkey:ALT+F9",        ""),
        ("Screenshot",        "SNAP",  "hotkey:ALT+F1",        ""),
        ("Toggle FPS",        "FPS",   "hotkey:ALT+F12",       ""),
        ("Broadcast",         "LIVE",  "hotkey:ALT+F8",        ""),
        ("Mute Mic",          "MUTE",  "hotkey:ALT+F4",        ""),
        ("Filter Effect",     "FX",    "hotkey:ALT+F2",        ""),
        ("Performance Overlay","PERF", "hotkey:ALT+F5",        ""),
        ("Open Overlay",      "OVRLY", "hotkey:ALT+Z",         ""),
    ]))

    presets.append(_pu("jetbrains_idea", "JetBrains IDE (IDEA / PyCharm)", "idea64.exe|pycharm64.exe", "JetBrains", [
        ("Find Action (CTRL+SHIFT+A)", "ACTION","hotkey:CTRL+SHIFT+A",""),
        ("Run (SHIFT+F10)",   "RUN",   "hotkey:SHIFT+F10",    ""),
        ("Debug (SHIFT+F9)", "DEBUG",  "hotkey:SHIFT+F9",     ""),
        ("Refactor (CTRL+ALT+SHIFT+T)","REFAC","hotkey:CTRL+ALT+SHIFT+T",""),
        ("Go To Class",       "CLASS", "hotkey:CTRL+N",       ""),
        ("Reformat Code",     "FMT",   "hotkey:CTRL+ALT+L",   ""),
        ("Toggle Breakpoint", "BRK",   "hotkey:CTRL+F8",      ""),
        ("Build (CTRL+F9)",   "BUILD", "hotkey:CTRL+F9",      ""),
        ("Search Everywhere", "SRCH",  "hotkey:SHIFT+SHIFT",  ""),
    ]))

    presets.append(_pu("visual_studio", "Visual Studio", "devenv.exe", "Visual Studio", [
        ("Build Solution (F7)","BUILD","hotkey:F7",            ""),
        ("Start Debug (F5)",  "DEBUG", "hotkey:F5",           ""),
        ("Step Over (F10)",   "STEP",  "hotkey:F10",          ""),
        ("Toggle Breakpoint (F9)","BRK","hotkey:F9",          ""),
        ("Quick Launch",      "FIND",  "hotkey:CTRL+Q",       ""),
        ("Refactor Rename",   "RENAME","hotkey:CTRL+R+R",     ""),
        ("Go To Definition",  "GODEF", "hotkey:F12",          ""),
        ("Format Document",   "FMT",   "hotkey:CTRL+K+D",     ""),
        ("Comment Block",     "COMM",  "hotkey:CTRL+K+C",     ""),
    ]))

    presets.append(_pu("arduino_ide", "Arduino IDE", "arduino_debug.exe|arduino.exe", "Arduino", [
        ("Verify / Compile",  "VERIFY","hotkey:CTRL+R",       ""),
        ("Upload",            "UPLOAD","hotkey:CTRL+U",       ""),
        ("Serial Monitor",    "SERIAL","hotkey:CTRL+SHIFT+M", ""),
        ("New",               "NEW",   "hotkey:CTRL+N",       ""),
        ("Open",              "OPEN",  "hotkey:CTRL+O",       ""),
        ("Save",              "SAVE",  "hotkey:CTRL+S",       ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Comment Out",       "COMM",  "hotkey:CTRL+SLASH",   ""),
        ("Board Manager",     "BOARD", "hotkey:CTRL+SHIFT+B", ""),
    ]))

    presets.append(_pu("handbrake", "HandBrake", "handbrake.exe", "HandBrake", [
        ("Start Encode",      "START", "hotkey:CTRL+E",       ""),
        ("Add to Queue",      "QUEUE", "hotkey:CTRL+SHIFT+A", ""),
        ("Open Source",       "OPEN",  "hotkey:CTRL+O",       ""),
        ("Scan DVD",          "SCAN",  "hotkey:CTRL+D",       ""),
        ("Preview",           "PREV",  "hotkey:CTRL+SHIFT+P", ""),
        ("Presets Panel",     "PRESET","hotkey:CTRL+P",       ""),
        ("Activity Log",      "LOG",   "hotkey:CTRL+L",       ""),
        ("Pause/Resume",      "PAUSE", "hotkey:CTRL+SHIFT+E", ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("postman", "Postman", "postman.exe", "Postman", [
        ("Send Request",      "SEND",  "hotkey:CTRL+ENTER",   ""),
        ("New Request",       "NEW",   "hotkey:CTRL+N",       ""),
        ("New Collection",    "COLL",  "hotkey:CTRL+SHIFT+N", ""),
        ("History",           "HIST",  "hotkey:CTRL+H",       ""),
        ("Environment List",  "ENV",   "hotkey:CTRL+SHIFT+E", ""),
        ("Find",              "FIND",  "hotkey:CTRL+F",       ""),
        ("Toggle Sidebar",    "SIDE",  "hotkey:CTRL+SHIFT+S", ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Duplicate Tab",     "DUP",   "hotkey:CTRL+D",       ""),
    ]))

    presets.append(_pu("docker_desktop", "Docker Desktop", "docker desktop.exe|dockerdesktop.exe", "Docker", [
        ("Open Terminal",     "TERM",  "hotkey:CTRL+SHIFT+T", ""),
        ("Restart",           "RESTART","hotkey:CTRL+SHIFT+R",""),
        ("Pull Image",        "PULL",  "hotkey:CTRL+P",       ""),
        ("Dashboard",         "DASH",  "hotkey:CTRL+D",       ""),
        ("Containers",        "CNTR",  "hotkey:CTRL+1",       ""),
        ("Images",            "IMG",   "hotkey:CTRL+2",       ""),
        ("Volumes",           "VOL",   "hotkey:CTRL+3",       ""),
        ("Settings",          "PREFS", "hotkey:CTRL+COMMA",   ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("powertoys", "PowerToys / ShareX", "powertoys.exe|sharex.exe", "Productivity", [
        ("Run (Win+Space)",   "RUN",   "hotkey:WIN+SPACE",    ""),
        ("Color Picker",      "COLOR", "hotkey:WIN+SHIFT+C",  ""),
        ("Screen Ruler",      "RULER", "hotkey:WIN+SHIFT+R",  ""),
        ("Peek",              "PEEK",  "hotkey:CTRL+SPACE",   ""),
        ("Screen Capture",    "SNAP",  "hotkey:WIN+SHIFT+S",  ""),
        ("Image Resize",      "RESIZE","hotkey:WIN+SHIFT+I",  ""),
        ("File Locksmith",    "LOCK",  "hotkey:WIN+SHIFT+L",  ""),
        ("Text Extractor",    "OCR",   "hotkey:WIN+SHIFT+T",  ""),
        ("Find My Mouse",     "MOUSE", "hotkey:CTRL+CTRL",    ""),
    ]))

    presets.append(_pu("anki", "Anki", "anki.exe", "Anki", [
        ("Show Answer",       "SHOW",  "hotkey:SPACE",        ""),
        ("Good",              "GOOD",  "hotkey:3",            ""),
        ("Easy",              "EASY",  "hotkey:4",            ""),
        ("Hard",              "HARD",  "hotkey:2",            ""),
        ("Again",             "AGAIN", "hotkey:1",            ""),
        ("Bury Card",         "BURY",  "hotkey:MINUS",        ""),
        ("Suspend Card",      "SUSP",  "hotkey:EQUALS",       ""),
        ("Edit Current",      "EDIT",  "hotkey:E",            ""),
        ("Stats",             "STATS", "hotkey:SHIFT+S",      ""),
    ]))

    presets.append(_pu("github_desktop", "GitHub Desktop", "githubdesktop.exe|github desktop.exe", "GitHub", [
        ("Commit (CTRL+ENTER)","COMMIT","hotkey:CTRL+ENTER",  ""),
        ("Push",               "PUSH",  "hotkey:CTRL+P",      ""),
        ("Pull",               "PULL",  "hotkey:CTRL+SHIFT+P",""),
        ("New Branch",         "BRANCH","hotkey:CTRL+SHIFT+N",""),
        ("Show Changes",       "DIFF",  "hotkey:CTRL+SHIFT+C",""),
        ("Show History",       "HIST",  "hotkey:CTRL+H",      ""),
        ("Stash Changes",      "STASH", "hotkey:CTRL+SHIFT+S",""),
        ("Open in VS Code",    "CODE",  "hotkey:CTRL+SHIFT+A",""),
        ("Discard Changes",    "DISCARD","hotkey:CTRL+SHIFT+H",""),
    ]))

    presets.append(_pu("canva", "Canva", "canva.exe", "Canva", [
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
        ("Bold Text (B)",     "BOLD",  "hotkey:CTRL+B",       ""),
        ("Italic Text (I)",   "ITALIC","hotkey:CTRL+I",       ""),
        ("Duplicate Element", "DUP",   "hotkey:CTRL+D",       ""),
        ("Group Elements",    "GROUP", "hotkey:CTRL+G",       ""),
        ("Lock Element",      "LOCK",  "hotkey:CTRL+ALT+L",   ""),
        ("Send Backward",     "BACK",  "hotkey:CTRL+LBRACKET",""),
        ("Bring Forward",     "FWD",   "hotkey:CTRL+RBRACKET",""),
        ("Download",          "SAVE",  "hotkey:CTRL+SHIFT+E", ""),
    ]))

    presets.append(_pu("windows_snip", "Windows Snipping & System", "explorer.exe|system", "Windows", [
        ("Snip & Sketch",     "SNIP",  "hotkey:WIN+SHIFT+S",  ""),
        ("Win + Print Screen","SCRN",  "hotkey:WIN+PRTSC",    ""),
        ("Task Manager",      "TASK",  "hotkey:CTRL+SHIFT+ESC",""),
        ("Virtual Desktop",   "VDESK", "hotkey:WIN+TAB",      ""),
        ("New Virtual Desktop","NDSK", "hotkey:WIN+CTRL+D",   ""),
        ("Lock PC",           "LOCK",  "hotkey:WIN+L",        ""),
        ("Emoji Picker",      "EMOJI", "hotkey:WIN+PERIOD",   ""),
        ("Clipboard History", "CLIP",  "hotkey:WIN+V",        ""),
        ("Quick Settings",    "QSET",  "hotkey:WIN+A",        ""),
    ]))

    presets.append(_pu("bitwarden", "1Password / Bitwarden", "1password.exe|bitwarden.exe", "Password Manager", [
        ("Auto-Fill",         "FILL",  "hotkey:CTRL+SHIFT+X", ""),
        ("Open Extension",    "EXT",   "hotkey:CTRL+SHIFT+L", ""),
        ("Lock Vault",        "LOCK",  "hotkey:CTRL+SHIFT+L", ""),
        ("Quick Access",      "QUICK", "hotkey:CTRL+PERIOD",  ""),
        ("Copy Password",     "COPY",  "hotkey:CTRL+SHIFT+C", ""),
        ("Generate Password", "GEN",   "hotkey:CTRL+G",       ""),
        ("Search Vault",      "SRCH",  "hotkey:CTRL+F",       ""),
        ("Open Vault",        "VAULT", "hotkey:CTRL+O",       ""),
        ("Settings",          "PREFS", "hotkey:CTRL+COMMA",   ""),
    ]))

    presets.append(_pu("puTTY", "PuTTY / WinSCP", "putty.exe|winscp.exe", "Remote", [
        ("New Session",       "NEW",   "hotkey:CTRL+N",       ""),
        ("Copy Output",       "COPY",  "hotkey:CTRL+SHIFT+C", ""),
        ("Paste",             "PASTE", "hotkey:CTRL+SHIFT+V", ""),
        ("Find",              "FIND",  "hotkey:CTRL+SHIFT+F", ""),
        ("Scroll Up",         "UP",    "hotkey:SHIFT+PGUP",   ""),
        ("Scroll Down",       "DOWN",  "hotkey:SHIFT+PGDN",   ""),
        ("Reset Terminal",    "RESET", "hotkey:CTRL+R",       ""),
        ("Toggle Fullscreen", "FULL",  "hotkey:ALT+ENTER",    ""),
        ("Duplicate Tab",     "DUP",   "hotkey:CTRL+SHIFT+D", ""),
    ]))

    presets.append(_pu("parsec", "Parsec / AnyDesk", "parsecd.exe|anydesk.exe", "Remote", [
        ("Disconnect",        "DISC",  "hotkey:CTRL+SHIFT+D", ""),
        ("Toggle Fullscreen", "FULL",  "hotkey:CTRL+SHIFT+F", ""),
        ("Overlay Menu",      "MENU",  "hotkey:CTRL+SHIFT+M", ""),
        ("Paste",             "PASTE", "hotkey:CTRL+SHIFT+V", ""),
        ("Screenshot",        "SNAP",  "hotkey:CTRL+SHIFT+S", ""),
        ("Resolution",        "RES",   "hotkey:CTRL+SHIFT+R", ""),
        ("Sound Toggle",      "SOUND", "hotkey:CTRL+SHIFT+O", ""),
        ("Settings",          "PREFS", "hotkey:CTRL+COMMA",   ""),
        ("Connect",           "CONN",  "hotkey:CTRL+ENTER",   ""),
    ]))

    presets.append(_pu("telegram_whatsapp", "Telegram / WhatsApp", "telegram.exe|whatsapp.exe", "Messaging", [
        ("New Message",       "MSG",   "hotkey:CTRL+N",       ""),
        ("Search",            "SRCH",  "hotkey:CTRL+F",       ""),
        ("Next Chat",         "NEXT",  "hotkey:CTRL+TAB",     ""),
        ("Prev Chat",         "PREV",  "hotkey:CTRL+SHIFT+TAB",""),
        ("Attach File",       "FILE",  "hotkey:CTRL+SHIFT+A", ""),
        ("Mute Chat",         "MUTE",  "hotkey:CTRL+SHIFT+M", ""),
        ("Bold Text",         "BOLD",  "hotkey:CTRL+B",       ""),
        ("Emoji",             "EMOJI", "hotkey:CTRL+PERIOD",  ""),
        ("Settings",          "PREFS", "hotkey:CTRL+COMMA",   ""),
    ]))

    presets.append(_pu("dbeaver", "DBeaver", "dbeaver.exe", "Database", [
        ("Execute SQL (F5)",  "RUN",   "hotkey:F5",           ""),
        ("Format SQL",        "FMT",   "hotkey:CTRL+SHIFT+F", ""),
        ("New Connection",    "CONN",  "hotkey:CTRL+N",       ""),
        ("Open SQL",          "OPEN",  "hotkey:CTRL+O",       ""),
        ("Save",              "SAVE",  "hotkey:CTRL+S",       ""),
        ("Find/Replace",      "FIND",  "hotkey:CTRL+H",       ""),
        ("Explain Plan",      "PLAN",  "hotkey:CTRL+E",       ""),
        ("Refresh",           "REFR",  "hotkey:F5",           ""),
        ("Settings",          "PREFS", "hotkey:CTRL+COMMA",   ""),
    ]))

    presets.append(_pu("chrome_browser", "Chrome / Edge / Firefox", "chrome.exe|msedge.exe|firefox.exe", "Browser", [
        ("New Tab",           "NEW",   "hotkey:CTRL+T",       ""),
        ("Close Tab",         "CLOSE", "hotkey:CTRL+W",       ""),
        ("Address Bar",       "URL",   "hotkey:CTRL+L",       ""),
        ("Reload",            "RELOAD","hotkey:F5",           ""),
        ("Devtools",          "DEV",   "hotkey:F12",          ""),
        ("Bookmarks",         "BOOK",  "hotkey:CTRL+SHIFT+O", ""),
        ("Incognito",         "PRIV",  "hotkey:CTRL+SHIFT+N", ""),
        ("Zoom In",           "ZOOM+", "hotkey:CTRL+=",       ""),
        ("Zoom Out",          "ZOOM-", "hotkey:CTRL+-",       ""),
    ]))

    presets.append(_pu("outlook", "Outlook", "outlook.exe|olk.exe", "Outlook", [
        ("New Email",         "NEW",   "hotkey:CTRL+SHIFT+M", ""),
        ("Send (CTRL+ENTER)", "SEND",  "hotkey:CTRL+ENTER",   ""),
        ("Reply",             "REPLY", "hotkey:CTRL+R",       ""),
        ("Reply All",         "REPLY+","hotkey:CTRL+SHIFT+R", ""),
        ("Forward",           "FWD",   "hotkey:CTRL+F",       ""),
        ("Search (CTRL+E)",   "SRCH",  "hotkey:CTRL+E",       ""),
        ("New Meeting",       "MEET",  "hotkey:CTRL+SHIFT+Q", ""),
        ("Calendar",          "CAL",   "hotkey:CTRL+2",       ""),
        ("Inbox",             "INBOX", "hotkey:CTRL+1",       ""),
    ]))

    presets.append(_pu("bluebeam_revu", "Bluebeam Revu / PDF Editors", "revu.exe|acrord32.exe|acrobat.exe", "PDF", [
        ("Select (V)",        "SEL",   "hotkey:V",            ""),
        ("Pan (H)",           "PAN",   "hotkey:H",            ""),
        ("Highlight (L)",     "HILIT", "hotkey:L",            ""),
        ("Callout (O)",       "CALL",  "hotkey:O",            ""),
        ("Text Box (T)",      "TEXT",  "hotkey:T",            ""),
        ("Stamp (CTRL+T)",    "STAMP", "hotkey:CTRL+T",       ""),
        ("Zoom Fit",          "FIT",   "hotkey:CTRL+0",       ""),
        ("Flatten",           "FLAT",  "hotkey:CTRL+SHIFT+F", ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("hwinfo_afterburner", "HWiNFO / Afterburner", "hwinfo64.exe|msiafterburner.exe", "System", [
        ("Toggle OSD",        "OSD",   "hotkey:SCROLL_LOCK",  ""),
        ("Take Screenshot",   "SNAP",  "hotkey:WIN+ALT+S",    ""),
        ("Start Video Capture","REC",  "hotkey:WIN+ALT+R",    ""),
        ("Save Profile",      "SAVE",  "hotkey:CTRL+S",       ""),
        ("Reset GPU",         "RESET", "hotkey:CTRL+R",       ""),
        ("Settings",          "PREFS", "hotkey:CTRL+COMMA",   ""),
        ("Fan Control",       "FAN",   "hotkey:CTRL+F",       ""),
        ("Sensors",           "SENS",  "hotkey:CTRL+1",       ""),
        ("Benchmark",         "BENCH", "hotkey:CTRL+B",       ""),
    ]))

    presets.append(_pu("ltspice", "LTspice / EDA Tools", "ltspice.exe|ltspicexvii.exe", "EDA", [
        ("Run Simulation",    "RUN",   "hotkey:F9",           ""),
        ("Add Component (F2)","COMP",  "hotkey:F2",           ""),
        ("Add Wire (F3)",     "WIRE",  "hotkey:F3",           ""),
        ("Ground (F4)",       "GND",   "hotkey:F4",           ""),
        ("Move (F7)",         "MOVE",  "hotkey:F7",           ""),
        ("Zoom Fit (CTRL+SHIFT+F)","FIT","hotkey:CTRL+SHIFT+F",""),
        ("Edit Properties",   "PROPS", "hotkey:CTRL+E",       ""),
        ("DC Op Point",       "DCOP",  "hotkey:ALT+R",        ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    presets.append(_pu("microsoft_excel", "Microsoft Excel", "excel.exe", "Office", [
        ("Bold (CTRL+B)",     "BOLD",  "hotkey:CTRL+B",       ""),
        ("Sum (ALT+=)",       "SUM",   "hotkey:ALT+EQUALS",   ""),
        ("AutoFilter",        "FILTER","hotkey:CTRL+SHIFT+L", ""),
        ("Find (CTRL+F)",     "FIND",  "hotkey:CTRL+F",       ""),
        ("Format Cells",      "FORMAT","hotkey:CTRL+1",       ""),
        ("Paste Values Only", "PASTE", "hotkey:CTRL+ALT+V",   ""),
        ("New Sheet",         "SHEET", "hotkey:SHIFT+F11",    ""),
        ("Freeze Panes",      "FREEZE","hotkey:ALT+W+F+F",    ""),
        ("Undo",              "UNDO",  "hotkey:CTRL+Z",       ""),
    ]))

    print(f"  [PowerUser] Built {len(presets)} curated presets")
    return presets


# ==============================================================================
# MERGE ENGINE
# ==============================================================================

CANONICAL_APP_IDS = {
    "adobe_photoshop": "photoshop",
    "adobe_lightroom": "adobe_lightroom",
    "lightroom": "adobe_lightroom",
    "adobe_premiere_pro": "adobe_premiere_pro",
    "premiere": "adobe_premiere_pro",
    "premiereproc": "adobe_premiere_pro",
    "adobe_after_effects": "adobe_after_effects",
    "afterfx": "adobe_after_effects",
    "aftereffects": "adobe_after_effects",
    "adobe_illustrator": "adobe_illustrator",
    "illustrator": "adobe_illustrator",
    "capture_one": "capture_one",
    "captureone": "capture_one",
    "obs": "obs_studio",
    "obs_studio": "obs_studio",
    "ableton": "ableton_live",
    "ableton_live": "ableton_live",
    "blender": "blender",
    "figma": "figma",
    "krita": "krita",
    "maya": "maya",
    "3dsmax": "3ds_max",
    "3ds_max": "3ds_max",
    "sldworks": "solidworks",
    "solidworks": "solidworks",
    "fusion360": "fusion360",
    "rhino": "rhino",
}

def _group_app_presets(all_presets: List[Dict]) -> Dict[str, List[Dict]]:
    """Group all presets by normalised app_id → list of presets by source."""
    groups: Dict[str, List[Dict]] = {}
    for p in all_presets:
        raw_id = p["id"]
        canon_id = CANONICAL_APP_IDS.get(raw_id, raw_id)
        p["id"] = canon_id
        groups.setdefault(canon_id, []).append(p)
    return groups


def merge_into_tdx_harvested(
    new_presets: List[Dict],
    dry_run: bool = False,
    rebuild: bool = False,
    verbose: bool = False
):
    """
    Load existing tdx_harvested.json, tag existing 3Dconnexion entries,
    then merge/append new multi-source presets as 'presets' list per app.
    """
    print(f"\n[Merge] Loading {TDX_HARVESTED} ...")
    with open(TDX_HARVESTED, "r", encoding="utf-8") as f:
        tdx = json.load(f)

    existing_apps: List[Dict] = tdx.get("apps", [])
    existing_icons: Dict = tdx.get("icons", {})
    stats_orig: Dict = tdx.get("stats", {})

    # ── 1. Tag all existing entries as source="3Dconnexion" and add presets list ──
    for app in existing_apps:
        if "source" not in app:
            app["source"] = "3Dconnexion"
        if "app_group" not in app:
            app["app_group"] = app.get("name", "")
        if "selected_preset_source" not in app:
            app["selected_preset_source"] = "3Dconnexion"
        if "presets" not in app or rebuild:
            # Package the existing 3Dconnexion data as the first preset
            app["presets"] = [{
                "source": "3Dconnexion",
                "action_count": app.get("action_count", 0),
                "actions": app.get("actions", []),
                "recommended_cells": app.get("recommended_cells", []),
                "radial_menus": app.get("radial_menus", []),
            }]

    # ── 2. Build lookup: normalised_id & exe tokens → existing app entry ──
    id_to_app: Dict[str, Dict] = {}
    for app in existing_apps:
        id_to_app[app["id"]] = app
        canon = CANONICAL_APP_IDS.get(app["id"])
        if canon:
            id_to_app[canon] = app
        # Also map by exact exe_match tokens for lookup (split only on |,; not whitespace)
        for tok in re.split(r"[|,;]+", app.get("exe_match", "")):
            tok = tok.strip().lower()
            if tok and len(tok) >= 3:
                if tok in ("adobe", "microsoft", "autodesk", "google", "app", "pro"):
                    continue
                id_to_app.setdefault(tok, app)
                if tok.endswith(".exe"):
                    base = tok[:-4]
                    if base not in ("adobe", "microsoft", "autodesk", "google", "app", "pro"):
                        id_to_app.setdefault(base, app)

    # ── 3. Group new presets by app_id ──
    grouped = _group_app_presets(new_presets)

    new_apps_added = 0
    presets_merged = 0

    for app_id, preset_list in grouped.items():
        first = preset_list[0]
        canon_id = CANONICAL_APP_IDS.get(app_id, app_id)

        existing_app = None
        if canon_id in id_to_app:
            existing_app = id_to_app[canon_id]
        elif app_id in id_to_app:
            existing_app = id_to_app[app_id]
        else:
            # Try matching by exe tokens (exact exe names only)
            for tok in re.split(r"[|,;]+", first.get("exe_match", "")):
                tok = tok.strip().lower()
                if not tok or tok in ("adobe", "microsoft", "autodesk", "google", "app", "pro"):
                    continue
                if tok in id_to_app:
                    existing_app = id_to_app[tok]
                    break
                if tok.endswith(".exe"):
                    base = tok[:-4]
                    if base in id_to_app:
                        existing_app = id_to_app[base]
                        break

        if not existing_app:
            # New app not in 3Dconnexion catalog — create new entry
            existing_app = {
                "id": canon_id,
                "name": first["name"],
                "xml_file": f"{first['source']}_generated",
                "exe_match": first["exe_match"],
                "exes": [e.strip() for e in first["exe_match"].split("|") if e.strip()],
                "action_count": first.get("action_count", 0),
                "source": first["source"],
                "app_group": first.get("app_group", first["name"]),
                "selected_preset_source": first["source"],
                "actions": first.get("actions", []),
                "radial_menus": first.get("radial_menus", []),
                "recommended_cells": first.get("recommended_cells", []),
                "presets": [],
            }
            existing_apps.append(existing_app)
            id_to_app[canon_id] = existing_app
            new_apps_added += 1

        existing_presets = existing_app.setdefault("presets", [])

        for new_preset in preset_list:
            source = new_preset["source"]
            if rebuild:
                # Remove any existing preset with this source
                existing_presets[:] = [p for p in existing_presets if p.get("source") != source]

            if not any(p.get("source") == source for p in existing_presets):
                existing_presets.append({
                    "source": source,
                    "action_count": new_preset["action_count"],
                    "actions": new_preset["actions"],
                    "recommended_cells": new_preset["recommended_cells"],
                    "radial_menus": new_preset.get("radial_menus", []),
                })
                presets_merged += 1
                if verbose:
                    print(f"  + Merged [{source}] → {existing_app['name']}")

        # Ensure selected_preset_source is set
        if "selected_preset_source" not in existing_app:
            existing_app["selected_preset_source"] = existing_app.get("source", "3Dconnexion")

    # ── 4. Update stats ──
    total_apps = len(existing_apps)
    total_actions = sum(a.get("action_count", 0) for a in existing_apps)
    total_radials = sum(len(a.get("radial_menus", [])) for a in existing_apps)
    total_icons = len(existing_icons)
    total_preset_entries = sum(len(a.get("presets", [])) for a in existing_apps)
    apps_with_multi = sum(1 for a in existing_apps if len(a.get("presets", [])) > 1)

    updated_stats = dict(stats_orig)
    updated_stats["total_apps"] = total_apps
    updated_stats["total_actions"] = total_actions
    updated_stats["total_radial_menus"] = total_radials
    updated_stats["total_icons"] = total_icons
    updated_stats["total_preset_entries"] = total_preset_entries
    updated_stats["apps_with_multi_source_presets"] = apps_with_multi
    updated_stats["sources"] = ["3Dconnexion", "Loupedeck", "TourBox", "Wacom", "PowerUser"]

    # ── 5. Write output ──
    result = {"stats": updated_stats, "icons": existing_icons, "apps": existing_apps}

    print(f"\n[Merge] Stats:")
    print(f"  Total apps:          {total_apps}")
    print(f"  Apps newly added:    {new_apps_added}")
    print(f"  Presets merged:      {presets_merged}")
    print(f"  Multi-source apps:   {apps_with_multi}")
    print(f"  Total preset entries:{total_preset_entries}")
    print(f"  Total actions:       {total_actions}")
    print(f"  Total icons:         {total_icons}")

    if dry_run:
        print("\n[DRY RUN] Not writing. Would write to:", TDX_HARVESTED)
        return result

    backup_path = TDX_HARVESTED.with_suffix(".backup.json")
    import shutil
    shutil.copy2(TDX_HARVESTED, backup_path)
    print(f"\n[Merge] Backup saved: {backup_path}")

    with open(TDX_HARVESTED, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[Merge] Written: {TDX_HARVESTED}")
    return result


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Harvest multi-source peripheral presets into tdx_harvested.json")
    parser.add_argument("--dry-run",     action="store_true", help="Print stats without writing any files")
    parser.add_argument("--rebuild-all", action="store_true", help="Wipe and regenerate all non-3Dconnexion presets")
    parser.add_argument("--verbose",     action="store_true", help="Verbose per-action output")
    args = parser.parse_args()

    print("=" * 70)
    print("  MacroPad Multi-Driver Preset Harvester")
    print("=" * 70)

    all_new_presets: List[Dict] = []

    # Source: Loupedeck 5.9
    ld_presets = harvest_loupedeck_59(verbose=args.verbose)
    all_new_presets.extend(ld_presets)

    # Source: TourBox Console
    tb_presets = harvest_tourbox(verbose=args.verbose)
    all_new_presets.extend(tb_presets)

    # Source: Wacom AppGestures
    wa_presets = harvest_wacom(verbose=args.verbose)
    all_new_presets.extend(wa_presets)

    # Source: Power-User Curated
    pu_presets = harvest_poweruser()
    all_new_presets.extend(pu_presets)

    print(f"\n[Summary] Harvested {len(all_new_presets)} total new preset entries from all sources")

    # Merge into tdx_harvested.json
    merge_into_tdx_harvested(
        all_new_presets,
        dry_run=args.dry_run,
        rebuild=args.rebuild_all,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
