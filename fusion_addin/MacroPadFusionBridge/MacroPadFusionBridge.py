"""
MacroPadFusionBridge — Native Autodesk Fusion 360 Add-In for ESP32 E-Ink MacroPad.
Executes any Fusion 360 command, sketch tool, 3D feature, or camera orientation
natively on Fusion's main UI thread in <2ms via UDP (127.0.0.1:36042),
completely eliminating keyboard simulation and the 'S' search popup.
"""

import adsk.core
import adsk.fusion
import json
import socket
import threading
import traceback

CUSTOM_EVENT_ID = "MacroPadFusionCmdEvent_v1"
UDP_HOST = "127.0.0.1"
UDP_PORT = 36042

_app: adsk.core.Application = None
_ui: adsk.core.UserInterface = None
_custom_event: adsk.core.CustomEvent = None
_handlers = []
_stop_flag = False
_udp_sock: socket.socket = None
_name_to_id_cache = {}

# Prioritized candidate commandDefinition IDs and exact UI names for common CAD tools
COMMAND_CANDIDATES = {
    # Sketch Lifecycle
    "create_sketch": ["SketchCreate", "Create Sketch"],
    "finish_sketch": ["FinishSketch", "FinishSketchCommand", "Finish Sketch"],
    # 2D Sketch Primitives
    "line": ["Line"],
    "rect_2pt": ["TwoPointRectangle", "2-Point Rectangle"],
    "rect_3pt": ["ThreePointRectangle", "3-Point Rectangle"],
    "rect_center": ["CenterRectangle", "Center Rectangle"],
    "circle_center": ["CircleCenterRadius", "Center Diameter Circle"],
    "circle_2pt": ["CircleTwoPoint", "2-Point Circle"],
    "circle_3pt": ["CircleThreePoint", "3-Point Circle"],
    "circle_tan": ["CircleTwoTangent", "2-Tangent Circle"],
    "arc_3pt": ["ArcThreePoint", "Arc3Point", "3-Point Arc"],
    "arc_center": ["ArcCenterPoint", "Center Point Arc"],
    "arc_tan": ["ArcTangent", "Tangent Arc"],
    "poly_circum": ["PolygonCircumscribed", "Circumscribed Polygon"],
    "poly_inscr": ["PolygonInscribed", "Inscribed Polygon"],
    "poly_edge": ["PolygonEdge", "Edge Polygon"],
    "spline_fit": ["SplineFitPoint", "Fit Point Spline"],
    "spline_ctrl": ["SplineControlPoint", "Control Point Spline"],
    "slot_center": ["SlotCenterToCenter", "Center to Center Slot"],
    "project": ["ProjectGeometry", "SketchProject", "Project"],
    "construction": ["NormalConstructionCommand", "SketchConstruction", "Construction"],
    # 2D Sketch Edit & Constraints
    "dimension": ["SketchDimension", "Sketch Dimension"],
    "offset": ["SketchOffset", "Offset"],
    "trim": ["SketchTrim", "Trim"],
    "extend": ["SketchExtend", "Extend"],
    "sketch_fillet": ["SketchFillet", "Fillet"],
    "sketch_mirror": ["SketchMirror", "Mirror"],
    "coincident": ["GeometricConstraintCoincident", "Coincident"],
    "collinear": ["GeometricConstraintCollinear", "Collinear"],
    "tangent": ["GeometricConstraintTangent", "Tangent"],
    "midpoint": ["GeometricConstraintMidPoint", "MidPoint"],
    "equal": ["GeometricConstraintEqual", "Equal"],
    "parallel": ["GeometricConstraintParallel", "Parallel"],
    "perpendicular": ["GeometricConstraintPerpendicular", "Perpendicular"],
    "horiz_vert": ["GeometricConstraintHorizontalVertical", "Horizontal/Vertical"],
    # 3D Solid Create
    "extrude": ["Extrude"],
    "revolve": ["Revolve"],
    "sweep": ["Sweep"],
    "loft": ["Loft"],
    "hole": ["Hole"],
    "thread": ["Thread"],
    "rib": ["Rib"],
    "web": ["Web"],
    "emboss": ["Emboss"],
    "press_pull": ["PressPull", "Press Pull"],
    # 3D Modify
    "fillet": ["FilletRule", "Fillet"],
    "chamfer": ["ChamferEdge", "Chamfer"],
    "shell": ["Shell"],
    "draft": ["Draft"],
    "scale": ["ScaleCommand", "Scale"],
    "combine": ["Combine"],
    "split_body": ["SplitBody", "Split Body"],
    "split_face": ["SplitFace", "Split Face"],
    "move": ["Move", "Move/Copy"],
    "align": ["AlignComponents", "Align"],
    "delete": ["DeleteCommand", "Delete"],
    # Pattern & Mirror
    "rect_pattern": ["RectangularPattern", "Rectangular Pattern"],
    "circ_pattern": ["CircularPattern", "Circular Pattern"],
    "path_pattern": ["PathPattern", "Pattern on Path"],
    "mirror": ["MirrorCommand", "Mirror"],
    # Construction Planes & Assembly
    "offset_plane": ["WorkPlaneOffsetCommand", "OffsetPlane", "Offset Plane"],
    "midplane": ["WorkPlaneMidplaneCommand", "Midplane"],
    "angle_plane": ["WorkPlaneAngleCommand", "Plane at Angle"],
    "joint": ["Joint"],
    "as_built_joint": ["AsBuiltJoint", "As-Built Joint"],
    "rigid_group": ["RigidGroup", "Rigid Group"],
    "new_component": ["NewComponent", "New Component"],
    # Inspect, Parameters & Export
    "measure": ["MeasureCommand", "Measure"],
    "section_analysis": ["SectionAnalysisCommand", "SectionAnalysis", "Section Analysis"],
    "parameters": ["ChangeParameterCommand", "Change Parameters"],
    "appearance": ["MaterialCommand", "Appearance"],
    "show_hide": ["VisibilityToggleCmd", "Show/Hide"],
    "3d_print": ["ThreeDPrint", "3DPrintCommand", "3D Print"],
    "export": ["ExportCommand", "Export"],
    "text": ["SketchText", "Text"],
}


