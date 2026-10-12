"""
Layer & Icon Store Manager for MacroPad Hub (pi_app).
Stores multi-layer mappings with custom labels, 1-bit icons, and actions.
"""

import os
import json
from typing import Dict, Any, Optional, List
from icon_library import get_compiled_icons_library, ascii_to_hex

STORE_PATH = os.path.join(os.path.dirname(__file__), "layers_store.json")

DEFAULT_LAYERS: Dict[str, Any] = {
    "1": {
        "id": 1,
        "name": "Media & General",
        "bank": 1,
        "slot": 1,
        "cells": [
            {"index": 1, "label": "PLAY", "icon": "play", "action": "media_play_pause"},
            {"index": 2, "label": "PAUSE", "icon": "pause", "action": "media_pause"},
            {"index": 3, "label": "NEXT", "icon": "next", "action": "media_next"},
            {"index": 4, "label": "PREV", "icon": "prev", "action": "media_prev"},
            {"index": 5, "label": "LIGHT", "icon": "light", "action": "light_toggle"},
            {"index": 6, "label": "VOL+", "icon": "vol_up", "action": "vol_up"},
            {"index": 7, "label": "ACT 7", "icon": "code", "action": "macro"},
            {"index": 8, "label": "ACT 8", "icon": "folder", "action": "macro"},
            {"index": 9, "label": "WOL PC", "icon": "terminal", "action": "wakeonlan"}
        ]
    },
    "2": {
        "id": 2,
        "name": "Discord Voice & Audio",
        "bank": 1,
        "slot": 2,
        "cells": [
            {"index": 1, "label": "MIC MUTE", "icon": "mic", "action": "discord_mic_mute"},
            {"index": 2, "label": "DEAFEN", "icon": "mute", "action": "discord_deafen"},
            {"index": 3, "label": "DISC VOL-", "icon": "prev", "action": "discord_vol_down"},
            {"index": 4, "label": "DISC VOL+", "icon": "vol_up", "action": "discord_vol_up"},
            {"index": 5, "label": "DISC 100%", "icon": "discord", "action": "discord_vol_reset"},
            {"index": 6, "label": "G321 HDP", "icon": "play", "action": "audio_headphones"},
            {"index": 7, "label": "EDIFIER", "icon": "vol_up", "action": "audio_speakers"},
            {"index": 8, "label": "SYNC CALL", "icon": "cad_regen", "action": "discord_sync_call"},
            {"index": 9, "label": "TEST CALL", "icon": "discord", "action": "discord_demo_call"}
        ]
    },
    "3": {
        "id": 3,
        "name": "Dev & Terminal",
        "bank": 1,
        "slot": 3,
        "cells": [
            {"index": 1, "label": "TERM", "icon": "terminal", "action": "open_terminal"},
            {"index": 2, "label": "LOCK", "icon": "lock", "action": "lock_pc"},
            {"index": 3, "label": "ACT 3", "icon": "", "action": "macro_3"},
            {"index": 4, "label": "ACT 4", "icon": "", "action": "macro_4"},
            {"index": 5, "label": "ACT 5", "icon": "", "action": "macro_5"},
            {"index": 6, "label": "ACT 6", "icon": "", "action": "macro_6"},
            {"index": 7, "label": "ACT 7", "icon": "", "action": "macro_7"},
            {"index": 8, "label": "ACT 8", "icon": "", "action": "macro_8"},
            {"index": 9, "label": "ACT 9", "icon": "", "action": "macro_9"}
        ]
    },
    "4": {
        "id": 4,
        "name": "System & Power",
        "bank": 1,
        "slot": 4,
        "cells": [
            {"index": 1, "label": "ACT 1", "icon": "", "action": "macro_1"},
            {"index": 2, "label": "ACT 2", "icon": "", "action": "macro_2"},
            {"index": 3, "label": "ACT 3", "icon": "", "action": "macro_3"},
            {"index": 4, "label": "ACT 4", "icon": "", "action": "macro_4"},
            {"index": 5, "label": "ACT 5", "icon": "", "action": "macro_5"},
            {"index": 6, "label": "ACT 6", "icon": "", "action": "macro_6"},
            {"index": 7, "label": "ACT 7", "icon": "", "action": "macro_7"},
            {"index": 8, "label": "ACT 8", "icon": "", "action": "macro_8"},
            {"index": 9, "label": "REBOOT", "icon": "power", "action": "restart_timer"}
        ]
    },
    "5": {
        "id": 5,
        "name": "CAD: Draw",
        "bank": 2,
        "slot": 1,
        "cells": [
            {"index": 1, "label": "LINE", "icon": "cad_line", "action": "cad_cmd:L"},
            {"index": 2, "label": "PLINE", "icon": "cad_pline", "action": "cad_cmd:PL"},
            {"index": 3, "label": "RECT", "icon": "cad_rect", "action": "cad_cmd:REC"},
            {"index": 4, "label": "CIRCLE", "icon": "cad_circle", "action": "cad_cmd:C"},
            {"index": 5, "label": "ARC", "icon": "cad_arc", "action": "cad_cmd:A"},
            {"index": 6, "label": "POLY", "icon": "cad_poly", "action": "cad_cmd:POL"},
            {"index": 7, "label": "SPLINE", "icon": "cad_spline", "action": "cad_cmd:SPL"},
            {"index": 8, "label": "HATCH", "icon": "cad_hatch", "action": "cad_cmd:H"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    },
    "6": {
        "id": 6,
        "name": "CAD: Modify",
        "bank": 2,
        "slot": 2,
        "cells": [
            {"index": 1, "label": "MOVE", "icon": "cad_move", "action": "cad_cmd:M"},
            {"index": 2, "label": "COPY", "icon": "cad_copy", "action": "cad_cmd:CO"},
            {"index": 3, "label": "ROTATE", "icon": "cad_rotate", "action": "cad_cmd:RO"},
            {"index": 4, "label": "TRIM", "icon": "cad_trim", "action": "cad_cmd:TR"},
            {"index": 5, "label": "EXTEND", "icon": "cad_extend", "action": "cad_cmd:EX"},
            {"index": 6, "label": "OFFSET", "icon": "cad_offset", "action": "cad_cmd:O"},
            {"index": 7, "label": "MIRROR", "icon": "cad_mirror", "action": "cad_cmd:MI"},
            {"index": 8, "label": "SCALE", "icon": "cad_scale", "action": "cad_cmd:SC"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    },
    "7": {
        "id": 7,
        "name": "CAD: Construct",
        "bank": 2,
        "slot": 3,
        "cells": [
            {"index": 1, "label": "FILLET", "icon": "cad_fillet", "action": "cad_cmd:F"},
            {"index": 2, "label": "CHAMFER", "icon": "cad_chamfer", "action": "cad_cmd:CHA"},
            {"index": 3, "label": "JOIN", "icon": "cad_join", "action": "cad_cmd:J"},
            {"index": 4, "label": "EXPLODE", "icon": "cad_explode", "action": "cad_cmd:X"},
            {"index": 5, "label": "BREAK", "icon": "cad_break", "action": "cad_cmd:BR"},
            {"index": 6, "label": "ALIGN", "icon": "cad_align", "action": "cad_cmd:AL"},
            {"index": 7, "label": "ARRAY", "icon": "cad_array", "action": "cad_cmd:AR"},
            {"index": 8, "label": "ERASE", "icon": "cad_erase", "action": "cad_cmd:E"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    },
    "8": {
        "id": 8,
        "name": "CAD: Precision & Snaps",
        "bank": 2,
        "slot": 4,
        "cells": [
            {"index": 1, "label": "OSNAP", "icon": "cad_osnap", "action": "cad_key:F3"},
            {"index": 2, "label": "ORTHO", "icon": "cad_ortho", "action": "cad_key:F8"},
            {"index": 3, "label": "POLAR", "icon": "cad_polar", "action": "cad_key:F10"},
            {"index": 4, "label": "OTRACK", "icon": "cad_otrack", "action": "cad_key:F11"},
            {"index": 5, "label": "DYN IN", "icon": "cad_dyn", "action": "cad_key:F12"},
            {"index": 6, "label": "GRID", "icon": "cad_grid", "action": "cad_key:F7"},
            {"index": 7, "label": "MID2P", "icon": "cad_mid2p", "action": "cad_cmd:M2P"},
            {"index": 8, "label": "FROM", "icon": "cad_from", "action": "cad_cmd:FROM"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    },
    "9": {
        "id": 9,
        "name": "CAD: Annotate",
        "bank": 3,
        "slot": 1,
        "cells": [
            {"index": 1, "label": "DIM", "icon": "cad_dim", "action": "cad_cmd:DIM"},
            {"index": 2, "label": "DIMLIN", "icon": "cad_dimlin", "action": "cad_cmd:DLI"},
            {"index": 3, "label": "DIMALI", "icon": "cad_dimali", "action": "cad_cmd:DAL"},
            {"index": 4, "label": "DIMANG", "icon": "cad_dimang", "action": "cad_cmd:DAN"},
            {"index": 5, "label": "DIMRAD", "icon": "cad_dimrad", "action": "cad_cmd:DRA"},
            {"index": 6, "label": "LEADER", "icon": "cad_leader", "action": "cad_cmd:MLEADER"},
            {"index": 7, "label": "MTEXT", "icon": "cad_mtext", "action": "cad_cmd:MT"},
            {"index": 8, "label": "TABLE", "icon": "cad_table", "action": "cad_cmd:TB"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    },
    "10": {
        "id": 10,
        "name": "CAD: Layers",
        "bank": 3,
        "slot": 2,
        "cells": [
            {"index": 1, "label": "LA MGR", "icon": "cad_layers", "action": "cad_cmd:LA"},
            {"index": 2, "label": "LAYISO", "icon": "cad_layiso", "action": "cad_cmd:LAYISO"},
            {"index": 3, "label": "LAYUNISO", "icon": "cad_layuniso", "action": "cad_cmd:LAYUNISO"},
            {"index": 4, "label": "LAYOFF", "icon": "cad_layoff", "action": "cad_cmd:LAYOFF"},
            {"index": 5, "label": "LAYON", "icon": "cad_layon", "action": "cad_cmd:LAYON"},
            {"index": 6, "label": "LAYFRZ", "icon": "cad_layfrz", "action": "cad_cmd:LAYFRZ"},
            {"index": 7, "label": "LAYMCUR", "icon": "cad_laymcur", "action": "cad_cmd:LAYMCUR"},
            {"index": 8, "label": "MATCH", "icon": "cad_match", "action": "cad_cmd:MA"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    },
    "11": {
        "id": 11,
        "name": "CAD: Blocks & Inquiry",
        "bank": 3,
        "slot": 3,
        "cells": [
            {"index": 1, "label": "INSERT", "icon": "cad_insert", "action": "cad_cmd:I"},
            {"index": 2, "label": "BLOCK", "icon": "cad_block", "action": "cad_cmd:B"},
            {"index": 3, "label": "BEDIT", "icon": "cad_bedit", "action": "cad_cmd:BE"},
            {"index": 4, "label": "WBLOCK", "icon": "cad_wblock", "action": "cad_cmd:W"},
            {"index": 5, "label": "XREF", "icon": "cad_xref", "action": "cad_cmd:XR"},
            {"index": 6, "label": "DIST", "icon": "cad_dist", "action": "cad_cmd:DI"},
            {"index": 7, "label": "AREA", "icon": "cad_area", "action": "cad_cmd:AA"},
            {"index": 8, "label": "QSELECT", "icon": "cad_qselect", "action": "cad_cmd:QSELECT"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    },
    "12": {
        "id": 12,
        "name": "CAD: View & Plot",
        "bank": 3,
        "slot": 4,
        "cells": [
            {"index": 1, "label": "Z EXT", "icon": "cad_zext", "action": "cad_cmd:Z E"},
            {"index": 2, "label": "Z WIN", "icon": "cad_zwin", "action": "cad_cmd:Z W"},
            {"index": 3, "label": "Z PREV", "icon": "cad_zprev", "action": "cad_cmd:Z P"},
            {"index": 4, "label": "REGEN", "icon": "cad_regen", "action": "cad_cmd:RE"},
            {"index": 5, "label": "PURGE", "icon": "cad_purge", "action": "cad_cmd:PU"},
            {"index": 6, "label": "AUDIT", "icon": "cad_audit", "action": "cad_cmd:AUDIT Y"},
            {"index": 7, "label": "PLOT", "icon": "cad_plot", "action": "cad_key:CTRL+P"},
            {"index": 8, "label": "QSAVE", "icon": "cad_qsave", "action": "cad_key:CTRL+S"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    },
    "13": {
        "id": 13,
        "name": "Fusion: SpaceMouse Radial",
        "bank": 4,
        "slot": 1,
        "cells": [
            {
                "index": 1, "label": "SKETCH", "icon": "cad_line", "action": "fusion:line", "hold_enabled": True,
                "radial_title": "SKETCH",
                "radial_slices": [
                    {"label": "Line\n(L)", "type": "fusion", "val": "line"},
                    {"label": "Create\nSketch", "type": "fusion", "val": "create_sketch"},
                    {"label": "Circle\n(C)", "type": "fusion", "val": "circle_center"},
                    {"label": "3-Point\nArc", "type": "fusion", "val": "arc_3pt"},
                    {"label": "Fit Point\nSpline", "type": "fusion", "val": "spline_fit"},
                    {"label": "Project\n(P)", "type": "fusion", "val": "project"},
                    {"label": "Construct\nLine (X)", "type": "fusion", "val": "construction"},
                    {"label": "Finish\nSketch", "type": "fusion", "val": "finish_sketch"}
                ]
            },
            {
                "index": 2, "label": "SHAPES", "icon": "cad_rect", "action": "fusion:rect_2pt", "hold_enabled": True,
                "radial_title": "SHAPES",
                "radial_slices": [
                    {"label": "Center\nRect", "type": "fusion", "val": "rect_center"},
                    {"label": "2-Point\nRect (R)", "type": "fusion", "val": "rect_2pt"},
                    {"label": "3-Point\nRect", "type": "fusion", "val": "rect_3pt"},
                    {"label": "Circumscr.\nPolygon", "type": "fusion", "val": "poly_circum"},
                    {"label": "Inscribed\nPolygon", "type": "fusion", "val": "poly_inscr"},
                    {"label": "Center\nSlot", "type": "fusion", "val": "slot_center"}
                ]
            },
            {
                "index": 3, "label": "2D EDIT", "icon": "cad_dim", "action": "fusion:dimension", "hold_enabled": True,
                "radial_title": "2D EDIT",
                "radial_slices": [
                    {"label": "Dimension\n(D)", "type": "fusion", "val": "dimension"},
                    {"label": "Offset\n(O)", "type": "fusion", "val": "offset"},
                    {"label": "Trim\n(T)", "type": "fusion", "val": "trim"},
                    {"label": "Extend", "type": "fusion", "val": "extend"},
                    {"label": "2D Mirror", "type": "fusion", "val": "sketch_mirror"},
                    {"label": "Coincident", "type": "fusion", "val": "coincident"}
                ]
            },
            {
                "index": 4, "label": "3D SOLID", "icon": "cad_block", "action": "fusion:extrude", "hold_enabled": True,
                "radial_title": "3D SOLID",
                "radial_slices": [
                    {"label": "Extrude\n(E)", "type": "fusion", "val": "extrude"},
                    {"label": "Revolve", "type": "fusion", "val": "revolve"},
                    {"label": "Sweep", "type": "fusion", "val": "sweep"},
                    {"label": "Loft", "type": "fusion", "val": "loft"},
                    {"label": "Hole\n(H)", "type": "fusion", "val": "hole"},
                    {"label": "Thread", "type": "fusion", "val": "thread"},
                    {"label": "Press Pull\n(Q)", "type": "fusion", "val": "press_pull"},
                    {"label": "Rib", "type": "fusion", "val": "rib"}
                ]
            },
            {
                "index": 5, "label": "MODIFY", "icon": "cad_fillet", "action": "fusion:fillet", "hold_enabled": True,
                "radial_title": "MODIFY",
                "radial_slices": [
                    {"label": "Fillet\n(F)", "type": "fusion", "val": "fillet"},
                    {"label": "Chamfer", "type": "fusion", "val": "chamfer"},
                    {"label": "Shell", "type": "fusion", "val": "shell"},
                    {"label": "Combine", "type": "fusion", "val": "combine"},
                    {"label": "Split\nBody", "type": "fusion", "val": "split_body"},
                    {"label": "Scale", "type": "fusion", "val": "scale"}
                ]
            },
            {
                "index": 6, "label": "PATTERN", "icon": "cad_array", "action": "fusion:move", "hold_enabled": True,
                "radial_title": "PATTERN",
                "radial_slices": [
                    {"label": "Move/Copy\n(M)", "type": "fusion", "val": "move"},
                    {"label": "Rect\nPattern", "type": "fusion", "val": "rect_pattern"},
                    {"label": "Circular\nPattern", "type": "fusion", "val": "circ_pattern"},
                    {"label": "Pattern\non Path", "type": "fusion", "val": "path_pattern"},
                    {"label": "Mirror", "type": "fusion", "val": "mirror"},
                    {"label": "Align", "type": "fusion", "val": "align"}
                ]
            },
            {
                "index": 7, "label": "PLANE/JNT", "icon": "cad_layers", "action": "fusion:joint", "hold_enabled": True,
                "radial_title": "PLANE / ASSY",
                "radial_slices": [
                    {"label": "Offset\nPlane", "type": "fusion", "val": "offset_plane"},
                    {"label": "Midplane", "type": "fusion", "val": "midplane"},
                    {"label": "Plane at\nAngle", "type": "fusion", "val": "angle_plane"},
                    {"label": "Joint\n(J)", "type": "fusion", "val": "joint"},
                    {"label": "Rigid\nGroup", "type": "fusion", "val": "rigid_group"},
                    {"label": "New\nComponent", "type": "fusion", "val": "new_component"}
                ]
            },
            {
                "index": 8, "label": "INSPECT", "icon": "cad_dist", "action": "fusion:measure", "hold_enabled": True,
                "radial_title": "INSPECT / VIEW",
                "radial_slices": [
                    {"label": "Measure\n(I)", "type": "fusion", "val": "measure"},
                    {"label": "Section\nAnalysis", "type": "fusion", "val": "section_analysis"},
                    {"label": "Parameters\n(fx)", "type": "fusion", "val": "parameters"},
                    {"label": "Fit View\n(F6)", "type": "fusion_view", "val": "fit"},
                    {"label": "Home\nView", "type": "fusion_view", "val": "home"},
                    {"label": "3D Print\n(STL)", "type": "fusion", "val": "3d_print"}
                ]
            },
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC", "hold_enabled": False}
        ]
    },
    "14": {
        "id": 14,
        "name": "Photoshop & Creative",
        "bank": 4,
        "slot": 2,
        "cells": [
            {"index": 1, "label": "MOVE (V)", "icon": "cad_move", "action": "hotkey:V"},
            {"index": 2, "label": "BRUSH (B)", "icon": "cad_spline", "action": "hotkey:B"},
            {"index": 3, "label": "ERASE (E)", "icon": "cad_erase", "action": "hotkey:E"},
            {"index": 4, "label": "LASSO (L)", "icon": "cad_pline", "action": "hotkey:L"},
            {"index": 5, "label": "WAND (W)", "icon": "cad_qselect", "action": "hotkey:W"},
            {"index": 6, "label": "XFORM", "icon": "cad_scale", "action": "hotkey:CTRL+T"},
            {"index": 7, "label": "UNDO", "icon": "prev", "action": "hotkey:CTRL+Z"},
            {"index": 8, "label": "DESELECT", "icon": "cad_rect", "action": "hotkey:CTRL+D"},
            {"index": 9, "label": "ESC", "icon": "cad_esc", "action": "cad_key:ESC"}
        ]
    }
}

DEFAULT_APP_RULES: List[Dict[str, Any]] = [
    {
        "id": "fusion360",
        "name": "Autodesk Fusion 360",
        "exe_match": "fusion360.exe|autodesk fusion",
        "match": "fusion360.exe|autodesk fusion",
        "target_layer": 13,
        "layer": 13,
        "enabled": True
    },
    {
        "id": "autocad",
        "name": "Autodesk AutoCAD",
        "exe_match": "acad.exe|autocad",
        "match": "acad.exe|autocad",
        "target_layer": 5,
        "layer": 5,
        "enabled": True
    },
    {
        "id": "photoshop",
        "name": "Adobe Photoshop",
        "exe_match": "photoshop.exe|photoshop",
        "match": "photoshop.exe|photoshop",
        "target_layer": 14,
        "layer": 14,
        "enabled": True
    },
    {
        "id": "discord",
        "name": "Discord",
        "exe_match": "discord.exe",
        "match": "discord.exe",
        "target_layer": 2,
        "layer": 2,
        "enabled": True
    }
]


def _normalize_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm = []
    for r in rules:
        m = (r.get("exe_match") or r.get("match") or "").strip()
        tl = int(r.get("target_layer") or r.get("layer") or 1)
        norm.append({
            **r,
            "exe_match": m,
            "match": m,
            "target_layer": tl,
            "layer": tl,
            "enabled": r.get("enabled", True) is not False
        })
    return norm


class LayerManager:
    def __init__(self, store_path: str = STORE_PATH):
        self.store_path = store_path
        self.icons_library = get_compiled_icons_library()
        self.layers: Dict[str, Any] = {}
        self.app_rules: List[Dict[str, Any]] = []
        self.auto_app_mode: bool = False
        self.untracked_behavior: str = "stay"  # "stay" or "fallback"
        self.fallback_layer: int = 1
        self.top_modifiers: Dict[str, str] = {
            "1": "SHIFT",
            "2": "CTRL",
            "3": "ALT",
            "4": "ORBIT_CLUTCH"
        }
        self.load()

    def load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    loaded_layers = data.get("layers", {})
                    updated = False
                    for k, v in DEFAULT_LAYERS.items():
                        if k not in loaded_layers:
                            loaded_layers[k] = v
                            updated = True
                        elif k == "13" and loaded_layers[k].get("cells") and "radial_slices" not in loaded_layers[k]["cells"][0]:
                            loaded_layers[k] = v
                            updated = True
                        elif k == "2" and loaded_layers[k].get("cells") and loaded_layers[k]["cells"][3].get("label") == "ACT 4":
                            loaded_layers[k] = v
                            updated = True
                    self.layers = loaded_layers
                    custom_icons = data.get("custom_icons", {})
                    self.icons_library.update(custom_icons)
                    raw_rules = data.get("app_rules") or data.get("rules") or list(DEFAULT_APP_RULES)
                    if not raw_rules:
                        raw_rules = list(DEFAULT_APP_RULES)
                        updated = True
                    for r in raw_rules:
                        if r.get("id") == "discord" and r.get("enabled") is False:
                            r["enabled"] = True
                            updated = True
                    self.app_rules = _normalize_rules(raw_rules)
                    self.auto_app_mode = data.get("auto_app_mode", False)
                    self.untracked_behavior = data.get("untracked_behavior", "stay")
                    self.fallback_layer = int(data.get("fallback_layer", 1))
                    if "top_modifiers" in data and isinstance(data["top_modifiers"], dict):
                        self.top_modifiers.update(data["top_modifiers"])
                    if updated:
                        self.save()
                    return
            except Exception as e:
                print(f"[LayerManager] Error loading store: {e}. Falling back to defaults.")
        self.layers = dict(DEFAULT_LAYERS)
        self.app_rules = _normalize_rules(list(DEFAULT_APP_RULES))
        self.save()

    def save(self):
        """Atomic save: write to a .tmp file then os.replace() to prevent
        data corruption on power failure (never leaves a truncated file)."""
        try:
            self.app_rules = _normalize_rules(self.app_rules)
            custom_icons = {k: v for k, v in self.icons_library.items()
                           if v.get("custom", False)}
            data = {
                "layers": self.layers,
                "custom_icons": custom_icons,
                "app_rules": self.app_rules,
                "auto_app_mode": self.auto_app_mode,
                "untracked_behavior": self.untracked_behavior,
                "fallback_layer": self.fallback_layer,
                "top_modifiers": self.top_modifiers
            }
            tmp_path = self.store_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force flush to storage before rename
            os.replace(tmp_path, self.store_path)  # Atomic on POSIX & Windows
        except Exception as e:
            print(f"[LayerManager] Error saving store: {e}")

    def get_all_layers(self) -> Dict[str, Any]:
        return self.layers

    def get_layer(self, layer_id: int) -> Optional[Dict[str, Any]]:
        return self.layers.get(str(layer_id))

    def save_layer(self, layer_id: int, layer_data: Dict[str, Any]):
        layer_data["id"] = layer_id
        if "bank" not in layer_data:
            layer_data["bank"] = ((layer_id - 1) // 4) + 1
        if "slot" not in layer_data:
            layer_data["slot"] = ((layer_id - 1) % 4) + 1
        self.layers[str(layer_id)] = layer_data
        self.save()

    def delete_layer(self, layer_id: int) -> bool:
        k = str(layer_id)
        if k in self.layers:
            del self.layers[k]
            self.save()
            return True
        return False

    def get_app_rules_config(self) -> Dict[str, Any]:
        self.app_rules = _normalize_rules(self.app_rules)
        return {
            "auto_app_mode": self.auto_app_mode,
            "untracked_behavior": self.untracked_behavior,
            "fallback_layer": self.fallback_layer,
            "top_modifiers": self.top_modifiers,
            "rules": self.app_rules,
            "app_rules": self.app_rules
        }

    def save_app_rules_config(self, cfg: Dict[str, Any]):
        if "auto_app_mode" in cfg:
            self.auto_app_mode = bool(cfg["auto_app_mode"])
        if "untracked_behavior" in cfg:
            self.untracked_behavior = str(cfg["untracked_behavior"])
        if "fallback_layer" in cfg:
            self.fallback_layer = int(cfg["fallback_layer"])
        if "top_modifiers" in cfg and isinstance(cfg["top_modifiers"], dict):
            self.top_modifiers.update(cfg["top_modifiers"])
        if "rules" in cfg and isinstance(cfg["rules"], list):
            self.app_rules = _normalize_rules(cfg["rules"])
        elif "app_rules" in cfg and isinstance(cfg["app_rules"], list):
            self.app_rules = _normalize_rules(cfg["app_rules"])
        self.save()

    def match_app_rule(self, exe_name: str, win_title: str = "") -> Optional[Dict[str, Any]]:
        if not exe_name and not win_title:
            return None
        exe_l = (exe_name or "").lower()
        title_l = (win_title or "").lower()
        for rule in self.app_rules:
            if rule.get("enabled") is False:
                continue
            raw_pat = (rule.get("exe_match") or rule.get("match") or "").strip().lower()
            for pat in [p.strip() for p in raw_pat.replace(",", "|").split("|") if p.strip()]:
                if pat in exe_l or pat in title_l:
                    return rule
        return None

    def add_custom_icon(self, name: str, w: int, h: int, hex_str: str):
        self.icons_library[name] = {
            "name": name,
            "w": w,
            "h": h,
            "hex": hex_str,
            "custom": True
        }
        self.save()

    def get_icons(self) -> Dict[str, Any]:
        return self.icons_library

    def compute_hold_mask(self, layer_id: int) -> int:
        layer = self.get_layer(layer_id)
        if not layer:
            return 0
        mask = 0
        for c in layer.get("cells", []):
            idx = c.get("index", 1) - 1
            if 0 <= idx < 9:
                has_hold = bool(c.get("hold_enabled")) or bool(c.get("radial_slices")) or str(c.get("action", "")).startswith("radial:")
                if has_hold:
                    mask |= (1 << idx)
        return mask

    def build_mqtt_payload(self, layer_id: int, fast: bool = False) -> Dict[str, Any]:
        """Builds MQTT payload for macropad/display for the requested layer."""
        layer = self.get_layer(layer_id)
        if not layer:
            return {}

        cells = layer.get("cells", [])
        labels = [""] * 9
        icons = [""] * 9

        for c in cells:
            idx = c.get("index", 1) - 1
            if 0 <= idx < 9:
                labels[idx] = c.get("label", "")
                icon_key = c.get("icon", "")
                if icon_key in self.icons_library:
                    icons[idx] = self.icons_library[icon_key]["hex"]
                elif len(icon_key) > 10:  # Direct hex string
                    icons[idx] = icon_key
                else:
                    icons[idx] = ""

        return {
            "labels": labels,
            "icons": icons,
            "icon_w": 24,
            "icon_h": 24,
            "layer": layer_id,
            "hold_mask": self.compute_hold_mask(layer_id),
            "auto_app_mode": self.auto_app_mode,
            "fast": fast
        }

layer_manager = LayerManager()
