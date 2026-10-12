"""
3Dconnexion 3DxWare XML Profile Harvester for MacroPad Studio.
Scans C:\\Program Files\\3Dconnexion\\3DxWare\\3DxWinCore\\Cfg\\*.xml,
resolves localized strings (en-US.xml), decodes USB HID MacroTable entries,
Sequence/Keyboard/AppCommand actions, Radial Pie Menus, and converts embedded
base64/driver PNG icons into 24x24 1-bit E-Ink hex bitmaps.

Outputs: pi_app/tdx_harvested.json
"""

import os
import re
import io
import glob
import json
import base64
import hashlib
import xml.etree.ElementTree as ET
from PIL import Image

CFG_DIR = r"C:\Program Files\3Dconnexion\3DxWare\3DxWinCore\Cfg"
IMAGES_DIR = os.path.join(CFG_DIR, "Images", "3DxService")
OUT_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pi_app", "tdx_harvested.json")

# USB HID Usage ID (Hex) -> MacroPad Key Name
HID_KEY_MAP = {
    0x04: "A", 0x05: "B", 0x06: "C", 0x07: "D", 0x08: "E", 0x09: "F",
    0x0A: "G", 0x0B: "H", 0x0C: "I", 0x0D: "J", 0x0E: "K", 0x0F: "L",
    0x10: "M", 0x11: "N", 0x12: "O", 0x13: "P", 0x14: "Q", 0x15: "R",
    0x16: "S", 0x17: "T", 0x18: "U", 0x19: "V", 0x1A: "W", 0x1B: "X",
    0x1C: "Y", 0x1D: "Z",
    0x1E: "1", 0x1F: "2", 0x20: "3", 0x21: "4", 0x22: "5",
    0x23: "6", 0x24: "7", 0x25: "8", 0x26: "9", 0x27: "0",
    0x28: "ENTER", 0x29: "ESC", 0x2A: "BACKSPACE", 0x2B: "TAB", 0x2C: "SPACE",
    0x2D: "-", 0x2E: "=", 0x2F: "[", 0x30: "]", 0x31: "\\", 0x32: "\\",
    0x33: ";", 0x34: "'", 0x35: "`", 0x36: ",", 0x37: ".", 0x38: "/",
    0x3A: "F1", 0x3B: "F2", 0x3C: "F3", 0x3D: "F4", 0x3E: "F5", 0x3F: "F6",
    0x40: "F7", 0x41: "F8", 0x42: "F9", 0x43: "F10", 0x44: "F11", 0x45: "F12",
    0x49: "INSERT", 0x4A: "HOME", 0x4B: "PGUP", 0x4C: "DELETE", 0x4D: "END", 0x4E: "PGDN",
    0x4F: "RIGHT", 0x50: "LEFT", 0x51: "DOWN", 0x52: "UP",
    0x54: "NUMPAD/", 0x55: "NUMPAD*", 0x56: "NUMPAD-", 0x57: "NUMPAD+", 0x58: "ENTER",
    0x59: "NUMPAD1", 0x5A: "NUMPAD2", 0x5B: "NUMPAD3", 0x5C: "NUMPAD4", 0x5D: "NUMPAD5",
    0x5E: "NUMPAD6", 0x5F: "NUMPAD7", 0x60: "NUMPAD8", 0x61: "NUMPAD9", 0x62: "NUMPAD0",
    0x63: "NUMPAD.",
    0x68: "F13", 0x69: "F14", 0x6A: "F15", 0x6B: "F16", 0x6C: "F17", 0x6D: "F18",
    0x6E: "F19", 0x6F: "F20", 0x70: "F21", 0x71: "F22", 0x72: "F23", 0x73: "F24",
}

HID_MOD_MAP = {
    0xE0: "CTRL", 0xE4: "CTRL",
    0xE1: "SHIFT", 0xE5: "SHIFT",
    0xE2: "ALT", 0xE6: "ALT",
    0xE3: "WIN", 0xE7: "WIN",
}

MOD_NAME_MAP = {
    "control": "CTRL", "ctrl": "CTRL",
    "shift": "SHIFT",
    "alt": "ALT",
    "windows": "WIN", "win": "WIN", "gui": "WIN",
}