def _build_command_cache():
    """Indexes all Fusion 360 commandDefinitions by lowercase name and ID for O(1) lookup."""
    global _name_to_id_cache
    if _name_to_id_cache or not _ui:
        return
    try:
        defs = _ui.commandDefinitions
        for i in range(defs.count):
            try:
                d = defs.item(i)
                if d and d.id:
                    _name_to_id_cache[d.id.lower()] = d.id
                    if d.name:
                        clean_name = d.name.strip().lower()
                        # Keep first match or exact match
                        if clean_name not in _name_to_id_cache:
                            _name_to_id_cache[clean_name] = d.id
            except Exception:
                pass
    except Exception:
        pass


def _is_sketch_active() -> bool:
    try:
        if _app and _app.activeEditObject:
            return _app.activeEditObject.objectType == adsk.fusion.Sketch.classType()
    except Exception:
        pass
    return False


def _resolve_command_def(key_or_name: str) -> adsk.core.CommandDefinition:
    if not _ui or not key_or_name:
        return None

    _build_command_cache()
    defs = _ui.commandDefinitions
    norm = key_or_name.strip().lower()

    # Context-aware Sketch vs 3D disambiguation
    in_sketch = _is_sketch_active()
    if in_sketch and norm in ("fillet", "filletrule"):
        norm = "sketch_fillet"
    elif in_sketch and norm in ("mirror", "mirrorcommand"):
        norm = "sketch_mirror"

    candidates = COMMAND_CANDIDATES.get(norm, [key_or_name])
    for cand in candidates:
        # 1. Direct itemById check
        cmd_def = defs.itemById(cand)
        if cmd_def:
            return cmd_def
        # 2. Case-insensitive ID or Name cache check
        cached_id = _name_to_id_cache.get(cand.strip().lower())
        if cached_id:
            cmd_def = defs.itemById(cached_id)
            if cmd_def:
                return cmd_def

    # 3. Direct lookup of input string in cache
    cached_id = _name_to_id_cache.get(norm)
    if cached_id:
        cmd_def = defs.itemById(cached_id)
        if cmd_def:
            return cmd_def

    # 4. Substring match on command names if not found
    for k, cid in _name_to_id_cache.items():
        if norm in k:
            cmd_def = defs.itemById(cid)
            if cmd_def:
                return cmd_def

    return None


