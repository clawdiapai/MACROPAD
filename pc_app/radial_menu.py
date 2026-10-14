"""
3Dconnexion-Style On-Screen Radial Pie Menu for MacroPad PC Bridge.
Spawns a sleek, anti-aliased dark-mode radial menu centered at the mouse cursor
when a MacroPad key is held down (macro_hold), supporting both:
  1. Hold -> Flick Mouse -> Release MacroPad Key (gesture selection)
  2. Hold & Release in Center -> Click a Slice with Mouse (click selection)
"""

import ctypes
import math
import queue
import threading
import time
import tkinter as tk
from typing import Callable, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageTk

# Menu geometry (logical pixels)
MENU_SIZE = 380
CENTER = MENU_SIZE // 2
INNER_RADIUS = 46
OUTER_RADIUS = 148
LABEL_RADIUS = 100
TRANSPARENT_KEY = "#010203"
TRANSPARENT_RGB = (1, 2, 3)

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def ensure_default_desktop():
    try:
        hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            ctypes.windll.user32.SetThreadDesktop(hdesk)
            ctypes.windll.user32.CloseDesktop(hdesk)
    except Exception:
        pass

def get_cursor_pos() -> Tuple[int, int]:
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

class RadialMenuOverlay:
    def __init__(self, on_select_callback: Callable[[str, str], None]):
        """
        on_select_callback(action_type, action_value) is invoked on a worker thread
        when the user selects a slice.
        """
        self.on_select_callback = on_select_callback
        self.cmd_queue: "queue.Queue[Tuple[str, object]]" = queue.Queue()
        self.is_visible = False
        self.center_screen_x = 0
        self.center_screen_y = 0
        self.title = ""
        self.items: List[Dict[str, str]] = []
        self.hovered_index: int = -1
        self.target_hwnd: Optional[int] = None
        self.sticky_click_mode = False

        self._thread = threading.Thread(target=self._run_tk_loop, daemon=True)
        self._thread.start()

    def show_menu(self, title: str, items: List[Dict[str, str]]):
        """Shows the radial menu centered at the current mouse cursor."""
        ensure_default_desktop()
        fg = ctypes.windll.user32.GetForegroundWindow()
        self.cmd_queue.put(("show", (title, items, fg)))

    def release_hold(self):
        """Called when the user releases the held MacroPad key."""
        self.cmd_queue.put(("release", None))

    def close_menu(self):
        """Immediately hides the radial menu without selecting anything."""
        self.cmd_queue.put(("close", None))

    def _load_fonts(self, scale: int = 2):
        try:
            self.font_label = ImageFont.truetype("segoeui.ttf", 12 * scale)
            self.font_label_bold = ImageFont.truetype("segoeuib.ttf", 13 * scale)
            self.font_center = ImageFont.truetype("segoeuib.ttf", 12 * scale)
            self.font_sub = ImageFont.truetype("segoeui.ttf", 10 * scale)
        except Exception:
            self.font_label = ImageFont.load_default()
            self.font_label_bold = ImageFont.load_default()
            self.font_center = ImageFont.load_default()
            self.font_sub = ImageFont.load_default()

    def _run_tk_loop(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg=TRANSPARENT_KEY)
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT_KEY)
        except Exception:
            pass

        self.canvas = tk.Canvas(
            self.root,
            width=MENU_SIZE,
            height=MENU_SIZE,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Mouse click bindings for sticky click mode
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", lambda e: self._hide())
        self.root.bind("<Escape>", lambda e: self._hide())

        self._load_fonts(scale=2)
        self._tk_img = None
        self._last_rendered_hover = -999

        self.root.after(16, self._tick)
        self.root.mainloop()

    def _compute_hovered_slice(self, dx: float, dy: float) -> int:
        dist = math.hypot(dx, dy)
        if dist < INNER_RADIUS or not self.items:
            return -1
        n = len(self.items)
        # Angle where 0 deg is North (Up, dy < 0), increasing clockwise (0..360)
        angle_deg = (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0
        sector_span = 360.0 / n
        # Offset by half sector so Slice 0 is centered directly at North (0 deg)
        shifted = (angle_deg + (sector_span / 2.0)) % 360.0
        idx = int(shifted // sector_span) % n
        return idx

    def _render_menu(self):
        """Renders the radial menu with 2x supersampling for crisp anti-aliased edges."""
        scale = 2
        S = MENU_SIZE * scale
        C = CENTER * scale
        R_IN = INNER_RADIUS * scale
        R_OUT = OUTER_RADIUS * scale
        R_LBL = LABEL_RADIUS * scale

        img = Image.new("RGB", (S, S), TRANSPARENT_RGB)
        draw = ImageDraw.Draw(img)

        n = len(self.items)
        if n == 0:
            return

        sector_span = 360.0 / n
        gap_deg = 2.5

        # Outer subtle shadow ring
        bbox_outer = [C - R_OUT - 4 * scale, C - R_OUT - 4 * scale, C + R_OUT + 4 * scale, C + R_OUT + 4 * scale]
        draw.ellipse(bbox_outer, fill=(8, 12, 18), outline=(0, 180, 220), width=1 * scale)

        bbox_pie = [C - R_OUT, C - R_OUT, C + R_OUT, C + R_OUT]

        for i, item in enumerate(self.items):
            # Pillow pieslice angles: 0 is 3 o'clock (East), clockwise.
            # North (0 deg in our system) is -90 deg (270 deg) in Pillow.
            center_angle_cw_from_north = i * sector_span
            pil_center_angle = center_angle_cw_from_north - 90.0
            start_ang = pil_center_angle - (sector_span / 2.0) + (gap_deg / 2.0)
            end_ang = pil_center_angle + (sector_span / 2.0) - (gap_deg / 2.0)

            is_hovered = (i == self.hovered_index)
            fill_col = (0, 150, 195) if is_hovered else (20, 28, 42)
            outline_col = (0, 245, 255) if is_hovered else (45, 62, 88)
            width_px = 3 * scale if is_hovered else 2 * scale

            draw.pieslice(bbox_pie, start=start_ang, end=end_ang, fill=fill_col, outline=outline_col, width=width_px)

        # Punch out the inner deadzone circle
        bbox_inner = [C - R_IN, C - R_IN, C + R_IN, C + R_IN]
        center_fill = (12, 17, 26)
        center_border = (0, 240, 255) if self.hovered_index >= 0 else (70, 95, 130)
        draw.ellipse(bbox_inner, fill=center_fill, outline=center_border, width=2 * scale)

        # Draw labels for each slice
        for i, item in enumerate(self.items):
            center_angle_rad = math.radians(i * sector_span)
            lx = C + math.sin(center_angle_rad) * R_LBL
            ly = C - math.cos(center_angle_rad) * R_LBL

            label_text = item.get("label", "")
            is_hovered = (i == self.hovered_index)
            text_col = (255, 255, 255) if is_hovered else (205, 220, 240)
            font = self.font_label_bold if is_hovered else self.font_label

            # Support 2-line labels if separated by \n or space on longer strings
            lines = label_text.split("\n")
            total_h = len(lines) * (14 * scale)
            start_y = ly - total_h / 2.0
            for line_idx, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                draw.text(
                    (lx - tw / 2.0, start_y + line_idx * (15 * scale)),
                    line,
                    fill=text_col,
                    font=font
                )

        # Draw center hub title & active selection hint
        hub_title = self.title.upper()
        bbox_t = draw.textbbox((0, 0), hub_title, font=self.font_center)
        tw_t = bbox_t[2] - bbox_t[0]
        draw.text((C - tw_t / 2.0, C - 14 * scale), hub_title, fill=(0, 240, 255), font=self.font_center)

        sub_txt = "CLICK" if self.sticky_click_mode else ("RELEASE" if self.hovered_index >= 0 else "CANCEL")
        sub_col = (0, 255, 160) if self.hovered_index >= 0 else (130, 150, 175)
        bbox_s = draw.textbbox((0, 0), sub_txt, font=self.font_sub)
        tw_s = bbox_s[2] - bbox_s[0]
        draw.text((C - tw_s / 2.0, C + 3 * scale), sub_txt, fill=sub_col, font=self.font_sub)

        # Downsample with NEAREST so transparent key color pixels stay exact, while interior looks crisp
        # Wait: to get anti-aliased interior AND exact transparent key on outside, create mask!
        final_img = img.resize((MENU_SIZE, MENU_SIZE), Image.Resampling.BILINEAR)
        # Restore exact TRANSPARENT_RGB outside the outer circle so Windows transparentcolor has zero halo
        mask_img = Image.new("L", (MENU_SIZE, MENU_SIZE), 0)
        mask_draw = ImageDraw.Draw(mask_img)
        r_clip = OUTER_RADIUS + 4
        mask_draw.ellipse([CENTER - r_clip, CENTER - r_clip, CENTER + r_clip, CENTER + r_clip], fill=255)

        bg_img = Image.new("RGB", (MENU_SIZE, MENU_SIZE), TRANSPARENT_RGB)
        composited = Image.composite(final_img, bg_img, mask_img)

        self._tk_img = ImageTk.PhotoImage(composited)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

    def _show(self, title: str, items: List[Dict[str, str]], target_hwnd: Optional[int] = None):
        # Capture the currently active CAD window before showing overlay
        self.target_hwnd = target_hwnd or ctypes.windll.user32.GetForegroundWindow()
        cx, cy = get_cursor_pos()
        self.center_screen_x = cx
        self.center_screen_y = cy
        self.title = title
        self.items = items
        self.hovered_index = -1
        self.sticky_click_mode = False
        self._last_rendered_hover = -999

        win_x = cx - CENTER
        win_y = cy - CENTER
        self.root.geometry(f"{MENU_SIZE}x{MENU_SIZE}+{win_x}+{win_y}")
        self._render_menu()
        self.root.deiconify()
        self.root.lift()
        self.is_visible = True

    def _hide(self):
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False
            self.hovered_index = -1
            self.sticky_click_mode = False
            # Restore focus to the CAD window if needed without altering maximized state
            if self.target_hwnd:
                try:
                    if ctypes.windll.user32.IsIconic(self.target_hwnd):
                        ctypes.windll.user32.ShowWindow(self.target_hwnd, 9)  # SW_RESTORE only if minimized
                    else:
                        ctypes.windll.user32.ShowWindow(self.target_hwnd, 5)  # SW_SHOW preserves maximized
                    ctypes.windll.user32.SetForegroundWindow(self.target_hwnd)
                except Exception:
                    pass

    def _trigger_selected_item(self, idx: int):
        if 0 <= idx < len(self.items):
            chosen = self.items[idx]
            act_type = chosen.get("type", "search")
            act_val = chosen.get("val", "")
            act_lbl = chosen.get("label", "").replace("\n", " ")
            fb_type = chosen.get("fb_type", "")
            fb_val = chosen.get("fb_val", "")
            target_hwnd = self.target_hwnd
            self._hide()
            threading.Thread(
                target=self.on_select_callback,
                args=(act_type, act_val, act_lbl, fb_type, fb_val, target_hwnd),
                daemon=True
            ).start()
        else:
            self._hide()

    def _on_left_click(self, event):
        if not self.is_visible:
            return
        dx = event.x - CENTER
        dy = event.y - CENTER
        idx = self._compute_hovered_slice(dx, dy)
        if idx >= 0:
            self._trigger_selected_item(idx)
        else:
            # Clicked inside center deadzone -> cancel/close
            self._hide()

    def _tick(self):
        try:
            while True:
                cmd, arg = self.cmd_queue.get_nowait()
                if cmd == "show":
                    if isinstance(arg, tuple) and len(arg) == 3:
                        title, items, fg = arg
                    else:
                        title, items, fg = arg[0], arg[1], None
                    self._show(title, items, fg)
                elif cmd == "release":
                    if self.is_visible:
                        if self.hovered_index >= 0:
                            # User flicked cursor onto a slice while holding -> execute immediately on release!
                            self._trigger_selected_item(self.hovered_index)
                        else:
                            # User released while cursor is still in center -> keep menu open for click selection!
                            self.sticky_click_mode = True
                            self._render_menu()
                elif cmd == "close":
                    self._hide()
        except queue.Empty:
            pass

        if self.is_visible:
            cx, cy = get_cursor_pos()
            dx = cx - self.center_screen_x
            dy = cy - self.center_screen_y
            # If cursor moved way outside the menu (> 240px), close if in sticky mode
            if self.sticky_click_mode and math.hypot(dx, dy) > 230:
                self._hide()
            else:
                new_hover = self._compute_hovered_slice(dx, dy)
                if new_hover != self.hovered_index:
                    self.hovered_index = new_hover
                    self._render_menu()

        self.root.after(16, self._tick)