# Built-in Base.xml / Standard 3Dconnexion ActionIDs -> (Name, MacroPad Action)
STANDARD_ACTION_MAP = {
    "Macro_Cut": ("Cut", "hotkey:CTRL+X"),
    "Macro_Copy": ("Copy", "hotkey:CTRL+C"),
    "Macro_Paste": ("Paste", "hotkey:CTRL+V"),
    "Macro_Undo": ("Undo", "hotkey:CTRL+Z"),
    "Macro_Redo": ("Redo", "hotkey:CTRL+Y"),
    "Macro_SelectAll": ("Select All", "hotkey:CTRL+A"),
    "Macro_Save": ("Save", "hotkey:CTRL+S"),
    "Macro_Open": ("Open", "hotkey:CTRL+O"),
    "Macro_New": ("New", "hotkey:CTRL+N"),
    "Macro_Find": ("Find", "hotkey:CTRL+F"),
    "Macro_Print": ("Print", "hotkey:CTRL+P"),
    "Macro_Delete": ("Delete", "hotkey:DELETE"),
    "Macro_Close": ("Close", "hotkey:CTRL+W"),
    "KB_Esc": ("Escape", "cad_key:ESC"),
    "KB_Enter": ("Enter", "hotkey:ENTER"),
    "KB_Space": ("Space", "hotkey:SPACE"),
    "KB_Tab": ("Tab", "hotkey:TAB"),
    "KB_Delete": ("Delete", "hotkey:DELETE"),
    "KB_BackSpace": ("Backspace", "hotkey:BACKSPACE"),
    "KB_UpArrow": ("Up Arrow", "hotkey:UP"),
    "KB_DownArrow": ("Down Arrow", "hotkey:DOWN"),
    "KB_LeftArrow": ("Left Arrow", "hotkey:LEFT"),
    "KB_RightArrow": ("Right Arrow", "hotkey:RIGHT"),
    "KB_PageUp": ("Page Up", "hotkey:PGUP"),
    "KB_PageDown": ("Page Down", "hotkey:PGDN"),
    "KB_Home": ("Home", "hotkey:HOME"),
    "KB_End": ("End", "hotkey:END"),
    "KB_Insert": ("Insert", "hotkey:INSERT"),
    "KB_F1": ("Help (F1)", "hotkey:F1"),
    "KB_F2": ("F2", "hotkey:F2"),
    "KB_F3": ("F3", "hotkey:F3"),
    "KB_F4": ("F4", "hotkey:F4"),
    "KB_F5": ("F5", "hotkey:F5"),
    "KB_F6": ("F6", "hotkey:F6"),
    "KB_F7": ("F7", "hotkey:F7"),
    "KB_F8": ("F8", "hotkey:F8"),
    "KB_F9": ("F9", "hotkey:F9"),
    "KB_F10": ("F10", "hotkey:F10"),
    "KB_F11": ("F11", "hotkey:F11"),
    "KB_F12": ("F12", "hotkey:F12"),
    "App_ResetYourView": ("Fit / Reset View", "hotkey:F"),
    "V3DCMD_VIEW_FIT": ("Fit View", "hotkey:F"),
    "V3DK_FIT": ("Fit View", "hotkey:F"),
    "V3DK_TOP": ("Top View", "hotkey:NUMPAD7"),
    "V3DK_FRONT": ("Front View", "hotkey:NUMPAD1"),
    "V3DK_RIGHT": ("Right View", "hotkey:NUMPAD3"),
    "V3DK_LEFT": ("Left View", "hotkey:CTRL+NUMPAD3"),
    "V3DK_BOTTOM": ("Bottom View", "hotkey:CTRL+NUMPAD7"),
    "V3DK_BACK": ("Back View", "hotkey:CTRL+NUMPAD1"),
    "V3DK_ISO1": ("Iso View", "hotkey:NUMPAD0"),
    "MotionMacro_Wheel_20_In": ("Quick Zoom In", "hotkey:CTRL+="),
    "MotionMacro_Wheel_20_Out": ("Quick Zoom Out", "hotkey:CTRL+-"),
    "V3DCMD_VIEW_QZ_IN": ("Zoom In", "hotkey:CTRL+="),
    "V3DCMD_VIEW_QZ_OUT": ("Zoom Out", "hotkey:CTRL+-"),
    "DriverFunctions_MuteMicrophone": ("Mic Mute", "discord_mic_mute"),
}

# App-specific view & command overrides for CAD suites that use 3DxWare DLL AppCommands
APP_VIEW_OVERRIDES = {
    "solidworks": {
        "V3DK_FIT": ("Zoom to Fit", "hotkey:F"),
        "V3DK_TOP": ("Top View", "hotkey:CTRL+5"),
        "V3DK_BOTTOM": ("Bottom View", "hotkey:CTRL+6"),
        "V3DK_FRONT": ("Front View", "hotkey:CTRL+1"),
        "V3DK_BACK": ("Back View", "hotkey:CTRL+2"),
        "V3DK_LEFT": ("Left View", "hotkey:CTRL+3"),
        "V3DK_RIGHT": ("Right View", "hotkey:CTRL+4"),
        "V3DK_ISO1": ("Isometric", "hotkey:CTRL+7"),
        "V3DK_NORMAL": ("Normal To", "hotkey:CTRL+8"),
    },
    "inventor": {
        "V3DK_FIT": ("Zoom All", "hotkey:HOME"),
        "V3DK_ISO1": ("Home View", "hotkey:F6"),
        "V3DK_TOP": ("Look At", "hotkey:PGUP"),
    },
    "onshape": {
        "V3DK_FIT": ("Zoom to Fit", "hotkey:F"),
        "V3DK_FRONT": ("Front View", "hotkey:SHIFT+1"),
        "V3DK_BACK": ("Back View", "hotkey:SHIFT+2"),
        "V3DK_LEFT": ("Left View", "hotkey:SHIFT+3"),
        "V3DK_RIGHT": ("Right View", "hotkey:SHIFT+4"),
        "V3DK_TOP": ("Top View", "hotkey:SHIFT+5"),
        "V3DK_BOTTOM": ("Bottom View", "hotkey:SHIFT+6"),
        "V3DK_ISO1": ("Isometric", "hotkey:SHIFT+7"),
    },
    "freecad": {
        "V3DK_FIT": ("Fit All", "keyseq:V,F"),
        "V3DK_ISO1": ("Isometric", "hotkey:0"),
        "V3DK_FRONT": ("Front View", "hotkey:1"),
        "V3DK_TOP": ("Top View", "hotkey:2"),
        "V3DK_RIGHT": ("Right View", "hotkey:3"),
        "V3DK_BACK": ("Rear View", "hotkey:4"),
        "V3DK_BOTTOM": ("Bottom View", "hotkey:5"),
        "V3DK_LEFT": ("Left View", "hotkey:6"),
    },
}