def _set_standard_view(orientation: str):
    """Sets the active viewport camera to Top, Front, Right, Left, or Isometric and fits view."""
    try:
        vp = _app.activeViewport
        if not vp:
            return
        if orientation == "home":
            vp.goHome(True)
            return
        if orientation == "fit":
            vp.fit()
            return

        cam = vp.camera
        target = cam.target
        dist = target.distanceTo(cam.eye)
        if dist <= 0.001:
            dist = 100.0

        # Fusion 360 default Z-up or Y-up handling: set eye relative to target
        if orientation == "top":
            cam.eye = adsk.core.Point3D.create(target.x, target.y, target.z + dist)
            cam.upVector = adsk.core.Vector3D.create(0, 1, 0)
        elif orientation == "front":
            cam.eye = adsk.core.Point3D.create(target.x, target.y - dist, target.z)
            cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
        elif orientation == "right":
            cam.eye = adsk.core.Point3D.create(target.x + dist, target.y, target.z)
            cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
        elif orientation == "left":
            cam.eye = adsk.core.Point3D.create(target.x - dist, target.y, target.z)
            cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
        elif orientation == "iso":
            d = dist / (3.0 ** 0.5)
            cam.eye = adsk.core.Point3D.create(target.x + d, target.y - d, target.z + d)
            cam.upVector = adsk.core.Vector3D.create(0, 0, 1)

        cam.isSmoothTransition = True
        vp.camera = cam
        vp.fit()
    except Exception:
        pass


class MacroPadCommandEventHandler(adsk.core.CustomEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CustomEventArgs):
        try:
            payload = json.loads(args.additionalInfo)
            action = payload.get("action", "command")
            target = payload.get("target", "")
            cancel_first = payload.get("cancel_first", True)

            if action == "cancel":
                if _ui:
                    _ui.terminateActiveCommand()
                return

            if action == "view":
                _set_standard_view(target.lower())
                return

            if action == "finish_sketch" or target.lower() in ("finish_sketch", "finish sketch"):
                cmd_def = _resolve_command_def("finish_sketch")
                if cmd_def:
                    cmd_def.execute()
                return

            if cancel_first and _ui:
                try:
                    if _ui.activeCommand != "SelectCommand":
                        _ui.terminateActiveCommand()
                except Exception:
                    pass

            cmd_def = _resolve_command_def(target)
            if cmd_def:
                cmd_def.execute()
        except Exception:
            pass


def _udp_listener():
    global _udp_sock
    _udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _udp_sock.bind((UDP_HOST, UDP_PORT))
    _udp_sock.settimeout(0.5)

    while not _stop_flag:
        try:
            data, addr = _udp_sock.recvfrom(4096)
            msg_str = data.decode("utf-8", errors="ignore").strip()
            if not msg_str:
                continue
            # Immediately acknowledge so PC Bridge knows Add-In is live
            try:
                _udp_sock.sendto(b'{"status":"ok"}', addr)
            except Exception:
                pass
            if _app:
                _app.fireCustomEvent(CUSTOM_EVENT_ID, msg_str)
        except socket.timeout:
            continue
        except Exception:
            if _stop_flag:
                break


def run(context):
    global _app, _ui, _custom_event, _stop_flag
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        _stop_flag = False

        try:
            _app.unregisterCustomEvent(CUSTOM_EVENT_ID)
        except Exception:
            pass

        _custom_event = _app.registerCustomEvent(CUSTOM_EVENT_ID)
        on_cmd = MacroPadCommandEventHandler()
        _custom_event.add(on_cmd)
        _handlers.append(on_cmd)

        t = threading.Thread(target=_udp_listener, daemon=True)
        t.start()
    except Exception:
        if _ui:
            _ui.messageBox("MacroPadFusionBridge failed to start:\n{}".format(traceback.format_exc()))


def stop(context):
    global _stop_flag, _udp_sock, _custom_event
    try:
        _stop_flag = True
        if _udp_sock:
            try:
                _udp_sock.close()
            except Exception:
                pass
            _udp_sock = None
        if _custom_event and _app:
            _app.unregisterCustomEvent(CUSTOM_EVENT_ID)
            _custom_event = None
        _handlers.clear()
    except Exception:
        pass