# Universal AppCommand name -> executable MacroPad action (for CAD/3D apps)
APPCMD_NAME_TO_ACTION = {
    "undo": "hotkey:CTRL+Z",
    "redo": "hotkey:CTRL+Y",
    "cut": "hotkey:CTRL+X",
    "copy": "hotkey:CTRL+C",
    "paste": "hotkey:CTRL+V",
    "delete": "hotkey:DELETE",
    "save": "hotkey:CTRL+S",
    "open": "hotkey:CTRL+O",
    "open...": "hotkey:CTRL+O",
    "new": "hotkey:CTRL+N",
    "new...": "hotkey:CTRL+N",
    "print": "hotkey:CTRL+P",
    "print...": "hotkey:CTRL+P",
    "find": "hotkey:CTRL+F",
    "select all": "hotkey:CTRL+A",
    "deselect all": "hotkey:CTRL+D",
    "duplicate": "hotkey:CTRL+D",
    "group": "hotkey:CTRL+G",
    "ungroup": "hotkey:CTRL+SHIFT+G",
    "properties": "hotkey:CTRL+1",
    "options": "cad_cmd:_OPTIONS",
    "line": "cad_cmd:_LINE",
    "polyline": "cad_cmd:_PLINE",
    "circle": "cad_cmd:_CIRCLE",
    "arc": "cad_cmd:_ARC",
    "rectangle": "cad_cmd:_RECTANG",
    "polygon": "cad_cmd:_POLYGON",
    "ellipse": "cad_cmd:_ELLIPSE",
    "spline": "cad_cmd:_SPLINE",
    "point": "cad_cmd:_POINT",
    "hatch": "cad_cmd:_HATCH",
    "text": "cad_cmd:_MTEXT",
    "dimension": "cad_cmd:_DIM",
    "measure": "cad_cmd:_MEASUREGEOM",
    "measure area": "cad_cmd:_AREA",
    "distance": "cad_cmd:_DIST",
    "angle": "cad_cmd:_DIMANGULAR",
    "move": "cad_cmd:_MOVE",
    "rotate": "cad_cmd:_ROTATE",
    "scale": "cad_cmd:_SCALE",
    "mirror": "cad_cmd:_MIRROR",
    "offset": "cad_cmd:_OFFSET",
    "trim": "cad_cmd:_TRIM",
    "extend": "cad_cmd:_EXTEND",
    "fillet": "cad_cmd:_FILLET",
    "chamfer": "cad_cmd:_CHAMFER",
    "stretch": "cad_cmd:_STRETCH",
    "lengthen": "cad_cmd:_LENGTHEN",
    "explode": "cad_cmd:_EXPLODE",
    "erase": "cad_cmd:_ERASE",
    "extrude": "cad_cmd:_EXTRUDE",
    "extrude...": "cad_cmd:_EXTRUDE",
    "revolve": "cad_cmd:_REVOLVE",
    "revolve...": "cad_cmd:_REVOLVE",
    "loft": "cad_cmd:_LOFT",
    "sweep": "cad_cmd:_SWEEP",
    "hole": "hotkey:H",
    "box": "cad_cmd:_BOX",
    "cylinder": "cad_cmd:_CYLINDER",
    "sphere": "cad_cmd:_SPHERE",
    "wireframe": "cad_cmd:_VSWIREFRAME",
    "shaded": "cad_cmd:_VSSHADED",
    "shaded view": "cad_cmd:_VSSHADED",
    "render": "cad_cmd:_RENDER",
    "fit": "hotkey:F",
    "zoom extents": "cad_cmd:_ZOOM E",
    "pan": "cad_cmd:_PAN",
    "orbit": "cad_cmd:_3DORBIT",
}

# Prefix mapping from en-US.xml Macro_<Prefix>_* to XML filename stems
EN_US_PREFIX_TO_XML = {
    "Showcase": "Showcase.xml",
    "AdobeSubstance3D": "AdobeSubstance3DPainter.xml",
    "C4D": "Cinema 4D.xml",
    "MastercamX": "Mastercam.xml",
    "3DxProE": "ProE.xml",
    "ChiefArchitect": "Chief_Architect.xml",
    "TCVM": "VisMockup.xml",
    "Firefox": "Firefox.xml",
    "Rhinoceros": "Rhino.xml",
    "Blender": "Blender.xml",
    "PhotoshopCS3": "Photoshop.xml",
    "Photoshop": "Photoshop.xml",
    "3DxInventor": "Inventor.xml",
    "Explorer": "Explorer.xml",
    "CIROS": "CIROS.xml",
    "AltiumDesigner": "AltiumDesigner.xml",
    "AutoCADLT": "AutoCADLT.xml",
    "KeyCreator": "KeyCreator.xml",
    "MicroStation": "MicroStation.xml",
    "MSPaint": "MSPaint.xml",
    "OneSpaceDesigner": "OSD_Modeling.xml",
    "Excel": "Excel.xml",
    "GoogleEarth": "GoogleEarth.xml",
    "IE": "MSEdge.xml",
    "Notepad": "Notepad.xml",
    "Abaqus": "Abaqus.xml",
    "Fusion360": "Fusion360.xml",
    "ExoCADDental": "exocad_DentalCAD.xml",
    "AcWebBrowser": "AcWebBrowser.xml",
    "Word": "Word.xml",
    "AdobeReader": "AcroRd32.xml",
}


def ascii_to_hex(art_lines: list, w: int = 24, h: int = 24) -> str:
    bytes_per_row = (w + 7) // 8
    byte_array = []
    for row in range(h):
        line = art_lines[row] if row < len(art_lines) else "." * w
        line = line.ljust(w, ".")
        for b in range(bytes_per_row):
            val = 0
            for bit in range(8):
                col = b * 8 + bit
                if col < w and line[col] == "#":
                    val |= (1 << (7 - bit))
            byte_array.append(val)
    return bytes(byte_array).hex()


def pil_to_24x24_hex(im: Image.Image) -> str:
    """Converts any RGBA/RGB PIL Image into a 24x24 1-bit MSB-first hex string (144 hex chars)."""
    im = im.convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    im.thumbnail((22, 22), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    ox = (24 - im.width) // 2
    oy = (24 - im.height) // 2
    canvas.paste(im, (ox, oy))
    px = list(canvas.getdata())
    opaque_ratio = sum(1 for r, g, b, a in px if a >= 85) / 576.0
    lines = []
    if 0.015 <= opaque_ratio <= 0.65:
        for y in range(24):
            row = "".join("#" if px[y * 24 + x][3] >= 85 else "." for x in range(24))
            lines.append(row)
    else:
        lums = [(0.299 * r + 0.587 * g + 0.114 * b) if a >= 85 else 255 for r, g, b, a in px]
        avg = sum(lums) / 576.0
        dark_count = sum(1 for l in lums if l < avg)
        for y in range(24):
            if dark_count <= 288:
                row = "".join("#" if lums[y * 24 + x] < avg - 10 else "." for x in range(24))
            else:
                row = "".join("#" if lums[y * 24 + x] > avg + 10 else "." for x in range(24))
            lines.append(row)
    return ascii_to_hex(lines, 24, 24)


def guess_fallback_icon(label: str, action: str) -> str:
    """Picks the best built-in 24x24 icon name when no PNG icon is embedded."""
    s = f"{label} {action}".lower()
    if any(k in s for k in ("top", "plan")): return "cad_box"
    if any(k in s for k in ("front", "back", "rear", "left", "right", "bottom", "iso", "view", "camera", "persp", "ortho")): return "eye"
    if any(k in s for k in ("fit", "zoom", "extents", "focus", "frame", "home")): return "cad_zoom_ext"
    if "undo" in s: return "cad_undo"
    if "redo" in s: return "cad_redo"
    if "save" in s or "export" in s: return "cad_qsave"
    if "move" in s or "translate" in s or "pan" in s or "grab" in s: return "cad_move"
    if "rotat" in s or "orbit" in s or "roll" in s or "spin" in s: return "cad_rotate"
    if "scale" in s or "size" in s: return "cad_scale"
    if "mirror" in s or "flip" in s or "symmetr" in s: return "cad_mirror"
    if "offset" in s or "shell" in s: return "cad_offset"
    if "trim" in s or "cut" in s or "split" in s or "slice" in s: return "cad_trim"
    if "fillet" in s or "round" in s or "bevel" in s: return "cad_fillet"
    if "chamfer" in s: return "cad_chamfer"
    if "extrud" in s or "push" in s or "pull" in s or "pad" in s: return "cad_extrude"
    if "line" in s or "wire" in s or "edge" in s: return "cad_line"
    if "rect" in s or "box" in s or "cube" in s or "quad" in s: return "cad_rect"
    if "circ" in s or "sphere" in s or "cyl" in s or "hole" in s: return "cad_circle"
    if "arc" in s or "revolve" in s: return "cad_arc"
    if "poly" in s or "mesh" in s: return "cad_polygon"
    if "dim" in s or "measur" in s or "dist" in s or "area" in s or "ruler" in s: return "cad_dim"
    if "text" in s or "note" in s or "label" in s or "annot" in s: return "cad_text"
    if "layer" in s or "tree" in s or "outliner" in s: return "cad_layer"
    if "grid" in s or "snap" in s or "ortho" in s: return "grid"
    if "render" in s or "shade" in s or "light" in s or "mat" in s or "xray" in s: return "sparkles"
    if "brush" in s or "sculpt" in s or "paint" in s or "draw" in s or "sketch" in s: return "edit"
    if "play" in s or "sim" in s or "run" in s or "anim" in s or "keyframe" in s: return "play"
    if "del" in s or "eras" in s or "clear" in s: return "trash"
    if "copy" in s or "clone" in s or "dup" in s: return "copy"
    if "paste" in s: return "clipboard"
    if "search" in s or "find" in s: return "search"
    if "open" in s or "import" in s or "folder" in s or "project" in s: return "folder"
    if "setting" in s or "pref" in s or "opt" in s or "prop" in s or "tool" in s: return "sliders"
    return "code"


def decode_macro_entry(macro_elem: ET.Element) -> str:
    """Decodes a <MacroEntry> element into a MacroPad action string."""
    ks = macro_elem.find("KeyStroke")
    if ks is not None:
        mods = []
        for m in ks.findall(".//Modifier"):
            mt = (m.text or "").strip().lower()
            if mt in MOD_NAME_MAP and MOD_NAME_MAP[mt] not in mods:
                mods.append(MOD_NAME_MAP[mt])
        key_el = ks.find("Key")
        if key_el is not None and key_el.text:
            try:
                hid_code = int(key_el.text.strip(), 16)
                kname = HID_KEY_MAP.get(hid_code)
                if kname:
                    parts = mods + [kname]
                    if len(parts) == 1 and kname == "ESC":
                        return "cad_key:ESC"
                    return "hotkey:" + "+".join(parts)
            except ValueError:
                pass
        return ""

    seq = macro_elem.find("Sequence")
    if seq is not None:
        # Parse KeyPress / KeyRelease stream into chords
        held_mods = []
        chords = []
        for child in seq:
            tag = child.tag
            txt = (child.text or "").strip()
            if not txt:
                continue
            if tag == "KeyPress":
                try:
                    code = int(txt, 16)
                except ValueError:
                    continue
                if code in HID_MOD_MAP:
                    mname = HID_MOD_MAP[code]
                    if mname not in held_mods:
                        held_mods.append(mname)
                elif code in HID_KEY_MAP:
                    kname = HID_KEY_MAP[code]
                    chord = "+".join(held_mods + [kname])
                    chords.append(( list(held_mods), kname, chord ))
            elif tag == "KeyRelease":
                try:
                    code = int(txt, 16)
                except ValueError:
                    continue
                if code in HID_MOD_MAP:
                    mname = HID_MOD_MAP[code]
                    if mname in held_mods:
                        held_mods.remove(mname)
        if not chords:
            return ""
        if len(chords) == 1:
            chord_str = chords[0][2]
            if chord_str == "ESC":
                return "cad_key:ESC"
            return f"hotkey:{chord_str}"
        # Check if it's typing a CAD command followed by ENTER
        if chords[-1][1] == "ENTER":
            chars = []
            valid_text = True
            for mods, kname, _ in chords[:-1]:
                if kname == "ESC":
                    continue
                if not mods and len(kname) == 1:
                    chars.append(kname.lower())
                elif mods == ["SHIFT"] and kname == "-":
                    chars.append("_")
                elif mods == ["SHIFT"] and len(kname) == 1 and kname.isalpha():
                    chars.append(kname.upper())
                else:
                    valid_text = False
                    break
            if valid_text and len(chars) >= 1:
                return "cad_cmd:" + "".join(chars)
        # Multi-chord sequence (ignore pure repeated zoom steps if all identical)
        unique_chords = [c[2] for c in chords]
        if len(set(unique_chords)) == 1:
            return f"hotkey:{unique_chords[0]}"
        return "keyseq:" + ",".join(unique_chords[:8])
    return ""


def normalize_shortcut_str(raw: str) -> str:
    """Converts human-readable ActionID like 'Ctrl+Shift+A' or 'KB_Esc' into 'hotkey:CTRL+SHIFT+A'."""
    raw = raw.strip()
    if raw in STANDARD_ACTION_MAP:
        return STANDARD_ACTION_MAP[raw][1]
    parts = [p.strip() for p in raw.split("+") if p.strip()]
    if not parts:
        return ""
    norm = []
    for p in parts:
        pl = p.lower()
        if pl in MOD_NAME_MAP:
            norm.append(MOD_NAME_MAP[pl])
        elif pl in ("esc", "escape"):
            norm.append("ESC")
        elif pl in ("enter", "return"):
            norm.append("ENTER")
        elif pl in ("space", "spacebar"):
            norm.append("SPACE")
        elif pl in ("del", "delete"):
            norm.append("DELETE")
        elif pl in ("ins", "insert"):
            norm.append("INSERT")
        elif pl in ("pgup", "pageup"):
            norm.append("PGUP")
        elif pl in ("pgdn", "pagedown"):
            norm.append("PGDN")
        elif pl in ("bksp", "backspace"):
            norm.append("BACKSPACE")
        elif pl in ("up", "down", "left", "right", "home", "end", "tab"):
            norm.append(pl.upper())
        elif re.match(r"^f([1-9]|1[0-9]|2[0-4])$", pl):
            norm.append(pl.upper())
        elif len(p) == 1:
            norm.append(p.upper())
        else:
            return ""
    if len(norm) == 1 and norm[0] == "ESC":
        return "cad_key:ESC"
    return "hotkey:" + "+".join(norm)


def clean_label_for_eink(name: str) -> str:
    """Creates a clean, crisp <=10 char uppercase label for the 3x3 E-Ink grid."""
    s = re.sub(r"^STR_[A-Z0-9_]+$", lambda m: m.group(0).split("_")[-1], name.strip())
    s = re.sub(r"\s*\(.*?\)", "", s).strip()
    for prefix in ("Toggle ", "Show ", "Open ", "Activate ", "Select ", "View ", "Quick ", "Mode: ", "Tool: "):
        if s.lower().startswith(prefix.lower()) and len(s) > len(prefix) + 2:
            s = s[len(prefix):].strip()
    for suffix in (" View", " Tool", " Mode", " Window", " Menu", " Dialog", " Panel"):
        if s.lower().endswith(suffix.lower()) and len(s) > len(suffix) + 2:
            s = s[:-len(suffix)].strip()
    s = s.replace("...", "").strip().upper()
    if len(s) <= 9:
        return s
    # Abbreviate common words
    abbr = {
        "EXTRUDE": "EXTRUDE", "ROTATE": "ROTATE", "TRANSLATE": "MOVE",
        "WIREFRAME": "WIREFRM", "ISOMETRIC": "ISO VIEW", "PERSPECTIVE": "PERSP",
        "ORTHOGRAPHIC": "ORTHO", "PROPERTIES": "PROPS", "PARAMETERS": "PARAMS",
        "DIMENSION": "DIM", "RECTANGLE": "RECT", "POLYLINE": "PLINE",
        "SHADING": "SHADE", "STRENGTH": "STRNGTH", "MAXIMIZE": "MAXIMIZE",
        "DUPLICATE": "DUP", "KEYFRAME": "KEYFRM", "COMPONENT": "COMP",
        "SIMULATION": "SIM", "MATERIAL": "MAT", "TIMELINE": "TIMELN",
    }
    for k, v in abbr.items():
        if k in s:
            s = s.replace(k, v)
    return s[:9].strip()


def harvest():
    print(f"[Harvester] Scanning {CFG_DIR} ...")
    en_path = os.path.join(CFG_DIR, "en-US.xml")
    en_root = ET.parse(en_path).getroot()

    # 1. String Table
    str_table = {}
    for se in en_root.findall(".//StringEntry"):
        k = (se.findtext("Key") or "").strip()
        v = (se.findtext("Value") or "").strip()
        if k and v:
            str_table[k] = v

    def resolve_str(s: str) -> str:
        if not s:
            return ""
        s = s.strip()
        if s in str_table:
            return str_table[s]
        if s.startswith("ID_STR_") and s[3:] in str_table:
            return str_table[s[3:]]
        if s.startswith("STR_"):
            # Fallback humanize STR_APP_FOO -> Foo
            parts = s[4:].split("_")
            return " ".join(p.capitalize() for p in parts[-2:]) if len(parts) > 1 else parts[0].capitalize()
        return s

    # 2. Global MacroTable from en-US.xml & SharedCfg.xml
    global_macros = {}
    for m in en_root.findall(".//MacroEntry"):
        mid = (m.findtext("ID") or "").strip()
        act = decode_macro_entry(m)
        if mid and act:
            global_macros[mid] = act

    shared_path = os.path.join(CFG_DIR, "SharedCfg.xml")
    if os.path.exists(shared_path):
        for m in ET.parse(shared_path).getroot().findall(".//MacroEntry"):
            mid = (m.findtext("ID") or "").strip()
            act = decode_macro_entry(m)
            if mid and act:
                global_macros[mid] = act

    # 3. Convert driver PNG icons in Cfg\Images\3DxService\*.png
    driver_icons_hex = {}
    harvested_icons = {}
    if os.path.isdir(IMAGES_DIR):
        for png_path in glob.glob(os.path.join(IMAGES_DIR, "*.png")):
            fname = os.path.basename(png_path)
            try:
                im = Image.open(png_path)
                h_str = pil_to_24x24_hex(im)
                if h_str and "f" in h_str and h_str != "0" * 144:
                    icon_id = "tdx_" + os.path.splitext(fname)[0].lower().replace(" ", "_")[:20]
                    driver_icons_hex[fname.lower()] = icon_id
                    harvested_icons[icon_id] = {
                        "name": icon_id,
                        "w": 24,
                        "h": 24,
                        "hex": h_str,
                    }
            except Exception:
                pass

    def extract_ba_icon(ba_elem: ET.Element, fallback_label: str, fallback_act: str) -> str:
        if ba_elem is not None:
            img_el = ba_elem.find("Image")
            if img_el is not None:
                data_el = img_el.find("Data")
                if data_el is not None and data_el.text:
                    try:
                        raw_bytes = base64.b64decode(data_el.text.strip())
                        im = Image.open(io.BytesIO(raw_bytes))
                        h_str = pil_to_24x24_hex(im)
                        if h_str and h_str != "0" * 144:
                            digest = hashlib.md5(h_str.encode("ascii")).hexdigest()[:8]
                            icon_id = f"tdx_ico_{digest}"
                            if icon_id not in harvested_icons:
                                harvested_icons[icon_id] = {
                                    "name": icon_id,
                                    "w": 24,
                                    "h": 24,
                                    "hex": h_str,
                                }
                            return icon_id
                    except Exception:
                        pass
                src_el = img_el.find("Source")
                if src_el is not None and src_el.text:
                    # e.g. [driver_images:V3DK_TOP.png]
                    m = re.search(r":([^\]]+\.png)", src_el.text.strip(), re.I)
                    if m:
                        fn = m.group(1).lower()
                        if fn in driver_icons_hex:
                            return driver_icons_hex[fn]
        return guess_fallback_icon(fallback_label, fallback_act)

    # Index extra global macros from en-US.xml by XML filename
    extra_xml_macros = {}
    for mid, act in global_macros.items():
        if mid.startswith("Macro_"):
            parts = mid.split("_")
            if len(parts) >= 3:
                prefix = parts[1]
                xml_fn = EN_US_PREFIX_TO_XML.get(prefix)
                if xml_fn:
                    pretty_name = " ".join(parts[2:])
                    extra_xml_macros.setdefault(xml_fn.lower(), []).append((mid, pretty_name, act))

    apps_by_key = {}

    for xml_path in sorted(glob.glob(os.path.join(CFG_DIR, "*.xml"))):
        fname = os.path.basename(xml_path)
        if fname.lower() in ("en-us.xml", "base.xml", "sharedcfg.xml", "default.xml", "desktop.xml"):
            continue
        try:
            root = ET.parse(xml_path).getroot()
        except Exception:
            continue
        if root.tag != "AppCfg":
            continue

        cfg_props = root.find("CfgProperties")
        raw_name = ""
        if cfg_props is not None:
            raw_name = cfg_props.findtext("Name") or cfg_props.findtext("ID") or ""
        sig = root.find(".//Signature")
        if not raw_name and sig is not None:
            raw_name = sig.findtext("Name") or ""
        app_name = resolve_str(raw_name) or os.path.splitext(fname)[0]

        # Skip internal 3DxWare helper binaries
        if fname.lower().startswith("3dx") and "unity" not in fname.lower() and "proe" not in fname.lower() and "inventor" not in fname.lower() and "solidworks" not in fname.lower():
            continue
        if fname.lower() in ("ignoredapps.xml", "wysiwyg demo.xml", "explorer_tray.xml", "searchandcortana.xml"):
            continue

        exes = []
        if sig is not None:
            for ex in sig.findall("ExecutableName"):
                if ex.text:
                    clean_ex = ex.text.strip().replace("\\.", ".").replace("\\", "")
                    if clean_ex.lower() not in [e.lower() for e in exes]:
                        exes.append(clean_ex.lower())

        # Local MacroTable
        local_macros = dict(global_macros)
        local_macro_elems = {}
        for m in root.findall(".//MacroEntry"):
            mid = (m.findtext("ID") or "").strip()
            act = decode_macro_entry(m)
            if mid and act:
                local_macros[mid] = act
                local_macro_elems[mid] = m

        app_key_lower = app_name.lower()
        view_ovr = {}
        for k_sub, ovr_dict in APP_VIEW_OVERRIDES.items():
            if k_sub in app_key_lower or k_sub in fname.lower():
                view_ovr = ovr_dict
                break

        actions_dict = {}  # action_id -> {"id", "name", "label", "action", "icon", "priority"}
        ba_elems_by_id = {}

        def register_action(aid: str, name: str, mp_action: str, icon_name: str, priority: int = 2):
            if not mp_action or not name:
                return
            # Skip duplicate (name, mp_action)
            clean_nm = resolve_str(name).strip()
            if not clean_nm or clean_nm.startswith("STR_APP_PASSTO"):
                return
            lbl = clean_label_for_eink(clean_nm)
            if not lbl:
                return
            existing = actions_dict.get(aid)
            if existing and existing["priority"] <= priority:
                return
            actions_dict[aid] = {
                "id": aid,
                "name": clean_nm,
                "label": lbl,
                "action": mp_action,
                "icon": icon_name or guess_fallback_icon(clean_nm, mp_action),
                "priority": priority,
                "order": existing["order"] if existing else len(actions_dict),
            }

        # 1. Parse <ButtonActions>
        for ba in root.findall("./ButtonActions/ButtonAction"):
            aid = (ba.findtext("ID") or "").strip()
            raw_nm = (ba.findtext("Name") or aid).strip()
            nm = resolve_str(raw_nm)
            btype = ba.attrib.get("Type", "")
            ba_elems_by_id[aid] = ba

            mp_act = ""
            if aid in local_macros:
                mp_act = local_macros[aid]
            elif btype == "Sequence":
                seq_el = ba.find("Sequence")
                if seq_el is not None:
                    txt_el = seq_el.find("Text")
                    if txt_el is not None and txt_el.text and txt_el.text.strip():
                        mp_act = "cad_cmd:" + txt_el.text.strip()
                    else:
                        seq_acts = []
                        for a_el in seq_el.findall("ActionID"):
                            atxt = (a_el.text or "").strip()
                            if atxt in local_macros:
                                seq_acts.append(local_macros[atxt].replace("hotkey:", "").replace("cad_key:", ""))
                            else:
                                norm_s = normalize_shortcut_str(atxt)
                                if norm_s:
                                    seq_acts.append(norm_s.replace("hotkey:", "").replace("cad_key:", ""))
                        if len(seq_acts) == 1:
                            mp_act = "cad_key:ESC" if seq_acts[0] == "ESC" else f"hotkey:{seq_acts[0]}"
                        elif len(seq_acts) > 1:
                            if len(set(seq_acts)) == 1:
                                mp_act = f"hotkey:{seq_acts[0]}"
                            else:
                                mp_act = "keyseq:" + ",".join(seq_acts[:8])
            elif btype == "Keyboard":
                mp_act = local_macros.get(aid) or normalize_shortcut_str(aid)
            elif btype == "AppCommand":
                # AutoCAD CMDACAD:ID_<cmd>
                if "CMDACAD:ID_" in aid:
                    cmd_part = aid.split("CMDACAD:ID_")[-1].strip()
                    if cmd_part.lower() in APPCMD_NAME_TO_ACTION:
                        mp_act = APPCMD_NAME_TO_ACTION[cmd_part.lower()]
                    elif nm.lower() in APPCMD_NAME_TO_ACTION:
                        mp_act = APPCMD_NAME_TO_ACTION[nm.lower()]
                    elif re.match(r"^[A-Za-z0-9_]+$", cmd_part) and not cmd_part.startswith("MM_"):
                        mp_act = f"cad_cmd:_{cmd_part.upper()}"
                elif nm.lower() in APPCMD_NAME_TO_ACTION:
                    mp_act = APPCMD_NAME_TO_ACTION[nm.lower()]
            elif aid in view_ovr:
                nm, mp_act = view_ovr[aid]
            elif aid in STANDARD_ACTION_MAP:
                std_nm, mp_act = STANDARD_ACTION_MAP[aid]
                if not nm or nm == aid:
                    nm = std_nm

            if mp_act:
                ico = extract_ba_icon(ba, nm, mp_act)
                register_action(aid, nm, mp_act, ico, priority=1)

        # 2. Any local <MacroEntry> not already in <ButtonActions>
        for mid, m_elem in local_macro_elems.items():
            if mid not in actions_dict:
                mp_act = local_macros[mid]
                pretty = mid.replace("Macro_", "").replace("_", " ")
                # Skip raw UUID names if they had no ButtonAction wrapper
                if re.match(r"^[0-9a-fA-F\-]{30,}$", pretty.strip()):
                    continue
                ico = extract_ba_icon(m_elem, pretty, mp_act)
                register_action(mid, pretty, mp_act, ico, priority=2)

        # 3. Extra global macros from en-US.xml matching this XML file
        for mid, pretty_name, mp_act in extra_xml_macros.get(fname.lower(), []):
            if mid not in actions_dict:
                register_action(mid, pretty_name, mp_act, guess_fallback_icon(pretty_name, mp_act), priority=2)

        # 4. Scan <Devices> and <Menus> for referenced ActionIDs
        referenced_ids = []
        for out_el in root.findall(".//Output/ActionID"):
            aid = (out_el.text or "").strip()
            if aid and aid not in referenced_ids:
                referenced_ids.append(aid)
            if aid and aid not in actions_dict:
                if aid in view_ovr:
                    nm, mp_act = view_ovr[aid]
                    register_action(aid, nm, mp_act, guess_fallback_icon(nm, mp_act), priority=2)
                elif aid in local_macros:
                    mp_act = local_macros[aid]
                    pretty = aid.replace("Macro_", "").replace("_", " ")
                    register_action(aid, pretty, mp_act, guess_fallback_icon(pretty, mp_act), priority=2)
                elif aid in STANDARD_ACTION_MAP:
                    nm, mp_act = STANDARD_ACTION_MAP[aid]
                    register_action(aid, nm, mp_act, guess_fallback_icon(nm, mp_act), priority=3)

        # 5. Parse <Menus><Menu Type="Radial">
        radial_menus = []
        for menu_el in root.findall(".//Menus/Menu"):
            m_id = (menu_el.findtext("ID") or "").strip()
            m_name = resolve_str(menu_el.findtext("Name") or m_id)
            slices = []
            for btn_el in menu_el.findall("Button"):
                out_aid = (btn_el.findtext("Output/ActionID") or "").strip()
                if not out_aid or out_aid.startswith("Driver_") or out_aid == "App_PassToApplication":
                    continue
                act_obj = actions_dict.get(out_aid)
                if act_obj:
                    slices.append({
                        "label": act_obj["label"],
                        "name": act_obj["name"],
                        "action": act_obj["action"],
                        "icon": act_obj["icon"],
                    })
            if len(slices) >= 2:
                radial_menus.append({
                    "id": m_id,
                    "name": m_name,
                    "slices": slices[:8],
                })

        # Deduplicate actions by (label, action) keeping highest priority and XML declaration order
        unique_actions = []
        seen_pairs = set()
        # Boost priority if referenced in <Devices> or <Menus>
        for aid, aobj in actions_dict.items():
            if aid in referenced_ids and aobj["priority"] > 1:
                aobj["priority"] = 1
        for aobj in sorted(actions_dict.values(), key=lambda x: (x["priority"], x["order"])):
            pair = (aobj["label"], aobj["action"])
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                unique_actions.append({
                    "id": aobj["id"],
                    "name": aobj["name"],
                    "label": aobj["label"],
                    "action": aobj["action"],
                    "icon": aobj["icon"],
                })

        # Even if an AppCfg had 0 custom actions, if it has an exe signature, provide standard 9-cell universal/view actions
        exe_match_str = "|".join(exes)
        app_id = re.sub(r"[^a-z0-9_]+", "_", os.path.splitext(fname)[0].lower()).strip("_")

        # Merge multiple XML variants for same app (e.g. Rhino.xml + Rhino3D.xml + RhinoFS.xml) if needed, or keep distinct
        apps_by_key[app_id] = {
            "id": app_id,
            "name": app_name,
            "xml_file": fname,
            "exe_match": exe_match_str,
            "exes": exes,
            "action_count": len(unique_actions),
            "actions": unique_actions,
            "radial_menus": radial_menus,
        }

    # Build a recommended 9-cell grid template for every app
    FALLBACK_CELLS = [
        {"label": "UNDO", "name": "Undo", "action": "hotkey:CTRL+Z", "icon": "cad_undo"},
        {"label": "REDO", "name": "Redo", "action": "hotkey:CTRL+Y", "icon": "cad_redo"},
        {"label": "SAVE", "name": "Save", "action": "hotkey:CTRL+S", "icon": "cad_qsave"},
        {"label": "COPY", "name": "Copy", "action": "hotkey:CTRL+C", "icon": "copy"},
        {"label": "PASTE", "name": "Paste", "action": "hotkey:CTRL+V", "icon": "clipboard"},
        {"label": "DELETE", "name": "Delete", "action": "hotkey:DELETE", "icon": "trash"},
        {"label": "FIT VIEW", "name": "Fit View", "action": "hotkey:F", "icon": "cad_zoom_ext"},
        {"label": "FIND", "name": "Find", "action": "hotkey:CTRL+F", "icon": "search"},
        {"label": "ESCAPE", "name": "Escape", "action": "cad_key:ESC", "icon": "close"},
    ]

    apps_list = sorted(
        apps_by_key.values(),
        key=lambda a: (0 if a["action_count"] >= 4 else (1 if a["action_count"] >= 1 else 2), a["name"].lower())
    )

    for app in apps_list:
        cells = []
        used_actions = set()
        for act in app["actions"]:
            if len(cells) >= 9:
                break
            if act["action"] not in used_actions:
                used_actions.add(act["action"])
                cells.append({
                    "index": len(cells) + 1,
                    "label": act["label"],
                    "icon": act["icon"],
                    "action": act["action"],
                })
        for fb in FALLBACK_CELLS:
            if len(cells) >= 9:
                break
            if fb["action"] not in used_actions:
                used_actions.add(fb["action"])
                cells.append({
                    "index": len(cells) + 1,
                    "label": fb["label"],
                    "icon": fb["icon"],
                    "action": fb["action"],
                })
        app["recommended_cells"] = cells

    total_actions = sum(a["action_count"] for a in apps_list)
    total_menus = sum(len(a["radial_menus"]) for a in apps_list)
    apps_with_actions = sum(1 for a in apps_list if a["action_count"] > 0)

    payload = {
        "stats": {
            "total_apps": len(apps_list),
            "apps_with_actions": apps_with_actions,
            "total_actions": total_actions,
            "total_radial_menus": total_menus,
            "total_icons": len(harvested_icons),
        },
        "apps": apps_list,
        "icons": harvested_icons,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[Harvester] Saved {OUT_JSON}")
    print(f"  -> Total Apps Harvested:   {len(apps_list)} ({apps_with_actions} with custom actions)")
    print(f"  -> Total Executable Actions: {total_actions}")
    print(f"  -> Total Radial Pie Menus:   {total_menus}")
    print(f"  -> Total 24x24 E-Ink Icons:  {len(harvested_icons)}")


if __name__ == "__main__":
    harvest()
