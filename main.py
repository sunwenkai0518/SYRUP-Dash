
import pygame
import pygame.freetype
import numpy as np
import ctypes
import math
import os
import sys
import json
import io
import base64
import zlib
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional, Callable
from collections import OrderedDict
import time


_WIN_CAPTION = "\u7cd6\u6d46 / SYRUP"


def _win_hwnd() -> int:
    if sys.platform != "win32":
        return 0
    try:
        info = pygame.display.get_wm_info()
        if isinstance(info, dict):
            for k, v in info.items():
                if v and ("wnd" in str(k).lower() or "window" in str(k).lower()):
                    try:
                        iv = int(v)
                    except Exception:
                        continue
                    if iv > 0:
                        return iv
    except Exception:
        pass
    try:
        u = _win_user32()
        u.FindWindowW.restype = ctypes.c_void_p
        u.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        h = u.FindWindowW(None, _WIN_CAPTION)
        if h:
            return int(h)
        u.GetForegroundWindow.restype = ctypes.c_void_p
        h = u.GetForegroundWindow()
        if h:
            return int(h)
    except Exception:
        pass
    return 0


class _RECT_T(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


_WIN_U = None


def _win_user32():
    global _WIN_U
    if _WIN_U is not None:
        return _WIN_U
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    try:
        u.SetWindowLongPtrW.restype = ctypes.c_longlong
        u.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                        ctypes.c_longlong]
        u.GetWindowLongPtrW.restype = ctypes.c_longlong
        u.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    except Exception:
        pass
    try:
        u.SetWindowLongW.restype = ctypes.c_long
        u.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                     ctypes.c_long]
        u.GetWindowLongW.restype = ctypes.c_long
        u.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    except Exception:
        pass
    try:
        u.SetWindowPos.restype = ctypes.c_int
        u.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int,
                                   ctypes.c_uint]
        u.GetWindowRect.restype = ctypes.c_int
        u.GetWindowRect.argtypes = [ctypes.c_void_p,
                                    ctypes.POINTER(wintypes.RECT)]
        u.MonitorFromWindow.restype = ctypes.c_void_p
        u.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        u.GetMonitorInfoW.restype = ctypes.c_int
        u.ShowWindow.restype = ctypes.c_int
        u.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        u.IsIconic.restype = ctypes.c_int
        u.IsIconic.argtypes = [ctypes.c_void_p]
        u.GetSystemMetrics.restype = ctypes.c_int
        u.GetSystemMetrics.argtypes = [ctypes.c_int]
        u.GetMonitorInfoW.argtypes = [ctypes.c_void_p,
                                      ctypes.POINTER(_MONITORINFO)]
        u.AdjustWindowRectEx.restype = ctypes.c_int
        u.AdjustWindowRectEx.argtypes = [ctypes.POINTER(_RECT_T),
                                         ctypes.c_uint, ctypes.c_int,
                                         ctypes.c_uint]
        u.SystemParametersInfoW.restype = ctypes.c_int
        u.SystemParametersInfoW.argtypes = [ctypes.c_uint, ctypes.c_uint,
                                            ctypes.c_void_p, ctypes.c_uint]
        u.IsZoomed.restype = ctypes.c_int
        u.IsZoomed.argtypes = [ctypes.c_void_p]
    except Exception:
        pass
    _WIN_U = u
    return u


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("rcMonitor", _RECT_T),
                ("rcWork", _RECT_T), ("dwFlags", ctypes.c_uint32)]


def _win_work_rect(hwnd: int) -> Tuple[int, int, int, int]:
    try:
        if sys.platform == "win32":
            import ctypes
            u = _win_user32()
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            hmon = u.MonitorFromWindow(ctypes.c_void_p(int(hwnd)), 2) if hwnd else 0
            if not hmon:
                hmon = u.MonitorFromWindow(ctypes.c_void_p(0), 1)
            if hmon and u.GetMonitorInfoW(ctypes.c_void_p(int(hmon)),
                                          ctypes.byref(mi)):
                r = mi.rcWork
                return (int(r.left), int(r.top),
                        int(r.right - r.left), int(r.bottom - r.top))
            r = _RECT_T()
            if u.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0):
                return (int(r.left), int(r.top),
                        int(r.right - r.left), int(r.bottom - r.top))
            return (0, 0, int(u.GetSystemMetrics(0)), int(u.GetSystemMetrics(1)))
    except Exception:
        pass
    return (0, 0, 0, 0)


def _win_frame_size(hwnd: int, cw: int, ch: int) -> Tuple[int, int]:
    try:
        if sys.platform == "win32" and hwnd:
            import ctypes
            u = _win_user32()
            st = _win_get_style(hwnd, -16)
            ex = _win_get_style(hwnd, -20)
            r = _RECT_T()
            r.left = 0
            r.top = 0
            r.right = int(cw)
            r.bottom = int(ch)
            if u.AdjustWindowRectEx(ctypes.byref(r), int(st) & 0xFFFFFFFF,
                                    0, int(ex) & 0xFFFFFFFF):
                return (int(r.right - r.left), int(r.bottom - r.top))
    except Exception:
        pass
    return (int(cw), int(ch))


def _win_get_style(hwnd: int, idx: int) -> int:
    u = _win_user32()
    try:
        return int(u.GetWindowLongPtrW(int(hwnd), int(idx))) & 0xFFFFFFFF
    except Exception:
        return int(u.GetWindowLongW(int(hwnd), int(idx))) & 0xFFFFFFFF


def _win_set_style(hwnd: int, idx: int, val: int) -> None:
    u = _win_user32()
    v = int(val) & 0xFFFFFFFF
    if v >= 0x80000000:
        v -= 0x100000000
    try:
        u.SetWindowLongPtrW(int(hwnd), int(idx), int(v))
        return
    except Exception:
        pass
    u.SetWindowLongW(int(hwnd), int(idx), int(v))


def _win_monitor_rect(hwnd: int) -> Tuple[int, int, int, int]:
    try:
        if sys.platform == "win32":
            import ctypes
            u = _win_user32()
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            hmon = u.MonitorFromWindow(ctypes.c_void_p(int(hwnd)), 2) if hwnd else 0
            if not hmon:
                hmon = u.MonitorFromWindow(ctypes.c_void_p(0), 1)
            if hmon and u.GetMonitorInfoW(ctypes.c_void_p(int(hmon)),
                                          ctypes.byref(mi)):
                r = mi.rcMonitor
                return (int(r.left), int(r.top),
                        int(r.right - r.left), int(r.bottom - r.top))
            return (0, 0, int(u.GetSystemMetrics(0)), int(u.GetSystemMetrics(1)))
    except Exception:
        pass
    return (0, 0, 0, 0)


def _win_set_borderless(hwnd: int, on: bool) -> None:
    if sys.platform != "win32" or not hwnd:
        return
    try:
        GWL_STYLE = -16
        GWL_EXSTYLE = -20
        WS_POPUP = 0x80000000
        WS_VISIBLE = 0x10000000
        WS_CAPTION = 0x00C00000
        WS_THICKFRAME = 0x00040000
        WS_SYSMENU = 0x00080000
        WS_MINIMIZEBOX = 0x00020000
        WS_MAXIMIZEBOX = 0x00010000
        WS_EX_TOPMOST = 0x00000008
        WS_EX_WINDOWEDGE = 0x00000100
        WS_EX_DLGMODALFRAME = 0x00000001
        st = _win_get_style(hwnd, GWL_STYLE)
        ex = _win_get_style(hwnd, GWL_EXSTYLE)
        if on:
            st &= ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU
                    | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
            st |= (WS_POPUP | WS_VISIBLE)
            ex &= ~(WS_EX_WINDOWEDGE | WS_EX_DLGMODALFRAME)
            ex |= WS_EX_TOPMOST
        else:
            st &= ~WS_POPUP
            st |= (WS_CAPTION | WS_THICKFRAME | WS_SYSMENU
                   | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_VISIBLE)
            ex &= ~WS_EX_TOPMOST
            ex |= WS_EX_WINDOWEDGE
        _win_set_style(hwnd, GWL_STYLE, st)
        _win_set_style(hwnd, GWL_EXSTYLE, ex)
    except Exception:
        pass


def _win_place(hwnd: int, x: int, y: int, w: int, h: int,
               topmost: bool) -> None:
    if sys.platform != "win32" or not hwnd:
        return
    import ctypes
    u = _win_user32()
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW = 0x0040
    SWP_NOACTIVATE = 0x0010
    try:
        if u.IsIconic(ctypes.c_void_p(int(hwnd))):
            u.ShowWindow(ctypes.c_void_p(int(hwnd)), 9)
    except Exception:
        pass
    u.SetWindowPos(ctypes.c_void_p(int(hwnd)),
                   ctypes.c_void_p(-1 if topmost else -2),
                   int(x), int(y), int(w), int(h),
                   SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_NOACTIVATE)


def _win_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    try:
        if sys.platform == "win32" and hwnd:
            import ctypes
            from ctypes import wintypes
            u = _win_user32()
            r = wintypes.RECT()
            if u.GetWindowRect(ctypes.c_void_p(int(hwnd)), ctypes.byref(r)):
                return (int(r.left), int(r.top),
                        int(r.right - r.left), int(r.bottom - r.top))
    except Exception:
        pass
    return (0, 0, 0, 0)


def _force_window_full(dw: float, dh: float) -> bool:
    if sys.platform != "win32":
        return False
    try:
        hwnd = _win_hwnd()
        if not hwnd:
            return False
        _win_set_borderless(hwnd, True)
        x, y, w, h = _win_monitor_rect(hwnd)
        if w <= 1 or h <= 1:
            w, h = int(dw), int(dh)
        _win_place(hwnd, x, y, int(w), int(h), True)
        rx, ry, rw, rh = _win_window_rect(hwnd)
        return (rw > 1 and rh > 1
                and abs(rw - w) <= max(2, int(w * 0.01))
                and abs(rh - h) <= max(2, int(h * 0.01)))
    except Exception:
        return False


def _restore_windowed(hwnd: int = 0, want_w: int = 0,
                      want_h: int = 0) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = _win_user32()
        if not hwnd:
            hwnd = _win_hwnd()
        if not hwnd:
            return
        _win_set_borderless(hwnd, False)
        try:
            if u.IsZoomed(ctypes.c_void_p(int(hwnd))):
                u.ShowWindow(ctypes.c_void_p(int(hwnd)), 9)
        except Exception:
            pass
        if want_w > 0 and want_h > 0:
            w, h = _win_frame_size(hwnd, int(want_w), int(want_h))
        else:
            _ox, _oy, w, h = _win_window_rect(hwnd)
            if w <= 1 or h <= 1:
                w, h = 640, 480
        w, h = int(w), int(h)
        wx, wy, ww, wh = _win_work_rect(hwnd)
        ox, oy, ow, oh = _win_window_rect(hwnd)
        if ww > 1 and wh > 1:
            w = min(w, int(ww))
            h = min(h, int(wh))
            cx = ox + ow // 2
            nx = min(max(cx - w // 2, wx), wx + max(0, int(ww) - w))
            ny = min(max(wy + (int(wh) - h) // 3, wy), wy + max(0, int(wh) - h))
        else:
            nx = max(ox, 0)
            ny = max(oy, 0)
        _win_place(hwnd, int(nx), int(ny), w, h, False)
        rx, ry, rw, rh = _win_window_rect(hwnd)
        if rw > 1 and rh > 1:
            if ww > 1 and wh > 1:
                bad = (rx < wx or ry < wy
                       or rx + rw > wx + ww or ry + rh > wy + wh)
                tx = min(max(rx, wx), wx + max(0, int(ww) - rw))
                ty = min(max(ry, wy), wy + max(0, int(wh) - rh))
            else:
                bad = (rx < 0 or ry < 0)
                tx, ty = max(rx, 0), max(ry, 0)
            if bad:
                _win_place(hwnd, int(tx), int(ty), int(rw), int(rh), False)
    except Exception:
        pass


def _set_sdl_env() -> None:
    try:
        os.environ["SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS"] = "0"
        os.environ["SDL_ALLOW_TOPMOST"] = "1"
        os.environ["SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR"] = "0"
        os.environ.pop("SDL_VIDEO_CENTERED", None)
    except Exception:
        pass

def _enable_dpi_awareness() -> None:
    try:
        if sys.platform == "win32":
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                return
            except Exception:
                pass
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    except Exception:
        pass

try:
    _SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    _SCRIPT_DIR = Path.cwd()


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", "")) if _is_frozen() else _SCRIPT_DIR
    if not base:
        base = _SCRIPT_DIR
    return Path(base) / rel


def _exe_dir() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return _SCRIPT_DIR


def _user_data_dir() -> Path:
    app = "SYRUP"
    try:
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            if not base:
                base = os.environ.get("APPDATA")
            if base:
                return Path(base) / app
            return Path.home() / "AppData" / "Local" / app
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / app
        xdg = os.environ.get("XDG_DATA_HOME")
        return Path(xdg) if xdg else (Path.home() / ".local" / "share" / app)
    except Exception:
        return _exe_dir()


def _resolve_save_path() -> str:
    fname = "syrup_save.json"
    portable = _exe_dir() / fname
    try:
        ud = _user_data_dir()
        ud.mkdir(parents=True, exist_ok=True)
        target = ud / fname
        if (not target.exists()) and portable.exists() and portable != target:
            try:
                target.write_bytes(portable.read_bytes())
                portable.rename(portable.with_suffix(portable.suffix + ".migrated"))
            except Exception:
                pass
        return str(target)
    except Exception:
        return str(portable)


def vlen(v) -> float:
    a = float(v[0]); b = float(v[1])
    return math.sqrt(a * a + b * b)


def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3

def ease_out_back(t: float) -> float:
    s = 1.70158
    return 1.0 + (s + 1.0) * (t - 1.0) ** 3 + s * (t - 1.0) ** 2

def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def breath_wave(phase: float, dwell: float = 0.0, mode: str = "triangle") -> float:
    p = phase % 1.0
    if mode == "sine":
        return math.sin(p * 2.0 * math.pi)
    if mode == "trapezoid":
        e = ANIM_TRAPEZOID_E
        t = (p * 2.0) % 1.0
        prog = _trapezoid_progress(t, e)
        return 1.0 - 2.0 * prog if p < 0.5 else -1.0 + 2.0 * prog
    if mode != "dwell":
        p2 = p * 2.0
        return 1.0 - 2.0 * p2 if p2 < 1.0 else (p2 - 1.0) * 2.0 - 1.0
    d = max(0.0, min(0.90, dwell)) * 0.5
    m = 0.5 - d
    if m <= 1e-6:
        return math.sin(p * 2.0 * math.pi)
    if p < d:
        return 1.0
    if p < d + m:
        t = (p - d) / m
        return 1.0 - 2.0 * (t * t * (3.0 - 2.0 * t))
    if p < 2.0 * d + m:
        return -1.0
    t = (p - (2.0 * d + m)) / m
    return -1.0 + 2.0 * (t * t * (3.0 - 2.0 * t))


ANIM_TRAPEZOID_E = 0.15


def _trapezoid_progress(t: float, e: float) -> float:
    if e <= 1e-6:
        return t
    e = min(0.45, e)
    v = (1.0 - e) / (1.0 - 2.0 * e)
    if t < e:
        u = t / e
        return 0.5 * e * (u * u * (3.0 - 2.0 * u))
    if t < 1.0 - e:
        return 0.5 * e + v * (t - e)
    u = (t - (1.0 - e)) / e
    return 1.0 - 0.5 * e * (1.0 - (u * u * (3.0 - 2.0 * u)))


class ValueTween:
    __slots__ = ("value", "from_value", "target", "duration", "ease", "t", "done")

    def __init__(self, init: float = 0.0,
                 duration: float = 0.22,
                 ease: Callable[[float], float] = ease_out_cubic) -> None:
        self.value = float(init)
        self.from_value = float(init)
        self.target = float(init)
        self.duration = max(1e-4, float(duration))
        self.ease = ease
        self.t = self.duration
        self.done = True

    def set_target(self, new_target: float,
                   duration: Optional[float] = None,
                   ease: Optional[Callable[[float], float]] = None) -> None:
        if abs(new_target - self.target) < 1e-9 and not self.done:
            return
        self.from_value = self.value
        self.target = float(new_target)
        if duration is not None:
            self.duration = max(1e-4, float(duration))
        if ease is not None:
            self.ease = ease
        self.t = 0.0
        self.done = False

    def update(self, dt: float) -> float:
        if self.done:
            return self.value
        self.t += dt
        if self.t >= self.duration:
            self.t = self.duration
            self.value = self.target
            self.done = True
        else:
            k = self.t / self.duration
            self.value = self.from_value + (self.target - self.from_value) * self.ease(k)
        return self.value

    def snap(self, v: float) -> None:
        self.value = self.from_value = self.target = float(v)
        self.t = self.duration
        self.done = True


SAVE_DEFAULTS: Dict[str, Any] = {
    "version": 1,
    "lang": "en",
    "training_unlocked_stage": 1,
    "training_done": False,
    "best_score": 0,
    "best_chain": 0,
    "best_wave": 0,
    "best_time": 0.0,
    "total_detonate": 0,
    "total_perfect": 0,
    "total_kill": 0,
    "total_runs": 0,
    "body_size": 18,
    "text_size": 0,
    "render_scale": 1.0,
    "render_auto": True,
    "stage_rank": [None, None, None, None, None],
    "milestones": [],
    "ms_on": [],
    "skin": 0,
    "fx_trail": 0,
    "fx_afterimage": True,
    "fx_energy_glow": False,
    "fx_detonate_self": False,
    "fx_swap_ghost": False,
    "fx_poem": True,
}


def load_save(path_str: str, version: int) -> dict:
    p = Path(path_str)
    if not p.exists():
        return dict(SAVE_DEFAULTS)
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or int(data.get("version", -1)) != version:
            raise ValueError("version mismatch")
        merged = dict(SAVE_DEFAULTS)
        for k in SAVE_DEFAULTS:
            if k in data:
                merged[k] = data[k]
        merged["version"] = version
        if not merged.get("_rank1_gift"):
            try:
                lst = merged.get("stage_rank")
                if not isinstance(lst, list) or len(lst) < 5:
                    lst = [None] * 5
                order = {"S": 4, "A": 3, "B": 2, "C": 1}
                if order.get(str(lst[0]), 0) < 4:
                    lst[0] = "S"
                merged["stage_rank"] = lst
                merged["_rank1_gift"] = 1
            except Exception:
                pass
        return merged
    except Exception:
        try:
            backup = p.with_suffix(p.suffix + ".corrupt")
            if backup.exists():
                backup.unlink()
            p.rename(backup)
        except Exception:
            pass
        return dict(SAVE_DEFAULTS)


def save_now(path_str: str, data: dict) -> None:
    try:
        p = Path(path_str)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(p)
    except Exception:
        pass


CONFIG: Dict[str, Any] = {
    "WIDTH": 1280, "HEIGHT": 720, "FPS": 60,
    "BASE_WIDTH": 1280, "BASE_HEIGHT": 720,

    "START_FULLSCREEN":   False,
    "WINDOW_SCALE":       3.0,
    "WINDOW_SCREEN_FIT":  0.9,
    "RESIZE_SETTLE_FRAMES": 10,
    "FULLSCREEN_BORDERLESS": True,
    "RENDER_MAX_SCALE":   3.0,
    "ADAPTIVE_VIEWPORT":  True,
    "VIEWPORT_BASE_H":    720,
    "VIEWPORT_W_MIN":     1120,
    "VIEWPORT_W_MAX":     2560,
    "FORCE_RENDER_SIZE":  [0, 0],
    "VIGNETTE_MERGE_SCALE": 2.5,
    "RENDER_SCALE_PRESET": 1.0,
    "RENDER_SCALE_LEVELS": [0.75, 1.0, 1.25, 1.5, 2.0],
    "RS_NARROW_W":         1200,
    "RENDER_MIN_SCALE":    0.5,
    "RENDER_SCALE_AUTO":   True,
    "RENDER_SCALE_BUDGET": 13.0,
    "RENDER_SCALE_HOLD":   2.0,
    "RENDER_SCALE_UP":     0.45,
    "RENDER_SCALE_PEN":    25.0,
    "RENDER_SCALE_PEN_MAX": 240.0,
    "SET_ARROW_W":        24,
    "SET_ARROW_GAP":      11,
    "SET_ARROW_INSET":    8,
    "SET_VALUE_W":        0.50,
    "SET_VALUE_MAX":      340,
    "SET_PAD":            24,
    "SET_HIT_PAD":        7,
    "SSAA_MAX_PIXELS":    12_000_000,
    "AA_ENABLE":          True,
    "AA_MIN_R":           2.5,
    "AA_GFX_R":           5.0,
    "AA_EDGE_A":          0.34,
    "AA_ARC_A":           0.40,
    "SPHERE_AMB":         0.36,
    "SPHERE_DIF":         0.84,
    "SPHERE_SPEC":        0.80,
    "SPHERE_RIM":         0.26,
    "BG_GLOW_A":          70,
    "BG_GLOW_EXPO":       2.6,
    "BG_GLOW_LIFT":       30,

    "SAVE_PATH": _resolve_save_path(),
    "SAVE_VERSION": 1,
    "FONT_PATH": "",

    "TOPGOAL_FADE": 0.5,

    "LOGO_SS": 4,
    "LOGO_BEZ_SEGMENTS": 32,
    "GLOW_ENABLE_PLAYER":  False,
    "GLOW_ENABLE_THREAT":  False,
    "GLOW_ENABLE_SPITTER": False,

    "AURA_AMB_CUT":      0.62,
    "GLOW_SIZE_P":       76, "GLOW_PEAK_P": 118, "GLOW_RING_AT_P": 0.36,
    "GLOW_RING_W_P":     0.22, "GLOW_TAIL_P": 10,
    "GLOW_SIZE_T":       68, "GLOW_PEAK_T": 132, "GLOW_RING_AT_T": 0.26,
    "GLOW_RING_W_T":     0.19, "GLOW_TAIL_T": 8,
    "GLOW_SIZE_S":       64, "GLOW_PEAK_S": 104, "GLOW_RING_AT_S": 0.30,
    "GLOW_RING_W_S":     0.20, "GLOW_TAIL_S": 8,
    "LOGO_SHADOW_SIZE":    7.5,
    "LOGO_SHADOW_ROT":   -15.0,
    "LOGO_SHADOW_ALPHA":   95,
    "LOGO_SHADOW_FILL":    22,
    "SUBPIX_STEPS": 4,

    "LOGO_ANIM_HZ":          0.16,
    "ANIM_MENU_BREATH_HZ":   0.14,
    "ANIM_MENU_SWEEP_HZ":    0.15,
    "ANIM_STUN_PULSE_HZ":    1.20,
    "ANIM_STUN_STAR_HZ":     1.10,
    "ANIM_TRAP_ROT_HZ":      0.55,

    "ANIM_LOGO_BREATH_AMP":  10.0,
    "ANIM_MENU_BREATH_AMP":  7.0,

    "ANIM_WAVE": "trapezoid",
    "ANIM_DWELL":   0.0,

    "UI_TWEEN_FAST":   0.12,
    "UI_TWEEN_NORMAL": 0.22,
    "UI_TWEEN_SLOW":   0.35,
    "UI_HOVER_DWELL":      0.042,
    "UI_HOVER_DWELL_MOVE": 0.085,
    "UI_HOVER_V_SLOW":     45.0,
    "UI_HOVER_V_FAST":     620.0,
    "UI_EXP_TWEEN":        0.15,

    "SHOW_FPS": False,
    "DEBUG_ANIM": False,

    "SHAKE_MAX_OFFSET": 16.0,
    "SHAKE_DECAY": 1.8,
    "SHAKE_MAX_TRAUMA": 1.0,

    "HITSTOP_DETONATE": 4,
    "HITSTOP_PERFECT": 8,
    "HITSTOP_CANCEL": 2,

    "DEATH_SLOWMO_DURATION": 0.35,
    "DEATH_SLOWMO_SCALE": 0.30,

    "RUN_LIVES":             3,
    "RESPAWN_IFRAMES":       90,
    "RESPAWN_CLEAR_RADIUS":  240.0,
    "RESPAWN_SLOWMO":        0.30,
    "RESPAWN_HITSTOP":       10,

    "TRANSITION_DURATION": 0.25,

    "FONT_BODY_STD": 18,
    "FONT_BODY_LARGE": 21,
    "TEXT_SIZE_SCALES": [1.0, 1.18],
    "FONT_HEAD": 24,
    "FONT_MENU": 26,
    "MENU_ROW_GAP":  8,
    "MENU_ARROW_W":      19,
    "MENU_ARROW_GAP":    10,
    "MENU_ARROW_PAD":    18,
    "MENU_ARROW_HIT_PAD": 7,
    "APPR_ARROW_W":      20,
    "APPR_ARROW_GAP":    10,
    "APPR_ARROW_PAD":    24,
    "APPR_ARROW_HIT_PAD": 7,
    "MENU_ROW_Y0":   266,
    "MENU_ROW_W":    520,
    "MENU_ROW_W_MAXF": 0.52,
    "MENU_BLOCK_ORIGIN": 49,
    "MENU_BOTTOM_RESERVE": 60,
    "MENU_BLOCK_TOP_MIN": 20,
    "MENU_LOGO_Y":    104,
    "MENU_LOGO_SCALE": 0.94,
    "MENU_TITLE_Y":   168,
    "MENU_TAG_Y":     220,
    "MENU_DIV_Y":     248,
    "MENU_TAG_TRACK_CJK":   4,
    "MENU_TAG_MAX_RATIO":   0.74,
    "MENU_TAG_TRACK_LATIN": ((1, 5), (0, 5), (0, 3), (0, 1), (0, 0)),
    "MENU_TAG_SIZE":      16,
    "BODY_LINE_H": 28,
    "BODY_PARA_GAP": 14,

    "BG":          (11, 15, 20),
    "GRID":        (20, 24, 31),
    "GRID_STEP":   96,
    "VIGNETTE":    (7, 10, 14),
    "VIGNETTE_REACH": 1.45,
    "VIGNETTE_PEAK":  170,
    "VIGNETTE_EXPO":  2.2,
    "C_PLAYER":    (34, 211, 238),
    "C_THREAT":    (255, 107, 74),
    "C_SPITTER":   (196, 186, 108),
    "C_MARK":      (255, 255, 255),
    "G_20":        (25, 30, 38),
    "G_40":        (55, 65, 80),
    "G_60":        (100, 112, 130),
    "G_80":        (165, 175, 190),
    "SLIME_COLOR": (30, 75, 92),
    "DOT_FALL":          1.90,
    "DOT_EDGE_A":        0.50,

    "SKINS": [
        {"name": "糖浆", "en": "SYRUP",   "color": (34, 211, 238),  "trail": "syrup",
         "tlen": 26, "twidth": 6.0, "talpha": 150, "tfade": 1.25, "ai": "shrink", "ai_n": 5, "ai_life": 0.30,
         "body": "drip", "req": None},
        {"name": "水银", "en": "MERCURY", "color": (204, 206, 222), "trail": "mercury",
         "mdark": 0.30, "mcore": 0.74, "mhot": 0.46, "mspec": 0.92, "mstreak": 0.44,
         "tlen": 20, "twidth": 6.4, "talpha": 236, "tfade": 1.15, "ai": "bead",   "ai_n": 3, "ai_life": 0.12,
         "body": "spec", "req": ("train", 0)},
        {"name": "气泡", "en": "BUBBLE",  "color": (168, 230, 214), "trail": "bubble",
         "bubble_h0": 0.022, "bubble_film": 0.075, "bubble_arc": 0.55,
         "tlen": 19, "twidth": 5.0, "talpha": 140, "tfade": 1.5, "ai": "grow",   "ai_n": 5, "ai_life": 0.32,
         "body": "film", "req": ("score", 5000)},
        {"name": "油",   "en": "OIL",     "color": (178, 138, 255), "trail": "oil", "hue": True,
         "spread": 0.55, "film_pale": 0.05, "hue_span": 1.00, "sheen": 1.50, "sheen_step": 3.2,
         "film_dark": (26, 24, 46), "film_base_a": 0.55,
         "film_drift": 0.34, "film_silver": 0.08,
         "film_cycles": 2.6, "film_cross": 1.7, "film_cross_hue": 0.55,
         "film_head": 0.34, "film_step": 7.0, "film_grid": 1.0, "film_edge": 0.60,
         "film_sat": 0.80,
         "tlen": 18, "twidth": 7.0, "talpha": 165, "tfade": 1.35, "ai": "iris",   "ai_n": 4, "ai_life": 0.22,
         "body": "iris", "req": ("score", 10000)},
        {"name": "墨",   "en": "INK",     "color": (206, 222, 252), "trail": "ink",
         "ink": (12, 12, 14), "indigo": (228, 228, 232), "gold": (255, 214, 122),
         "ink_white": (250, 250, 253),
         "ink_gexp": 0.80, "ink_gfloor": 0.28, "ink_bodywarm": 0.00,
         "ink_bwflat": 0.78, "ink_deco": 0.74,
         "ink_rim_a": 0.26, "ink_rim_b": 0.58,
         "ink_cboost": 1.5, "ink_gspow": 2.0,
         "ink_gvein": 1.20, "ink_gw": 0.30, "ink_gflow": 6.2,
         "ink_gvein2": 0.62, "ink_gw2": 0.20, "ink_gflow2": 4.3,
         "ink_gspd": 2.35,
         "poem_col": (252, 226, 168), "poem_a": 235, "poem_bleed": 0.34,
         "tlen": 34, "twidth": 6.1, "talpha": 255, "tfade": 0.82, "ai": "poem", "ai_n": 6, "ai_life": 0.44,
         "body": "poem", "top": True, "poem": True, "req": ("score", 20000)},
    ],
    "SKIN_UNLOCK_ALL": False,
    "POEM_SS": 6,
    "POEM_BLUR": 3,
    "POEM_HALO": 0.38,
    "POEM_SHARP": 1.0,
    "POEM_POST": 1,
    "POEM_FS": 22,
    "POEM_SOFT_PAD": 4,
    "POEM_FONT_PATH": "syrup_poem.ttf",
    "IRIS_BODY_SCALE": 0.8,
    "PV_W": 60.0,
    "PV_H": 32.0,
    "PV_CX": 28.0,
    "PV_GLYPH_RISE": 8.0,
    "PV_TRAIL": 26.0,
    "PV_TRAIL_W": 0.427,
    "PV_GLYPH": 18.0,
    "PV_GLYPH_LIFE": 1.55,
    "PV_GLYPH_CD": 0.95,
    "PV_GLYPH_A": 225,
    "PV_GLYPH_SCALE": 1.0,
    "QI_CAP": 16,
    "PV_FREEZE_T": 1.7,
    "QI_ALPHA": 178,
    "QI_GROW": 10.5,
    "QI_WD": 2.5,
    "INK_PREVIEW_GLYPHS": ["墨", "极"],
    "POEM_LINES": ["直挂云帆济沧海", "天生我材必有用", "人生得意须尽欢",
                   "莫使金樽空对月", "千金散尽还复来", "飞流直下三千尺",
                   "疑是银河落九天", "大鹏一日同风起", "仰天大笑出门去",
                   "长风破浪会有时"],
    "TRAIL_STYLES": ["材质", "线", "关闭"],
    "TRAIL_STYLES_EN": ["MATERIAL", "LINE", "OFF"],
    "FX_NAMES":    ["材质", "拖尾形态", "冲刺残影", "能量满微光", "引爆自反馈", "换位残留", "诗句浮现"],
    "FX_NAMES_EN": ["MATERIAL", "TRAIL", "AFTERIMAGE", "FULL ENERGY", "DETONATE FX", "SWAP GHOST", "POEM"],


    "PLAYER_SPEED":      300.0,
    "PLAYER_SMOOTH":     6.5,
    "PLAYER_MARGIN":     28,
    "PLAYER_TRAIL_LEN":  16,
    "DEATH_RADIUS":      18.0,

    "DASH_SPEED":         900.0,
    "DASH_FRAMES":        8,
    "DASH_COST":          1.0,
    "DASH_CANCEL_FREE":   True,
    "DASH_CANCEL_FREE_CHAIN": 1,
    "MAX_ENERGY":         3.0,
    "DETONATE_ENERGY_GAIN":  2.0,
    "ENERGY_REGEN":       0.35,
    "TRAINING_ENERGY_REGEN": 0.55,
    "NO_ENERGY_HINT_CD":  30,

    "CANCEL_WINDOW_FRAMES":  6,
    "RECOVERY_FRAMES":       8,
    "RECOVERY_MOVE_SCALE":   0.45,
    "CANCEL_BONUS_MULT":     1.40,
    "CANCEL_IFRAME_FRAMES":  4,
    "INPUT_BUFFER_FRAMES":   5,

    "DASH_PHASE_ON_MARK":    True,
    "PHASE_GRACE_FRAMES":    10,

    "SHADOW_MAX":            2,
    "SHADOW_LIFE_FRAMES":    180,
    "SHADOW_DRIFT_SPEED":    40.0,

    "SWAP_CD_FRAMES":        72,
    "SWAP_EMPTY_CD_FRAMES":  48,
    "SWAP_IMPACT_RADIUS":    90.0,
    "SWAP_TRAP_FRAMES":      72,

    "MARK_LIFE_FRAMES":      180,
    "MARK_HIT_RADIUS":       36.0,
    "DETONATE_RADIUS":       100.0,
    "DETONATE_SLIME_FRAMES": 240,
    "DETONATE_KNOCKBACK":    260.0,
    "DETONATE_STUN_FRAMES":  45,
    "DETONATE_EXEC_FRAMES":  150,

    "PERFECT_THREAT_DIST":   60.0,
    "PERFECT_BULLET_FRAMES": 24,
    "PERFECT_WORLD_SCALE":   0.25,

    "CHAIN_WINDOW_FRAMES":   150,
    "CHAIN_MULTS":           [1.0, 1.5, 2.0, 3.0],

    "DETONATE_BASE_SCORE":   200,
    "PERFECT_SWAP_SCORE":    150,
    "KILL_SCORE":            100,

    "SLIME_PLAYER_SLOW":     0.75,

    "AI_BASE_SPEED":         155.0,
    "AI_SPEED_RAMP":         0.6,
    "AI_MAX_SPEED":          300.0,
    "AI_RADIUS":             8,
    "AI_PREDICT":            0.35,
    "AI_SPAWN_INTERVAL":     14.0,
    "AI_MAX_COUNT":          6,
    "AI_SMOOTH":             3.5,
    "AI_TRAIL_LEN":          12,
    "WARN_TIME":             0.6,

    "SLIME_TRAP_FRAMES":     90,
    "TRAP_SLOW":             0.15,
    "TRAP_KILL_DIST":        32.0,

    "SPITTER_RADIUS":        16,
    "SPITTER_INTERVAL":      3.0,
    "SPITTER_WARN":          0.5,
    "SPITTER_PROJ_SPEED":    230.0,
    "SPITTER_PROJ_R":        6,
    "SPITTER_PROJ_LIFE":     6.0,
    "SPITTER_MAX":           3,
    "SPITTER_INTERVAL_MIN":  2.30,
    "SPITTER_SPEED_MAX":     295.0,
    "SPITTER_PHASE":         [0.35, 1.0],

    "WAVE_TABLE": [
        {"dur": 18.0, "spawn": 6.5, "batch": 1, "max": 3,  "spitter": 0, "spit_interval": 3.20, "spit_speed": 230.0},
        {"dur": 18.0, "spawn": 5.5, "batch": 1, "max": 4,  "spitter": 0, "spit_interval": 3.20, "spit_speed": 230.0},
        {"dur": 20.0, "spawn": 4.8, "batch": 1, "max": 5,  "spitter": 1, "spit_interval": 3.20, "spit_speed": 230.0},
        {"dur": 20.0, "spawn": 4.2, "batch": 2, "max": 6,  "spitter": 1, "spit_interval": 2.90, "spit_speed": 246.0},
        {"dur": 22.0, "spawn": 3.6, "batch": 2, "max": 7,  "spitter": 2, "spit_interval": 2.90, "spit_speed": 246.0},
        {"dur": 22.0, "spawn": 3.3, "batch": 2, "max": 8,  "spitter": 2, "spit_interval": 2.65, "spit_speed": 260.0},
        {"dur": 24.0, "spawn": 3.0, "batch": 2, "max": 9,  "spitter": 3, "spit_interval": 2.65, "spit_speed": 260.0},
        {"dur": 24.0, "spawn": 2.8, "batch": 2, "max": 10, "spitter": 3, "spit_interval": 2.45, "spit_speed": 274.0},
    ],
    "C_SPLIT":            (206, 92, 200),
    "SPLIT_RADIUS":       10.5,
    "SPLIT_SPEED_MUL":    0.80,
    "SPLIT_CHILDREN":     2,
    "SPLIT_FROM_WAVE":    4,
    "SPLIT_CHANCE":       0.32,
    "SPLIT_BURST_SPEED":  235.0,
    "SPLIT_STUN_FRAMES":  11,
    "SPLIT_FLASH_FRAMES": 10,
    "SPLIT_MIN_DIST":     108.0,
    "SPLIT_SPREAD_VAR":   0.55,
    "SPLIT_SPREAD_JIT":   0.30,
    "WAVE_EVENT_CYCLE":   4,
    "WAVE_EVENT_FROM":    5,
    "ELITE_SPEED_MUL":    1.18,
    "ELITE_SCORE_MUL":    1.5,
    "SAFE_SPAWN_MUL":     2.2,
    "SAFE_MAX_MUL":       0.5,
    "STAGE_PAR":          [14.0, 16.0, 18.0, 22.0, 26.0],
    "MILESTONES": [
        ("total_kill",      100, "猎手",     "HUNTER",     "kill_hud",
         "HUD 常显击杀数 · 击杀回能 +8%",     "Kill counter in HUD · kill refund +8%", 1, 3),
        ("total_kill",      500, "清场",     "SWEEPER",    "kill_bonus",
         "击杀得分 +18%",                     "Kill score +18%", 3, 9),
        ("total_detonate",   60, "引爆者",   "DETONATOR",  "det_ring",
         "常显引爆范围环 · 引爆范围 +6%",     "Radius ring always on · radius +6%", 1, 3),
        ("total_detonate",  300, "连环",     "CHAINER",    "det_bonus",
         "一次引爆 3 个以上，每多一个 +22 分", "+22 per target beyond the second", 3, 9),
        ("total_perfect",    40, "完美主义", "FLAWLESS",   "perfect_range",
         "完美换位判定距离 +18",              "Perfect swap range +18", 2, 6),
        ("best_chain",        8, "八连锁",   "CHAIN x8",   "chain_bonus",
         "连锁倍率上限提升至 ×3.5",           "Chain multiplier cap raised to x3.5", 4, 12),
        ("best_wave",        12, "深入腹地", "DEEP RUN",   "extra_life",
         "每局开局多一条命",                  "One extra life at run start", 5, 15),
        ("best_wave",        20, "远征",     "EXPEDITION", "swap_cd",
         "换位冷却 -20%",                     "Swap cooldown -20%", 5, 15),
        ("total_runs",       30, "常客",     "REGULAR",    "regen",
         "能量再生速度 +12%",                 "Energy regen +12%", 4, 12),
    ],
    "MILESTONE_GROUPS": [
        ("kill",      "猎杀", "HUNTING",    ("total_kill",)),
        ("detonate",  "引爆", "DETONATION", ("total_detonate",)),
        ("technique", "技巧", "TECHNIQUE",  ("total_perfect", "best_chain")),
        ("endurance", "深入", "ENDURANCE",  ("best_wave",)),
        ("devotion",  "常驻", "DEVOTION",   ("total_runs",)),
    ],
    "MS_KILL_BONUS":    0.18,
    "MS_KILL_ENERGY":   1.08,
    "MS_DET_BONUS":     22,
    "MS_DET_BONUS_MIN": 3,
    "MS_DET_RADIUS_MUL": 1.06,
    "MS_PERFECT_ADD":   18.0,
    "MS_CHAIN_EXTRA":   3.5,
    "MS_EXTRA_LIVES":   1,
    "MS_SWAP_CD_MUL":   0.80,
    "MS_REGEN_MUL":     1.12,
    "MS_SCORE_PER_LOAD": 0.03,
    "MS_LOAD_MAX":      0.18,
    "MS_LOAD_SPAWN":    0.992,
    "MS_LOAD_SPEED":    0.008,
    "MS_LOAD_SPIT":     0.992,
    "MS_LOAD_BOLT":     2.0,
    "MS_UNIT_MAX":      0.34,
    "MS_UNIT_SPEED":    0.014,
    "MS_UNIT_SPAWN":    0.008,
    "MS_UNIT_SPIT":     0.010,
    "MS_UNIT_BOLT":     2.6,
    "MS_UNIT_BATCH":    0.34,
    "MS_FOCUS": {
        "kill_hud":      {"max": 1.0},
        "det_ring":      {"spit_interval": 1.0},
        "perfect_range": {"speed": 1.0},
        "det_bonus":     {"max": 0.7, "spit_speed": 0.3},
        "kill_bonus":    {"max": 0.6, "speed": 0.4},
        "chain_bonus":   {"spawn": 1.0},
        "regen":         {"max": 0.6, "spawn": 0.4},
        "swap_cd":       {"speed": 0.7, "spawn": 0.3},
        "extra_life":    {"max": 0.5, "speed": 0.25, "spit_speed": 0.25},
    },
    "MS_HEAD_H":        28,
    "MS_ROW_H":         54,
    "MS_DETAIL_PAD":    7,
    "MS_DETAIL_LH":     15,
    "SET_TIP_PAD":      6,
    "SET_TIP_LH":       15,
    "SET_TIP_KEYS": ["set_tip_fs", "set_tip_rs", "set_tip_shake",
                     "set_tip_ts", "set_tip_auto", "set_tip_lang"],
    "MS_STAT_NAME": {
        "total_kill":     ("累计击杀", "Total kills"),
        "total_detonate": ("累计引爆", "Total detonations"),
        "total_perfect":  ("累计完美换位", "Total perfect swaps"),
        "best_chain":     ("最高连锁", "Best chain"),
        "best_wave":      ("最高波次", "Best wave"),
        "total_runs":     ("累计局数", "Total runs"),
    },
    "MS_FOCUS_DESC": {
        "max":           ("敌人上限提高", "enemy cap up"),
        "speed":         ("敌人移动更快", "enemies move faster"),
        "spawn":         ("生成间隔缩短", "spawn gap shorter"),
        "spit_interval": ("喷浆更频繁", "spitters fire faster"),
        "spit_speed":    ("弹速提高", "projectiles faster"),
        "batch":         ("成组数量增加", "larger batches"),
    },
    "TITLE_GRAD_TOP":   (246, 249, 255),
    "TITLE_GRAD_BOT":   (172, 190, 220),
    "RUN_START_ENEMIES":     2,
    "WAVE_DURATION":         20.0,
    "WAVE_AI_SPEED_ADD":     14.0,

    "TRAINING_HINT_DURATION":  3.0,
    "TRAINING_COMPLETE_HOLD":  1.3,
    "STAGE_NAMES":  ["移动与冲刺", "标记与引爆", "影与换位", "取消后摇", "完美换位"],
    "STAGE_HINTS":  [
        "鼠标移动  ·  空格冲刺  ·  黏液会拖住敌人",
        "冲刺穿过敌人 = 标记  ·  再穿一次 = 引爆回能",
        "冲刺留下影  ·  SHIFT 与最近的影换位",
        "冲刺结束 6 帧内再按冲刺 = 取消后摇",
        "敌人贴近时按 SHIFT = 完美换位",
    ],
    "STAGE_DESCS":  ["活过 15 秒", "引爆 3 次", "换位黏住 2 个敌人", "连续 3 次取消成功", "完美换位 2 次"],
    "STAGE_GOALS":  [15.0, 3, 2, 3, 2],
    "STAGE_ENEMIES": [1, 2, 2, 1, 2],

    "CLEAR_HOLD_FRAMES":  60,
    "CLEAR_HOLD_FRAMES2": 90,
    "TOAST_DURATION": 1.5,

    "MECH_TAB_FADE": 0.15,
    "ESC_ROOT_EXIT_GAP": 26,
}


STAGE_NAMES_EN  = ["Move & Dash", "Mark & Detonate", "Shadow & Swap", "Cancel Recovery", "Perfect Swap"]
STAGE_DESCS_EN  = ["Survive 15 seconds", "Detonate 3 times", "Trap 2 enemies with swap",
                   "Chain 3 cancels in a row", "Perfect swap 2 times"]
MECH_LOCK_RUN = 6
MECH_STAGE_REQ = {
    0: [1, 4, 2, 2, 3, 1, MECH_LOCK_RUN, 5, MECH_LOCK_RUN, 1],
    2: [1, MECH_LOCK_RUN, MECH_LOCK_RUN, 1],
}
CTRL_STAGE_REQ = [1, 1, 3, 1, 1, 1, 2, 1]

STAGE_HINTS_EN  = [
    "Move with mouse  ·  SPACE to dash  ·  slime slows enemies",
    "Dash through an enemy = MARK  ·  dash again = DETONATE (refund energy)",
    "Dash leaves a shadow  ·  SHIFT swaps with nearest shadow",
    "Press dash again within 6 frames after dash = cancel recovery",
    "Press SHIFT when an enemy is close = PERFECT SWAP",
]

STR_ZH = {
    "title": "SYRUP", "tagline": "黏住它们，或者被黏住",
    "training": "训练", "stage": "关卡", "run": "实战",
    "run_locked": "实战 · 未解锁", "unlock_hint": "完成全部训练后解锁",
    "run_hint": "无限模式 · 追分",
    "best_score": "最高分", "best_chain": "最高链", "best_wave": "最高波",
    "menu_hint": "↑↓ 选择  ·  ←→ 切换关卡  ·  ENTER 确认  ·  ESC 菜单  ·  F11 全屏",
    "locked": "未解锁", "paused": "PAUSED",
    "continue": "继续", "restart_run": "重开本局", "restart_stage": "重开本关",
    "back_menu": "回菜单", "exit_run": "退出",
    "controls": "操作", "goal_col": "当前关卡目标", "how_to": "怎么做",
    "progress": "进度", "score": "分数", "chain": "链", "detonate": "引爆",
    "perfect": "完美", "restart": "重开", "menu": "菜单", "seconds": "秒",
    "run_goal": "生存并追分", "max_chain": "最高链", "detonate_count": "引爆",
    "perfect_count": "完美换位", "score_detonate": "引爆分", "score_perfect": "完美分",
    "score_kill": "击杀分",
    "esc_title": "菜单",
    "mech": "游戏机制", "settings": "设置", "quit_game": "退出游戏",
    "close_menu": "关闭菜单",
    "ms_goal": "目标", "ms_gain": "获得", "ms_cost": "代价",
    "clear_save": "清除存档", "clear_gray": "清除存档（按住 C）",
    "clear_page_title": "确认清除存档",
    "clear_desc_1": "以下数据将被永久删除：",
    "clear_desc_2": "再次按住 C 确认",
    "clear_success": "存档已清除",
    "fullscreen_title": "全屏",
    "fs_on": "开", "fs_off": "关",
    "shake_title": "震屏强度",
    "shake_0": "关", "shake_5": "弱", "shake_10": "强",
    "render_scale_title": "渲染倍率",
    "rs_names": ["省电", "原生", "增强", "高清", "极致"],
    "rs_heavy": "高负载", "rs_mid": "偏高", "rs_capped": "已受限",
    "rs_auto": "自适应",
    "rs_target": "目标", "rs_actual": "实际",
    "rs_target_s": "目标", "rs_actual_s": "实际",
    "auto_title": "自适应画质", "auto_on": "开", "auto_off": "关",
    "text_size_title": "文字大小",
    "text_size_std": "标准", "text_size_large": "大",
    "lang_title": "语言",
    "lang_zh": "中文", "lang_en": "English",
    "back": "返回",
    "mech_lock": "未解锁",
    "mech_lock_stage": "完成训练第 {n} 关后解锁",
    "mech_lock_run": "完成全部训练后解锁",
    "mech_tabs": ["基础规则", "操作说明", "失败条件"],
    "k_move": "鼠标移动", "k_move_d": "瞄准 / 决定冲刺方向",
    "k_lmb": "鼠标左键", "k_lmb_d": "冲刺", "k_space_d": "冲刺",
    "k_shift_d": "与最近的影换位", "k_r_d": "重开", "k_esc_d": "菜单 / 暂停",
    "k_tab_d": "练习模式", "k_escm": "ESC（菜单）", "k_escm_d": "保存并退出",
    "k_f11_d": "全屏 / 窗口（也可用 Alt+Enter）",
    "k_p_d": "暂停面板",
    "ctrl_hint": "鼠标移至条目查看说明",
    "ctrl_rows": [
        ("鼠标移动", "瞄准", "决定冲刺方向。玩家始终以鼠标所在方位为准，移动与冲刺均沿该方向进行。"),
        ("鼠标左键 / 空格", "冲刺", "沿鼠标方向高速位移一段距离，消耗一格能量。路径经过敌人时为其附加标记。"),
        ("Shift", "换位", "瞬移至距鼠标最近的一枚影所在位置，起点与终点各产生一次范围冲击。"),
        ("R", "重开", "立即重新开始当前关卡或当前一局，进度不计入存档。"),
        ("ESC", "菜单", "打开或关闭暂停菜单。菜单中可查看机制、调整设置并退出游戏。"),
        ("F11", "全屏", "在全屏与窗口之间切换，效果与 Alt+Enter 相同。"),
        ("Tab", "练习", "在训练关卡内开启练习模式，敌人不再主动追击，便于反复演练操作。"),
        ("P", "暂停", "暂停当前关卡或当前一局，再次按下即可继续。"),
    ],
    "appearance": "外观",
    "appr_hint": "左右键切换  ·  回车进入材质图鉴  ·  每项独立生效  ·  即时保存",
    "appr_sub": "材质决定颜色与拖尾形态",
    "appr_sub2": "可单独开关的特效",
    "on": "开", "off": "关",
    "skin_gallery": "材质图鉴",
    "skin_gallery_sub": "选中已解锁的材质即可使用",
    "skin_gallery_hint": "↑↓ 选择  ·  回车或点击装备  ·  ESC 返回",
    "skin_in_use": "使用中",
    "skin_default": "初始解锁",
    "skin_req_score": "最高分达到 {n} 解锁",
    "skin_req_train": "完成全部训练后解锁",
    "skin_locked": "未解锁",
    "milestones": "里程碑",
    "ms_sub": "达成后解锁一项能力 · 开启会同时加重难度",
    "ms_hint": "↑↓ 滚动  ·  ←→ 或点击开关  ·  ESC 返回",
    "ms_unlock": "解锁",
    "ms_unlocked": "已解锁",
    "set_tip_fs": "开启后窗口铺满整块屏幕并盖住任务栏；关闭时是带标题栏的窗口，可以拖动。",
    "set_tip_rs": "画布相对窗口的采样倍率。原生为一比一，最快也最清楚；往上为超采样，更锐利但明显更吃性能。",
    "set_tip_shake": "受击与引爆时的画面震动强度，只影响观感，不改判定。",
    "set_tip_ts": "界面文字的字号倍率。展示类大标题不跟着一起放大。",
    "set_tip_auto": "开启后按实测帧耗时自动升降采样倍率，最低只降到原生档，不会越降越糊。",
    "set_tip_lang": "界面语言。中文需要内置或系统的中文字体支持。",
    "ms_kills": "击杀",
}
STR_EN = {
    "title": "SYRUP", "tagline": "trap 'em or be trapped",
    "training": "TRAINING", "stage": "STAGE", "run": "RUN",
    "run_locked": "RUN · LOCKED", "unlock_hint": "Complete all training to unlock",
    "run_hint": "Endless · chase the score",
    "best_score": "BEST", "best_chain": "CHAIN", "best_wave": "WAVE",
    "menu_hint": "↑↓ select  ·  ←→ change stage  ·  ENTER confirm  ·  ESC menu  ·  F11 fullscreen",
    "locked": "LOCKED", "paused": "PAUSED",
    "continue": "CONTINUE", "restart_run": "RESTART", "restart_stage": "RESTART STAGE",
    "back_menu": "MENU", "exit_run": "EXIT",
    "controls": "CONTROLS", "goal_col": "CURRENT GOAL", "how_to": "HOW TO",
    "progress": "Progress", "score": "SCORE", "chain": "CHAIN", "detonate": "DETONATE",
    "perfect": "PERFECT", "restart": "Restart", "menu": "Menu", "seconds": "s",
    "run_goal": "survive & score", "max_chain": "Max Chain", "detonate_count": "Detonate",
    "perfect_count": "Perfect Swap", "score_detonate": "Detonate pts", "score_perfect": "Perfect pts",
    "score_kill": "Kill pts",
    "esc_title": "MENU",
    "mech": "MECHANICS", "settings": "SETTINGS", "quit_game": "QUIT",
    "close_menu": "CLOSE MENU",
    "ms_goal": "GOAL", "ms_gain": "GAIN", "ms_cost": "COST",
    "clear_save": "CLEAR SAVE", "clear_gray": "CLEAR SAVE (hold C)",
    "clear_page_title": "CONFIRM CLEAR",
    "clear_desc_1": "The following will be permanently deleted:",
    "clear_desc_2": "Hold C again to confirm",
    "clear_success": "Save cleared",
    "fullscreen_title": "Fullscreen",
    "fs_on": "ON", "fs_off": "OFF",
    "shake_title": "Screen shake",
    "shake_0": "Off", "shake_5": "Low", "shake_10": "High",
    "render_scale_title": "Render scale",
    "rs_names": ["Low", "Native", "Sharp", "High", "Ultra"],
    "rs_heavy": "heavy", "rs_mid": "high", "rs_capped": "capped",
    "rs_auto": "AUTO",
    "rs_target": "Target", "rs_actual": "Actual",
    "rs_target_s": "Tgt", "rs_actual_s": "Act",
    "auto_title": "Adaptive", "auto_on": "ON", "auto_off": "OFF",
    "text_size_title": "Text size",
    "text_size_std": "Standard", "text_size_large": "Large",
    "lang_title": "Language",
    "lang_zh": "中文", "lang_en": "English",
    "back": "Back",
    "mech_lock": "LOCKED",
    "mech_lock_stage": "Unlocks after Training Stage {n}",
    "mech_lock_run": "Unlocks after all training stages",
    "mech_tabs": ["Basics", "Controls", "Fails"],
    "k_move": "Mouse", "k_move_d": "Aim / decide dash direction",
    "k_lmb": "LMB", "k_lmb_d": "Dash", "k_space_d": "Dash",
    "k_shift_d": "Swap with nearest shadow", "k_r_d": "Restart", "k_esc_d": "Menu / Pause",
    "k_tab_d": "Practice mode", "k_escm": "ESC (menu)", "k_escm_d": "Save and quit",
    "k_f11_d": "Fullscreen / window (or Alt+Enter)",
    "k_p_d": "Pause panel",
    "ctrl_hint": "Hover an entry to read its description",
    "ctrl_rows": [
        ("Mouse move", "Aim", "Sets the dash direction. The player moves and dashes toward the cursor at all times."),
        ("LMB / Space", "Dash", "Displaces the player rapidly toward the cursor, costing one energy unit. Enemies along the path become marked."),
        ("Shift", "Swap", "Teleports the player to the shadow nearest the cursor. Both endpoints release a shock that traps nearby enemies."),
        ("R", "Restart", "Restarts the current stage or run immediately. Progress from the attempt is discarded."),
        ("ESC", "Menu", "Opens or closes the pause menu, where rules, settings and quitting are available."),
        ("F11", "Fullscreen", "Toggles between fullscreen and windowed mode. Alt+Enter does the same."),
        ("Tab", "Practice", "Enables practice mode inside a training stage. Enemies stop pursuing, allowing free rehearsal."),
        ("P", "Pause", "Pauses the current stage or run. Press again to resume."),
    ],
    "appearance": "APPEARANCE",
    "appr_hint": "LEFT/RIGHT to change  ·  ENTER opens the gallery  ·  each option applies alone  ·  saved instantly",
    "appr_sub": "Material sets color and trail",
    "appr_sub2": "Effects you can toggle one by one",
    "on": "ON", "off": "OFF",
    "skin_gallery": "MATERIAL GALLERY",
    "skin_gallery_sub": "Pick any unlocked material to equip it",
    "skin_gallery_hint": "↑↓ select  ·  ENTER or click to equip  ·  ESC back",
    "skin_in_use": "IN USE",
    "skin_default": "AVAILABLE",
    "skin_req_score": "Reach {n} points to unlock",
    "skin_req_train": "Complete all training to unlock",
    "milestones": "MILESTONES",
    "ms_sub": "Each unlocks a perk - enabling it also raises the load",
    "ms_hint": "SCROLL to browse  -  ARROWS/CLICK to toggle  -  ESC back",
    "ms_unlock": "UNLOCKS",
    "ms_unlocked": "UNLOCKED",
    "set_tip_fs": "On: the window fills the screen and covers the taskbar. Off: a normal window with a title bar you can drag.",
    "set_tip_rs": "Canvas sampling relative to the window. Native is 1:1 - fastest and sharpest. Above it is supersampling: crisper, but far more expensive.",
    "set_tip_shake": "Screen shake strength on hits and detonations. Visual only - it never changes hit detection.",
    "set_tip_ts": "UI text size multiplier. Display headlines keep their own size.",
    "set_tip_auto": "On: sampling adapts to measured frame time. It never drops below native, so it cannot get blurrier than 1:1.",
    "set_tip_lang": "Interface language. Chinese needs the bundled or a system CJK font.",
    "ms_kills": "KILLS",
    "skin_locked": "LOCKED",
}


def _collect_font_candidates() -> List[str]:
    cands: List[str] = []
    if sys.platform == "win32":
        wdir = Path("C:/Windows/Fonts")
        for n in ["msyh.ttc", "msyhbd.ttc", "msyhl.ttc",
                  "Deng.ttf", "simhei.ttf", "simsun.ttc"]:
            p = wdir / n
            if p.exists():
                cands.append(str(p))
    fp = CONFIG.get("FONT_PATH", "")
    if fp:
        cands.append(fp)
    try:
        import matplotlib
        base = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        for name in ["simhei.ttf", "msyh.ttc", "NotoSansCJK-Regular.ttc",
                     "SourceHanSansSC-Regular.otf", "wqy-microhei.ttc"]:
            p = base / name
            if p.exists():
                cands.append(str(p))
    except Exception:
        pass
    if sys.platform == "win32":
        sys_names = ["Microsoft YaHei", "微软雅黑", "SimHei", "黑体",
                     "Arial Unicode MS", "SimSun", "宋体"]
    elif sys.platform == "darwin":
        sys_names = ["PingFang SC", "Heiti SC", "Hiragino Sans GB",
                     "STHeiti", "Arial Unicode MS"]
    else:
        sys_names = ["WenQuanYi Micro Hei", "Noto Sans CJK SC",
                     "Source Han Sans SC", "Droid Sans Fallback",
                     "Arial Unicode MS"]
    for n in sys_names:
        try:
            p = pygame.font.match_font(n)
            if p and Path(p).exists():
                cands.append(p)
        except Exception:
            pass
    seen = set(); out = []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def _font_is_good_cjk(path: str) -> bool:
    try:
        if not pygame.freetype.get_init():
            pygame.freetype.init()
        ft = pygame.freetype.Font(path, 32)
    except Exception:
        return False
    try:
        arrs = []
        for ch in ("糖", "浆", "黏"):
            s, _ = ft.render(ch, fgcolor=(255, 255, 255))
            a = pygame.surfarray.array3d(s)
            if int(a.sum()) == 0:
                return False
            arrs.append(a)
    except Exception:
        return False
    for i in range(len(arrs)):
        for j in range(i + 1, len(arrs)):
            if arrs[i].shape == arrs[j].shape and np.array_equal(arrs[i], arrs[j]):
                return False
    return True


def _dump_cjk_fonts() -> None:
    try:
        names = sorted(pygame.font.get_fonts())
    except Exception:
        names = []
    print("--- available fonts ---")
    for n in names:
        print("  ", n)
    print("-----------------------")


def _bundled_font() -> Optional[str]:
    for name in ("wqy-microhei-subset.ttf", "wqy-microhei.ttc",
                 "wqy-microhei.ttf", "NotoSansCJK-Regular.ttc"):
        p = _resource_path("assets/fonts") / name
        if p.exists():
            return str(p)
    return None


_POEM_FONT_B64 = (
    "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"
)


def _poem_required_chars() -> str:
    chs = set()
    try:
        for ln in CONFIG.get("POEM_LINES", ()):
            chs.update(str(ln))
        for g in (CONFIG.get("INK_PREVIEW_GLYPHS") or ()):
            chs.update(str(g))
    except Exception:
        return ""
    return "".join(sorted(chs))


def _font_covers(data: Any, chars: str) -> bool:
    if not chars:
        return True
    if not data:
        return False
    try:
        if not pygame.freetype.get_init():
            pygame.freetype.init()
        ft = pygame.freetype.Font(io.BytesIO(bytes(data)), 16)
    except Exception:
        return True
    try:
        for ch in chars:
            m = ft.get_metrics(ch)
            if not m or not m[0]:
                return False
    except Exception:
        return True
    return True


def _find_poem_font() -> Any:
    need = _poem_required_chars()
    for rel in (CONFIG.get("POEM_FONT_PATH", "syrup_poem.ttf"),
                "assets/fonts/syrup_poem.ttf"):
        p = _resource_path(rel)
        if p.exists():
            data = None
            try:
                data = p.read_bytes()
            except Exception:
                data = None
            if data and _font_covers(data, need):
                return str(p), data
    try:
        return None, zlib.decompress(base64.b64decode(_POEM_FONT_B64))
    except Exception:
        return None, None


_UI_FONT_B64 = {
    "r": "eNrsvXd8E8f6L7yzK0uustVlSZasLnfJsiTbcu+23CsuuFdsgzFgTDW9994JhF5MSwiEBEhCSOGknQRCKklILyc9IQla32dXNjgk55zfve/7/vF+PlditKvdmXmeeep3ZtYCQxiG+cEHA8MyCwtKApIEORj65zm4uCmzpCwl/vuwGRi6XQi1viwoiYhcI/t0PIahJfC9vqm7oWetMUOIYayfMMx3UVvDpB647gXtT8LRva1rWmvTudhYDJOtwdDpF9tbGpp1QV/DLeQNH9Z2uMA6QHTA9zT4rmnvntw/5nRhEHz/HMOY3l0TmhqOb5E9jGGiBRjm5t3d0N9D/Iyo++1QP3B8Q3dL1tudYgy9UoNhRFTPhEmTh85hkUB/DXW/p7elpwdncKH9TIqfPqDH1KNLGPo4jqLXB/Qmz5qogu/1VP8YJQscwy7Ycr+o8437GfMigA8Me3fXV2zq+OlXT24eemQoirhGJMNXD6ou/aLEpyGPwWc83CeJa3RPo19zqSv4Qmw3SAejqTCwQKweq4fL7vQVBvESWoO5YQx8GT4GvjtcR1SLRdLSwZkYA1GvOTBUdxQYSOmNapiVX5mNkrDAISlRPDQOe56hQaUunqCRDD9LSQJDeCJWiOAa6sAmoY1YHvTNhWuJhAVLw+dgesyJ5aE2LBlKJBrE5LgBU6NwTIfOYVlwrEA/QZtEzAKlBUoMlAwoaijlw9+tUCKpczQdmwUlhepjpKATWDBRg0Xj2zEvvAurwSuwLPwCHEOh+EI5Dt+vYDWIC8V36BG8FY5/YDVEAtz7EMpncL9s+Aj3cCvQ9MP88CexSrwD8yPmYRK8BxPhxRgT78VikQ7LQCQmgqMK6CcA/xiqAvrNmA2fgVWj7zE7HOPwFMyOxoIsZsL5OLjujZUg76HHQdzVSI5VE1uxauo6FKp+NVUPUe1vQbsizBdvwSpwNuZJxGFCnIGxYSye6HcsFIVgJuwxkGUITV+GOjE+LQeqvgELpuVSA3THQ9mOcQmqHMe4jHhsEnETuwBlhavg1XC8DMcYOJ7Fj2EZhB/qIPywMsQGfUGB61OgtEL5HEoxlM/o4+fYMiizKEuA70bMhkVg0VgYFoIFY+GYFJuEhWJpcF2LxWMG+K7CgrBMzIwlYEmYGpNDXX+sChNg3hgHbM0PPrUYH/OFowjjwluAieGcD9+kmARTYEJ4e4EtRQAFJabBYqD/MGwAeo2GaylAPxDrpz9V0D8frlsxGaYDSQmBqhRayaFPGVz1By+OwaKwOMyOOaCGHNqYofCBSgS2HguAaw6sEOqasFa43gU8iLEJ0I8AK8fqsGqsBhuH9WIT4W4X1gG8KoB3A9QMhX54cG6lOQyEsxjMApQj4BgBvdmgp3aoTUkkEWoaoJYC6IixfDiX02899MKDEQigfw5WCn0VYpUgORXINQrqKkC6kVgf9F4AkiyC2gHQnpKTCNr5ArUg+K6Gmv4wajHNlRo+/aEnG1YB/UTTVDnQTgnXKe51MDYRfLcDfQnUpGSvhDM21Myjx60ATQbDmQbGJAIODNjjMPo2aGmBMUfC6KRANx7agk/QupIDT3KoHQga9qW169IvG+j4wbUA6M8HNJoAtCiNquH7ZPiUwh0znIfCaIPgHQ5nOrhGWVAg1NPDNcr+TXAGdg73goAHAZwr4JOSA2UDGqhvgRpzsXkgezE2FjhchzVBnwegRwEtcy3WiBVDK3e6FRsjoFU0PVoplgrUTDAeExz9oR9P4JkPLYxALxToq4GeitaJEs4CoGUQzVs49BcIrX3B9mXYTqAqhjoRYGsqqBcERUv3LwZ6CjgG0/Kk+hDS9mairSWC9qMAuBIG5+DRcDSBDDVAndJXAO0VIjhLpiWjoC1QA200NF9KWgu+oEGXfcmBHqWVYGijoj0oDFpJQf7ecMUHRuYB44vBurHxYNENYN/NWC2UJpBbKdxlYlnQJ2W/0XCUgwT0wI0URqLGSmg7s0Etf9BlsyvLgSwxuELQmYKPMXx74dIbcMMdvYHNxk5B9HoT+zWQH+gfGBCoU67XXtW+YsSNPvlYvlc+O5+fr8kPzg/Lj86356fnZ+c78sfm1+cvz1+VvzZ/X/7B/Mfzb+d/kv91/nf5v+b/UcApkBRkFBQUlBTUFAwULC84WHCp4L1Cn8K4woLCqsKawoGi7KK8opai9qLOou6iSUV9RQuLVhadKXqs6GrRK0V/FLOK/YsDigOLNcVBxcZia3FscV5xR/H24j3Fh0qEJaklmSU5JWUlDSWTS5aX7C65UPJSyWslb5bcLvmk5MuS70p+LPm1lFHKLuWURpTOKn2pLKJsS9lj5e+Xf1D+U/nv5WQFs8JQYayIrcisqKiYV7G84vcxu8YcqmRUsip9KoWVkkp9ZVBleKWpcl7lteox1fOrV1Rvq95Vvbf6bPVvNYwaZo1vTUBNbE1CTVJNQU3Z2M/G/mvsD7VELbNWXxtdm15bVttXu6H2QO0vdVidb52gzlQXW1dS11g3sW5u3YK6zXVH6gbrnql7tu6relTPrtfX2+sb6yc0+DYoGjmNwkZxY1Kjo7GkcXbjnMYbjZ80ftGEN7GaPJoam8Y3rWja33So6dWmD5szm/c1v9QS0RLTYm9JaMlqyW1paulpmdyyuOVky/mWD1o+afmlld0a0ZrQOr51XutPbVibR5uiLbgttC22LamtsK2uraGtpW2gbW7btrYdba+3fdLOavdtj26Pa2/qqBqnHBffqeps7lze+WjnK51vdPG7orqiuw52nek633Wp63rXR12fd9u7k7szuh3d+d3jusd3T+1e0n26+/vxbuMjx0ePf3v8hxP4PYM953uZvdN6v57EnrR40uFJJ6cophimmKZYptin5E6pnLK2b1bfgr4bff/q+6nvzlQ01Wtq0tQFU49N/aY/qj+pv6t/fP/aabHTLkz757Q/pntNnz59YPrm6ddmcGaEzpg9c8bMizNfnHlj5h+zQmZFzE6evXf2wdmXZl+Z/fzsV2a/PvvW7M9mfzMgHggaGD+wao7bHO85ojnOudPmfjn3p3m9876fT8w/Ov+x+e8uiF9QsSR3ScuS9iVHlzy95Nmlc5c+vfTK0n8uvb3002XY8j3L9y0/vvzk8ovLryy/vvzN5Z8s/2b5T8t/XUGsVKzUrjSsjFo5deXClctWvrfy1spvVx1d3bp6wupZq8+vvrj6udWvrX5j9c3V765+f/V3q51rsDX4Go81fmv4ayRrFGsG1ny+xrn2ubUvrX1l7WvrJm9YsuGXDb9vIDeijX4bwzcObPx84zcbf9qUvilvU+Gm5k1TN63etGHTxU3PbsY2szYXb67d3Lhl2pYZWxZsWbtly5adW17e8v7WJdtmbLu5q2DXK7te2x045DHkPSQdGqJx4Ml7Xi0OlIFXr6G9GjN6g1d75PuM8upY8Oos2qvr/tarf7nn1Xn/m159etirfy9m/huv3v2AV08a5dU3hr36W9qriVLv/1e8ugK8evnfenX8sFd/es+rdf/Gq2OGvXrOf/Fq37/1avQnrz74f+LVrUNt7v8Dr7aN8mrlf/DqD/+PvPrE/+de/cx/9eof/4tXP/X/yKvHP+DV7/xHr/7Hf/TqtP+RV+/4G692B6+WDA0NfTh0cujo0Iqh7g9qPxj7QcUHMFd8+9zbgxj2auPpOaf7T0893Xu66XTt6ZrTxaeLTmedzjidfjrqtPm0x2nWabdTP576/tStU4+dOnvq5Knjpw6d2n9qzaklp8aeqjhVeir3VPApxSnGyW9Ovnpyz8lJJxtOVpwsPxl1ovNE+4miEwUn8k7knsg8kX7CdsJ4wvuEx+Afgz8OvjB4aXBw8Ojg4cEDg3sHdwxuHtwwOG+wbdA6aB4MO375+Ibja4+vPr7w+PTjHcdLjicd1x7nH+cc9zmOH0fHnMd+O/brsZ+OfXHso2MfHHvmWN8x/dGrR2uPJh2RHPE/wjyCDpOHfz184/Arh68efvzw0cNzD0877HWo/VDdIcYh/KDz4M8Hfzj46cFPDn548NbB1Qcz9z+xf93+5ftn75+xv39/y371fv/94v1++4l9n+37ZN/H+27se+3h5IftD0c/bHhY9zBr7697v9r77t4n9u7eu2pv4l7rXsNe9V73vWjPF3ve2fPSnkt7ntxzdM/WPZv2zNszd0/Nnsw99j3qPX4PffnQ+w8lPmTcnbw7fnfcbsFur92MXW/vemvXgl19uybtqtk1ZlfFzqGdP+18c+elnRd3bt65eKdqx9Udu3bE74jaYd5h2mHYod3hu4PYgW3/1/ar2y9u37J9w/YF27u3521P3O63zbltxbZ5oPXWbTXbqrflb8veFrstdFvINsM2323srb9s/Xnrpa2DW1duXbS1bmvNVuuWpM3TN9dtmrnJvkmw8euNr298ZeOajRM3jt+Ibfh5w3cbvtpwY8O1DVc3TN4wYUPnhrYNLRtyNmRuSNwQsYG5/vn1j65fun7Butvr3lt3dC13rfvqJ1bnrLq56rFViavkq/xXHF3x8IrtK7asWL9i/oqpK5KWly0vWEYu+2zZR8tuLXtz2cvLti2rWGZc+t3SI0t3L528dNLSoiWHlwQt4S3+avG7i8cvHre4ZHHgoncWPbWoZ+HkhZEL9QtlC+4seGHB1fmPzi+bXzQ/dr5tftT88Pkh8wPn+8/nz/ty3tvzNs2bOg/N/WPu93O956ydo5zjP7BjQD7gM7t1dvVs26w3Z12c9uK009NOThs/bcy08v7t/TX91f35/Qn9cf3qvvl9c/um9U3tG9fX0lfWV9qX2ZfUF9sX3Rc2hTvFZ4rXFGzyxcmnJh+fXD25arJj0preG72v9D7du7h3fu+M3t7ent7u3s7ecb2VvXm9jt6c3rTehF57r7U3cuLrEzsnVvSs6lnWs7RnyYRPu1/vbu1u6q7vru0u7DZ33e6a0TW1a2KXqkva5d/F7Pyp873OtzpPdh7p7Okc1xnYKejkdtzt+KPjx47POj7seL9jsGN3+y/tjLZDzZFNZ5pONzWjdlQ/snLz5xfxNP15Bfu/r//7+r+v/7+9uFBmYtOw6dgMbACbivVjnTCPx86hoYXnMMZKuCuAtw1zQI1XUQY6jM6iV9GXuDsegJvxJLwcb8Z34SfwD4gAIpboJg4Q5xg+jGzGBMYmxhHGk4xX3QLcVrkdcfsXM5CZw2xg9jFPMJ9nXmd+z/JiSVkxrGLWCtZjrDvuwe5T3Be7H3F/0v1d9988/DyCPGI9sjwqPbo9pnks8rjm6e4Z5znT80nPj72MXjVe/V6HvS57vest8870nut90XvIR+7T7LPS57zPP3y+YjPZGnY8u5U9ib2D/QKb9JX4Gn1zfKf6Pur7k5/Nb43flxwNJ5dTy5nDWc3ZxXmM8yrnPc7vXDE3mBvHLeBO5i7n7uU+xn2J+wX3N+5vPCZPyYvlVfIW8s7zbvHT+R38tfx/CTIFkwUHBJ8ItcJJwnMioahKdE50W6wQ94tPit/0t/gv8H9RIpVUSh6WvC+VSMdL90q/lTXIdsg+DJAGTA+4JU+QH5b/pEhXrFP8Ftgc+KQySrlN5a6KUvWotqleVgvUTeqH1V9rQjXzNLe16dobOlxn0s3TvacP1a818AxTDC8GmYPWBP0QXB78eYghZFrIU6EhoRtCvwrzDUsPmxv2QthP4cnhO8LfioiLmBPxvFFvXGz8zcQ1FZnmmU6YfojUR9ZFXjAzzXbzXPM58w9REVH9UZcsHEuL5ZrlB6vFOtd6xiayjbPtj5ZGz4r+OCY6ZnHMp7EpsZftxfZjcay4lrhj8T7x1vjm+D3xnybYEgYTvk60JS5LvJakTpqYdDPZlnw0BaVMSPkyVZE6L3Uw9ae0xrTD6Z7p49MfSr+dEZ8xM+OpTE1mf+brWRFZy7LxbEf27hw8pz5nXc7XDpVjfy47ty93MI/IW5L3Wj4nvyX/5YK4guuFEYW7Cn8pmlH0Q3FS8fkSY8lgaVIZUbagbKh8WfndiskVlyv+GJMz5vXK6MrrVVlVl6tN1Stq/GrWjvUeO3Xsx7X9tZ/XVdddr6+v/6XhdGNoY3fjc02Kpk3NiuZ5zUMtg60xrbPbWG35bYfbXmjntNe0H2n/tqO44/I4wbg14+52RnXO7PyhS99V03WuW9Td3n1kfMD47vFvTkiesHvCZz0Tes5MlEzsnfhKb3bvuUnCSVsmcyc/Atm8bcpTfTV9b0xNnLpp6vv96v5J/Xem5U/bN919eu/032dMmPHUTPnMJ2alz7ow2zb72IBl4JU5aXPenFs89+q8kHkvzV+8wLDgyMK0hVsXVS+6tjhh8ZklpUvOLcWX9izdu/SLZcJlbcv2LPtx+eQVlhV1Kx5d6bYyaGXzyuOriFVjVz2/OnD1k2uC16xf8/7awrUvr4taN3XdH+sb13+yIWXD4g3fbezZeGhTwKZtmxWbl27hbdm3NX7rM9tWbZftYO8Yv+Puzn27knYd2B2z+/RD+oc+2TOwV7/3vYcnPHx5n2Rfw75t+wP33zrQeWDLgQ8PVh984pDPoU2Hfjjcd/irI1OPXD8qO9p99Nqx7GO3jo89fnlQMLjoBONE20nuyd0nb5zyA+S+/zQTMP+LZ9LOHHpE9cjsR9GjEx59+6zh7OqzXz8W89ij58LPvXZecn75+d8ez3h8+gXswsQnfJ7of+Lmk/Yn1110u1h/8YVL8Zf2XPa83Hz5zadsTz3xdOrTrzyT+8yTVzKuHHzW/dmOZ/c+++vVrKvbn1M81/ncreebnv/5hf4XvV989MXfr4VdW3rtpX9E/mPDSz4vTX7p65cLX/7klepXrrxqf3XXa5LX2l7b8tpb/4z856bX3V+f9jr5xobr8utTrz9xI+bGlhu331x7M+7m42+1YDhWCBDoW/xTjMBYGMZTcpRajpJTiHaTDaiK/Br/1ClJwZucO6HmpKHfsR/ws1CTBzXNhFqkCsctUQm4OVIo4DPnNfqmKTliXxbLV8xRyeX4WZL/KoMtFvD9fdxEhiAhtQ6aB5E2C78zTA36oEpes8g6p1low++QN5GBvAn1IIbjGUCLWsnFEMssULPUNrpYzHQxs+giUKtZZvSRbtlWQ5FhD5QxbbqVO3RFuj1Qyh7do9uDzp/JuAyvjDMZj8Er4wzQThzqQz8SPEyPGbEYDNPymSyB2qLT6S1CocgSTliirDaLWSAnRAK4CEfEl+MiC5PJs1otUeG4Hv1Y3ZhobxEHNMaYUoI4pZWJwogglZd/eagxK1xEHmDytYrI0J0xFk9xiPL5mir3DetxH498L1/8Dx+pwR5aVMUcOxa5MVmMHA82fttbEZaIOAKFP9/jdSKEFLgZbTKdjO+JYW5Y2tAv+Pf4ZZC5CAvBErESkNs9uctxAZ+NIzNS8yITcIo1tYoN1+Q4eqCO/oH7/1RGafl8bZRy+IgyU8kZKTJBANfdnRsgEMioowwdUEbp+HzdvWpKqMBijaqQyg3JjrblhHK5oTm26OwQLprkzEFTfRSWIINF4e2tsBiCLAofcuDBelEPVgG96GGsc2CsYaCVVNCLUGgWwDj0TKaaHo7VRulmZFBMlshqtZmZTELFFPCFIko3OoIvNEdabdAEx8W2CI0lRMuLbIgyFkQr0sv9BN4MSXiCVmc3CPLy18kCiAqPoDuqMI4oxqq7kROnT9EciDPNlUhz3XylgmCNNDIjOL49QqhXq3jauBCx2GBVJJTqzgSXG5J60WWjTmZVSa3B6lAyMyZZGviKOoOaT4CNY6doG8dGrJuybLiTPBSNouCOD4aJdDpqPMA9xfqt/MKS/OJih6Pg+Z6vBhb9q3fOZ/0zv5pO9RYJbXTDbegR6s1Cyt1YkVA9v5hq+Lyrtqsl1UaOtqA10IYNHNj0NpHezLKJWCKWnuWoXCSd7VXuNVu6qCo9KxO92KEotixdailWdET29VFt1Zgdd8MDqJ1zBEnbAs4GrmDG3Z4ru3q17DmEP0edUDV1Q/3Ym4CwoKYogbCYwcpYOr7an13Cl+u4SxTp6SmywOyMJDHUzUK+aAKqoGWiFCizkJ58C1VkwZ0KiCpvAkajelFRMnFFk83qgAA1RBGmMNggFBqChbRkhz5CB/E3qF4om0dVeeSPefgbTjZEDAvYjiftJ3pwm/9i/UgRVZ6gUiWUR0VVUMeKKK1Vw+ForFqNVc3hqK2eisLlnZ3LihSKomWdncsLFQ7/pO7Sku4kfziWlMKR4qcFPjohSjGpGGWxmTlqxDl2zV6FNyuzg505UAOiC44DV4EYZgMZ0SwwWRardYQzFksA8oiZsChHLA22+CtzgtQFoeZiu0KW0lNqQK2kra5iek22VmuUebK88tzdhcZcS0RJZVuqwiOX4iFj6Bf0DVAIoeVHRTAzPVidGjQXSRnMPYq02Qho6/kouEBtcBj0qUZZc5PNWl2b7ZDnKyUFhp5JKTE5qXM9mawCT5a33KTJiU1PjYmP8vTMcfcur0/L5jB9ytLrO0DiahgbB0bvifmCr1K2orQgM8es5qgJAc4pLiXPIWNX8QHmL0ePHm1AR8hk1EQ+zASey4Hn36Gl8i88A6uUfbCG2WXjnwSnqvSJhpDMSFl1lyxLGYHShrAAnk48bZ4+q83Fpq86JiQ/04OJKvMvEkTzhISKaAnwFwMWgUAyUkw3yiJYYAIs873+9SMiEvCRwliSqAmpWtmIkpozDAyCn29u6JXayu2ZOTn2ohxPaVJnUcNDkxJzNYllJr52fK+5IknjKCrOz8tLOEPpwkqluGF7UFqUAjDRM+R89CJ5uwZvzx/j3AuWGwlceQNXSsg9cRRfOootm0WnGx3ZIOfAgRiRCmWzvPucCpGiZ5ZQHSoMjfaPKoqOLoryN5n9w1S8mRO1ZgU7JXWht8KsL87Kzc93ZHrWNhvsQf7uDH52clCaSSo1pQUlOvgMd/9gu6F5LFrDU4VKYhKmSkJVPPJ8akxmSkpmTCotv59o+QVgQWC9wIpNPRKI73uWejRba1Ka0vVuDF6+2VhgU0ijy2ONJQma4KoVjfOKHDmZmVk5iZqk8kiBRmIpiTFXJutkKV2FDQ/1JqIUR+KY2ori/GygOwsighNXQUQQUbnufkwgRp0/ORwfVMNHtE8YFCSkCll+L2TgWArEqL/vayRijXS0k6+SsIupyHW/K+cbo4IYHRvDIDaG0Pp1cxNoLVrcjaxFe0k5+gjdOHKk7ErfFYz2jBW4G3ppBFMJ6LcafUTVg/JS2eayB3oTuFm0Wgv0JofealFb35Uy6I7qK3jod7QVvwhRzQZaoEzl7+MImxAIHkBkW9z5aqkowI/pI4/UqgsDxHlR1kKrhC3RioVyLqvAMAqt/chTqbRCriwgUKgIEnl4eRW6s/0MaeYgW1Agx0/qL+XIX/oTmMOx6KF1RAJ+CUugMInbaMpgFio6aQ/btFAEWI0ykHtuToVh+GYTgI1bbS5UdS84X23c2GxOm7J9zP5Hpab04HSlPMOYnq2OdRh0Fl+P7CCPAJFIJ/NdPZA9UGfdc3BCV+8ea5IXTjC5gZJAo9KPxZGPj2pcVtG0tzfx4PbEcbkh8Up5YXpiQ4pKJjG9GsaXqRUxhaZ5c6Lql5Ru2aZM1SAfR5K3yF2g9vdRR2eofQOEbEr2kJPwNeDPLOpMq2SpqaxDEGoCfUq+lFuDWP2IWdc+xXvqK6/gZwH2KFAq+SRovQbaaaCdgH62AFDAaK8G4dxHa2rBqNOa59OqLMJwm9oY4C20Vqe/uysyM0wgCMuMTBtryQzmcIMzLGPxs8Lw9AhrLofBCgiOUkTkmCVokackTKULE7E+Jp/zlBq1gWEB7B+orAuxJpSONaP1Q4HaEVlTWEnAZKIFWZNLwsJLpzmMmQp5Vrh9TGyA1FYWa8o1BJR7yguWdzcvLdV4epZ4+ciSO/JLOhP9fdj5PhyQETXWSTBWb4xKiSNRQc25Py4O0jhmjDGZxsxwPH/VWpWs1iZXWrrws9LcJV0tCwuVILqt/vHt+SUddqHzM8rPoE/0K/RJSV0AUxKXAwnQr2QLmgdzBD75dVERfrbwzdwfhmu/D7U9QNJUPY4aWpylKlWheXjrh4XkNaiLDcujFuTxAEJ4UCAU5uGAUFbm9peGhZfPyhebjSG+6kpLbHWiUpFQaRcni5d/qOu4JxgGy5NZyGaLE7pKK7vjBEzWm7nkbm+Oize83TUSRPEFxQyfeHs1ebiqClXQZlNInoTJ0idIOjx27Cw9ywK74ahrqqqoOnBn6JEhB/YY3IFsyxrJmlYL9MdnMn2D2N5yf1tEVc2jBFGIu2XE4DudVdXjhnvES2gNYUo1oaZZMPPMCC+ZfMdUVWX6sYf8GGWQjwMPt5ASDHhYprehjZtLA2YOuk1Oq6KE7tw+0udHLl54ZurNobI+3XvNmlPMU6uqmKcbH2GOgT6T0SVnDl5NpqCLzv0jbRe6ZAJcAC8Am6h2K1Ecs2oqeYxq5byMJ0ErauIJNkbpbdf/GNtNypmQq9PlTsjJ6XHodI6enKTCMA4nrDAp0XX0VBYt6+hYWqxUFi/t6FhWpMwLTBuXkzUuXaVKH5eVMy4tEBu2aylwyQb8MOLBlGELRjkvp+ap7Ea7OCC+IbWt6rwxRc/h6FOMdfhZibU0Nr7c6v8LSmarY0MNNpUv+ZZrJBPokVBzOQxRcVuk1o/OqeiB0eC7JFG55kmdDW6jR0Vef2BMqLpiZnGEx+rFo8ZGDvy7cYHZ0U9NYUqCqVLTFjEcoXholNt+c8md41FedTK7JVGWkfUqedyYHioQhKYb85EYkV/gZwXGgpiqsX7k+6jRQ2YN1UfKPMnfKdQL+M6JP4VZXNrSW+QEDUXhlJ5cP+h0IhrtIFZgoi3ExzfcGqfIL/TRJJgsOeGCiX3+5gi9t7w+QgMQ3UMeHRFbFCmc5enm7uFWwvTycItKDgyRC719ZCEJ4XVjGSwPt2Ivjoc4WCVWSwRebIUx3dxaR9mdH+VEdDTHKHvjAF5FQy9WXUPf4q3ObXhrIdSpBEtroSM3jcwo56JiAsiE9jNUO39eJTcoxRiZavCrXODZOYBukAnwhcs1pEaip8ngGRNclPAqFyWXdxBqv/pnmFerv+0B0z6MV9BzAwmGEe2jfchVk3pLaucxV3atZM6t3t+7krmmF1qdQXdJBp4HToE7SWgNeAYHR6HmhTzC1ZRHt/3jtY79zJONb33YcZp5oQU1oDLyNgogT5FbUTB5A1oC3sBzh+PlcEuO+o+f2y8wH2/6tQoFoxXkVRRLTiGvU1KLhdqZLm+1IT2NaqkgG4tWI3IRwJlOdMz5Yw3OYBaWO39lFtEzkmhEwOyTHr0AbEugzniytfVJ/E7O3TeoSIaJhnagT0dmyEgtKkKzi/A7d/dR91RD0dgHrtYiiAwQidWqtraLF2cToTl3k6gaCciOvhxG2QS1gsRDG+fOLdvRtw1uxJFX0AxyIb2vNxSFfhqaTlGhOEY/kd6LMuB6NN6G/YF/76IuUkdPKM3Av19G+YYNtO+O61xZm85lHLWeTYzgGPMo3EXQecKFY5ApqcTEy/bxNpjj5A2ViugC436vgKggaWKAPEmaVi/YrYwM9DPiOv/QBA05t1ioEnuX5hlTDNwwcRDAM2Yug0GKbcZKd5FBERZGcVINnCSCFPiYYVRWhajPoqK31fqX5Z76tAoTj2eqSCso4Hg5yjmFqcYYuYenPCbClKT389Mn4bqgnLaE6Ja88GhjLX6HfMZoJ/0BU+mDc2OUAdY8Y0SuVQ7SsYPvXgEZqP8zZmATyBI3NkmpTBobF5YtkqcFh8Xp/Px08WG6nAAvpT7IU5rcWVTUmSz1di/w8uFHFMTZ8yN4Xt4FDBaTgBHGwQiVMELqGUwqN+r/PLcQcYgHI6Ey28evPCe1IpLHi6xINcQGy9wfNiXpfH11SSZTjNzdQx6D33G6V4ZEUyO1teaF+0p1YhTrzJTB8MLzbHK1nRputJKSsH1Y14GuSMxkud0f2mhGWMMssHB3AifXcQ0pprCxCm+d0RZAjz+xOja9LNyvzF0aFRphV7ERSvNS8kShycECvm8B09vDbUQQQclFBkVMiL84PIX6owpqjRPV4ndp3ESNkfIVKiqZ78scqWQaoefAQHlVlcSYGuSrYPvjj7HVceGZZAi6numWUR7hR+DpbrQ8o0GeOsB6FkqefAp9A0ag4q7lAdFa/iragaXqDEl8ZlUFpzA/rdzM45nL04LsQZK/SlhGevbMdnfL9i4cazVaDFktCdHNjlBOQJC4hQyVRuUaw3OjAlTROfrgHFsgjLIahM0DPUvveRRnRKI0EkkgUK0lI4hT7i4KCpSYQtRe5eXe+nAzrpNEJOnJZahcYVJyWaJgDbkezPZNiYrnTukP5hzY4/gnEJd8/zyzY0HEWAwzhACpWJxZXo4PcJUqDkel5DY5P8bwocchvrjaKf4yu7y3EkEFezY+0sthP4UfW8ML0PBZ5aLw9Ps93j1PQGwk2KroINzb+VVyUZjf8IhxGDGNt/RqAY23YAKE4xOeDSgvV1zovH33Lgwl870/qNowv/OG2r6u9S+KsnAYlb8eF1culngIvLylTGs8vty5PEiME5kEtfxFUSFSQd8ho+RKuyhr1CklYQG91iFKIPB1Eakh/PKQeHGIRuZRbrD7h2pknuXl/sWmpFyOtzbMRMk8WU8uR+WJae4CbQCDEn9COkugV5BLcVmmURkRJFHx3bF7etX9O70KRvRaAUHtv+pVlker1eWV4dDr/wzp3YtAcWMTwRPHxoXHa3z9tPGhYfFaXz9d3L0YNHLM5hsL7fZCo0DgOvJdsTYaYq3ur7F2WHr/MdaW/5dQS76Nf9wwEmpDHKNC7bDPqoCyGAt1zQ/+HHr+xlFV5e7S4DjDvSAYFyx13/cXF3XKULh/kNzvXhyUGcQNpPovYZDWImoDDjjUCuZo5ZlRG+EtiQzVgNp8dOFmMa7L95SGa8jduKxRFSymbcAOtrsfp/6iBBP9Pc4Tilg61+LQCMq7yQ8L1Xqx9cEh3IRED0mEPixWxW5o0OfxmaI0XUyMh9AQGJ5s4HYwCQaLyGG4Mwm1UawQ+Hl4SjSRqpRCT/dsD+/AcIGE58Py8tda9UUOihdf4CUB30HZo9blPrQoOcPr1+CFlOoIrpTtJ+OExes5hYXlixYxOfIUgsjGCR9dqgVFZM2Zk0XeCDSIPOiVaWpFWUZb+DAOCMdHQUIbB/fM9vLWhUX63wtg/sYgpTco4ON8KRi0JDxZj/rIIwqTirJ0NZpAceoJqmdAv6PQoWfFPuau6hdbIbrGoqsQpxDkRYzQQ62/QYfC8l7motZlzN6yTZ2LmIs7oZUdPUsV58foApkOrdlA6Bdo7UKHIgg/gA71apb6+RP1S5iL6gbPNa5irqtHPORx/Tr5G/nVrVsUZ2CPbi6aIpDhMDiEgadmpPNvjt3P3FHxNM8QUxg3OyEZl5JJ6LLzF3NhjJwaFWXBN6AtjRMt93BiKDKSn6O55MsolSzPQEuZmcnkFCaNAk2AEz0g8skoT7dQy0IWKllFmQVgL1QgFwoF1CoR8tgi1WqlW3RSf3hJdc9v/UgtKZSoP9paGBD6kd7IZhv1H4UGuPZKsIUjuJKjjiwpAVSZNIIqf3fREtFErDadbpgmTcRFE7x+mMgWmUYj29I/mkDhPbpUjzLsJu6N5tD2BrGCtnKW3hVraTewiZhMND8iWSjSSiVyRj4zKy4iUeTN44vY/tTXzJtqP47AEMrMKVH7ebA93ehTiAp8NBNV4Jfov3n6y17fyHq1Kx48qrSH+vuH2pVwlEjgqImM1HAVIjZbpEAzJfSNEIkkxFUhN1KjjvQRKbhchdjHtU5pAn0HuXIoEtzf7kGgueEdH/ITes1yVd6OHXnbt5Pf5VGegbywN9FSegb/N3s2yGtkARXqBmOpiMSF9FqOnqWntqOovSh05eTJ2JMnYk6eiD1xMvXkyZhTcEKdU38po8YCgK9Ymi/K+0bRcAPORu8TIb5KKlUppVLyXxSf3w9/Q08L9HoBVTrLPhEY9Hy+3iCAnql9ZU/AXBJMR+FO3gPo9h4E0z4AKLokEanB3hK2t5Qt1QpciAx1jkIZymEoBmjgHjxr+hPywLhDv+M1NO3/RBmNBK9hLPC3lJ+jQQGXwgd/S5nU0ThhBDQMo018J1A3/hltPog4XcyMQv14PUBQjyVLyr8YBULVFCz9Yvibt2IUJv0zLqUuu93jzyV/IovmIg6jHPPvpfD3TD2oE3QURBNEiUbiK/13PKJx/1lJf+X3r1ojttEc/+/y+6Am/2f8PufB9/IC1cb/vWr/yu9fdE1QT2oQ17B+ek1WB343IjVgRae9dwbCVI7+QjioMCvV+ku9nW30icRbgtYPX5LG6kUivUHsIa1yHWQj3+EE5HQB8q+d3mkRU9Z9nyJvNI0LLhJaadJIt+i2QSTW68Ui8sn73YG9rhjqR/HYAJUlbWZQuNpq/bIkOTgjOGrAvtGWtIaKX1SdAqDJop5IGal1jx6QG24xTFPqaonepukZDBQdvBr7nRATOLXSiWh14tVPtlYQeA6ZAlxcHlqHZqFt1F0RvVJ5ubXiSQ266LxDtY0ZWkeooK03ZRn3NvPVOjwmJ6+4IC0tt3gDSpvxblvP9d4pN7uegf7OQn+7R1oMb+VTTKPstILivJwNxblpyNF7vaft3RnfPtNFPTOQgTh4Gyob2TnPwJXOW6gsDcNRB7qDX6BXSqjoTRFXDzMBR/RoklhRFvYJfJaG4neSltrMqxOozzUgtzJ0Bx0cackbltuI/FaUhSmg1XOlYYpEsQK/E7k2PmmZlf6k9JKM7mAvjazuuGitpEkNE/lLHVev/a5eh7uDOlOGHkI1w/q1CWmcOMUWWq/JkNRVaWXNluCILuC0dWgt6sFWuvbvbKOsSjRq27E1NyYmlyoLlcHBSii+cSkpcVB8dGq1jipA7/Ohf+I/EEzq7/8Ry4KQQM9hoavvIzfk9n4ePuPDdsQg77bfclZRf7aPFWNVxCK8ma6t1Gv1ZoTU+G9wEz88XBNF56H3yT9Iag73GfT9vatvm0XEE3FsAvTZ+ygP7t9o/xA/jJxVt9rJu3/ul4fMLKXITaQuRoz2W/gB5KyArusodtD7FA/Lhn4iavHnaR1F0cCCGjvtScsaDjY2HmxwfaLae6cNB6HdrKHPiE78Om0xHvgsNBVNJZeiWuqTXAr3jaiG2IeO0/cBphmJyaimqIiKGzZouRN/gd639HLZmwgKAWU2/q5TY8W7netnEa13t+Ev5N12kB/TyDti6DXiMKF27XFAVYuSI4Ij+h2duLsIzcpH3egpsiIzk/BikF9lY/TO4V5iB/7usP1ZXHs2IpcR6KOJZrK2cG3qkVCj7aAdX+twODn4t0tNqyMy4jYFQ+uwoZ3EbvxDwLjUQyFMasYCyEvDozCn23AneKFcmbfqtWgUuoPsIoTkjwVnzNExZ1LxjTaLczKueGxL4jUkz829mvCQPS39WBTFVcjQUaKfkNB/SQxaZykJ6vEMvQ2QPniHkidiKSlcRPQ7z3jhGoGbIiVlhmR2RDCPQXgRzncUBR545t0z+DznbLxgF/lQcpKEwcpl4uwgY/huEzpLzCYTcqhf/ggeepE4gv9My9iXilwIZlxKi5njBgOgxEdhHMJn5905O9FvZAk6PlLwn52yzEz84x8OHfrp2M+PUhoLH3qEWI3/hFmwWDo/KVn0dpCLbZj8UCCaFgiNTW0j3/VQRU8tTNgoclE2NYugtveJ1eQX+Ftie7RVnKYK9FxHeGoa/aP4WWpDZ2xpgdvDyF2WyInixnITIm3pN3HyY6KB3IPvJW5GRcuZa/DBJaRnuFFEMLIJ5OMvQQ+l2DRTtDZVnX7hXG3zU/MsYQG54hhNhqUtwfAsPn5JxssJOUvIhuSxXYWU/KVDO4jHiECYs8BslEcFJKEbzTqTpRVx1NLFH6anb0N+0TNuJme/MQtNLCpCawre6P50f0bls/UdV0p2MJyPubLfTqKeCLknXSW97QafFhFImkM944j7UZtuheQZlFdInhoqRATpxDvISvIdpEUHn2aQd8hvEI8q1Mxm6CFiE6HC4iGTMlnADbignp5aCkCcI9IE+en0NqHItX1otYj4LCUkfRG1yw1jgdnUJqaXe6RN7OMl0QYLbrl5T8rSxnf4T5wakz/W7tefr3K0eRB3fidyGUjNk7r7+borxG4e+I4Gm0bJwHGCFx6C7rgvKU4wFZkSa9c0xsbVNCenKBICohL73LMnpxKyLc5rMj6BEIMns2ZTkkgDP6shqL/9p347AHwFZ903aa5NCV8ovsEGYLYCcRpmMXoqFqPhI1HD4DAJbWFOlrIZwg+DyUbku9zidVNjepblccgLKJ/p7fBye15YJrfIxgiRklevs6gaRXhiHfnqRJNNwmDkM3BfrS4aqawLnjtaHV+87XRfrv0AIVtr8tY0SyJE9YGkRjdRFSkdr6FiiXHoJWIfQa8qaelQMvIe5mh4KxjnoPV3V6B15FMokdyCerwDWQ4PtTeqJzejJPKyICvrd8f1nJBaDo/bG5Rz3QE9a0GLRwnqr/yxEavSWzGb0uUYIiZLSWlTSBy1zT8cm/P6ZsuHiJVG3inss45ZElbkH4iiwxJizrPzqk90tp6tzZiFtE+vnm2vfX8aJzXFMad94gWw4HigsYjwB88OdEmb6hrp9AyWiwrQEzExltY1FpzIeq89puONFLSAG0Bay+KkfJmS34h8Sh0V5O9N6KnchKSo9Sr8mxnkncqEcrLv7uLQaB6TxShy53JKUM6a0FXk0xWihflhKV/nAHUD2P1hQg/UYd6IRqmS6aI+fIUeLR0HcDdpoSopsFSCogcuO7KvLjMvfCqrcn5sjnVWSeF4fV5Yb2nWuem4b+zisODgJSZnTWxvcvKkOIe1M7HmuyPyhz4pr/j6UMDZO9VxbSaQsHTon8QxQkOtBmkjbcNeoqfnxRQDNiqFiawa22htMhksOS4S4leaFwjH9xTmVzdkKgPZ7r7cKF58lJGj4LM9lyNJvfMAKmL5e+Z4KpjI0EQ+u1mRUOyokrllMwmGD+R3H0GCNDouUeTr5rhR51CPVfgqJgQ6uu6UqFU+BEHP/3cSeyFHhY72YUCkHPWwD9A+C5JxOS2gC9pl9zJ83COj5WxfeXTkK8zY6X32nonRjDu/4TgqcEMyPjXZ5Lp5oHVJGZpAcFJGRDx64+EXtzXbaxY/tqkgyTDGm3jB+ZVMiCOWUGyKBU6Chp4ATrR0NKEZuR9PwDEtIgFVtHD1nqfaqAzHArZGB5O9BPLw9EpNbZ02vdVqD+hjL8h7OReF4l4MQmIyhUtDNYFs3PO93Jd9lIGlc6bnm0PdvNEaKTM9IFDj5u7OkCTEokR5tvJ54nTUb8RtR+KNhOAQHsvdwXLzlkhfjya70Nwo8rQi0IdgsRhiidUM8SRz6DRRiL+N8TEZpqVz7wMBxTKSxAnQs0gE2oX6hB/O0JWV5ge02KwigvAlnC1LY86EGcNOxvdOQ3PHe7l3kIsn429Lp5N2bUKynMksYBL88DAdWluTP10xOzjPNF9F1ur32UNV0fsNgMXNQweI7bSlWbAYkGQy9ZSCGgLD/dRnUf7NWyRQ3nsjmOW6WdQCkVpgZpktamJ7OXlNaDYmSatkHCZ5EhLEOLSJPr6H1CCODZloKTkVBZIfIIvz8DtIcfNb+vWHfcCoD+IRbhkM3I3rr4hNtyfGxp1KSMhkpCYknIqbhiJSqdfxxDnUylzC0AliA/4RvesDuGdUsh7mEngjNpBLBNExLeJajcqbnIKWk1fxR8mb6FA2+brRKHRzz3PDfWQBSJj9XU7Od1TuTBo6TmzE3wcdKV24DVFZ0+VlVIK6F4GslPsJ1uPHnKVoTNhSM7qSmZYQu9qQxgucSr5Yb0gU+su5kTNDyEeJMvz9HPL7sucsAT1loTkvZ9i0NhaPSXjmunP9zCeKsrMBy6iHthMnIKp6wsxegkXSYwL3/lMWcRuOOKNDkStTiugwRCy7ewmtYAekeandUVjEI/aw2EeMd69nL7PaYtbmED7Lr+ZmP79Ju+yp9IqMpPTCAntOSnnGhcX4AYfDlMIXVfiTvdaNmhj1SqO3aXqiOXm+hVwbVBEbUxWRoys2l8zWDWTnzgicX27MDgRJyYdWEw8RwZAHlNRzAEyWmbYbii2LxazTq13si5RuICpg7qEL/vq3nU3R6ZkZUScD/Z9GywW+OewAQNOPqBTktUAx3lJcn102cLIiqGjXrNW9SdlZOraq6o+c9roSKqNFD+0GW6V+jwjyjoYYhgo0PuCzhFxiezT5foX+8W22lYfzcdyBI94LAWlfIN1GcnJy6z9/3ROYRGRF8jz+ST2XQ2D+EMe2Q0ZXYxHU84BaERVAqL0KHQFWpNPDjFIkFGlFFA6mnw+yWe8hZHBQt5HEXpIoEnAjNdoUdZnyCusZJu6ZR7jhTFTKJAc50UqhiscTe/JJjd6cE5VmzVsVhLuJW/Qhio7A7WEVYUEBIVEDSMnN4qabLo0bE5IcmK1Y9lS4QsT1N+GPdDc7m3BJSUX0GJiL/EtZI7cIapTAexVI4ijhB/lJgYWNylAj2dglFpgP09kJUSbjUgtMJ9Bn6gp1nKpKgxbaNM3hoesnmdbsSPNg5BFMuczaSaaExxyLDxWb+X556J28TeGa4PUZzm8SY/tDUqcmpuZuvbQu9hyROzukdXO8aQqSJIWvjtJJ4wVSDr6dcC6nULkAYspEwkCvJaip3Sc0HMr0o+X3J4elHncSoQPSIkEUt1CWEBiWFmy0JcwKRJkoVmyPj/RP0Km8v1+ZnU0YxI2KGFWrTN4+zlmP8/PTo0oQY3K6s8hmFboxshmET6AaL3Vy8cs4pWVvkFQ7IQcEK6fX6+5xYLW5AXkO5TjDoqF8689McdQoRqvPDLda0/r0aIyqUrOMMcnsL/T3cw+bEiQHkBYWYhBp5WLW2izCr7fCWYtzizMtld/PzefpvUnv7FK70Nsn38fHGzf5RPBjnTeCQ6D/XDeGp0iKrjjplWMO2OFxwBr0s9XI9cwdBC/1PTRlBk2aISbf591GHCd/zSXfQvr1Mq1Dl8Rx+PBn5966Re5U6rLDo2O3ZSF5Fvkcisn6uqpQWvRinZ8j6zrjtayv0WedJc4xuCw/2/SPn0BTfkNbifOAx9kjq7gjmhoOLqxR4uKJ6JwAtmVBoCy8L/JQR1jbVptl+jjjuMXGDzSR2SarLXe+7rHsgMzs2NQUf5TscBCqSZfsSelHOyfuLLA5zk8WjWtxtuCivMzQmh9mkLsZi9rmtGWGx9f2VJF9OJ8B8vAb2kccAeTnialG68sGkw/X3I6SDnVFQwkHwnOmKignyJ5wMAU/RX5213n5F/I75DevwbcZZbf7FWxC/oR7J6Ua/9QC47sfkaHke9nZSJ37A4fIYYQIHH6Cu7QWdhAXQQvUr5thWnrDclgG1HIkne0oBxulggWD1QXBvTX29vWm218WIB/yrnFPh3ORNizdaI55KF00+Arpjr5pONxhafl8ce4TxPncga+a8OP9tc5JuE9usuX1ryn71A5tIE7SGuDS9vln+RPUPJzKY/82BeF+yW8s1/d9kZD85qKg5TdS30a/OccTQWS5oS4YLYoJtwXPV9m4qonkM6HJSl+BiKet0hGqmoOp6ckni8ccSU9OOVZPLkxLez4jw9alZ6eHhOq2RNoV4YQPw42Z5u7DDmyOpP52ij+0DqxUOjwTdM3rRxkHOI4SWZQBuNKCqP2qzJCg7FCLJa0/aDH6gAxE68nzKJOU4HMIz1kVzhpcmpkWW/T1vFjnP1DykSNZx4+T6hx6Ru87dJCetVCrVGp6R360xwruA146O0IcEVFzg5FrGbrgrDCbPbdfg293nkMeHiqvDM8QD0Q4l6FYbTm3gF+ufdozQ5Ehz/Qk/Pvqnc24b16mpe2rWQczMwMrpHzBJLlzW0ZGEwqr9RtLftSUmH/Xwc/8wwGa4gytBExuAM6SsIw/84XupQ69mkNhSjDM4dUB1nBsoY1VKAI/HoaeNmSmlhJQmtKUZbKZMuYp8dNcjrdepEz31/Ou+uZaGCJPsVQV521W5uSFBfG9JiJmr19uK+H+4hWeRqziefuwyPzL7oRjHMFpa3dW4ercjKgxv/U57bkGuSojc9Jl8oZPrIHIYXL5QQ5BiLUiWh3PFXDw1SyVKIvju7wy61JTenBIMDJO7PDyoGKRCGa5+2CM/hQmHZ41UvY/ksmpBA9DGD12fC5SO+cjn1u3fkVI4ZfD1v9COm/fJi+qQ7IMkdEp0zUwhfwt+53saTp24Eo4ol+6G5xduHtGclzV5/TfSXEhAr4ImTjsvv1TT7q5ttA4w+srtNOBDDmjXBJ/OHZFg2XcfPPgYO6hQ7oFY6OzDRHRe1My1caqtUFXv89FvnjEymtFSU03VpAL0wcH09H4vjdarB+gO+nxke/8IuxrJ8eOeXNa5hHiYCZG71Bsp9cnRHTsuY9w1Zz74VipHRUENpHPI0QOUQsceWFJ5baiVm2GQIJWOM8Ztblh0dYd5Xjazqy92W/hhyd3WRovdAXYY1v6s52duG96avSjQ3S23E6cg9F7YWbAIfYHLGskFgzjPBg7x6y/B8Cpx/qoFC9CAL1BTQIUJg+G0VvtE9X449POZ+un16n3ppTEmKOLeL7os88Q+SvyyEZC8kv0+edIIBr4lBzYu/fLPQRvYruzAfdMzLCU3Zl9dzE3ShdoVSQHmezlQaXWgAwTwlvS+vG+tBaSjBujjhOja7NmzQLuxUMbiV6ae38sFkt4wF9Fo9IpFRdojDgyTby3gEbXpdalkF6tSgk02RJaVHhRmn9ctFWcDtNOkoUyDvpw94tju5pNY7piuFMgkJl9tKJosdwSU8BHjNRUQjitAjKbMCnHWPGvuR640zfUJGYwMhk4WybDx6Wn56XlLT+2ozaq4OFD40xmvtkvRR1lNoc0fDrRC3e+gjHpPNxLKOiRKMH+qV8k/A+jUbueQecB2wRnJDFyePSIkJ9MmaLSxFqaNXhduijKbBTa5TJP8ruzKciWuCA19Ul5Ra2xqkCcVxcXaq0hBI0lzng8MtUe5Phguh/h9IX5I4ORxsC9JBJ8HInwdOdFXEw4n0A/kP+auqg7w5zY1D8JuZGG4hyLYwwG3PNBD6do7iMxK2giEUsbzT3X9sCUYcSWKNemnNplR2BIYETg8wIWzOksItqkYhQRmUFGW9p0OX5o4HS6bnazqnKCKtFqDTTL2Gzi7Xe/xwvILz/9nOBxYw8OkPM2ohm73tuYtWsXwZ3Y4RyLC7MTTcUI9d9dzA7RKszSNL5eZMwLDrIJhNF6NKM6I6OaXGh2BEiV7uhSFbySxgqyxo4tAusSDW0jniSEw1kn9K85h5qC8VxmNDpju9wDJWu1mcHWmMJe1Rz0CmlyoBjyuWtRW+rD97VnRswcGzl2i+kP5JuJOIRHH4UQeNlpkc2fTteR/8g4RNZkTItIql5Efoz8k7ps8REDWanFjPxUyIVSQE1HIEryAFNS64FG11yNnvGYh+MkWPd9XnlucAmcmbYYi1ILIieOOOefErIbfuD75fhIv2zyUpJjtOHZ4YbElaXIje+3UMIjf85FrzvIK/SDuI9kZg5Y09INbEVNmm02qmhtgYAvLrSZziDPk5U1VdVOI+om18ckDQ6CNUgAQx0jtMChgkbgIfRTuMP4yWy5B2kE2tGxZmTNnAId1Lq5o8HZNOYfP//sQB7kr+T+AE2WNtgU3xCIG8hTqGB0wSOd15OT8ZCapAqiNKnm4/E14Iue6UlJpR/PJefn5S3Ou1FQEFsKnCmAs36C+r3XkfWGdNczlpRfUfNGOuy7yrA+LfeEquSziFFCBT4BGVOPJNGF6NcalXylv09pXH5CSYKX1WhPjPyC45vD5d8m9XhHUGCKSm2dnoank+OtJQn5caVoLrnYpGMykhmEn/+4Y8eOHn0TrWk+mhdc+9bpV+1admjKx8o4tGJNgbMP3Y2PMh1GHLK9/eZi+kWhIiHE7ktEEP0LwDbwuVR6RVQ/4mb3IbyAdi+3e7Kn0puZ86dIP7yngKgFlEuWiYkp/eEpdapYIYcXHpHnl+Ir/CLDK9iQ4Xxn7KxZaTNmVJOfSwLTVDJLTJUEF8tU7rM8PTjk5ZkzDbFtTc0ddlurdeKqQJkt8+0W79LczLnnC7qT0ORHMh4hTmU8Qq4g/LqrnOW4e1pYbNntqc7rSTtbAvjbyXe+AB0Jh/YTa4kIzAMTQCwMgFhou2fhoIfRNkPtOGnBZggqjEARUYfRa0fEWucpUuSR4y0h92tD0g0htpRO7Rr0MjkNJZOXcjPwxkwyRIgO7eNbo+2iVJXcA386OTlLxA4oLJ/V5pyIE+mxUWVfLyD7jh+PSiMfPnSofXli4mx9EJ/BSGfgngLhOODYa2gV4BY5jRoV9Ewmi87fI5HgT4hFNIwWta7EyoOBif6Mr93u42tqXEQGGZ2JPLIQK9v5nSo8I8hiy+kKeccrjBfFMfqgYrZJYAk0csgplyQFShSgD47Sd0qsXhozSVqMMj+u0EeeJnkXn4nz5j7zAnH1CprR0Q5zV3FmtmXse4suKsqlMlGZrCOgRK401JOHk5O/CW1R+kZHqINXhZsEsTiHcHNLcvf1VlQY0tLov+3fSmyG0ZqwaGqnSsv681YKazjBUrzT24cPbJ7cRxb0+sVmHNraUzVcribCLNqOWLHTuqzjJkQy0LdoWj6aTn4sC/IWi72DlAwWzs7JS1JXSkitf4M2TtUmWSIq1KoU1J6KMMqIwsSTNvdY06KqZrQIHaiXINc6yC91EgIhguOvT8MDVzeEaVdbyU+Nq8JC9CvDIMJHwLxrHREMI4nHUrBMek0Z+B8ejIVeU6bVMGpzgXpiRTCyhkstdVAAXAmAGuq5URNn6NGdJTIaQ7WasPAIAeFfu3NmyL4Dqj9CNUE1O2NSBAJUO+7aXS9pAF+jEwXKvWFkzrvmaGRuI6df9SVu4th7bt49ESEatR8BL25I8HN5k+oi06OnVZNq/+jkAzUKpTyxj7xxwl/sQcDoPQXiIAMiE6MmkfuTm/fvb04GXBsydAjmTO7U3ipEBVxP72JwqaUlm4haqucSx+3zHsmxvrokZsv1YH2qNkISHGNTxFwRpDYi9/ObyY/a4nqQfV9WlNTGCUxoLt5A/kihVOXQC8SjBPVr3ZrRKPXe2qxLVGaXMWsBuTMJPkkiCfkpmnj3ZdRLfob8SaeuyLDtWnJG0ptrDSk259O48cqYerRqXdaB9PQDWevs4tAsx56mpiPpaVq1x7xpi4CuBsZzkhBAXKD2AoVcGqrjeohc9DSMycKnM+0DfRn98xJYzt8mTI3xKPKy9/cRfq+SP7wxw77wY6T54O7Ls19CzJfc3iN/uLkabDlm6ACxASKoa9VzeM2TDjMgHxHL1T295klsuDuINvkFu+f7JGbFHTGlRhxOIInCTcb86E3FeIHDYZvN5cmfeKKQ/LEmqg75lZITK76YKB/4upp+ppLa6SaCaQzx5zk2JTELFduG/d88ErKV1O8J4L6GF3cZlr5lDntma9jZs/7kdjSBvPoCL0EYJ87mBj+uyRBlREY/S76Ao4lI1r0tJM+wtWvMhuTsjK0VDsapLF2dRBfQrlSEdIcH1OVkHXd3UGgtDGb9BwA1u2bSCvqX5+/l5+HsTGcJ1nAupt4ji7/akY35H8/cXXxm5cocNNux8iY5D80eKc4tcVejVFHPxaMfUl8wyc1XU/EpZFlqKjqa0kG0wr+UpqamlIbUxp/5DZp4TZPwTXG1PENXTf8yxABE/zLgTe/Ky3+3Ae5aYaQRMHBJlInsqSZpUpDK83fcO3aLLipwTryse4xpbHMQfseBUvPwJc5dpnC+OzOXyfCSKHAsy2bcGZViWhWTOjM1KX3qrBJnO/7hFmIjlVODKOyCf0Zj8CD6t8npHYnR+xHDM8ORNX4lRzuCWiGr2igocGyuMMoW7W/Xyj1Ifva8eWD8K4gocjmSktteQ1+/6njtNcerL6e3hYfxmEyHG+Eplud/8glMD9vS0trIded74ZXa10f9jocbFj20iagnNJBdXPqi9gTNww+rgapGHpRwo3bE4brbsGHhfV9+mf3ZZ9kkL6BYmiwsCkRpu7J37SK3csaocrU1XLyHdNC75I8+wtAEb7NHxO00P0J+hORUuer4LTMg5Zd8jI6R24lBgvq/BKjfh7f8xYLpDbfhSTHAO4F2ZLcAoASLrxUN757i2frBNSHrDoSrti0MX7+Gf/MDhF+4kP9zqzPQNzsgJSCPg2JPDiJyr9yvWJmjLPZFwtZ1ttz0ZbVlq7NTstbWZ7J8X8za878Y+w7Apo6sXc8dFXdZvcuqliVZstVtWb1L7o1qAza9hA6hhBJ6DzX0DiGBQCCQ3kMKpJEN6b1s6maTTfLvpqHxu/dKciH7v/eEBbZs5Ll3Zs75zjnf+YZyEL0be8Bxl1luOmG989MXmHm5bag3JAinmvF7FezdAR/DI+giHDsQZx04B4x2kN/J5s+p/MxVENAhTQLIlDSwGeZ7Z5hGP1A58krllG1mdJzdKvPKhrDBcFa9yCFqYKHm0uLm0oS8mbEAyxs9tUOjdX/UoQvMaW+HyrFng/7A2aEnd/uSR0ejh513VyiMx6uOKkYLTaKRkkBe4h9evvfb5LBIbNFEpzhm3mquVsWap+F709l7GB6EJlJ/nzgNoRbHdUTnLrcPP+DGITN4EsZlntkLI4ImAufRsxdGxb8PDyJmsqzSHB0nqWcoHsqX5obzlAWvvP8C/kDMkkaFR97OOvkE/rhaqqnWRysCEnDmiScMwSRmDnr8Q6/PKQoMVbazOJzxqvCqwKrgHeCs7bBNYTpk9a9CD60KMW47OEzRfn7qjjsI+yLv3YN7CELjKJZTl9OeM4zoVdWQGIFIUqUTCpBIdqfTU4oyOz7uPguIX01/cTtb/HD2XyC3/+LwmMZK7Dr4AK1QEJHbRPRCd6dlVlBbgr6uMkYqq8BwaoS6lunkVfBr2PrQq4U8gZLh4zrKmSUMdnFJSW4+NWUo8XJ8Am/J0ddff03BjkoSyiQDPPbKKzUjRy4zWafoXQxlR9zeOOU47rf2jD0Xlgd3jAH3zpNStvBqWVpWrUATpl9bW7NmKHPWuaRXpeCKlBoHiHpOaUWVR2ryAzX0tn/Wcet/qEevAUZgC2HlFuC4YzQeIQnx+4KDpDRUIvrJib/TTwUTljQ1pSY1IvRRw9t17zagD3hAANGsKjCGgn4A40ErRH+CMRg6BnIhuoD24+/r7D0KD+F+RkqyZfAdmX5rrpV5U+UUHkKz/15fnzpa9xWaBe5A94PGJGhAF8EWMBS9+A+I9juAGX4NauL3JPZiuxP3ENliYl4fwiPPXDwezmaLTZiWnkay0K4YWOwmfFsWC+K7qct6dI1p1LKxlRNcx1Y4vpqwH5NT8AiLazR1S3vEogIKtRCiX6n55tnTLOPH6Ypw3FO++pHWiGvuvlnM5U+P9m3+EYWTTb9YK40sSm6STpRNNQ9Y/F23TXd7bMPGDeUYcIygxD3bQqgiVSHJmlq2uoKPCb+nTj6dyVbcRJ5R0fqHqQL7WYwVegmvgl2wLndr3Vl4fgf4lsKgwNKo3yNuKC9nYfhAn8MgXdfdE+geoaFDbM0XzbmtYhY7wBRzQJRZxwJ8iP7Nq+OhS9iQWWjkLJtLSpbCmWVlY0FHz5ia40/t7XKMWHnvEUcnYeFVuM8ZB4Wk1SJyn0b8RcLnZTM+GpL3pGJS8VeIb9jT38haNuxthSwvyrI7vcLUZ2BV+E/wUCg1t3ucNlp5yzhA0y+RVMjnayBWLJZgb2EpmcksolCj92BNqYsYTP1ZhtVhqYeO1E5dM/lXfEXN2L3AC4pKb5G5tdOFBN7j4LM+g7RI/r7aRNbwZyJjGp3bv2HhALode/DNXVrRkjA0GhrX615fwSkKFfJHGlylEg/TynEJbSIB+EKCyWN+n6hRV8HBeC8CCtXQOcrfNUyNo9zVRy0+tAnca663Be5ujk9xFNoWBFrrA1xpo0QrbZLqReDn1Ey7R0qhNFExpk6LaSy37Hpk1y0Vo+64Z7diHunbD8JFOIIsyknkNOS05HTga3hgVg0yye6i7JfsPkpJ9meIlTSAZ0KwwfG/qETukPiUaWVDe4Tvslt5XlVp/sdOpw73KmVsFg00AoYcdx+lRViAoVEr2SpRSQIwVUqPQsHAEomXAkAVCiF24plGALlYqkBvFkEYoGC5HB72N3QuiB536qgwjIecAjHQzNs9yyf0TdgwF71YpuNA4nWWHJQt2Dk1KPOPWTs3mA/i6Bz+lwVLXcXK0U+AQTyJtebo3Qan4dEbcaaNmcyB5ABOJkPQ581JfMMn7sbg+5N1KdkQlrjwHvj6O4zWYc6WePF7n8Gnn44/8gh4JiH0uWvFyTJ10e+spNgpjLLRSwyfoJoTZIO5iQRY5rfGxq1ssEWnNMccMRgDdRh6KAY2E1deJaRQWij4ahVhm/WrtQr5SuNPhsXlMvkS3T1YitDTkPQeg7eQ+6WKZMMNyoxmNgV7wCrtj95IV0kmTUsbJWGfR9SgLStGo+XjRGZ+lxrURWdUh+frHn9hcpwxPDWkyLb4qaf+qKuDQpgqMVpEFEo9Pq5SGSgTTVJ4VeNL0Vywf/08R+jukYktJbQIXcsJF3L3JZaDjTB1ibCYZfiKmwrZOYXp7Ez/SPGVROdTCLNJpmSyvCoy4FcNTgekB00Ez1Zy5IqkyOdxSWIOzfsAXfuycO7yq1eXyxVMbr6wXfkISP2kaBODXEOpQz6GX1vAq6u9coVfo5hGK4/HIRumCo0WAYVSR4EyHR57smL0ov3hO2gg108tEM+2x2LWuYpCv0ZTtk5vEmog3B7eiVEp+dgymCJ5qmYcjc6FxElN6b6PDAAZkEHrg6Zk6SZbOEmnnZyDlhOxfGa99dZDWqtKoJKy5kYX+R/944/buBy/UxLMZUyMPnMjyrGafaJQqbTwnkgEa1kUnvC7Tk6nBigUhmAfOgva8HXdNiG8qFbPW7SiQG/fCNeFnoWpIr2RR6PH6bBAKMK2wNR5HMfyerfidozIz9jSmQsyiZ5eGmS+b1B2rP+KwM1j1maWGPju9nD7VkPPGu1y75M//hj++usntU41p1zGBrX4HNW6RDG1pvh4OPxj5WKZQTavEryRehI0bpjtiB4bM/szoOgJTYLjQz3PWXQUSpAC2QLwED50g1VEzA9WLJNgy2HqtWRpl6xWPUZBIKs0X8pF6hGl6zW+bG6sL37E77YTHy9/4FqjMhUDvsKvVqNi8ul2lRTDo5X9N/bcKNLlBgur6dovasQJISjgF0xKlOj1flELrzi1Cows0ekc/CC35CXwRCTyy0svYXeHw8JQXlnxsBJuu1duwFga1lpK6k+dng2pMTomkm7EJiCGwciFlDAVSKTt794DTlO29vTgsR+Zwz4GZ8MSfAcT9YK2nO6bdnE2yOzLwqa3SX/dnTDUgJgLkkBBNongM5d2QUQXIIkZqZn/RqAgPIKvDPGr7TZBQCEvQJ2WO9RG5Yoqv3F2va57neHnn8d1FUwFRY25jXN//hmU+/3DrDA31yIrrFTV1CqkvIgsv5jDLIbU1G8VLdOnu1x+EyzBUgydkU/OVpFYslc+t7xWP09+AxRHZjrd3juGfeUfkwfdUFDiKS4Y70ensAIs9exVZplCDTGZ4TNsuFJsY+qLK7mM/EK2pFDmc3kw9EmVmGgDyTHglroeqkhexiDI4hjM93XyOfgtwH+0mArVrfVNom67hYfhWxZdpQU2b6i+faWHjr4CEgyDTRBArHMCemJatQeHJM10yDJUtP3ZdvqNQz2BYZsf299U2tYBZV5RI8mv2gUn4L9fQbLBbgZN/V4QB1UwjcedTNJ8MXEsOAEW4BYmFA2K2k1lDEjJB09Ry8dNCUzpKs2fPY9aR72PEv0hLPRNXQMal46tIgZ1eZLXLaLRGmiUYp15CODZL13ZN6Gy547T99e9CJ9Dk8sE/qL6fDF4NBZDIyQs3BZxcbQ7GxJKCTqyeov7Max/3zrYTlW22kcsAycg6x8qLpNQQWLA14r0NS3CYXwWyMNW0rRRT6Q2XEZbsAgDk0C07sIFqIyNSf1N6rLSchtzMamUD5YOAae/uHuEpvngO8eoyTM31kPsBmptxR5OfYFJSb9EVMGqcAxHnF6WA7Jh58BcPBllaglszCO+6kPMGUpfX8IR38fwgvjE0/X3phRfHKxP+ltNzXsMYREf3Ldw5uZ3J45Cm7GOUB4EPVTchokM5dP4k0uldGo+RF+zm9ZP02xcL/zsh1wI5sbUzrJhNeHKuLXR5zbVHo9K9FLP7Ih3XM1QbMRbfl7FBmOFiUXJx99MVlbaImya0ar0lc/oDNjL8Wty9G6G88lVoCGv6f+6DoiaPSjTDs5fE+4sU/TD36mAioncHhc/UK4pwRcpPEwTJVv8jTEBbdFiSgKm3gE96BBw0XNvCMskLGYez889BC5d5UcE1zSakDRShHVNRBdnVFkEdHojlcJQqoeC3KFPvXik2zh026MPJ16gPLsglpolEqthUT2dwzTeE4vHGx83SibFRK6zNnxdC/EY4SBuewoIlcebeBQDcr/pBc1npnEDZ2C6d57W02gLW4ZuNWCzscI8sd1SJRJYbC5Ra135tOFNu5fWHLtXXlHGYZeVyhjUXAr22+zpqdswel1D9fh/L07dGXVXGLkY/uA7LGer9UFPALxORbMW7a5+eMWbejH+DVAgFJcPTavGHsAjOkDmPPvYWf12EI/j5rWh2WDLc0uL9oF7bi+Z+DLYVYdawbm6H1i0OppRUM/i/0oqOR2CR3DcpyD7g4n3GYBj+/EREYHCI682oe+gacIYb0+nBvv732+JMGf/0cUcPRFwm8D5BNGfPuvOhQlPfPzCCYk3WbRwgUkUFnI+B9Mh2oWvGRuOeo5ABT5mMlulITkM2fxwuiagHVQFIYhEYCuamUC3gB14PDsqAbrQ8W/FPcpaxQQx+EY8zBbQjxd9HPvjj9juGBgP0aHYROcuvU6/q+qyeanPYNxsxr2KG99/e6AlR4Z7xzIyf5LOnGR+sfWmFCs+Dkhk7nC/T80W8fagW5PoVrAefXxMoXFzzcXSZ8QORkhUdRJ9nHwXKN9+G338bvLtLfELF+LTwIlgpVJYJ+Yo22VSaxh1TgPd06dPvw9/Tk8r0xyCu/G9wyB63kBW0Y4MyBXcLFAFv4ATqLMe7QTT6kEr+jD8mk3V8LAfG3Yqjuzg5TiYDZcl0MuyedpI9S0SHMfU9R6HU7Ffcnh9ldUsUMymU/ALwzccWzEobMGRY9rfgymyDmGAJ/Sd5IvKWAwwDn32gIr3O4gwDHqfGHf4l+IH3nsPsPS7agw2q7whv8TDEDKw86jm+46AAnyduqozCSj0ZC7GlYDPUiXY1qVL/atX49dLoN31UIffefegUQ0wB4MxVsY0sP/Ce9yiHM0PFHKkt7m7ZWoOg53HS0of+/zCheT586/+JG6W9ur0/wIxjsVqF/llwtyLdYBXeV+1WWnECml5WH49tbBQuilYdypxEh5LnKrz3anjtnrBV6nnjUYu7mKoMF8kA39LcQlEK+vdDe/FvsSxCFFrzGH38QyJ1rdMG1y2ZJ3NQX/Ft9kS9ioe9ht6DgxNlYOq339vAaKzqpk8O2+mHNv3xPFnNgxTDl1w/iAoqUNPost40ONJvgGvJcvFixRO5XIxvl6JfMolfCbTa9VOdhIMSjXjmBT3CcwBA1LgN1ORTctTM+FYlqo/9AOuucotrJaL8796mMlAzwsc5qjJJoBU9GZuYRGgxtFysJx8vlCzyVIzWQqaNAv1VsMU41fXdDoWlRajwXy+6CIYV2ntzVlzYVOLIbn0xCKQjAm0qh0dHd6O7SNWWCvnVgHJfLPdOZ1I0uOYdA+ZcyKkkPCBOvpDl8Fc9UHEffCjaa21E0wd6nXaj+uqhVK0aJXLKhCLGPoVRtwCbEWXQH06I7UNGINHKjHGFI/JctlTrdcW5FPy6uhFBWW7fcmXYsewI7GXiK4Zee9eeBFDOWqCSUrtJy6psrfPTtpMClFXSbOWyCwjXPPa7f67ZhpfW3B71CH1uGM+j3AXmH9n0Wb0yHYsoO32L3sydd0/x9VROiExtrLNEIt2LH5q7dkNXWXDVx5be4Oq5NVxZPRFdRP2uEe6wLVDU2wrWol1RXBi7sLRCR1H6tX9LGn2AE4VLU2OUdkJi5SG7nSCbkkfMEIn9qdkSlmZerJk/PRTQf+pW5WvzR9VW7G8s/a2g/pP8sV5ddpDnPyGIgZ4C0k4DLBPO8Qx/7nUP9xjx9Rii0VBlofp5d64XtZo0id1UW+iZd7oc522xYB21Ke8RVdybMRE+tSmSIMp2jTP1FgLFs1pbVhAMiUOwMewf5P6PQYSpdcStV6uyj4Y6fGzjAOiK4l4kRg4QePRpEk+RPqZTuBwTDIy9rfFDI/RBx4O6CoBOGq7PZxcbFubMDkYPDCaX1uVQOHTYF9BhUppYqO206dPmxeeHst64O4yRoJGxxKxWOqf9MKyg66pEyZPckyd3XF9WzK5/bUhs8HLW7Z0zbqQjJ+99ciGL+i8lWTV4hg8C/Nxf1eB45Yosa9V6Sipz3mSvqCfImHX0DPf5/EG0ZVUmdIAORsnIscLjUxXeXvJG2DrKsYdX7MsBcZT5Twv0+fSng4jgfaNAiPbs28ox461r7nS2PTKOuWSR2I9LVVY9ZBZG75NHY90dtWDh1c+L6sXKDAsROGzI8UMUZdYwhdN0AinVj+/cqSwtE1amgslHamFYp+uPCCN8m3y8KxgcE40oAGlw6vthPhjzo7ee6Efu5zu8eWn2T04ulUwd2Bnm1I/YYx2yL/xw7Au7Grqc4zUKZL2noLDcAtdSlaR4KCWH3zV4f+1DwoQvSdwWAFQNjfUlY61WNgYpAOUb7KDY6jLaLa3bNC1iPgvop9BMfZgan2NW0ymbdg6bRdo6KoLoCXg9mqLr/XqaIa7HL3/PT4nZfiaOoh9Q3Ylkz6RTWS5Ce5utrEkY8nOY3MaURl4P9VSd7zGYz7djKl8Zysdlrv9gA/+hirBWnQZ3W7YmnCE9jtAovKgNeI+bMLft673DDyK23LiRGNBGukM8IEKO9FCSgjvwaMrmHrjaNEYJSd1K3gX3QFmxT/7DPsymlph1LMoebhzE6ixcdHUdrAnhv6Dv3Mz7stXQGuGndfn3QaYuAyLYyDNCltYfUrvYBpuQ506bxlbrixyHzcGLJsc4IOOGnS+DltSj0TgKyTCXqq85PKKHbAIUnDUVphX9UCkPHrIVDy6KpUL9qPx1bHr1/H5k+Dx/17cpgjTGX5iytIbkdyB6fZPGtHdzFTAvchsqQe/NKKO+qaxFZ/NRu+DhIjVxmGD+1JnwRnUgbVMHoeUkQhY0tEau+fLel+yOGlO7QYwnec5Bo9gP5NzVZo+T4R4f6KbemCS36kgMP6j2MjUyXrwHHJj+1IHOeDTAkhTD+8aKpjmr+bBPIA4yofhDOxn1Ou/HZ2YtFvqrhFSqfUUWKws8ynOBPG1MaH3MdyLVGS4djUkMu8LmbLTRqUNbPmzZQIMUrqxn2GClVa5gv52STNPAlpSH6LfQG5kyRJsHqDn5Trc5R3tOoPLMGfmj2D4wqUGLjtapokqJNQ8DBvZ2WBMHh7HcPtiqQ+wHXEEYG6HSi4nkHplubJt06JoZPm2KIdVDHCEzhHo3fi45TjmIbpRhWQd3fD/jvrgQBreGeXql1rO/0f15um2Bk+yqnWPKcEVgXvHr9v60dpmtLS4eUESa0qiCCEGBWYmRN7yjuqoNmlLuBw254G4QK4IzWry9MTaS1pSt4BFaE1t+MEH8VFNw9dJJ/ZtDjPDocoZDLEI5qidRDdMLW6fp2H/Erhd1eKoSlGQOhFfC75AQ8Et4S+/xL5NuassfAjjFKxAIsWmpqhYMBRCncCJrv7nwTRn+y5YB02Z/o0Bq1HtVFTRBzet8zOODffAdliXRN7k6JFqBMbMQttVLFWrwMpr1YcCpu4nXWGpEmxvenXlVPAscKFpNTUgqhKHY08tVbEEAZ5HHJI59V73xRaZXh8dsz8Q+9vfiDUr6D0K74R5ZNxRmu6eSwc5drtaQ3h+9oB7/zN2ItUJZAG31+UVgVuAgr0RPXPHxiSWl0QbwTy0EaNEbr17+wh5+6Z7lv5GNSe5IkqKC7aj6cHQVUJZYUbvfbgtrSbvr+ImtgIJ9DM2gTCrToJWN0zgrq0WxdTyvNS5JMgpkdM76bKSAzgAP5C8fh07lVqor+BAIplUwBdhylQ79m9VuyhfVK+4jvYk3s4hc5j74URozmGRp9ArSZ2GLLrJNOtRCU7qwDU2MbWZEmvzO71SkCjgJ/L5NPQAVpZ6f24d5qxHY8ARNAZ7An2+/fryquZ1h6f/YLUVCULC93allGA1WuwNPvMMUTfg4vbvKagle/rTnM5MZz8+wWrCVzrx30VXDEavKqJyBQmkv/GTcF3s83Ua9NHmyCfrz4E/vgQNLLNVJtBL+bQnY2g9kEZ27MDyPTvrG/fWhrbsjO8I86LRMTcqq3hUmKTgsFR6Ek2aCqaj7UD/JTGiIb3n4TzozNx/DYk/b54Da9axkHViJiFSrSJO94Dz+E6rQxBQSAvQ+vADBXxaA41biB754AP/8OFAfO1adWcndi41R1fBoVDwxZ/PF2LWVAy7IW2W5AvjstQqbHs09RtYjJb7iXMnqTmj8bV3BkfB6ZjMStYfs1V7Zlrq9X8r3WsI1kambE80scIzKBxTiJTff29t5ie44rtogtxYrjj32IPH8Ufq+YkTQeOp9MMQSGBltWouPqOr0K/tV7rzm5LKoUwGp1sdWhVaEdxSB/68sAo9tOK5LfjqGYkj0jtJJglhY4nsR4boQzz7bpGC1i89MTChTyb1SYsLVT5U7t3i24KK337bN3QodgKl2MV/MA0GPdOk5Ax1tblbPXdziv+DhbAf4cvX4B0vwMupD7E1wVQKsHxKdE2jZUGqjwJZss/Rv0EB+gqI0INgvcGBh0D0nM7effBY3zgJdpKH5Omq+oNHTWYiqX2vZYJK/GtqxgpROX21x752ZuyO4NWrwc8+S7368cf+0aNBp6+ry/e9b8EC3/egPYiuBEAONc+7YknZnNtseTDiPuBQmHeFsdIJ3m5stNecui0C/vwz6WvA6vAPXzw+Fd148UVA6VGIkyMjOp/Um3AyylcLh6mDhiGlxI6dgiOuMdi/+jVCBuI0wgBr8Fmfgv2nMXUSG4nkoAd98d57w2HixkN+P3YjtQWbjbiEhQh/SFi42fguHItHjMS76Qa/FxxAybGRCUQtnyzs0QlAOxv7qT51ChturpIvcIkntVmmT8kD167TsAT1/U8pgOLc2gM7bpxxuWB+6lZsferv7spFFtcEuyuwdCQVxidroG1oXJHPqdiEj2IWPj/jsP8hR2EfPAp6ZlmnHXU2r2nPCtINSADMwn5JpI5gY6p//+yzrwANQrNPx7VoRBhGORF96qmDBx9+OPr7BDjixl12O+SkxmIHj7TUtIiaRFXlFIoHgyW8Ak3Jyy/X4i+6m7CGHBJDbIPTMvea9ACDRkZynhV9VR6IfzIB0uqIW2z/eC9auf/TTxPHfv99Ohx146jDDkWpLuz4itBtBH64LTQWjkFzd+Bx0TQ82p2YmYG0Gof7L/Pwv7v/KpqZl/WJ2X+nYX/GUtux6YWS0xNmHBNvnOSw6U1q2zhZDYsLnM1tnXuba/BBOL32C7Zcy3lnKPlHvCDy76ZJcOSNk/iECVOjsaPoqL/SWW2uLjNpHEZ1hWGBnV8qt7dayqMVLlB7jq5h+NjltADdxveLHXR89JPxlTQF+7NvXYpx/20efCVEisGZVrEhN5Q2PankhiJ2FDn6yRDEU3dgsxAAG9G8EKG/AoTozQh4IDwH0ChFa1bxRow30DBK3boJorYJ9h7YdeO41QqluHu7N3yXOfTJyQ8/XCFyMzwjZR6u0aIsMHBn11T7qxwcsiPqCNwJLTiaVw/qxlRlke5NGRorF6yxJZL2sO3BaX8CiYQdZ/JwfP0z4Kd2gbxPPqn7Fhs/byxig61ub+2dH8eDIZarJo6uoFQ0CmD8bngyjv/W0t4H4Ckox1Fo481KMRllByb+hNnEvQ/7L7oO1P6SSMY0EWWRU4BJd4V8fr/P4hQOZU6KzY+/XoQx9bpygV7OAXRsdXx+nlRux7ewVUsrwFAB1fV8tbhizMyZkcmTraEF9rpSGYQQ49rMoFMWVf1A/ZsW0KjfRtFRbTnpq6Cg7D6jCc0B83TojFpehOE/XcI31RSXiuuZ4UIVmBpNwT+i6D6OlMBvmt7DcCbu1zkku+O/DdqpuKn61Jfz76MMaEiV0DaK7VE7IxiZOTN+yy3l1oNgFWBRodTvdvFiGiLbz4DjmO4JLe6G7lr2OMnCCc5x08WzQAN6HVx4WsXzFcdL+CAc/xn+GEdvFnN/FKN326usAio1ScGKFXLFO/55ZzaFjP4le6fdernV2HxqkvetGKFdUI5HfYvxqFaYY8K9mu+myFbbrwwD/+v1pV1yKZbtel3MxGSxSFDcgoeCGMwH6Guj2mdsFDXwhRep/ler+eGOefMaJkyIq/7gdJbqpT38Mfn+61FR+K0wEf5U2UR0ehMNMlRlw8By0WiHJnZ/W3G0FlEV4gZWklMKmhp+h/9pQK+KSybJuwRWbqckrNBOlSXFU8tJltVeeB6qcFRjGcRf7KMzOO39ZMuByyzN2CCuiJDBwGaoDqyoWrRPJ9+8qHL1Wu6198D588lPOlNv0wKv1bB0k+bOjc2aNaz0f8DuOwFnwg5n3LNldPuWukBse3ec91L8MDyA3o0v0ohjRXV5ctAWBzQM3Yij50sLHxF9iiOeit6n4SkMDUQ8RB/gADZ41t4r7DRVX8M0YYY1mX5Bos2LICzCU0+sRodALKUHEXR09RNPrAajn17D2Asuripe9jToWf0Ekmzf/smuD7cnd+0C/lWBRQH8Y1Vosb+7wA8ETB+zYLx/MfEIrcIfOaSyyJPwOGTjeJWITCrJVZHGhek6MzWTjiY70FRZ6EBARYKVwMUHxh7AaifbPR8RVMokRXGexZwa5bLmLV01AXwwYdGi2JrcmiD4KhpFx27fDLbc2AruRG8AUz0oB4wwDlyFQrAEQ7P1Bg6VXdvuDKkWhkIHQo88EhsfwCCGToKyRcoDqXeWBoNLQxEYJJp4cti9j8DHobCvjuHtXwfpXedU3UTVJsSe4QC6Nl/F7W+gxX8AO1e1orN8+vbqbwwnJuseG/LDfVu3xsGt8W3bLvyOo+9bs0/tE2DqjY/B9GefTTwB+NWtGrdlWkNwuTXQ1u0GntpGrB7/qEWX3cAeDruCNWE0yusd5e7ERuTk5OHW5CC+Eyvx+CS9KpwZDmgTGancXIEB/207slXcWsyuynpHfj+Cz4Y0RJs3XJz6djVXU8Mqz5dv55kZPlE5mkh1PmkvNrdOmxbq6Ykq/zxzxnPffSc4lQVVBeaSr7mVxVUMM7s3JwQuhzNtbW7sHHoChAxVSr6bwxMlpUqDLfWVhuNhxAtFYHS0F96IoocEReCh55/niJICtbiN08mPShTihCD1KViDFlVebWnxNDfn5OTmOHqfgIewX3FfSvQS20nM2pDTle6R6NeuSU+Pllj+2WCAUK/JJCLxC+1LJaW/6czyu7P815uXZRHYeOMY2ILuBe3oGewZdBm0onP3jPt1G8PLK+f4mGDBfzrL2D6OscTHT13jhfgOTlQEvsxVFdUUl+WuEzZxTOwGEVpM4eX78sTUbnDHjT3gDvQasCRBFWh0Ol02d2+v23Z8506+n6kq8XJ0O3fieEKo5vrZqIfdppSrOgVlwhhHzAmzJnPbJbbSTsFEUZJfxI2xu+pqauocLViTg0BoChw5noFiMoKsJLBjVl/qv+RMrNx0TyiP4NxoMv1pVJJxCPVBX4k74pGufS7ROr92ZWtNubK0NtwtSbDYP3PqPP5Ly6Q7GxvRWxY/8zKDVYZtHDdJNXtYHkGAoMQ6xnU5xk4cucVnLu/+dV1ek7dx0UvD6/0UQCgaSe9puHd8RfnJ4ltqa0NNRDSi7t0Kz0FTX4Yna+v+P/M8zptLjOdEe16vO/er4LVj8XB9o230XkOzQAzOzVyx5dMZE9AaWtvuOmxePVJeuwYEL7yAvrmWeAFsiouc6saKoMpfGYnZqqv3R7kaZaI76uh0tNBbUsPBgyhp+3T06NGH8OfoHDIvtY/UEEuzyJ3pigi1b7TOAXTydMWBqciOn5+1I1Qi4Q23/3zgEPpB/MaB7qZAl/54163qmtrIclWSycPaU7crBNgYJDeyWODb0Yt2PPgaKgfvks+OoQuWN3VpbHajR2I0uJ1Wy5CFQFzurHQdjnDlKp9Bgt4S8Nm1DXYtC3wTCpkjD7gNppq0KsUheC9UknF9OYn7/tK2nb4KlhPg5pydKaTWMcVfCcYeWuiev2eU8BFRmbJZYOAm1TKlKzq7FIxOlO+NVfi7ayHX35zc/OnzU93jHri6LJjk1PIaBF6BrdI5DuQsu7EULsdurMDqe3z1/kY1eXriNrJnVExWcejZJoGBc06hEu6NjS9YgtKndhDJ9Jt+CtzOKmb6ak3cFq2l1TD3si8gV4OVK9B2hFR/B03zt7S9iN5/X3MN8C6E0YNVoiFVVcLh5Q3zNNv+1VBdKsbWFxYUlGpqOWa2rMxhXRORaxSBOaeqfaZ1Xejt0OgNs8xB49iZCTnDrPIJfPxyk9eyqU5dSirw2nGMdwqWZjrB0uuA5ewrx3HoLHjKtuVqRRt6vfqe93PRHjCphcyAhYTxIR/N/OBKfAyAh+r/Qfm6voCDrpPcpP3wLuw9smfqr/1MWSuHccovnzKefMSof/6Y5eLzXLQdzMVN1OvoSXArmLv2iUR9+4X5U55uibRfvTV5PR6/niRmv7J3F7wbcvH3lpM6EDe/v5Vs+yHkWDQkVZWwnlxMonvmmP7QM2bd5buMFx+SoKUzgLwRyGekGt4Cb4Pf37rRs9aUcK4bPWRjOOlbMywJqnfDnehKMkkvfuf77z8iGVc1+FUdh8qblWhIoTs7aX+ypokQWSQukezRUlQ8eKRy52NW03N3mkHUjbbi/h57V60LViT4CRb/cdAMcG9zGQPTgG7Wnpp47e4pI08EwqteqKMZ1rQG1eFzHUyv9yws7vQnzxTWpXtu7oRTYXmOBI97ytPKQQMUKsmqVIYkRIyGPZDYlG3kfZVhNnZbTdbR6glxa6JHNcZqEM1cVJBbTy+6Wg9a488+iyjl5UUbROoyTLPjiXizNVTTUjHcUWtt1dVLDx6NtUzJGzoyFcb+TOW3DMEeSH2NCVGb/9SaMwt4OEIx41bxCDTgVpGIgMNkx+vgQoizT6CUNiAmHjBs0r5nxUwHlk3AIQaLmafuUYRlY7RAYdG51ON5Pjq35X0/X2XUJKwzLNOtzVVK4YhxhdRIbv6JojJFaJFEVjiJV6oGsTg4kciofh6I0AsLjRcaJNHTFkZ3raLqfmcFx0jJpwC0JFQZbpxlmdIal2+8kBjfQu3sSGx7KO6e6j9y+5GlAnQRh3GTXeHr19PnSZ2EB8jsZ3m6kpiRFsM/Y/9VrY5UZqNzz9aDKfyCxiIRGNIwDy3hVDkahPVycT5BcjmHxmClH2NT73inQVisbH13K9of32utZFHpCRrMF5WuilfPjse2iskM+154jIzQKv+XGBgfAr9/CNoBQwC7HPF4Tb31sSlfg1wBq6mEAz7g4hE61+WuEYbV8gKA/gTUXegoePNpbPaMUan/AQ95QrX7Xwnb3UUWSxjtjNxjquRTqXEaLBSI9kSSU4PBzeX4qCbhCHUGlOF3xEbW2dIN2ORdYfMHqyHyudnC+8AIGc6Ip9bHwQwGp5HJ/6kBFObnh1uIh9Mnq18E4Cj1WPTpbSVqRU+VZUxNBb0Iu/vDXbs+tNqLtU2ILssbpVUqiUhY5HaCB+Gnqh5zsnKieqFKVUTUa3gS8gjfUtwLPgYrcooHzVt64mBW7KWPY5q1iJfqwCS6pC5fSAPx+t+jV9ZZFj4Yb4hcXOBY92wEHQYLGsB8bNLi52TNRcKk4LnF6KdRByLB4L4RaBO4dcT+sD96qCu+Hd4Rx62Zp3cn2WFM5M1dN68dohCSVu8hCayDeqeJZTUgn3A6AeaxSpJFEpBIKFLPYy9SC/NibbX+6qOAVrNwUkX3lEoq+AHa0S9SdT6Hk1+mpOZBbObaV9yG4tIhL6+5LRRCs2MGpdQReJrXMWeIOlAa6YyVRCLny8QYABiTp3HmkNqje3DcUEkyc28aLRyE1fBhpmvozD5Qy7Xy7k+C6cziGKcENCXW3rqNu2ZBomzSfpthZNCXLMttKuCpe0LoXuxtdBWUofcLy7FF0877FEyn676pqS20BA1g8bpRo83e6Ss7qZOi7kgxuDMUOhZ5GBBW0dd7AO6CRnxsRJzv/ctOHOSFyLtGaOFmAM5AHcPMzN+XANPSGoANdc2J94banjmhePxRLRoDHs3NpWCUBgpGLQYN6FAutekzP9JoZphl+pl69GP1bSp5+ZJK7Jblz5EagS+sSFlNYyTuZmVSNSQULk265PugdpZuhC/MyROMUYNTpUGem+mVKvgBUag0yk3HeHfB+2Etvja1ZLxQ85cVyv5rKtFJIjTNXyqJF/AlKylK5slpoDW5iffv5x/9U/Tkk4219kRl/Xq9RwbA1qGLziG0LIT258VnxrFEEiXAQyiBrZp9f52IxW1iP7YYbY0K2hrLI+yortKkd5TPdSkVwN3q8XVX2/OcqV+Js9517ttvT6+TE/A8tOBzUfeXeUgDH94As2jr91uD/00TROmZfj98kk7FwbT0Oh8Zv71q4iq9Lp8hjkQigjadvgTWf7dIvvnbZnrxSiSd9nI9g7XzPsmM5+r+jYU+UZltwsimanXdGP1CbMnyp8l1/8ztqX3u8JpRLEpohC9YSqNFqJBtMJQrfQsqvKb5AVlp10i3otMq4DdZPbJWo9crknq80gad21I1ch6BRtS9x3AsKs/hZpSX+xkFWaVPQuSV3icllFXEJKpwWY2De5eJA16vsF6rLiQqHY1olSzabfXp2mLL3GsbJwVqHKNsfPQpmHyW26molo0SY11JJDZXiymUJqLhRAFeS16GTzMe2L1xeHXT8tt3Vt25c2+D3r9y4R2JVMq826BRb7OSnJ2T8CQsw3FzujcgRCgaANogJfFMRwaRPrASkmb/5XKoZGxqV2W3iwb/AoxksHbza+xWflChKNSMuFJxtv2fLZOK2dieqcKA2y2sK9MUoV4A4qkNr+EP8CyrVWaXDWEjymtQZDalhpdXcCEMUUCRSLBn+2LX6Llu8Jgm+l4YKYw2UVoqSSYDL4dfxV7WDv/HMPSEeadOWX5Hxcrhw4ndQvT8nMbXG6EUaMLxRn0Gb2RryuSu74sNiJAxa9WzVFPqTW3c6WvNsjCn6xo2V/i4GmBq/P6y+sKb9egfGomfZWKG5bp7YrGysSpN+ZKKzvwagV9Qm4+9s4xX46oWBNWlBYSibAIdlY/i23jDlQBVW9YFVaUViWm7/G7Hsi4Vy8Jy811cBaBiN9aCiepWfkTQo+c5zzqE5nttM0KXzVU8Uk2kQCR9IHQ7tiws6Za5VGNlZEX7bngR8nIK0/oEirSGZvoqAItPJ/QJ0iJ0YLOS3cKvdsRkYNfezuj01alDruWyBulSL8bXYO/CVIHOyKXSWrAe9N0nOpD/C9K1A+0c/nT0xihinTf23gHXkVlHBZEr62NLkekaIjmTzU9YM36LTaP3iTkNYsKQ0OP+xidZNdwajpdl2dOwxyl0MT1sh/DpZjfK+6phuPMfHSGl1bi53Mw1udBhp7GWK5CxYi3oA+jC9Jtek7UIVdwOieYhysVScZtcUdosfW3TjGAQoe44KKQFxVXqLVW+UjtgUyE9SisqsnRHo2mrdBgexf6VYf9kM2YZEgDBdiBIOdSK5+7VPfKO+RKUex3hGq8EG59EJrB804v+WNPn98w+urJO3bj67qXAhrbGP/mE8DwyHINdwv6H7MAvHagp2l99J9+b31fboeD/qrXYJMOZ+YbFz5vR9/TGdo83IMVWNyDOuOoLZl7FmYilBfBbhDhY7QJPjdxdHXY/O3PTq/OqRqw5dttb6OXkkSPPFfv5CZGfu4Y1WtOiGytI81X3wn3YTySiiN7EVyXGAPgD0ZedqFgQz37OuAbfCsRzALz4RGwzxIxmAXa1IXUNGxGmFtDMNnnAr9CZ+P9D+e1lyrUFbQWzQM+kgslPAD1E18EiClohUAstFqFaSKFhxcMXPXxnu3TE+vuWA90X4ZEjEVVo1PMFBBZjmwyBYg+jodBdmCykumk6tpvDbWDWshr4fp5FzSd+Bjfy6ft8As7F73OWwT0ok0+E1f1EWC6X8HsEx4MkV8zNx+R18ahwZGVFCQapIPU43R30W2x87N7UIYyf+jaKx56b4l9+Cc6iHS6PBELc4pRotNb7LZuenacavun0ciD7H4ti99Sp6I3/eBcSo9Hie+IEvpqIjI87J5hWgkhnibPMeXtmm6hI5eH00FRpPiE5Nmo23UkwzTl0eOKF5OX8aJvV5pRQT9y9+eliPdP4lKcmWl4pxF454uSoHz1Uk3oFs6F9LGOxfDtbV6R5ElwJfvNN20SPVeusNQQ13UGBgyUf9/Avk8piK+5fAWyfSg3VwTXg664g28WVSeNi9PCaLkkRsVYq8DjyDPZbVumKjP7JXkJ+hiyevZj0LeXQrTeV061cRVbfmWAMkWICZ+THXvcMUY0rzX1WzhOVFE7Nq6z0Gw1s7EpqCeXJQ4ci90ePH7+C1utqOpNay8TRIPUsuHD//SWh8m0L/llUVugLFxbU5JUU/GP4plHKIcvv2QjMHyxus49zN8Ak/uEe546YzK4qhc+FNXZ3fzgOj8zZvdfhITIjlNGFzCoi9lHe0qxZBdYFAik+GPFe267a+Qcr8ehGzCpoZBSAT1Gh1ITR0e+iWAyIdx2pXn5jV30yRB9aWT+5O0meodb7JDyMfULy6slTQ2j9a8+pYBOHTP+lzekwekYNjJBNUbc1NYgm2c0syEQvVXaDn5AMNv8S5vknbwZDl3VFsV1fBtAPtT4Zye9h6ip+BqZk6jOlwFOAxxnglWQSRXlc/Eq5vU/DrTCtxEheUn8ev5/jl+77yihiDRaNydwJuBWxpTrwwQ3QnAJg1MvD1+uuj0O/gCouA/0OBHQqFd339wptLdfNlD4qsJTExKav0A5KIRiC9hexwTXgtFcFt/r9W7HmqGvsIZ/B7JXJZF6fTstNiPiyFrnQGvJKvF6TCR/zrN7zcCP2BRFjZfTu+0O/dOuFYrBgEtwI8kCuzBcYunzpcG9I2oRhqe3Yk6lzTINx2oi2ccZyLp0KDws8+S4nH1KpUBL0gffg6n81oPn/MuhKiJcK1VppkMjaMHF7eDSjrZPuM1UwB7OQmKoBPet9heN9Zt+TdYDPttmtIl+phPZa3ctJX3vllB1OBBQCaYOUDb7GRvW0LoO3oYdNlTyy+7dIIP6SPKNxA+gKxgMtpyfGHE0FTQZSv7MdjzZP4z6UT9oKzsDei6xaC9c6IN6jZxwsUzWA4s/Mdi86wcFSrYgnYefG/BHvSv8arIhalFuml5YbHIyo2M3zcc9wbTW1NeYSYM5nlRQXU/KwY+UKKiVJgYVcMDs1EduL1JjyHspJpOoMahVGyz8VjmOVEs1qB1iEbhw+PTNu9PTsOQTqUwERgymN+nLIjq998ACOeIksvSfb4avqV8brtw92kAn7qdybiV9MoqFWYce+P38+vieyN3r//dG9kT0pFIXSeGoWmAJYjEpbubBSIqK/HLkSAwwonROYSD4C8+Ec4gOxz5yZohr2ismAL4YoBSvk8FagR0E0BXwjCevcTNg2fN4Z+H61pvcLSbTKytup/rcZoGY9ptPOzrZOyNC/Qnsjn3/+cAjNEuvlXBG7MBxwBhcGVoOyyiXzFNOnarBm+2qTybDEDl5DF8F2wIc94eloerlORqcGMayEh9/x2dgWpMek5+CZL+4YsmCizW/sGNu2Ev0oG2uIW6YS2unDe7fDpThGl2T0SjOZk5uxVlpz6ubbSs/cVuL/aAl+9tJkanriObYTR1phbumKxEq13eliVXPvAi62tcYirFZKc39MfB8D1u8wSRTNBFux1U8vXfKU2MetYDdJJUexw0JLm0YU56NzTfdpNSw6LUqF+Rx+O/oZAMYbgNt05crmtpy8nFjvTrgDyjKKUaq+OkgtuUKY//VWE2CEUOgj/POAaghR+qVnqiGAtlquY/F4rPxowOdb+g74FUXxtXn13//WBMGzYfTc0qWPL1/++FLvcig+hcr1pTQYgrCICxalxmP7kQJTn54fCqF/vvqqa1hqOhHQWj8fO3bs4cn4A48alL2H4AOkVibh/xLEWdPgvzDGQJl20I3OLPX+NBt56hBpjfurI5BQ3CQNDliY+PnnxOfJn39Ofo4pE3FGRaWd4xTxaA/GHoy4mhR3jfgEcDkl17Db0AlWCfjqi0mH30UC8A3xvPZAtf19k+/hGLayzBmnhPEPZ1lZajW/LKpWMalUJwXLZXFszz2397hS6Qp0uAWlgIb+kAndo/Vgj91utaFftS6bMYYRFkjfuxm3QEZ8dsz/rc/PrrpZaCyNVIj1hIOT0981oD9zKzqStYlmDe0P9OLfS4zsKMdRrHxV7GLWF1n4Hz7Y0JsDQDiJjoAxwxaNra6xdfQkktX3xcqGy2SK8QqOdopWIh1eFvv661MVHHyX2np34yNykieNkJnsgXg1m+roS8wMUNXO1j+/4lZWBCuMLDBGXJTMk+QB/HcXmNhRlqkI6FMusMM4ShTljzKgK9w6SUic5GOT311wcmOrsmnFzplAOUxRzG2Vx5B9yKf+Yv+H7YcjkSlAMZ09Bn0xua3jn2Fu6Juh6fiS0ETTZ84MqCXYMDePlE9kVBWDVg/dnlZeyrYapTtF8JCZAE1vC6sqIpWVHDBNkJssEoLwSbR+5crYN/Fj330D3thwyLv8FcXZ+R1DrVhF/S3VW2ekPm6r7w5it/1228nF7armhQeWAnUdu1heH7xr61ZfHZbAP3ytra1ILimX1FSEJEb7BJ9/jJstZXzYpquqJ/Ode+ApSM/hkpZ7ULs8AeUIhgj/LxVXMl+hspO5mP6qK7ZwfSt9LGCNKapZeunSk8gSWdE8f1Lhre0dkyfeWW0faRpS7dYESg0uwbVHnwHihy6WVGnMmyeGsYNMSpQq50Tzma+GPwqDByDa/hg9ijs9hz3aXJNMtG0QzAl3r/a8EYm8Ehi50W2uolGItWvq3QaP4/hLRDD3/rp2M6BLQYAJePzTZvQLTT+8taa+WUP97vuLsPA8ugvko/+AJQk0Fewau2Z2vNo/fnZ7gg+wRILQHPwD/x2W3jNwG+6hy4lsm6ZPNx0jcuZaPmegCJUiDVgyXC5KP+7j4vhlG62EZVGrAwpdTQGSgk9pTZSzHC/Pwo9xlKPRx8VWvVhexM0vhug1MBq9ObRwxrjT4Mjd64Nry70ha5UrCUqeTdwD60bK6rh6drtUnXjxt4ix1OCRdSkZurx4YTGgx2IpTgE+5vm9x6EfinDfgaNfQgKI7Ia4qQuDODMP+6kp5cDDm0uFoBMrgMpYZL1wk9nEgVSI7uKDMDrRBW+FNzbBJvTRHbWX7Q4ehZ6gYoVKVWsTkO1IK3edhePwiEdIqnv6cuIEcwOPY1R068BATEvEXAoCiQ88W49NvpqpxmoyrAXCypAFoTRE7QIt/yxEeUBUbRku6lIpGBhGAegP0TfoN0Aw4VEh4OZjQmdNXFynUxWDXPR3QQp9ZQ341MJGCdqkry/jRyVgmuupKjpV/qwb2UMXqouf6cT+9cNUtL2iikuhh2lYgVhm+bD4m+kB4kWTiUPFXyRbPqXfTEd7dU670M00SYM2vptzsTgh1EhZdSwXJyj2N0mJu9DUuwtHFgbcYqUVNsg8WrqTmCQ0pXks2YY9Qg4UEGwcuvWmbn4VO30y0UCHB8+gH2N//HFlGcfksAmEs7Qqr1gx/6XUA78dyz8GaBgUu2xWrtukhBgNHGPvBS2rXl637uVVsXWbIxcvRiaAo4Z6aYeJGRjCD3rR6AkYM4L+vtF2l81kFZD0v1KdaqoK8Lc/PG3atDPpTmRqjh+PZE9h/8Tj6mpStyWc5gP0C9D0s6Cc2cNcBs04eS1E0pCYdILKwMevC04uEI5Hr03Kb3r8pZfuAvvPXLu2m8WvEYZZN/7IP1QCxTU2MyeEQxAMo2GHuNsv3QCPoR8BE728+u1Ns0qr8/i0CJa/AXX9+msXWl1QphXrbq/ABNvRN0QjBCQwn6hUNR2/ml1R9MVXy95eTTwIjNrSewA2QkUOM0dAWos0uOj/w6Rm5f7SB7SVAG9TqhU7l9qIzUuNB6PAhrYOr7ZHhkTV092aSWIc/z2fesQTPRy/Mwa8ofUdFcpVNvRH92xj2W06kut2GO7C9yA9R5llrmR5OnwS7gx2soShsiqIhdGnmknaWkwc3mu3OPbV5a2KboZ8my1gs3CxVas7wds9q9DpTZuAsulgrdVzuB203vVmxcunMbPhdo/Ft8p8DA0Bp6evm1WvjY5bPDFa+Ecshv4AtN/utKyL2KIbagpenO+f8kJOQY6U9GO8AbxedY6DjP8TJAsrK+GE25AMlYqdGaKWkJEh63eDe5DtfX3GZPtxtueYSPrBOfa9bn3tdmvKTEAvMA+9AmxD6rfb7DV31lNSr//G8pfknj7OqjCZRDaJIO9RcARsXPKBfsrhAJpMpML/LWnTV5S3yIDE6ta57dg3ge16b/larwx9d8rpdLhc6FH7+rAhucN5rbq6qrhMgL5arFKV0GghGsxlc7vPJ5/a4w0dHs2OTtZ2aCylLVpgSFQ1mdLdQIfhIajB/YmSVALo5wlnhcuyXRjZm8IeeLDEJsBK7QL5b7/9959VBckiBe37Pz/6CL2q3e6xureV2hT2mKXW5N9Rzo5EcA/zYXyRuLh0Bjf+YQJ86DrqcJkP2tD7niiqAEuqHR7rxSTZEXyQrCXQM6ftZEUMM8qrhO5fZu0MUEZ3gph5RdBUu7wS3PVbauEtjav/g4nfvpJ6W18dNzsrts3B/hVaZa02rvYjJfqwvh68CVEltqiuDv2n/s1QArHBbqfNueESqWd/CF7Edw2dzKJb+kfAzqRSuP3sGu1AYYz+HIQCNJXfHrG41yk95Zvej6B7wGOeBv+BcqXpgn/FPospYbLZ6jfrscQ7QJhaC9jXwC/Y756t7urKnQ4kDdm3tcbDTX7pUGlMM1EyZu/IAFKBZbaq2sClJnT8pWDwpQg+OmKc95D3Kb2GS3Fv7e8fLb9/7VIHjvKv+X0qadWomRR/vW5N0BxaqlkAriInWEqsVRRUWcLm6srADg22dzXPbreIfHJxHuoAZ9BqTD8BHRivq+I3q7Fffdvstea1tRXo8mPxuCsWUwejiAV21zjdzgfj6KxvawXuaPHIGzdZkjm+VhDwtUXqKmolcQnBIWPj9upuqMM/0+ZU9NvgvhVAxqvpqbf3pxKz4E1BKHQMPAwJZM6WJfAyqFWv8liqV8uxUz+eDqHe0O7r5Ta/SsOYCyrmlrTM+zH12/VbJoxXW8IWs6F+TgVQkEeG9D2xlPuQu9p+yIn+NgphlWYsZ1Tw4hdLFG2b71oMCqkKdqS4eP6MIuqSWAJHOus8Zlf9/pHoo8a1DTUE75Gew8BX9VOQOC+8LMeYYyOvbMxNvUX/jd2XOTokqz9PskAGiruTjWyZloO0aFXmvuB+lNigXDe6Xut2e8HcTrtrhmWR18Zh5Wv1nuJACf9qVb5O7ZqS6owtstknSzBeFXMujVKIEiKtX2Kpss+TgRnoeVDr4HkLcHSnL6RN0ThdanXxd6xKGvY29sln2JEfsO9TU6eNGT3DNOPWeevKmP7wc6NoQ+rDyx5pmDEZypdsqqzZ5Eh9uegJVt6hHTUhxAEbdLXO2tPRyx50iWkvoHLoFQWsojt99d0BtaY25JjxeLGOTmQuDL2P4/iCOO1cQ1Z++6oJdP5ArXTiaLmB/a59iiFZpujDhqWaoG6BtrmFKRbY/AYpm0KjJmi5uRVGVUeTwaID/5B1iupE7dLUkFJ7YQPDIoHK6ufippYXbBdpKcSTUChUKBQrfcViGLTYyqgUCsXlAB/XfD5cM+ozD5rT+sNI9qjv2vEx63ovwQsZNYNaUssuq2cwuNzQJ5vTp8XVf0F9zifbjKWQ32Y0G1bIx9XTGXnJ4UK9TuR0i7sXG/ZOb5h2oDHUdWkdQ63mlso5bhOtECmL7eImib0YW67qkUeko9WY3LiizKxaqkWd0lFetZKKYVBYYysMhgNNbeAViG4d8+0p1Qu908wKZTFGyMRLa8Cp1rcSrOjfhhjsDyX0DY/ZcshzZA7AB/AZKczRZ1j3aWIIn0tSbnkDqVd9ConOjN5x1sUTKA+MKrGJEgmVNFbyg2bXfP17w8SrFlQsXsL87Btw4gRIvjnqxhymOj9UqGRgnE0bADihGqZJdcIV1AcEZVNKH514wB6c/OLQbQl3dHdPLI/zXHwvvBO9E4PuN4bmjXgl1PLZU2nF0Ifgo1BN1qJCOXU5reluzAHZ8MyJy/1sySyPjs8fuKaIY/oGsEx4A1A7ja46f1aOLoBxudR6Sh5YgfbfCjTK/e/7RRXKRo6J26bseQwcFYf41byA6M0QvTjP7JF5PaVuc5KvIipDmlJK3nzVBKGP361KTZF7ecGwFYx3LmyJ6hvpNdXR+xuiFTvH1pqEAa5blBQ0hDiyzvJKQ7dsu8BvkggJZfvKml+wd8pERImohFN+1XDManQeN/3g2BTiPpqJ2y/i67KC7IctywnmJDNxb+Y2DDhDKZvr0/Rttv/9RvSddJkTanUuSUY5hVgnkoODaCy4iBrqNgqHc+ysDgmYqhnDc/O71C0RWnGu3Svz+mQeS4KvFtrsArWMmpfaKWhheVnNYmzFsnGWXS/wbKLoqNCYiAesRCt5XaIaeY+AYdpqMtp2GBsE1Q6pmLjoquoXKCfLCB0ojMnVDJHfWcGr3F+WPjXyGO4ZifPJ9KT/HrBIgbX/vKzBooskxsmuUtCq1MfjKl5NEdD/kboXFL///jaBNBqWRPOLiUP8rlxJTcksUPCe25YaDlfBxyXCOh4qjEa/jb/U2Sg6fSU/HnoePtvwUlySWZZE1CTGLcQJaMz0JhNzkfjvrH9CRuAmcvv/ey7osDy16KRRWcNxlYgvCR2MCL8azQHf42ZXJ/SLnOL6kpdL29l+Tot0aDS/INfh0TlshlpbnVCpqjCo8MnIT+2Qu1lhRy22Hd0NhtVptLxGkVA9XCbXt6AfXkJFVaMkZbKx0qkVO0wG277yNkGjRirGLSK10nYdXlSKMQoFcjimHtsaH2vfVHztCfDZeBSW42iKiAkIhE3o4/aJuhBnh5NrkEYnaRQDTUrfAus7dJy4ai6Ply2zYypWpWBI2D2qs3DKdEqUAnahiZSiIm5tEfqq0MCLxaQ8DxOdzEwV7Kq8VC1eckvV2Lm2IHPJLcIoo5YdE3/lmjT12cmGTSD/kWisEpsbBQ0NNPUq7cOikCQ1GZ/Z5wX8dumbmUlEH3nnP9W1q67au+zQ9N3YndLNL1zXbDWx7Ts1hJ+X4zvtOI5hiPkVkTMcJfvjFMyMcA1TkXVQ2aN8iD6UATM8QF2NP6gg1Hc3PkEvfJQraM7lgAC6JvMwXEyvCMiREnycfbqVHaoa4TDN0BjEYy+j0WypshoqmHW5fJHIYhXKRAWQkjpZ6igJM13yn8D7vHiJ0I7K1O0So7qrFMyPxdbXrW/u1sx1WsxLjXapSq7VFBOnbLBNpoOUDSJBPrHtcrkCxWzjbW5+7XIz0ddS0Xs/vA+ayCymnOTkpvWaOjPqm9oBx80SfCbCxtj41oFhVpoiNDAtQviMv96VvpsC9944/ietMP8waCoujDGLQeQkTYCu0fJp9BdLUQibn9qAmUj5kIDD4HWBufUep7lalqrV2vkBuUWNKcL4OwtMFVVms1lv4tQJVTqtWikVF0E6FnC7ORVCj1FUojN52NHhJYoSTDT8RfTdCZfLabdPd3qsSQtj+JCqZKN8e2W7TeYbYjgpkujkCkKZGzK1ZUspMyUcormQzmSbiP4XVe95eASqcrz4zo/idrg1Z2bOgpyl+ApRkmevkvhP0QfiFFotn8e3Dsi3DdB8T+fdSKNAdM/wM1X+7GLiO/m0/x8vlrYbpe5SltZs9ulMInSkMuCvNJaAAzAvguUvNarKOD5+SQ/6gy+VmSWeco+6kCWXlrBzGbC2mFloTJ0G1egKl2hrdW3ZslsYZ1WxYoL3KEFQkE+3eWVuD27wIyK10GoR4jaGtk46XOjkDy1NTaypdld4HlfpRVqtrUo/+d4JS450lXm7Z3RtEnZg0iYD31Bs5fI9G5vKhtSKGidUcATlQkGlSOorl2jAVKfjZfu4M/wGfq2sjdfDE9BCYqGA8A16ywHKEjmPWKTFTOZqycwyi2624kTDbfx5o9Ia7Xf/H8a+AzyqMm077zkzmZSZyfTee6+Zlsxkek0vQAgJIbRACL2DVJEmKFiQIiDSUbCA2MXedW1rb2tZ93N11y26zXnzn3NmEhLE3X+SubxCEnPe8vTnuW/0TizGc2BRRvMvUff1BLkwvoU4OTpOL1ys7g/vOTpCN39lO1thNOTOKp4sqwtrJFXdywzrp6qZ68uvJQGUBDKYdgQxCnycLp4arx2/mCPDPDduOb0yy+9SmWRTRJAtcuXme1c0TKitdjThk1ggLQsnFAuTvkZbrUPfHA+lxi95gJFkGIWBBUKEuzji1MeNu2ZP26g+uMDvrGFLbWFwr7Jb4uBNkuXPhyffsqFm7elbmtTB1eu2Jxsu3rYYb0LHbOQe9DjmEbSOzvCOkA5w3ZyxIPWXGyD07rH531/cR/Q4k8uwaDQJDYMWm+5amnaL4HP/rkTJXLfLz41JhRWYNIB7EEcoZ3dywCpqrvIkN8qxChtZho3wZY7OVCdNGJp9HIFWzsa2pmJBm9so9gTF0kyDd3zbYVC1S/oPmdMpxL14lCpW8vcajv+2TxO55uBygO7dK4qz7Zwc35T8eGfo+k7BgqNpt6GWKzYmS5AS79BJ9DbMg+0gdJLyymMtyAsuLSO1Ci6RmaWMjplLR/KBoxCz9XhinD+C2IjeBn9TwZmeqZm0gi1VqpicCgY1Vs6uonkU9X4+e/JSy5Zp0qq3O9JkNNvF9/uqeVGFpGyLlV1/zYsvjmsg97weoQYaXyeVZcvIwLtIMFVtU8yQgOev75uwULdtesDqZAgMWYMuoJKrJus9qUA8lF145nYmG9szzlNGC7YSfHP4wgPi0lSl4K7EZnpptFzDiTHpNze/hLh3tau1s8R24TQV5tf7hk6ge1F9MeJOX/VGYJpI57ky9/+Ls8eRTPChPby7Cic72EsX0TxKbVBOL48udW1Nm1lQA94nkxoohzlBjkOQZqmWwXdYYm1AmbE0+mlcpRTbqqrKfA0I/HT+PKChd0D6j/etTiVVhupakTDaGmxtPgCEiXExBNEvkCTYJk6jUJ348zX+Hf28TccSFl2tUGpOqYABvp+6HT4l0xpSOgO2xgnYyZ/GTt6FaV5c7/5yjaOEnl8kFb/ieoAiNgJePB8eNMSxUtDTdD7dpdGF1QJ60zhDX5uSvalsM0rC5b0MxylVl8GPaKK+YE1mJUusw5xsKqMSDj63HT66PPEcyPInKXHRzzc8/vjSeq/KbKs1apPu2kB2wd3cJFcV9c8RoIEtQh3TmrBdP23mcvX2ldWWsFCqy4DDT8FJ4Dg4jh6sUU0WO/ndsvw+IMA0nGroVvQMSikRYD6wY7hSNNLjNxx3oiNyXbzGFLz/yo2e2ZG7CWD+bigeFfY9meXGjzef+IBisCaNBsbj61iDt7+duR7ZCd5JQR74ds2dW9u89cv3rgfCcr0wzdeUn4I/T9s4Tle/YP91oJqtTys5y5IBd67AD38aPYL8TKCD/XImRHnFFLSSix6By7BjSIsyWmklQcLxBIg9cW35YXByc+WaJ3GIJUDLHrHZ2GQcsbJMKNuS3Zc+SksBGSfNrDqV3ldCsGIdIXpOVAUk/FIK86ryXIgDiCTZGKxNDzhbWj2J4/I6BQGZuGJqHb+l/9Zbs1u29GmRkodE4WBAnNZqqH8E620cGfyn1cIhk5tIOKz6b2WMerbstdTDpAdSD8rooC6T329zColvU8VipBWffpATfMpKzFtqLZk4huV+1NXEue6vaoy0/2s1/OEiMTo+SmEwXEZ9XC3nzN6iuWlQwjxSfqyUlgalpSRQXwYvVPFmN/l71vCVOi2LW0mDtbVxptVZK6qT88uy9bx4/44dmZUr414U7ObOUJlUM7mHMPGu8zkDXn99KBZumX+Yk+SknuTOyXgMcdP1kyYsM27tT3lqZdbICwIu/NliZJLI9SSUwhW9LeCkGMr3YhfR87EneVzzp7JukUPUKSB4nPHpfg3mP0eIjrxRteOx2KjD2bH/tgM+PmGc0e33D8x9wHli2RSv6uU332z49tvHlS2BOQfzDwga2Dankx/iccp6XLzGzsWL67u6JlBuNHVOs/WnJnWlE96ewZPxnckd6Lbkzvi4LYEJDjCLKoF/0OmYZMwKIeV84YdKepIreyOFucCpi0ol57ruvvVFLMHTmE+cKxm8AiWj2HM6aroUC3pw2AxiGuMK2IwxGSKfln/Fgq9cMXqaQqXUJmydnTaHg+OhRjV+dx8/w+GDvTCtUHrXxd9HQCmKsC1GPc+q4iGl4Ob4ugq5Rl+f0zu1pWWk/Ftomm23mrguEb+MQRukOWYuWRLv6IhOjGjFUtyx4no8P1SF2Rucbv+FVnbIEa91Ims0p5Fb6kr12pNytYaJktIIiaNYpTXBl4Fa851eUQmwX6SyZR5oEMKv9GY29iMoUskXfEsmqzMV6pcSDyEXE/cJ8EhZOXQbugCVYZFEIQ+cw+MoQBkNunSVu87+ZVtbUcUNN9UUekxxBjLQOJNjNukEZrnA72fWpmbNSk6ZUiujaLGnNhtNQouQV34guZ9iMUf1uqpP9nx04EByD/j4AOiwwK+0+NFnyChX+Ac+O8cSP596GL2YOiNg6MCCvEtnYmPfJaFlXP4enOq+a3tOHhvctmjvqVOn4Nzj87Ss48ePFyaQD6MXUWmJGrO+dXiGCvD/+xKJUvvlqerLcKIElCgODDBCyz38a6CtrLNKp4sJWzjUDje3OzJvXmru3HIOtYKDzBVP3V495Yh0/RRLk5kP3lc2uCfBNzRp4xRP24v5fPrHHy9dSr8IrlFq4RdqHYtcli4HfMnXSnZaJX4qdZZ0OnWMVEYml4G40CUPVNfqvOpJkUi8tktn+dadkyTGQe9g9Pbbo4OR6aQpmGSzho5hfqehRIn5Gc1jdfHVT1RbWNAvDMVoPaAcSfq2o4IEx2rz8LwaQSLHamxfsyYzMOCVIBNvWbmSF/B6xXVqRQU8BKbCzT8/8UTu7bcBG8oUWVY1PyUDPaIKLibUegZKSmLCIfsjl5NmiN6MPok+Hn2UXclfGH/DaBcSWGeVIskj8YWx1YkN6NrEavhHSbMooG0TE9r8IHoUVWArdBaw4P/XlfWNVWlEn+AoTAoumKJ3cxxWk8CuFUzRioPT16xJDw7qdRTuly+9VP/66//JvwdsoDR/EpS/+mruddDP5sPfGM0clNRIQrmKfxloWZbpYuJB9EJiL5OlDdyY2Ixem7gx8ZvTicTp5CA6O1lCLtENHUL3oHLMQmYJzp+Jwz2NBf/36vqVfEVcfjmdPQoHfiwkBUAXLapVlpVLW7g2h13gEgvKW5wMT/fKlchnoKyUZzF3uhxdFicv0/JxE7vp816BJmc25WQSKomEwB1p8GwOvgbc+BuVnE3fx6Er9FQp/EanZZDJKUzg2Jz/E1GzNNnL6Xtf5jh0OuwsSSjHYfkJ3cYICZOCAEeoESAkAq1Oosi7wPMw6PhmcDDS31/ADtyHnsN8YXqJvaSR4D7iqoc7iPGhjv9xnD4+Wf1fhpCVlOIYF3g69SG7qrGcS3kvDQUSF8/ttAo8RlG3RRyevm5desaMUDkyaz3Lqb02a2rZUr1/sX7GDY65OaVu7R4Rp54lBIOvPygTunqVFmRg8cUGFZWXkl1cDP9G48F3jGYWCW9v5Sp+1FVl2cZHUmfRM6nbxTply1JrmzeZ6LDk9ClpnTasrJ2WbGlgheuTrVa+Vz8VzxXzsft7P8FlEC/JYHvQdrXpcs/lChXFXazE/g/FjA+Ek0cYy5FbtLtn6SbtMytu3WDasosHv+uUWWL9ygyn6t/dtzbm71Gl2BazkWNW8DpVbHfXwEBq+nSbmXJBF3i1C/5nU/yGGx5vXKiIqhbUZ2fYo4aBhtjnUp//wAS6U1a3GeZjNzGl8Pc6IxvbCRThS36vqMhUqV9Mn0fuS59lcVWAFo6uf/ZS5YVLlx7Cz106dACz0xJi1TgWy/+H3JIL9cgiKc6VEwJ4gyo+eoFHQ11OF9tht7CdWt5kQ5Vl9pIlycmTrUYKMu7T2+M/xg88Q6kORmxOLvgJNoOnE5+ugLfO/vFH0Mfnwk+NuJFMYIep/JuWmqYZH08+gJxP3snmGBzz4WPVHpCcf8NjfbrGbWevA/y/2kzsDqTtzOLF+fdvwlZVS8S71mI3anZ4YukXA0sj80p4MpL9K345ZbRffiT5gEXjZoeq5Lty1wl4dVVujel8ojr/LvgGdoNjH8ONHKezSdAqE5Xjo1/wReD/zTbSLeDR9ZSljwIt/AiZNni0RmVixbjSm9FdPE6Ka7Dbjs31Hjvm88JTfqUeBz+sIyEUDp/tD/tCpYgXoZd5KJSIL4zdUhkWsx7BPEROiRfzD7pKpl6N3x3zo8j/wzcuZRO07+z/JrREfwouuOiR/P03VbAnfENjZJms9/poVAYkc1wOG8cjFpZnwnTn9KVLMTfCoiA5/0FlbBBXdXBsssVTZTN3eO5cK5uzwz6zRSa+9jC/qp7BBDPgDzIT61UOJwC+jkYz7VGrkaYLRavt/ovwGwOuv/FxNy7vezEzRdU8m7ofuTd1hkXPcUHSNbupES70NMqdrnQwrPZLElwD3yRw14S9DpZNF75OGLaaVUxsn0RDR9FTqHZkGjg3SqMVFNr/uub8KyhtmZfbHLjgYuJbFjNZKfsoDimtHIcNu+M6XpeZVTdx+fJEb6+ZW86ybNZY9VutIOXZpdUZbnSCKixEpT4H3kP6Vz8VMdNEk59aDf+mhZ8QJiuN3XTVXzS0JEt7KXMRuZA5yq5Uc3nzLS7zYtE3yjmqqGWJFP7wdCLxdBK3W0IssjuLWjC5xdEVGkpaRvOA/ioN6P+MAH2jkUbPQmOqTFE731UvFJ6l8MuSZeLSSy9exF5wB9ns47psFq5TJCjvqGWYlyxfnps506295oHCyxLLIn6azXbT65WdMWUrh8aZIo9vim6M3wCiKiYb/qXgBJOQci7vCwktU6Z5L3UaOZm6xKiyb4IPb3zuhgKu7D70HlRczKoTWbv/aYjYo5qXRnWzjuSshofSC1vC5wG/Xsm2mQ1cs5I/qCh3T8Wu8sBAHO0ED8B6MA++Dwwy91RWfZdPMnmhkV1r8dXX0VKUSnHIBn9CmvPvvMOqBV0sGnxDqyeWhHJE0FDeQNdcTGFaN7VfYgVr4f3PNTbWtLbmX8F0GkBCjbZ2iy2zvr/MaQ6FqIBTVzcjuBbH1i7Uje4g0L1w/rrmkt7/vWbcmbpy0I8/wqtThNkgOOQKnPFcoqXosqNVx82wzAYDxyTn5CxVocysWYmuLp6ZXjazymaJmM10hJWEK37vd34pkdqlk/gOmix1wSdUVwgZpur14LlX/pT/9Pt77klfBO0VEvge5i+jpDgJZQrzYnqWKX6aEOHT5SyK4djs5ccPdGjqr9u/CsTfC/b0PJqz0hVSrWSOyso3opUkQPZRaMZoIACfn+73T/dnkbQf3xUldt9PolKCzQlnJpw2Oib6FR0HCoA7PnS4h204H0D0nag9hQ4UQqaLt2M4yccvjlaB7CS2xe4UBjB3LWfmOifOnx+fPJlbXYEkl8BLK8quAXXzTwhDrCgnITxSbq/yV9nLBDdlMrA+fQv8DnC28m1+nYtZVWFn+KrsFR57JTj0JyAFkzBDoNdhnlsjGSlj876T0FJ05SM5LIbOHS7naUCOIUITiJABP1bPt8rMS1Vi2WyhgD9dBJ+8byP6Z/Pz6Nr74nMMtXpbu71U3sMX87pEGpYkMieO1+JEmCfzJKb7FCW1JT0l00uWlazCKy1g1CUY0YOjb8l/a8ThU/6HviRsBYWnZ44dlWDyi7wy/9jAp8tpPJqOP2krjRliMtefU6l3yitsPC/VTiODaRNcjknu/mobi8p3usO8Oibngr1CJfdOy09DRE6WyaDg62XcqJ4fSPX0RJub/TTwJZtf3k2r2M3QapVsA6eKtCX8/JYt4EMKFuTXljM91ojZVmmqicQdZX66QDlFolFU5J+dNHnCTMvAooV7REZD55MraONykS2PNs6eBQ4pKjnwc8zxIJNSJESg/IuImqwSPR+7n3Qudo5H3lN36zTtfhXslSurULQGQUoZnOwF8K/NTU3+5uaSshL60H70AqatLrOD47gNrf8/PhW7iKaKb7gS+w4+Za/ENBSboLnzjIynEQgkajz96pMwTGYbz6lkJ9z8XGLGjMTUqR5WaQ+4E06OAzH8euOf/4zI/vY3KFu+HJxcs2Za1yZ/askpXe/Omj+BihRg/rD8COjiV8DfGU3sgtus/E5Ulebwn0ucQU8m7uaU68GmF4Ntz7zwws6ODtikn+D78J05qbC8rToSRoORha5ChvE29BgWNyjxuUjyZfYSIj4fReriHsOqsnXbK031r1yv/OuOYJ85AORwM1jVgvPD/2TtT+/8Lr87OZjsVc9UtXmsHebmZINn0/jctux16MbstlzXdd5xbnBwZ6d9QQqvaTViHuyjqBnz9ewEkhllFIPK5TQTcY1Hc/4SXc1MNXMYOw591HWw27V5kv2h7g4lV+QMTGHjaPv1ExhRfw/cQpW7ThlEOj715d8B6+vgfZuH+lJ5lVgenz3XP+CL9c9esV2l9bZ8MqWqI5ZZ/2TLwJRmBq+Fx8L8pSqw5Ot6uA2+ez55fJAnP449M29oLxZtGUskhQ4v8mgH7CoPPXau1FeQNB56znlqunv3TMfM3dXj9DJ1KDYgaGXLwZzpzEiwF96EZH4X57mXrAWpNQPKL5xe+qcsVlCWGJzrGaxLevt9Sw84bfamL/upDfXp6x5pHBynEcXpDRUK8H+5HLQoKi2JI3NUXbfgp8zF9vhh7JTTeC6KPAZ4BL0a+KvXc1nFKCkULC7gUMYsSl9YA/pw9abOtn3eY60NEq7YxUT4LqddEBeJyhESBdlaKve64z6/iIT2vcBmphj8AxCiALwKguPYjWwJMI+j+Z3t67XmiruruLpw79JZA4HBedfcpNXo4SmbnUsipclIlVjsOeVeePPSdn3Lurt2aRqzUxyVlvnZFjONUkpqf6mXlqvPrX2yaf75+B0zsNPBkTJuweRYXSIawXBuvXLVYxZTdMCx1Q7jaw0Tlw13sqBj66VEFpuPXrCvb2u4xbW3JS2v4lqsrYw0Swy0TVUeWyN8HmZekDLSTBWYqTZRz5aRBfAm1QSryzhODsrFU+Ueabdydo2zbad1V3Oj3q3IaHkhic1vZRhjUxbMGKzrH1x6UKqoybw5vqItl9zwZPNcpCOT6THQ9YOwO35kNqf83N7IWpfZdk0I5p3blXr5BjfclQ0tmh7sWzDJZFN2JBrE3S3xAAeXMcfQHmJHqgu8rlfshW80dvZoNt1fHjm+W3gu8oJ7Q0vzbuf+hrRCLPRXcu64Fp6/7rHH2tponT8kK7xzjthzrAYBD+iamT578yq1gX6KTBXB2DPP6EJT+/tn1/TPXXS7XWmhyXbgU587kjeWl0ZLlawEnbE3nn1xQkVnOHXdU80DZxN3zKOL7oevPojZRdPQHZhdNBGawl1SQyCPtl9ezfByWKOPdoynROhrM8J1g8L1BVcSp7KLpKlPehY11K93Zfq1SSGfV+OaUpWqEgFymmY3N8C+ASjf2NOTnJOcMSM5Zw6YL9NW3szi5n8AHSyrxcSzq3k4SIqsrmfOrOkB98yaZdtsSl0KoL20THt806Xm+eDtSGQgMg8ZxD4jA/B30TsHrMdgEHwFV2u0LBSNIghXZj0KpiaTgcZGzDLxMI/gPlSB3WhLEZGtvmRmybz/fquLGLjDc5ClFHAFw3NxF3j6Ky/5lTBu/OGzR++rXpxJbrPtyKSFPKrf28ZIMUSA1kizWZM/fx1fbH7qjfiDD8Y7VoAn6U5uNcdKgx+Wa5k+up4K/qzQVhygVppeDocNwrQsl3B13qHe0dCUlkgW7eKUR0rp7/EdSqNrv8zMOV2mCFi9XdO7pvq7+685pWPbY6/1MJO5zO6nGqcDt3KCI/Qa6aXQIyu7o+AhRYdIImpRnpC3Sjj8DhWcHz+xQNJ7u7bRp+UkVbBPLwh6w3qrRmKpDtr4XIYi4MgomMKUsEZXFeATGKAPoRdRJ7a7nuJEUJZAdh2znfzRO02+Gt0dvsd4zxeuIchFDGR+Qa0UUJPdw/4q/hX4iyXLibNZoDRe5VCnlmtWN2SXaJeG3FKxCNKD/cpNd166FHn88UOHIpoZXsRVLg36hfnvZs8+PmNZ0iKIW8Ek+Huw6ec7b83eBy8g78NLQIQEHJtjdI++NjTFUO0O+upC/qDb7U1pxQ9LE6pjQV8aTfiCx06u0mQkYCmzpSba1RSNRp90cZ1SFXyrIxg8jZ74KBRqLGCHH8HunKmA0kkeRZk10g3F4xcaogrwWwVGMHTnta82Nby6zbTluXTjHNU+sEnMaioVlJHKwfyD8r5s5ukN+bWyyfFoh3iSc248Ot/TaJte0/TsNZkuO7Mqx68SZ9Y/3VAzxYy0z7srHj+9gMjs3UbEyuaSFBYpEz0Ql5n0vIV23YLBGp3yxL1l4mS0hRry5QCLN5zv1RZyKFewVYK/nS6XyX0ik4D+2GOvra5gpZ/glEXJbMrJNCDRaOuePw0eWZC+hu50pRwOFm3tDjOv5qgX9rAofVVVHRwXr5rjZ8CPBGlFUFnP+9PvFGouqSxFRhmct2PzIrkJ0QYOlRGRREvZzYHIvKNJvBbdm1u4dZwys2hBI7gRMBWcGF9devbuqeHgjPyN1k6ZXDJZtbFmnV5uWIM3hpbYMP9jDzEJjEVRFCVlFIT7CH1wNQE0pxuZwt1MAWA/wkLImpb6euk0dzUPZcBz1NDciTXT5rjKENJPYE8ZvzxbKaGAOUjzBqEcvsIIhaUoqRlF2GZzfur+7Y01zTecXl/GmZRV1XM40k5FtoDLcxC9FfmamHovAcMst0S7srfaR3QXKXEWYyV7JO+u0xFQR5fz7R50JRzgTD680nn0lAw+CzKlAHvB/0POwQdRQAI7JNgvijxuh1joStQ0KY0sjYahUNBJpeCGwdM3ZyPdL1+fcSvoJo4hk8k5xC54v8lltnDwvvDqGI5q8ye9HIfCo0qkFj1uEx8ZOoUqkU+Kcygj3Ai4TeBi70eQ/npoJ/jI3uxEPT+/Eo+D7/BOsTQ+2oTdyplDJ7FbqSpyMBUYaq4GuEXQdWGqYFjrapluJnp2oygW84lSJm0F/BhoWuB0+B4wpg+A0+x2eUg2jgMFB5CeLJS6PUIyXg+hSZXg9exz6NP5vchH8Imffvqi+g6bynzIuQDHeMTrjv1DN6HTkD+OzPAXWJPHgoMVBQBvXMRZ/PABZzJRVsRRwNBpgoDPLYyqZJXfVrWOC7Rl+HAxDuSHXPjsr4eQ+Z+hcPEh5I95n9XOI5NzZLRCINrfd32LtX7hbTeBNCc/Ezx1/HjjJ5/cfqymxtHx1VclBCvcLvQo8hPBNFZJTIj/f6Z3Ch983v1IZ/4UQoUR8CRp0XxW54L21iW7qgVxe6ipjZujVqm6QnAdmoDbgR2+yW5CfoKnX2luDra15Z8rjZNQcijt7DA6IjunVVRb/GE6YIfDs0IrAIrtmGfoefTOkWcrYj+Nej5KkX0CH90aziYOn+JdyPr8esQL2eD7ucD2883AVn/NClkHO8xuMEIZt1Phl0/kYQ+z+/22tlhb20V4NJEAU1B4FEz5WbvLrrZsCAL7DUadaRs+N+TGJOhOtLp4kwp4gaFR2OIjI6nDSDBqXK8Nz9VfHUQdWQicP+8GLvjztyKDL8CTvsqrpgeY5i/gz6n16+F77HqRTdzABnMlaY5blOVDdwqZnII28Bb+Bo9EIk9FDBZtXMETZgRqaSDyFFB08azCNlGpuFVsULRz8x+A3XCB9fX29rrWVkwiXEOH0FOoHVtB7Ug1wlOMlUe7FOrLvet4npbCBaORlzyegvt5ZQFO/Hn5ygX3Sk2zt4hocVbVe3/XinuxhdQ0A3A9kr4us5mss9VoVeVH7mdv2wfPNSD9jdAFXsffQNvKDlIqci5tY8CnZJhkgbS2Hs34E6RyNY8+AVBDzz4b66lRm+P1qf0V5qia0Z+fC5bAnfbHGxoCzc3Y2uyYdJ1B/lpkx3IQUd9oGslCHyVzBB6ZWQSlxPHBcSkbKSChe5/4usV9fL1s6S5LqNGZyOkq4UfACHeidrgLk7Z3K63Nnx6Fis+Qsk/gbz9r+OSThiqzTh+SxcV2qanJkrNam8HCifH4RHhjX1CpJoFLXdgr1MOq7+lpxJ5UjJ3CE6gWi33ShH88AbvTYyZbiltP0AdxRkZISrW/oKL4xY9fcSRJU/c0zskHkBMnUlu3gt0HEP1EoZWb0UoGEJ96dZOx4Rott6FOF4nS12wDGzemH3wQeSm/OouMy2C+7rP4G5BrLR3eoIRhC/Ygk4J17PIgiSSMCmrEEYmz42nXJGVIO82vi6trFAFNkCr0ED/moouC+VPgVjjH9cb48bUTJ5aUlxiH9qN3o6Aoy3iesZqQodgYicbLREziyqk9uFZkqvEzIY9x7wj3hmhWIqAS8dv7ONKdP4Zw8auUn4BeC9UBBAklTt1e2bPggbNnkXWubGaJalVj/TT11LjGx5eDGRDqqmu0+ZfPnl0QOosC+MfjXtwUnqiFL1UqJJXzZwh4dZVgaiazZGlb0FTjjMdtflOtsS8UCPTVxie2ZT+hVaZLigizLORHoitfMUqf427PCGAaPglJLqB8sBhYICrs41XB8dR4NpUI88Cf4WQ8qYQgP+b9FoeIVJYtR6SqXT1bxzky83dfC2b+7a67vj/hsSYKMyhHiT6HIgtcgYVydFXtKnSUhYEA9Hj+X2oFeJPncsQFUaWkAjbmYp3OS3PhEDBI+M1VEvBFfhs+YQPOI3ODFsjSmzilZRkyWs4T1DwN3oslanedS/nqmIYgvGPBvXPn4r35Osz3m4eKS9gjmDT4tDOBXKAtDNaOwXvxKa9m8PAWGj3ujWNas2DvcGJEyphxKPBiI2TOS6fj5+INDSuAjaE1ukVeAbv07jJfNBKppn97Ep7DXuD4SZA/d44Z9lrYWQn8q3m81Fc9671wGBwJT0f7sM/w4rxRp6kqpcRKUQqHf2TqhjZDbt7OvX1nzkh6e+umzDkTzclt/U2egEeQ5m1STbabcoO4V6caOoGeR/XEOV8BX/wLimXEmXxpiWvxY/H60H3rq/9yI7wbLMOLlfUgAF8Ay8GsnrPhZOZsN1wN1nfd0RLZ9kzqjsxu9IbMHSnsL/EwbfYo0etx+S+NtN9cCZiM1Pvv3RrYdp/v1VebX3opcNf1oRvuDsB3wbRmMAOp3vbR7OSyb7fB7bmHH86BVdu+Xh9e9sF19UdIB+tx35CHnd85VF0iIPivCwsa1i/D5Q/MhBGOodpGEISPQcviuwvDkmB50JhxNbt93eJrt2VuuIFrnIBQkFJSlVpbp9QwT4risUikjgdCVD6fXUlGyP/Xbsdcty/XLqpuvtiVeRR9KLOZq515U9Rr1LHIKMugRdbCf28/uT5tiS3Ycx1oyTdIGAhgKRlNwmGswnPYDrGL9YoS9tjsD6EuyMpfYo4qycPbV9zYqScP3bRasf/Mxk3GhbPu7FMsfebUWygJ7haEal3iOo2Sih3RdU1gfv41yy0xb+wGG1gYOeOz++4Kgu+tqYg1Wlsf6azLeTLV9cnO5sT2f9ucPDKOVlYpkX6R24iuO+nf5qp1bAgY1jrSvuu0+K5ziF4eNYHf/qu7jlmnsf4q7rezC0lqsM+VrA+1ejyzVDffVr9li0AwXgk+3CCMRMKiBoOWvv63/o/XfwAq6v+dqYcM8I9dK1yxZ3syj5AuZubw+ZN0wJaFTLtLQMCq4dCv++E/HvKdA7zsE+ijBZxLfFpdU6wMjrnvhd1jjrnvTLydCjekiC/+5Erdxkej9Tv+bF72ZAb+hHk4W8GKeoLgxgk3/eEPwPUNKM1ucibC1+bg68B5+/yk89osoPanMeFM98O/v3L99dfjNSktJm8XsGfAuT8KjC6FUx5L+FGgwKQUUJnBfzvx4clX7fPnxqXCWVfbEXOMLgMXerZmzy0TwvyJR/8Jzm5pgytpreAHeEwYDPjFCfwC3AZmN4Du/N9NB6PW2jtNIOW9t1btuScEtsojlpDP7vXeFFSxNZnxaYGWnbLEmi3P1yVpKXjbOauTj5KyJDyq2ZOejHQfMM7VRsRzTCTxDH3GMiglZkbuxHbaiO10gWvgf2kW7RV1c8Safm6Vdc2j0Wz0wrUWuAUeAJvgnWByFvTCI+A6+IZiHM8vaNXCtLyT4+d0KICtZas7HdnaCO8DTS2b4qklBzI/pZajS1I/ZTbKB7Rm3UzdR/J+hU83W4E9H3VoN/oIqsTsW2h48vjXrutoGz3M/erVFlo78CwESqQgwCS6R5xyhIPOHsHKtal168SiLBOxOW5s69zrPjTBFOLJgCzuTwWi0ndAKeOl98EWUczV/KUyqXdyQbkwKYVc8NWWydb4MxOI5sgFQmGHCN4Ya+vtGl/X0RU+NHPDEwdbzLndFzf8nWZL65hrEwMHwxPB4aP9vjXj8dtdNbQP88Fk2M2qIbgt/z+WpB9OvY9GatIXoJtKuTweaJBYU5ZsoKaTt3JdavFiKT/MQPyOjZ29+6y397Q7ylQNybqGRhmZhDn+H2XXy+LmjvUJ25bGTxFhGyDVJKEUfLFhiavz7MQ0JqbpeRzJJCk8H+uYOrujpq1/waHB/Te3OTtvO76heWYy+UCia2dN761Trg8+rpNvfKWE6G3eg9kMI3ZO1Tgu3H/JPP66wuEXywaPuo/39j1lvdQ7XifnuTy9nBxLCgamVdUFZsAedTrjTgRd0yWbt2S2bxeL27kf2N3Uj6qkitTA4Jz5yZlzlu31yd0NX0yvzLbkNl5qnndnpBuqwPtreq2RS525J0mP5RbxlQuUhuTROar7CpJ+O3ov8v3IfJ8F7w27Cj8AzpGOywC4gtYH8dzyjXb1A/WZ5LOL9YufTMN7wUr4MbITfoZZ3dgnQPvBB/CjTzIfvHtjMmFaUo+znqavMca18xPxCWANvHZCHKyYPHny7dh7cuF59mMyKS9iw4dKsEsDCgAzxRAJn9+6PCVHoRBzcPjmooVIcJguqrj1BaHxjLXbuAECskhOS1l3LYJkAfpiFYch4pHLkXhZZZnBIJM5DJtok2cpQ9Mk6a5GxQyrxDBDbVk7Tm9f4eQgvXNfzuV2/qBaez4GL4AVObAUPpS7NB9sVQXT7rimEw3XfMymI4AmMLsEjQapEM+u6Fwn+tb4QY3dFVB6nuH7OAGGi7Ot2xbmN2jU+U/Ny6NwaGh9T8IyJRDrR2bEgrN0+H5whp5AL2KaWDByQiN6invlskAB6ZlIIOC4WNW55xabN1xMN935tWbBc43wWTCjCczMd+L8x33g8JM//w6VI2tC01Qx56z4ocO7O5OqgXB0JmlqNP8qqIcPPJ/JhOrr4Xcx7DmqhvZid1xATMDiM3Y4a+Kv6yMCAviKiYtfGAMwg1YtznkjNa4pko2bckuWCPlZNge8AAPg3//g+6odohqZuOL3iAVuUDVVp1zjZSCkmiZMcPo0/xYmZdi9/mrjFGPiyQnp8+i96Wv4vAlicDr7I5xnMHNIOIlBpUAIFmXvmXyiWZm9rw3xvRo1xN8I4D4MHfMC7kFNBLdIgdWKKHRdARH4XxSuFnfr8YaT7bByOzPK9whSjMASZQMnyq6Tw410vyjpaAi4pkmu3ZJctUokaOCA38BkFzIJyWaz5kUytXyhxmTbZJcb5tjhCXFOCi3gwwWLLY2PjU8/gjyU3irkT5KqMhm4K5MhZg5wtnX89GNjELmK2d2R58bxjYu5XZxg+deen4/eBf/dMDT09NOvbqg0MoIMW6V7jd8YryizcA9+8ZvfwIerHIKMNlZr6RQvWpqZOpU/Tvhi5osvMntSuzOyNoFcMF4s62iXsuj18szu1B6POCaCRvDO1IWW2KPj05hLmb6GM8GI60bG0C4CAUaFyXIjsc+llOJcHv5UlGH09MutG/9t10vHEqujp+ArSddZjSPU8dU+8/Sbandx5VwWi0nhR0Wnf+CxkgwpPFvlFiR9UZ99smz1uuTgIF+cZYKvUpO9y+RWxcrA4CPmBz7vQQ4kFnvLbI3qGz+eUOebG6UAhBwtrSgTdFkS7TaacQYcJ0yLoQF8f/1UR/SxzvQj6IPpdVxxh1i5pEs9SZ7V95u6ekPjH9mJyyyV8CscmI1zYf4xgUANrs6OW2B2u/oZaYuFpdGc5ucl98+bdZdyf5/PqTF6A3OEWRYDCLQN9n5olBiTpmSNr1mwYHVy9myu1Q1KU+HfoxxfMgX2puDfARV7t8bdjY3hOm/SGXNbbDX3ZdhWRSw2wxx3G52wHLy7esA+/q7e9AXSvekJLFt0UaSfrGzIb8bC9gP+yF13Ffpq96GbCAyyIgswKAI4jXy4Kb9+hL4rSgrIpNRvUjAFHiF6Sjs/+HeVV5h01LlNEyQr1yRXrhQKsqzZrCZpQJbjg1ZWVlOryHBRJQqfyT8USd2ZuSn1lSgtgWrw5frJ1tpLE5MPoheSGwWCNuGbxjUavXGh6bB2sVtnWGrGb6MJRzYn0FxdeD88+4otpxSVqvYXj138DqYTxsJIjknMYqpumA/GszV08O7Ypk2iuE4mqo8FF4Ke+ETNquvi998vCU3RaMMr45KGABC3NjHqG6atWbDTam2PTeioTFewpV0xeA75tjpshP/CPPjXy9eD9xvG1fWj0+tyWo00IDXfejKdtRka3MS/xdSGuMKbaDp0VJswwIloDCWTa2Ptk+yNt/RVxl3e2kpgD0dmc8avC68g47eThp3fw5guYWMWFu+u7Lg6Niz6q0dIvko6zOshrinubg7jxCK66LXXRm+L3YZ9fs5zJzzBWme3aOXaxOzZbG6ICQzqbYtES242Knat0qzcJPj9jwA8B959CQHUTfAczuUI2pB4NNqL9GCf0WgU7jRFoRZ8t2mqvvGhtuijyMPRZSx2s/jFmkZeSjY+VDNeGRa3+utIZVVG4IBv+Kl1wJNMVqdKSksqh06hZ9AoJo1tmEfRXzKvZFEB1X50yFJcFtGMVKz5j9asRb3KxPXqr4gsPk5KQKWqij4JYZ2xv8JzE/yw6JltbKvNww/IhGXwe3GGo2fXy9S7wN1wy+2Pn65QV3roljL5Vk9lrVhw/1vHY/n/lFljRm+trV0wf0Fs8mSxuBpU19d/CbZMNsgaSF6PymAhA8McJj8OV4ItdwZa9TomiRwhoWUsboxVw/GLolxDIAgWpEIsJ13OCFexJvJEdl0oBXcF53I6oRW8t7hbm3xofBzTaPHVDO0U0J3y7VPKrFZXXGxh2HQSEWsTgRVUh3kAJ7DImV7CIyL/EjBKk2F7OFI7H74bBWwPTDpAaaHuBT62RGI1bZp6zKVdOTsyKf8yr1cTUvSKkZWOxbfp1QfXOVftrKsHrMOQzJ6gaNN2sZHa/hmmjidWsCKN6Tfl93a6brXqtbtc+ReiyeMz+k40hpPbDs/uRLt1m18DujaYTyli/+kooODtQx8g+Kc0BH/h5edUEq7iWAzYwpA/eQSUxIc9OYeCxxabp7rSPBZId8Za4LcGX6simp4fXZeZkPD7Gs2Mv4E6caBDj5R5nqmTbpjjmb7ci6RAxQ3g1NnfVrX4Em9Lzs+ZCk+l59621rH95LZmS2zBNdsymYf2bmxZVbf74d7jreHk9oPTDRGknUPf+iFm6c1DjxD5CSXulYzl4OYzC3YTz/3wR9i2SUXgKV+RBhmf1z9KoVNCkUqZlGr3CRumrHG4bs7IdHLM6ygto8D70R741SS2OphZkVu9ullRdqyxUadDMR9VWFONfIbCw6Hldc75dvidUYl7rkK5pX2mQpxg1JOpSAeaf0KCPIXCf2XhcW45gu+1EvNOTmMapQbzTqb+6hw2PhyJz2LzipPYY+Zer0BhIHOLpVL1WELJIm0SeporrnLJdWEdi7l0j+LAKh5jS+mmUsrM0pmkUpAGZBKoLIU/omWASoH/oLMmtBs7Z7I5fCWTzatk0QbYDSKLqIEDBziJxZMDm9cK1nGqIlJNlZ0nUXsD49krwIYnaZzZOa9CbauTWmOuuDndOo2dYBuz1AS11LtGgYoXRRVJuTmlS2q7awNt3vFRm1wl5orMUfCJpJVn4uYENyZWP3is17X6r7f6lHZ5kGVn+TzW5o8Gk8loDJMn9dAB9H6UifnTnpJcEbNiGHx7ZJx72JXDvkQLSWY88UdRE0EPjikCrjI3SPQi+sATtfemGjgVpkj6uJ9t2+F7BXsdbARsg7YSqJjSLLXDbjxkrQX3jl9t6ztuPDLJFJOIwBFJ1j1+Hxy0JZudC6iC+06VISm0DJlQKmIkaELy0via1K1cmgHEFG6/Y9Z9MiaSQDWO7bXhbk/+Z31K35CNhRPWhfWJdHqhI+kHs5ZlckvwKqxp6BDmw7oIvDwz5nUTMQR7lA5hqwkNO4IkqyRIv5UciltLUfouhw14umm4wvfPmlxN7WxJulKATPDeRlm4BOWYdXOFi0RsNP+p5IY9EiRefmt+CRc8g6LwNdsSvkS5yAiiZAT6eSBjnGMUWZYLkR0z2l2hE1m+0JWAm44kyDaPEC1PlyECzdfxL0QvHjrU2Epheul1HB8dXhrwHanguxkeupuByeuSoXvQXVhcpL2qvF4FDM5DJkhIir2ahMyiu0orKJGUgcsxWaqFTckbPNXBs+1UmZwuEtMs6lJq/sA3lIlbqwxqJYfW+Ic/nOn1aw0kBEEEXifyWzK8ybayNhi73vetQk7DBBblysKxQ9PatIFSFqeJymYiv0PhX+pxSVUPHcUk1ULU9Ys1jOHtv8zJh0uujkjhEWN/w6K5PL+7YWIkt0reQRcjqXD+IPIOl0O1SaXeKiY7/zaymlpO4ZQxaJSqMmT1qqmelgfa+Qr34XgcBpvsMqVRbV43O5hZ1rVMxOcwhNVEj6146Cz6IKrCZAALFrSE2zgqZuRzL+NR8AB3xN9AH6y54XS1MBisEzZolRUNart3hdKv3ur33wotoptXhZfeKPmutm7JH26FNTYbl0zOlaKVEjnyMbppRZ9xhbXGvM7cewd4IrM1v8a16HercYxSKeazP4jdzlLsJO3DKH9EEuqKvgXuZc624iNhT4SsSt/VLnxmPdC54QDDaJgmHCfBTPxXoF+u8a3UBBpur9kDfaYDS6uf7/wGWaes4carPfnu+PHv4QmTlYeW1ZcilUIJ+DE1tSlqXGgOdCydeD1oSC99YlzN+t+kCF73u9GLBCMWjm2bJeaKsedwF6cgKOgwAVOxdEMZeWq8RoCF4qOnzcdAFxLUqQRWNaiadNBVbzk21fXahOmPHe7sNNl61SLrfLletsSCfEoS1gVc3JBKRQUI+ke6UokDT9l15HKkkcQojzTIQyG5MyCCD2p6uCYhq1MJXgne29tzIVy779j5TWClO5c1Z7knxPXCRvk4sehlk1NIQtMIQhWLBCk+fEwmoxag3wxhRdwrk2A3HOVX28HB/M++1xJsWujVcEGP4IxolSUULL4q9KPjjI3DCeYr+0yGN0SrZBJQSpThyHOTZlBhkMzToU1TBTXBBmGbQU2Dzf8xLZSbFfNMIARU8NP4wYOXxPQGRVrWxEAr2c2ypLyDS8/kD7mrMWcBv1UyNdKYuVvQJktrJgiFcF3in5cqE+/FFP4PUzg2lGXoDnQWqsXkjU10nxRqh+4Cd8Qw8OmIYitWxIfTy3inHD7UPpw3Qdb/IQNXpb6GTepBmcHY7gQfHgab78i/o16iNFmnaxHa4cPpO/Kf0tKSlDRDQ1VH88pUCvnshInTJk2a4yp4y+fY61VuuzRpauZ/8DX2Esffq+UHPkhg+1pNsLiQsX2VE7huOHbMyL6SKZSCyRlOLhO6YfhJh6vf6PDm4khou1VzpAbpgBqN0md57V8Djs/ndziYYBVPnqdpFkpM8nkqsKMevNEEX3pDTKuXZqTNVYgNvoSSOe2SpHIC77MMgthq98dqGlM6p6o2Fxx4VSkAcd44SVrVw8ufAI/CjBcky+NfhYU1XybgT3//O4HYeSOBvWEg8lTRAtrsZV5e0uiMg3L0yPkIHQPlMmRkcee71dM0IOq1B41LpeFKJcyvUjl4PF6FpEfzNaC+8ELTDz8AfX6ddKHBoFqi/LdxtdwsXWl+XMMYp2xST+QAR+qYhdMdMXoeq/WLIgwqWt5QRqeq96ayT+TuQA/mnsgCqnK8oIbdIW0TdUkyql7xX+h1byfE/vdSeMxmHLoLPYJaCJuJz8SNG21r8I6xy3ocvXz92USJWj0WaeLKReJV3xGhQI+UMspqwtH21ng6zKN6ogOSNJ8HlpGFgbqAKKOXVZLhOZMa6P9VpVbXZjO1BiWpkpQ/L5mrM2oWyL7SLZNZpIsNiPXig2pGqzyjaGUOJqplEnxi25UAJyV0X/3drbyAGTpsFk4ZJV1GqhDKwcKMDb67Rq6g4VPcDK65BpxV9fBDvC7ZRH63IqPpE7574EApPfZurdj/bhK7qzZiek5DcCK6ML8zgk/CjsIUGb6lRbYKnKdseExj2MPElz2cKyZUOnlkEzYdnjntLuOJ3un+Kswl9sfrAuwvc3/3JGynHxfFqnv35yeLZxpMqgEpKLv9Gcksm1G9QPk3a6fZw8l/Lac1yluULcxp6Y6mhkg0M+O2Gds3TtR2bNh73Q+bSOtj17BnPhBpXuHJhZFJ8jaRn90q+eCBB9LydkUtB5PLlR3mqZH2ishv44LA+2nsNlswL/EUZiFxNG8Trjm0l6EEhgNUfBSBwPMe6ckfHvYavr/rgDE/Byi+/PL7f1VKKbkq3T/gv775Bt4gnWswaOcrmmVLTEbNMrXawOlUJhUT2OxU6j/Zj3KmbhZdfW3uoywwqjqFtbx2GXxVM5Ffxx4vv4mZeDeoqnknTiAN4BOpdEK/mUuqiXhLOUrBXTFrrP01MeNjP4iegh+93gDP1784VAJKBhdSF4O6XvqipUCbn65YoDPqFsm+NqxSmOUrTC9oGY3yjKyZ8T1ohOfBQ7fBjT4fWHtb5lh5aYosY6SYlXd7lRMFNbwOSbegW5pR9ko+p0feqBV534p//xA+TyYduh49h9qI53aXhEvGF+eOh3ORDj4B43JZe1CGJ828+rGbLUeKqtFXqNhTiD5OdLhM7yOrmfxhRQ4+uusnXlWaIqUAKjwbrwU1dlG1ZBHHwxIGP7zGqarkM4Xj3hbO4xnl/ZyUptdgNHfLVyeAIharrq2VIkgaKSOzZeKcRZIE5XQTk45SEPhdJgN30zLinKyRjgzGU2Y6o4sbXxiuCokMkl1ap1KNllfgA9hl1AV0SQ/dz2nhw481TYKAKCmdigYWXTveY7HXL552d7VNKqsgAVRhAVkUPketwGw00xR8DtyC+lPfBKXh34WxmykeOozFLzhfBo7EO67ov43KqDCvICcdlfckj3btinkED5+pHt5UNvYjRV/vfu328wG+z+MW1imklQ7VwbdC8M88eYLt4EQkFoE5skwVFIqAbTl8OyFVh1bpNLpF/rlQviEl0m+uTqWmUmv4fm6QfqoB/mwcPKD+vjTtuablvNHERskZElIhEAETI2TdNEHIC7C9wjq+geWxXheWmVTZxwdRm8OgbFMF5fWybnCgUVrHTMnzCFS/r52nUkrmqeAl/571Qcv8YC1u7VVDJ9EZaFUJrYRL9FnhFaw6gnOC8GaH+UuL+0Gw12MfOLXJqB8YpudmjzCIEBcP+UwmKY/zql0Obv41xSShUdQtfwvUxB8AtbH89z0diqhy4qzT8pliq6BPUyaNVqqklXUiMG9arSPQWYY5l2LkXTTPM1q4JFICFfLrhUnZOEH+BSSZfwLA/JAE8aH5V0/GpqycC0goHFq9afY4ZBtvvCSimCjJPx/8NEktj38c+WNHU6C7mUBFvRl9BPWUSEo0mAeGewtJAveWcnlQrtAMP4INyuNpR+nbAkXFZRXF5w+TgHsxb4KPPqKYezgUvbVXcc/AlNocKGOW05LlGlA5o3aaf3f+oHKCyqRpV571tU+25v/ZNMMyNaeSUeOaRm1z1Z+zgKxua3U1pjAXEnTlcqAxIw/qDH5R1BioX5lw8bRMzkBiWZPM+oMmx3PzogrltFC8B/7QGPdH4nto/ie6xLkX6krJqilLupx+e6q7QwT3gyUogWF0GItiHcT8lIPwkUb4JZmEX12cwSvoZaZ61DUfMbjKyy4eXicbsTt3WXc+5+m9q/yIWsuSMehviihZGu+1n3V2+0KFWTlo78j3GQfFBvFsC3IMHofntYtkZskCA/IWPA4m5f9PTk9LMtIcnZ4IXrgefpbI1lHp1HQZj4mcaWPRpB1woMMrbBB7xSlhDnlb2ChKyJvFp+fMYfK75Sl1n4g/u5+Km9iad+P4bdYPnUEPo0wc6Z5ANsa7bzOFmc/C8DF5TJftyAxywape9g1/iT1B9L3jfKzDC184CO+5pnwjyM3J3yieoTcr+xXgZmkdK6jKna6wsUNMR8WfKrzc2jAfrtEvkVjE803oCvg+vzbgFyVUikr4OyC/G65EwIdwmpyekzYqMU/ydZaSlCTJWW8px4truONku3XTdIr0XKZislwu7hV75VNkqulOt2iSBDMMUvjP2FajhUciZchoBY+3NOaYHo1soSto4bciopp3EviOGIkqnL3Y94TjKraUTCAw/4nMxeVJA08hdVE6BgtMSRnpSx420L4ClgHf58PuCWXkIvCL/4zPKeC7iN61oHR8J0CkiVhY2m6ysABsEDSN51VpvP6psjRLBM5Au0IG3iybl++VzNEaFXPk7eK5VoNmqfQU831eg1D1GYp+PFGmgX0yZqOsQdXO+oz5BbdRqPoSIX8prsdcB9q+NNPh4qMophNpYiH4PPEW1+QM7MswjI6Y0/T+3+UTBT72OCn8XD5e5mOPl9TcKqhj2G+tz9VJazKV8fejotB76Yp9ggjDua9csIJVy/Hje2bGdOI61EBoxMv923hFjOm+snvSzRwOhchXDp4Ma45iR+VISLT5Q7bdmRRk5AIK3JP5EGb0s2VG+WwdWCJpkzuwZwarJe3Kak2LJH+zdK7RqJmvOgoG4B4wkP+JmRLnpFkaqoXfwgqziU0qzVDQcq4o/irSD4QqQRMWhLQLbjf1SW3SGapFuilKm6rHALvVE0VB7jh5vP/MwIAy/dsgv+79OLZSJxY/XcQ8tfISJuapFbqmGon+BdxhI2SC/AuQ2RFMi8u4d8UuUnRkCwos8cPO6mV1cRjnaaFxswweHOD1KfTyqXxk/s5x7dvNW1tiBqHBuKQmVMb6hyRR3b4NWjSyBNdgXRx+VzhFY5BPk4CZdK4hbQtyp1YF+BpRkJr/QkSLS2KSDBW5P5GwVdP12YWy8Vwvr02Y16RbxzXUpVta+o0e751PV0n90cFDsVwdMn0gkv8n2K1w+XY8DfOKiSIPZ7xMqdGvbg9s7byXG+YaeBGWrjz9WYQb+QLnOMF36VHkZ0KrFOYKojiCycikkbJADDl8wPwrLgSZd2VzyvDo+Mi+/F08Q2NW9UuRKphLIOEkHFJvtxtsm9X7fdvVRtVmH5wuGdCaVQMKsMV30zT75G3OtHvTdMfCLd4/AHIacPJNCmpUnBTHqIhb1cn389qk+gXnL1RoB8VB4Uw9Kpsoj2gnSd9U9wj8mL+8JbPcE/GvysBXgTW3pDYcnt8YW44sjZEqY2+HeDW/jeLsJ0PH0ROovLhiXAJSBdyWMc78yED5lR7yqGnMgqzg8bV+RF1g/w9kMXDnFwD+e+/95S8pnCjxz/n9opkqvbJf8q5mkdwqHTCCGvAF0+l08YIyQSk8BrrhsedUVRFhVpKg/gF0I8JwIBD21QU6kfGBOp9CMY7n5bRKOvnjxClMg+afARfhXVotm0SqIaPlTK72JhCrqZFXpt4N8mvfT04Lh7Gbbxg6R+D004jZn+HsjJeYfuKOQgr3DJ8nf5QxJPjdcMswemH4SsFgArDorHoGG1TGMds/UWmUT1LMBk/nmcppaouyV4Ma8XGTONz/rpIakaakcdo/wMz8T8hxZO3Kx5x6mjby2MqApp7r4eRkd8RiEW6zMqHFjPoAqFsfj1Mqk6/FuNE3krFEAv45Gi0wTdyOnsVWoi9pI2KCOcQKxhJEuXHuwMt4EgRRJoULOBQ35Qqs5aJr4xs1haf9tWANPXsny2ixC20yXunOnb2Py4LORl6SxfsCQoYGVM2Fq5AjpFISyjbqbQK8wIagpchkstTnDFZ7uGS0diuNHyvnls2GN/PGKc3KcfwaTOTNmMi7FJiAJyVpKmAlHzbqGWRyFodXEx1KJmbE7brYHc0VIU9WWZdd6gL2YNPgx61aPYtcilkEKk/ou1S75NCahD67bu/6Q8lkfaWkU5+slOZ4NYKkAL6NiX4AE/2bK9OfhbmR3yXx6Eo3dAumEW1FfxjX/rNKFo6gOhEm7rJOpFzRXDm2nEjhFqCcC5Q4xd6RkUQOfzjDQ4RolOGy0mUHY0f+zI/lApQM6lmIGC4VdRhM2glisW+tUW9eGwA32neoVcotXpgQz9XpVPMVyMOG1Wc8OuvNKGepQscRcmkt45WD+wLLLFImn19pmKa3Kdt0gGSXafsbdWzJTpbKMcFjjkea8yfEVU2KlKyFhTwXiwlclAq00kgKblCkxX5BQnpUNE7r1XUo3uBNkoXV3eI/Kbv5Ps4EOeyJ1+wc0KoO1yVK7XQmNchk0md5LHFXf4iClsZJ5eXSPqfO3CGjYiFPe4dbIKVwMm5Htd+vqXufGn0nrPC/Tey5cegYupeo7uMZg4klvSXTS+ZewWZcLPUX+aFGwOVxvcvjusd0bY3C0MK78DiXv8TttdfDx+SAQ0GJ5sWRbMPnDz2Uui118mTqtvznM0xW8XhpqbpPZlFO1P8T6X8CnGIajEF+UMgpnYGWhjQWqb7KqvbqrQJkQalXaOaLaRaNM3kGvWsQOe40Uaae1TNisqwmTUEVPXXZbC5X10fq6VM12YLKdu49gvGKkL5Dxqirk6bgboOeQSqNk5EyrggIzZq42+G0V3c41J7Wvni5p06v06pdbXbVFvCewz0trlDG4EN1C7p11OwnSXHz7zwlJZUlHiyyOYeaiVurLKKdBC7PVlxdj7GZI1yCTO2oFBMx4TTc91bM5xanp4ttlmBeCtAF5ekyCaCk8qd40xVm6UxB+NP7wb2PfJpfWxRdUL0PLNsHl1YERSlRuAJs37cvsS//rXNvrWTNJrDjpajIcacHWb3ioXo+nd3z0Ioa2SRuDXeCKP8BqM+EQhn4ACxK6IYW7MVKfRRnRz9L1jRiL/hDVVoVyPkebNTEpA0svNbPxaw0jiVfi/kvk0dquiPZxhG/tnTUeK2X5btqvnHMFcKj3GFQScqofUKPl9PK/OFgrj6YCDDdgW5Rgs8ETQBFgCDgDfATKlkFAGQAP9QrAfIpXaH0xOLVekVpeWl+B1o+W+uRNjCDtpg/LEtw7JUhWoD3MknNrGPqSODN22c366USEvaqjoIb+dbmC+O4dYYO+G6L1SkgIF+pYikHSBNNLvjhWrmciqchmTxVCLhnh3bnqqMrclublV077pwHZiLwVZ5uuZZr3aJt81/wVVXf5+k6eBCvSxiGbkWPYja+csSzsRPc3AV4cbz7A09vDbcWFoVOf8V/wY/Akb/h701gM1z1D/Ax1LyraOXGWW1y5KR8Ii/E7VRdy3JUpMus7C00KSlHElMRBD4DQkCKTsnCA2chor3BLXTc6gA03Waz27nNzNNfaxSZrzVRrdfpuLatxpIKAs/0EirFLHSWQMScWNJT0lcyv2R5yboRJpe6UQ0H+iK3b7HUVAzuR4+GjTQj4jmNYtEa7wMCl906JaX4DQp/lBXVF/t03cPrp9CVdJ8r5g8KowKTixlkcQGF42KAh7WYuHYEpCqBxmiQS3ZxtT6umVEbHqfYkTh+165dA+CLWTt3ntkMj2GujbmslmIhIatwL6f/euw1JcS0mIxsu5BPEZYlz8g8exxrHduMIsNmxwaJ+f8xdh3gUZTpP9/MlrTtvfdes5vtvZdU0gglofcSeg0dBQQRECkC0ouiICi2O4+znaJ3eOqd/ex6enh66l+vyE7+M7ObKvc8N9nRJBuSb77y9vf3y9wxVj32riMLwHQYecs4WqxfyKfU57hhfrMxJvIYTAIRyyBRS/VylZ2n5zscJneoxRfzRAAN+S7iifnAHrcbeUX4kZgqeV/0Ta0H/d5o+G8yOQ2GgwSonM40C2RBP8XJpbp5YXGYhmViOX0n4OMwZiHhbDLgf8HEJfIG3YMBYC/20I7Rflr34ztWrGC5fR5eQiEuxwn/Dv7j17/OvvYagAtvkwye9GYjt21BM42TYKlBsjKVnjfPzZ8lHs12stqk4GRP4rrVyiMS0ySYKpI9muiJr0quhXqTq05J2FzkHAg6qHUC03vT0oLQuwmypfE69Pv0VR5lD79L5JdPFGMShI1avA/DhjJRiRWlGJ0vjrxIR8/ARlzS8dgGG/LwtcNQSwa6i/rpVxdWcubs/5aa+9WLL2auXZviEotDgiy78FYsoxEJQwEvP6VW08mRpSbvIh2F5cgYcn6Fx+eRBTzb17y4fpzWS6IwGkD1G2D+RfhBZM91MjHh51sfDsDcpkjLSxeaW1QEQp4I84Khnvr27rBugS9oMziDNTWhBnXW5U7+GUujfYSdeV7fMfgs3oPnL7EQNBZ17UhoFc3/9ISYhoCHd5LCFfcVzh1csSK1L91b+DmaVAo5Hr+Xl1RJq8jh6TWOBbpKdk3a0uyRenw+YcIGlu7b924GPJTBYiLYDU1dm0isjS+FFqOv+JKmWPvvz7aNUhKJ9USY7Qp1TxzT4dUt9vo96K7218Q7VKMd0dDptYWnwCNIU83n48dHZs5En9SD2sP3oX68G3/OprLROE6dYkAVKngDdb2ekdFyTA2Qi4SGmJ7QjKgDHzD3B5w8nLis2HoDnkAOgtUMSh7VjzOQFrlfv9Mtsdou1Lws59aI6lmuaob3eZ1EXc0XVfvHiycLKphkCpVSRdBDRNkilU7Zoyh4pBNEFn637Avb7TqlcauRDvlkywxazTIlcjvYjizNIfPA3TloY8wjp3KaY7x6Jdmn1nse1FEdQpV8qcYglRCqCYCYIFSVm8ZCJBhVREGYWAHJifJOlovVISezW8VB2Vjui/JWdoTdKpWeljVxXMxG8cbko48mm6EiQ80e+GnoPfQzER7/wDQCj3QLJmJ0ZoqsJVgZIQM1r4ZAT2FhEqya0FFs/XsAPIuEHcRl71DNU2fNWg7Ca6ZOHSuF6gCxnKzX+nzWNQBWtea9uXoJBPVCwj1cGZfCgEkE6L26wg9KgytXKfx39vV8/vXs58JKYflYnUJpDYExHcyxmxcHgu5Jc5rV8XweuarkMnjifAX2HGpUcv0KeqeMimffyoaELHCQCHw1f/lI/QoPeokla0guCr405l3wA1JBjF/vphxdtmwdiK5YvrzFC7yhuUlPbHoEuiuSLOwDH8xZ5Xrpn/l84WMtw0BLi3/OfZBDX39nUIHbt7It0LkyhI1JhLH/Qt9icWncr8Yi6+hdigncaoKHsij1b0ys5g/D7GcPUKC74ErkzQx4MossJgU/iND8XUuXrgSupUuXjrJCVkIV2eqjSiU0r1G2bbVt5TongLIQTHGW8wTljBoVukPOIUpIU3g/q+f4qzNV/L7se7nce9mveXR1i0spxarrLN7zY3bXxbLrDiyWn4K2Jsd7oFcFvAoAaGIX1piA2qPX4aOwCuN71vSjHgziOhYBA0qgEJAWrLz5MNiKYWl/Z0rG02OFGQH3j02gEbkMLMgb/Hz+Ru7lcdPtUy9OZ7W7noWv1r2MJU7LdKjt0gHdGIqP8d9h9zWlFiB4AB9jH/RbvtMWEoQU4orv67+pcNRm7BYmcH0FXN9/X/8VAO7voRsFuxGjiq0jQBU80XYMQr9tU6siO23jgmMXLlxApp9YqKCfOHECHc0GVNa04FUTtFLdBOYzltKJChejZFeTS/Y0RAGpXOHZPEj+BwrfzP7nP9mbsPJoQZBOQ389gbgwWZ37Er3Q37yx7zL8ICwodTrZ8R7QYQwOWHMlD8MoGEasNRSrACczf7CyqjyTi6P+gzcoRN4ExnoMwFxlcQtEtX4LsYqA1H0A0b9A3vyg/osNXWaFAitsQQ3ZUVDFRsLawj8TVin2HabAkgaiQ+iVvA+9MP/Nh56uw9CX6J6mlDFKCCoKdDWwo4XhbWDQfjwsdQT3E6yXZsEHTynIoXHZbKErOw6c/n7+hfnzo9gLOplKFVZBPqjQ6ILWQogV/A7xA3jjxo1Xb0cvHJf1TvgK9HOpOsWGZ5mLnH2YeuINUJcN9J/ijHf9nWD9A4B3L1zUEF4WiS7LjVtqyTWIp92pX309jXwLnUW+zr49F2F+CSxffpnCXj3aEPIKiEKxRCIMO8feHogooxmnCzX8VNMDYAOyLjZHBE5NmTLl6CT0wualq+8+eB66ckK8yrSoaVv66wddrv5KuyHAsEBBGsl41c/ijX7er2Y9I/rZHhMpJLSq+gt5TuhQ6DEZy8lL0N0ExpOgEmyHKwkQH1WzvLQCo4MjQQ/AlZRs1pEJV5FAG5KDjuQKP378MdB/+iny9seZT8HhCla4glX9Q6WSHWPIK55Ou/lSyXylrlKTAD7TZrPVzCKR4qj7IeCJRkv4weRCb41rXFQnuPlvVO9laz6aM2fOmdnohck4G3pGH4a1qMU4qew2bEfcGp2fVzuIJASGw8ig75e6Ffrz2/301+gqkwfqJFQc9NcRh9X3ewapNTmqIk4J+mt64/4tWp5uf5QvoqPWLp9bDhEgL4HA0mk5ZhPXYYE+8gspOovJ0LFUQbVpfLVuNghAJKpD98JHE30aa1zazEaeAEdYs41c/pM2t3b1o4+yVSJkvLyO15mqaR1Le/gJAtQglNQmFD4G8evVxINHCAR5lgW1/AlewvGw/Gw/hyPhYHKURKUJRWzYoVBUY1+aCp9CcRgmh1OmVrsmPHvtFGKbM1LPBkujE40WVUDczE3kOTP1HGFsDrvzWPQ8TIDYxrBjXI3LuTAdNCdcRsWUSSxzVbAnKKbww1x0BfagcikC20pSqQz0Fzj0+3Qliy2SL/w1/zVDWd5aLqEBSeGvkAA6UgChCAzk7RKqsE6GvPzNN9mff8Yk7xTUTl6B/k4Bfvosxbp6aIAsxuNmDUp6VFThaIRuD4xh0BfTbNjJWwEqSTDHbungTxIJoArSR0Jd0pTl5vgC5DOm6BByfgaP33ztGvguUO8bFSq8eg26vR5pm2+ycQnkehIk0BwHM+I5dfaxMbS29F2jcoUYdDU8D5H/HZm6ao52ztLAzZvYWGv7foXagC68EsWKx3WLuQ3XECieYVg8+AexZA7zVJwA5MJhReD1N18DC5F3gRY5+6nK4OGHGdyTkignorC8i7oXauR9wFl5c9+KZ9atC/f2Prl2LdgSjbZH2yNmlYMb4XKFDVK11RlBv3Pgh1jsh/gl9EJ9jjN9B2A79LcB/vRB5KoiCgi2OmegO+oRGviu/54Jt9y8lM5Bs44e/er48eyZM+hzWvsuwudgVkn3YBqxrJ+rfmhDOK+f7rPU8AJz99y8fQ8gIveAOXVgDnLPU0gMXB16Q/rCy4kE5G6Pt8Gj4u07GxruaHinsTHcVkQEP4pKOMlA3BzDqCpGNIcmO0rOHuuXTwY4Vo8tYLKmeV5T1L6QvfXO9Pr1J8BjGQw/q/8GO6XpFkdbCDGDP0XmJu3xP45OPwU/ni5sgQM3X0gmoZaTJz8+fDh1+jQ6i+K+Q/AFWI3ufKx+sV9nYgznqgEC235bHo/8DGCgqIdTtT/T0PC664JXFn7Q3ee6L6lI3O0Gh297HuzPI7acf4zoQ5BdjbQXEcX6b1gN//iicL4hZu8RVZpnaePKSZaH2iOFH4Mh8DqNlTLNr0fONdze6Mvni0zWR+AdMHUAC6WEzzI4JMw6LQmzgVqk/swscchg4R2F71hi8GIGmZnJTbReGfc5qGTQ3/iKSlp9mHgBLDhG/vWximowHbm9ig2+LTwADiAzB29wXKFG4hYraEvFvEu3hRTakF1AhmMwn5FgVui1IYnxZniZ1+tyoWPW9B2Ej8PREktf8pdjHjroX/Sn9mccfvEAxwt/okjB+3mkKR/sMHb0mv4FhHTaF/+pJiJ/+I5po3jZXob0j3wvI8K3fox0EqrBXUg3hQpRCneAS0jT4A028czIWKMJWIKRaGBVIiTWB8y8EN9VaeSEOQJBXqwyOEM8c0Aj+8Y52+Gzo5ujsmwyKtFOwsphFa/FNQncOg4NUBGK4a31V5ECLDZdsm6IRf+5aHVR9u1LbE2uX5/citzx/ffxHpBIgZeSyDPI0z2gdd0za9cWbvb8aV18LSyfl5qJXqkeaF7PzevQ118eP164BIUKzwXBq3v3nt+3b99vz5yRHESvsvKyFlSq74crcalRtAkby6aVzRqsc8DGV2TZ6J//XyyECjOKMXxU4kCV+pDwGP5DxH4UGSy9PxjVwR4Qnt6FPDO1ch4IdRT++O67PZHpFfLqWqq2XLeLLKd4KUqSvZthqAgKNPMjhUsTJoBZkjkT7RNm8kezOGaBimmr5ptsWbqvmgxiK1ZEdwi8rMY5c6Ld3YUFE6CXqQIoAgT0m2/BMPKPCYdFSZaAn+eyBA0CrqCRx5N1y6oy+bs71KdPZw8fbvBtfKLN2nh6rlGjFLqFGpZME90Rp2iZn4WPHnWtgObtC7dAzeHM2bM4mvBh+AhqkfSvMYZtNsAEjW9bj2oo3vqA4QDj3LYMHBcc1yAjYOzBUl0drzUYntRBvvwIqFWKM+YQM0flXV8IentBubxNQARfITwJOIpMygAq8j04WHgbWMU+eh3TLXiJ6uVG2C56daQzsSFhn/TwktxTY6yq5IlmqiudeypnMctnqKF763qQj9IHEHlDg22bh1+z0kLVzlfJJbN06MksRzXJFXQPe3DU0+QvakvRhxt0eTHQNkYRePsX1abYtnaijihOV3fnnvZRuww7G5scFEjgcYSE9NfE8vAyzxLgXydR7a9RXk+9agsbth8ThMyt25GrdyB/6uwE67SptGZadlS+MZxJdu2fdtf6BqVODFIuu+HgV5nM3PFIqOPivYC4AVqXXsaY8niqabkjFwbPP/44cgLUypY0Ny5DJTgb1S7LUZ9KgOvuMk2/K4G17hZh/PBbxQD9T9QvgmCMD9OZTCIbkqsuxuelFsYuF7aDUZvEygOfSGTe5DguPH06C4hgZIkFTCQgN8BEMAbdamAuhOwDLBh5ADkGrU4mF3QiYpBx6q1tf5pdOAg6seoQDL/0IvRDmXRAQmDsgPmRCHKqIdkV/GBphshHfLT9uRZ8slWY0MAQyvBMIHx4zpGQZvlYaesMecBpsV39EKJ8/fRvy6VzrhYefo8v9fjG8FeB2iVi1X5A6QWBNQh3/Hhwrrc3vmbN89ZaHqmt2qxRuoVpro7vaFSAtZNisUnIxvHuIJ0CQhaLo+Xa9HR6Uad0Anoh94IAawKXO2FUY8Kgx6uGqH374GWwHT0jRYQurE4OR2cGwxGWh8D8DTk0OHjhsK2Gqq+SBYgjtKFzoxngv4OXMY0GHd+sZG+ObS03GiJGHY1dZfcv1qSpnE/MRmT1W2xNcL19BYjdJjYceV1qPmG0/n39+mc2b0Zmjx4N2tdDz22GDIVv9SasTpAAs+Wtzz4bnh7VBCcsmfwMt9Luv7+ZJ9UFwzWFP4BOtVv/yAvp9LKuP9q95iDy8cKFC2chz22Yz1a758+fj0pUuG8vaklZcDR4jDPAj2MI4523WHzPiR+kUnMtowR+CIZuPuyhS4YjjLkhRCzwgTO0nvsgify9Ud5t2ryfz2yuFrzxrXX2uSSSlNnu/UCqcUfnibaB+Ie9vdENG349nU5cDUIbiRTE3N29NfbIIzGl2wfOWcMUUy3S2RJZAM+D4HmTEDtotzkN9a/OyGSqFy5E3rdklizJmpG3QRKVCWrUGjoDfYbF7vFsdhkGcgEUI9qDRoJc3AftL8yC/oNsFkVDAXFWo6pGlsJjC48Y10XD0fUq8Kxtmybi6DVBn9Uh/0busDl5MLGJAFEkMjAm91jTxXRN8sEU0XYl4hh13oKOwtt3Fr4XDpZVoGOox3u3B6qLhuAwD6Bx4SbO0DhO0TkmKkt0GVicDHPpsVILHgPjMsP+OXzvzfvAUb4wp2fvE4WXrK3nRNtjaV5jz0yHmNfRtIHCB0t4Xo9LGFHIq38tbuZ46VTk39IQU0xX8x/LASWNi3yUhciZz7aqpRN7JELo99GoU8/J6r+PaF0etoepEvNdfLtNWks1qe5VOP5usnBhOI6R8Anvlc5QWsQcWkWMzK8xIp+DcbJaABOuPgf3ld2d0cPlehFqLXPxHJYOXQ1Nqc4WwyFQDUEe8IzEbC/hCg20ERZ1Dp6RQ2U61JXPf8SIiVK2DvtKz/Zd4Uzl6KspimPytm1iUTMbzNTMlsTFUw3IYXkTI0sfpdj03GcNvuC2xzfBOrjwlF1UL0R6wLHpy63370pvrKpMVWk4aTrzrnSvlNsiBNd8r6QMuRcSyP3+T3LUuq8iyPO5S1vNU+9a5MKzQXfDe2EzKp19+JoOAYgYbkyM7Mrvd8sHQCP6q9CHpecwEL/eupV6H0sKqlq+vCze/27mWzbLbDIZ7DJ1yq5P1GZrHZ2idXckguSXF1H86RUrWM4oRHJte3W/aseTK2s/4YscNoMq5U5pf7fELxRANtfmpFipjy48HA7bNo3jMaV6h1ElFiHPpMzIQnBxTY85d6IhtrO6PCFTJBmUQ7GZLPvoWbH2TYudYVPXvDo+X2l3mh0mo2vhCaFaUoZXlO+Dj8FE1L/UoloqfAuEmV8uJ6tkRrBwL1MxLNILptFcgqg9FqxFH+22rJMaei5IDaR7e8X8LJML7kdGJ4EU+eSRQuFJAD/22Kvg/z74zUVRnRSZAo6tmW7IXmrJbKbCKYKOnWRTd2fm8PljJRAJ+Sm6rfDe0kxmaWpZCn1hI0/0vQLfOVDpYiiysg1WCfTXcfVDApRQz/GPK3kwg8lp4HJAKv924sWQ0vVSdqX/WkqZuOYFh1A1uurmr8Eq5B/QAmjBht+FbJTa1IsbM5IFxqR5odS0XBoVLbcgv3ojlXojjY1E2XcfvBPV89VlbFTqJkojGShXGFFkM7KkaQDwCa9CLUK2qjgPZMEccYrGBOOzhYmh+91C97EEWBa8ZOOZH4qD2/8swupSm/UGunJs4QH9wbdbkFfK+eQGJeoDQzDxV9Ad8x4YRVH7H5h3ByUm9QijrOOMICvMDzGR6/FTZjsfp9+kScXb2ja6ooaJ8TgvzqmasiUc3oLl2LCKwSM43xk2t5iF3jRyfkdWC5IH3SjMtITRPcIbplO5I2XlBXQVqNWpSi6YkEdWBd9JCxpe919Nvelj+d7MiqgS0JUtvJEFNKq04iZkKbzxa0fOFJ6mqKFQ/2H1dYiFNd1Tj0jvaUroFbVNNiW0q2m7RUYRRLc3NYjrGEFaRg4zMvyYtI4hVjoLL9lskJfj5RT+BHZurHGadF01aibNHbFamGFNTcRSq7fKaTamTm0u4py+hkp8K+pZcdHnHyrvi6YzRuoAlUxnFrzi5t/AIjG1kawoB4tungS/088QNvInG38SjpXlnFOgXfX1PXIas0dS2FFX1wVMs7iTkC8m+ju+S4iWIN9if68GtX1PovYKCz2F+aEd2uiR45Uydv2YZrz+fU1mjSSURPeQC/O0HUVPm4Pu+M9d/oBlGj9LZ/14ubpaH6m2019tc2fQSZc8zBOXR6rM9KjGAode3sLf80rE+OJF6SNPCpE9YBUAL0wmrQcrt1G27AJgJXRbd8rmejAs0OmSAn6rTD5L2LPxAF9UmzTXMmWSMaKGLPLZmJWSBs2qcc1La3LWhc1JuMrsp0BZMTNPrdSNAphJj56VvajUtZYxUA8mg3NmYNU9+N4oxTsxusGhz18kk8Jc7sHAsgfbaiXAwCJUGgfDUCWi7g6894qY46C70gpVMh/IVzArkal2X8wzmV/H4fx4P4MbFHFABegkVBHFQY+Ln1Rj3gWE/F997NENlh9uR/6qAErkL9C+5KefIq99QfkBei1iUKvU9UG7rHM3laVnR9Ixg2ebj2pWRuQWaUqLXOjyz1Dr2TCchKBKNtsqQ777wDvelo70vN8Vee9wV6QLO1OCvvPwk7CgjF5WZD7JYix7AD/zpUXFZkAz8tFRw4FLxDEfMfGFvqv2DDSI4rhTRVduoKH1nx5nRgU4V9hmeoBfXyPkIY94XQH7BFEdm/Xv37oYQaqLAYRrgFaBvLx89GVIUXg1W68B5t5qboSaqg7ywTFOi/rbm49CZerpgsJNfpKapMRQf7b9tqrWhDQs1tjnOdQdXSF97eEoxaJINIoN0i5+y+qp4d5ZrW0Rr1KcmLwO+Ytildpo7FXRLNuc0ajlfg+sWqMxGtdrUXmpQ3XOGVha6q+L45hAQ0MtpVhfEfunv5yQO6TZWj10y6M/jf6w/93dyKMfCLvVFvk0iWFTDsxD7s4lz6yHPpRMl1tlk6Vvxd6KckLvpoDllQMC5MXpplcuy86/IEXOgJn1YDZoDy2OKEcLHZyxCte78FuRh3q87RbwR0UXz8HpQvcDq0ORUXVxkNR8UUPDnZlplnrV9FQM5OEMiGG5kkpUYp6CRTjKEZYtaSvrxJghQIlqYyQ9B9EzEvgSg7rFkQlY/TBd/Y75LQqRcUT1EwAqfPj+lSvPPJP48MOXCgdF/CzDQXUKkvyAtXZJ7fo7k7Nn31VpYboYhoq/kXQMD11fDsrBaY7DbuF5xKIK5BNMFQMpxAp7vWFP1DsGGu2Nej4XCLolteIGKbIXzHeMjTr3bI2CRgLyWBR4jWuUXPlq/UeGXh1T2atFfcrHkfNqPQuvukH3vnw3iIZCHqyet7yM3ncPvArvozTi/WoY+jdW9VTGKuWLhgVZS0/PGDZRDNawjoX+JtP+cj9Pv+WPwSnjHhmGkv0Fl5Nk2vm+ENOmcpnrOQt6Q3Pm3JWZMCGycGFd5EemxW7i1Yr55ctJYgvqCZqphbfIGrqbriG9W25Gp0tfDpUvWrQIIH9vawM2tmCSrNbViDwIxlra3OrIvlQKjIaQ8ylkK1hwf+Yi9FDmfmQX9HbBrNczicQYCa7k8C/kZ3e4FflZu++daNmsYWo26p413q5hKTcaPz5+/NOjmZDohS/QXcNGLQes4tmBV3dMKJtSNqO/6nkYLS62e0qPznAOtp8Oci4O7KThs4mba/CIDYX56lg4DHNn4Yeazp9I3ojtPHTocUDRaaMGPfUnPjFRyXsX0Ty+b1/0fOHz6hpehBMi0WtdWe7StZFFiwTcBJ1MklJ9VBnh92Q13YPOHLR5LnbdeeMGuBLsbUS+NZsBozEYXbh/S1pcv+bOHhDLUKu4+fAbkWAICqxG3hZkxMg+MM48qUKozqxLJ8F4CDmTzAj4o0VQlXmrmqLdrP+7+TYtU7dRS4n0RpEd8zDPo+8M/BDUV9pPZRoyZxhrY4mSkERW9tcpk/sjz1gll6NULuP2DCYtR3qP0DevsV0BnyAtF1c8UK8I0Gyi9fsv57gOqlxOMc+wh65YKCfA9durdyP/4HQ1mf6cH2Uf+8H02S+2OPRu0wZ5LVuOZN2H6jXZIzVgVPCiW2V9KvAl6RWTkYmjYlSwuY+QiIBcT6qwTCUQiHFCBVnQYIKrQI4gZeRoTEFnTYW3wdt2xA1XwC6VVb3d7JVp51unmyLaGVZYNlOf1i2V4DxaZ1Hb3Vi2rGxt2e2Yhz9kKsjFwi83dkIGZgWrEvFgOUwPo798jcMjk4sz4vYUeVA4IxFUiinOIlmKjjessZ/0i8njM2rcZoFDxq9s2l8xtzLBuXOFpV3pYHgrtcr2xdM/dBKDnJQqm922bVQU6IxqWZ1qbUfMJ3Zbc8FtWrHpWLBSIKSKxBS5mEIkQBFAJnNNZq9E3vT8ZDDBLjDoNhgMIn0v8mbtgbQofI8XWLzPeSXuq4F71pj0LBIxQYDL+eLpMAlUxIhEsx/AAAIkF6DKWulSOEaECvAPhEqggOcG5lVVixVkspFrYkIEVHVCJi9gwft5EW6Um+KKBYJKLKtZwRVwhAK6RqOmQRAwuqbqqDqmTTJT7RGpoDGqUbIQr1ELuB3iiGI0C5V62r7T8FHo51IPRhjVBRgX/Jhf7tXiogywaGKBeN7wrTky3Y++iRnVrJGTfvc6Tq3LIQhKJZXPmOeVR6SL7nzHrCz3stONn0LnNyh/9cjJ/Rql1qTfKDeyjMjlb4Hzxo3kt98mb/yhLoQUWDE7yX4uJAmftIJ27wUbL3I4uhNebTAwcU7dKi5vAgkmBUlkSYoEwU4yWe7Eur9tvTEiGUiENuE8lZevA5/k8/nbGtHrA4ORY+YjnyrbODFWs4LAaRImNFkujs1xGn4UtpQtQPdsb9nGsq1lO8v2ld03ZO8WWw36N6yqdIxLuEQje/vw8PYvMH8HPA30bZVHhRmUxXNPdg/uXLhIjEV24r2AqKVFgwY+JcMjQNMhJs/tsHHdRslVs1VPd4mm3XbAzHfRNHJKfhRyg9HUQTc6jXlhEDWr3cgZFhe0k1vaierJPreELVIbU/w4iwPgpCpWv1K2oSk+Ta4DIYinYgk0uY1NMd3xZxpBhVGmMqxVKCmmUyRJwC0oPFG1XimrPkJcaWJQzlfvUcvoe0mrRCoqwXK2Vuk6YwdN3idtXOtj0UXdehMLi+TAfFmWBMOQn0Dk+wkEG0wiyuyLTXPNGuUEK42pdAgE80xJldHmTvMEFu3CYLVF45uXCep9rojX5ihns3VVdBZRb3RMTINyGdPGGyfz0zSQtKLe528Lh4VMZjgsonBNSQmDm0wyhAJkFepq+Wh5CT0visnrWZgvY+q7Cj+AV9nWYD1IrCH9Iu7+asXBxpKiWCJpGP30Cf3lbOhbKSqdViGbpowrxinGusysoHZxeIcLslzmmeU0gZhibDa28EXQpL8X3v/rVfBnRAKF/5qtzH8ZBZfTpMoK5am8KrFXBxPScl3yfB2bnCdi0P7ZcjrNthQiQtBvCrszGainvr7woZ5urc5X2xkljLCnYHWZuiyJWuhj8Cfof4D+8Q8bPubBk4aCjZL+K3Q2G5Vm3IGuuQBVSJV3iIPSFuUqtcCnXWP9DWzaZaVYmGwhxRrmUzkWJgeebrl91Lh7ag6MbTVSmsaEMw1KIgS3gsezG8VpW/umvGVT/QcQEDQh78PO3wSrPc/6wW9SVWzj/pgoepeN5HdIc88EBAkihwxVZsgsRmACBMEQjMgTY0Z3dfpbu+fdtuPVRbrO45fWmtamUo8lx+4MdN41aXvwNzSHY8ljD6np5qpkuRXvUdD3nYLvgyVlsrIO1JKbPnx1ByeHBpW0MMCrvG6JSqfjYWh0t0Kk6+/D5AFeKRuYqCZRYfNoXkyYU6+TKkKqtbWn4JYx3lAVtzLf0FkDm8vpmjZdRk2rnjNdt2qamLWvfC+xfBppKomUrQZCMvJZNRCQkRt03rQWR9cSKp1tZrKkFEI1PFmcERtHWZEmMg35t42mA7AcnAkBEuy5nBEkdwUp7qSy6eWQOMKgV1aloIroZgoReV7nWGz18cRpQ8iSGruEnWJr81XxKkLkHvCqPC7v0SQ1U3JNUy3zO5UCuURhorp44C11jmWI1xaeMpOTVUlikoL5hMq+o/BjsAH1+jNl9ag9M65sKl6XPqzlrZTVK6Fx47LPyXFqhs78wNQP1v4q8bA9b7imGGxk3fI7do3NJPAKuaSP+aL6mbq7H5IRkyQe6vu+wODc9bubv6LRqsjCDklC0iZUN8qFQfVa5Wnoz3IencOoMoWXcyHlRAUjG5kTsHRKQExar4iIUJehF/a+lCX5XwsBwv8ZzGyYWEeEK3miN7OORGpGZryAIU1nbN6nJmVJ5VXKMxle4pQaEDxuWf1rRm5OTCDmyFU033TytKXt8ru23Gn07IwRjFuSxtgu83wlRVudLzfS8Xn7LWo3s3EMkWIWKzzsnJYAt9zDDyqZrOyvKcEcBk6JmV5TrAiOswQM8VhZVNYuWcQ1cIId6zaYgfF2q5bP5vKqAyFVXsSCvp1YuDQRpG7iF7IYWn2NOeVbcClWwVEcSYsT+5VEEDfLD9/PLE+ROWQiOU2m03JjARECvgI7lYK+/unixW/u/+Y5r5wrSVYZithaR+CnUSuOXxYoi6G2QjPqOf437GIyV/PLA1d8d7DoW1NEte93mItPN9Cm8LT0kbmzT8sPTvQ79D5dYJEoyGQBZWbc1IKORqmqELSIg+IW4VI7z6vZrFGP5kHMc3w5nc2ssAQW0yFNLvZPiiMQfNBMs1/yrYTGfVzxyM5E9vtR9Anfh4Eml+wYlYtHM/4Gf9wZ+1Udz6ZJrh+dHpMmVlQrT+bFseMa8linqPHzWhKdmIJkhPJseVV1YEY5YCZmcTqQmzQPM8UNUndKObqMSElktcjS2jYaKnkUfX+An8B57GvLohiX1630its99ASQiP2ldgN4lpjrU/LHixgQxR8OMuiUCmWnLC5uV4dTTkbYuNVgWiAFX6lEDB67yprZXAHK5n0UQp4Hh7z1eyaq3Pt9i/aAt5/6R+EvX10AlwsFyP2ooFxPTfyuFpxPkiqqTEeyoug+OwFqlcsbX3aQaMScjEjOlFdTXfPLgUlzqDWbrkslgnFNq7gzPvOVROKV9DuoYYlarRmKkYpFyvSoHsJqOmh4X3us2LusGtbnQBwyBw7PrZQT1gIwhCdrsIEZPvmvVxHZi++8U1c4RKNRyiVjpGHxGAlxrFJM9xunGS5C+h02uZDOYVWFXfoaAx8czYOLdRjbIPLFNBD7KFke/zwOHczsTKd3ZrbBt99IEyurtaczwtgpPRGqkYvaT3sEaSK7HC7PkqtpDWNg1DIpfIURo8QTFy5UCSjainS5gY7jAN4Fn4btZY1li8pWD6kOLoJsDanFJyuHU87jbnBx3Yf0P6hwJkdPcWrALRUUiTxEKpAGDA74NKGSbHVWMO0uUUoJCMbuDktrsxwGRqqezlJUOaZcvkEXZivF5Z8jn2s6xDXnmmvlbs0M1BQU6IV0upjOEHGJRAK4+TatmlouahfHRG3iFQpmWDNXfxqQgtFxfAWDJip3e611PKAl+K7XU2LvBnuaTDIpDKgWMwgQQA198saZrpB91NzuKhNMhGMVNOeBVNhP4TdLUsHVMohMqFdp9LutbpkBQMirUjrmptB4QqMCWDKEyir12ZwkflRHCujljU95eBlQUUmFKlIEZnVjN2r3IHdJKHpKutJMQ6WPuu85+AwsQq2dCI6d0F7WjWX1+sXKUOk5rPXX4wakW8QaihwJMEZbweCNBJQoSSkP8PiVS7SCyTJIvdIoENHYDLKvZiqNIqZQKsmiRlFM2CRbJADzE2Pk3i7pqYdSTz8tVs+V2HljDKnfgc8Kf/4VNcyv5UWpQMaICdy8CBVhE4z3tOlJ4z6E5gkbXnXDdFKawCbD5TlUvDSPRcUvKU2uqNLcl+PFDttINuSnnuaEbVkoCeohBLV4xKJZap+yW/0Z9EqBnYZrC4blMol8qfqofrFcJF2kLUzXlwso5CzFiElsAx6/1Jcx8ZM5rmwKHrMZHuDDQI+JtxJRHs4Qd5w00H6jGoTZJw0hLHVh8sypGSbL0Qlc+Om1a4n33vtbwF+L1CDXaVXUCn6bxC9oEdgTYolbs0CfHfcHOY+pYJqDzkA5DXwrmSnjayfJQLIAl7v2maSme2sNOxeLN90hRW4CYRWAYwSo4u+Frw3TxELpbEUVtOlXFdlHspC5OzQJ7g51h3YyV0YSBEq14lyOHzmLHnF3SDjqmqeakpQTyQkKPzQdJgAwh++vctBrOf+poKO2Q1I+UeSsU8QVzYGoI9wVh+/J2k7RfdwaXrD6n1K5NFOpYuKy/QHUK9Sg2nxm2dyyxb+Q7c7+z3il+BYm10AxGjy8v2s46/0QBGPUgeQVPcYStEcRTJTsxHcluhwxBpVaLkmJw+KMiOtjk3WigGKjZrIJbLW4mWxGuS4ylwtPMqdHS8Q0ttOp55lU8koocma0pPVyllC5dLcotstbQV88ju1Z7X4bLK5GnvFFaMBjuO0nkVbLsk2Ra91RUROyh4FQkDZox/6KvXvBkxlSVbXprkZO5h4zDEGpiCj3mY9akWFVVteRKyi+nnIIqbcmV9UzIt0uj5BICBNghsbA1ftn60OKJQmadHQiJGrWs/hxTZgVVvgTP1cG/+Vn8YJ2UUJcazTWz4M6M5nCCamKm2Brsb2r6zsAH0MtTkpZEK/m7yibUOyv7g8rYpm9UnfRUGuSfGu7A2+xxotHiqFKfLKxo4BZVwPWJngk8TO3Kl0heS+BPCMWxPgCO3iMK6Gy6BVmz3wGFz/39ej3G8UzRTyfao5aNkoI/HEx+OOVisq90adDk4m0A2AX8urTTz+NWKCaxzIk39N+aOXYQykJhTtmaybYHSn8C6wzKzVcPkyuQ6c1NI1EyhDLq3WHM+zoUQvR5ZA2POOEq4jSMXvGL3GbEavHC97g1keRiwsuLFpUp6gUV6aIUkpZRZm17xJ8Fvq6xN5IG9qjgdWfeEps2th/WP9DjfI66M2C8eNDh97c9+a99x7fdXPLXaASuRvMy4C5yN7fIl7w0tAb+vrJ21vRC7mOTAsEwCG3xwqbPO65LtcU5wGXy+bFMHxlffvhc3AItYb8/1M9eL/1V0R4w0QL1nel4MAHb+4HdyFXQQw5+qFT7uQFmPJXRQlGQG79ADkJwsizZNu1w8rDf3RNRB6XnL8qR86D6XAzBGaB26LR9tDYUFhi5oS5UnGHRO+sRb9u/ybSza9TzEpuj9WJu/xRaS1s0EaLvXhHUS2vHqizHl53q/YohiGDOkfSOSKn6maCtXlkep1vsQBUHkNWg9w339T/5S8t2+cFR88B5MJ2cC8yHdwLrrg9yGiHA7QLLJnuyfG10R54bnTtjIOG3nHIla7DGOcRKEv0nYV3QDfwOvMRrJI4Qlz/hwKfLngHsoMlBNM5dpuF7xIKKu5O7U3tyQCulI6sh3PQyVFZhGexc2GcCU8gBHdiNNrYXfgS6m6ox/hkaH33ovacpMyIaVjNSIY51S2SRMWbiHXIDTbOYc4zdg+CO6KSjYO60UO7p0BA0MJ10JPSlK/b4psh2Xtow4Zdu1JbtqxcuXcvFEjSSa6QnEaTB9znCA9ug3dkfZQ2QGuubr3nA/hjwCUgXwgV/MpqrlJIqPgPv1vql3TKkXeAbvIkh3dLNDU+0hVbAM+LdUXGp0Z3iGrSUgkBggiu5H56HX1/dYpydzWcIriEKbHoXtQ53i/MiXZrhKiEg2ncGkwKJdHZPwmbynio34axYawsW9PPsaQbQHvsb2zlMX7RdVNkYcSJdwamZkSeTMVhlXAghoAo3PIXebB+DrBCNonvLhf/YYxAyRBVazp5SUGj4jW95OuUb6tBbj0aYkuEAoFAKSSWE5JEUE4i2Wp0ep3BpEfioJtpMhvYdj6H+NZbb0E3QFVFucOp1Wi0FlMycKdJ6TgbFMj5Ag5HLSFWEgudb0HvKtbpa+jWChIoT5Go6mU1CvMsLcUrfw0EoRPcmDAmybNcUg5qNBOq6Hw/USwj21h8IQH9hqXwE6RFghoNg0BIE0Alm5t4BuxqbHyjPC8VS9CfIFhqQBw6wM+J4/JRnJSMh/4jIoOjd6xsbCwr9Rg8jJ5E05DKyM6h9balLckYAaaGV3QU3SmsjnKgjHIAuwAn8FbgRN5sMtY4WazBvfvExKkPyXZPCtUo3BbPaHFGTPPaxrAzXApYiszk88AO5FljJR0Y3c3jNhcuWT0ankEhWErSamJqNe3hRdBM5MbHiwA0C7kBOH1l9lzOMtHgcFoCMrMxoHYYzTOcgKNl2Mw7IjQHP6JXIH/hsHi+UW6DGGYW5A4bAU4TII7k1/N25EXRWQc3gYV/O3HCHQyePzbVwFrif9xnNvlRO+RI3zHYDzsGugCHdBvh1eSDfR+wvwkpa7whZXYwxaAKQU83dkMP3fwpHIMp6QjFHX9n1643duzI7dqFyWtb3wvwGej9MjHG9YbLNMVQ+BwSccC4Zg1WKRX5xbYhr8FKZGHNUge4z2Pwbcl7RbIm5P4Ga4jFk9IN838D9tzcBg4gLwJfA6iF7slkXPMMvKjKsWVKSKsnMggQOUmgVkunIQ0nk8mTqV7CihTO1bEb1SAY2ySOsDKEP28EfR6xyHaBC6ZhMM742/1+l45cyid5Spx656y3N9fttu1tqJczrZYUO8nkA20z3W1vQB4JIl+MI0b3nD49VSqhUSpJnIzwALhwTZLiXRfLXdIU3yeYdOrUnJo/a4zUhzg8fXzqtGmzQlNnLT8i8aYvTaGMymS2Ptc8paZSVp4g0PcltpEgcpxAIouWOtNp1xJ5Va1VYVxiM7mIdyZ2Ust3ps4ssl1E19fY9xS8BbaimryYmcE8zVLfHobJXjIuefgWd+LtqIMJMDcG1I8XWpQKneEtoKJCHPD1TJ+2zBOVsIVM98SD7qwatLv8bxcuMozGURNie3UaBhEmIjRXEhiFKQbS+5fcxx/3Kq0WCwtC/WFRyA12Mtk0X/b8eLk/WBdHXl+n1dAxLJQqsZRuZoCbqZiwVXDtHHqhT4Dxfp+GBTiPULEXrL+lQzHAIqRgjVD2ztJWcnIwQYe3eYBZuU8/zYEydDC5vrILhudOKI89X9uBPK166NcSZM0qwMsB0YpCx3Ug+CNkaEh1w+PQV6qhAYnXz1LU6+a13t2Z18/JJW9MhLtuJG+crTxy9uxZLGoR7LsPPghrS4j5o8rG3prpaABlbRgq/sgan2GgNpqRoF1gffaf/8y+n/3hh+z776mXy1WSxQaYQ6RVhnP6UaMMdo8QPF4BIEki5hfUmzQ01AlE/kJVKVXptMquJVYQCuflvXq5ep1GIGd3qVLqCULI2JKcDk1FX8nm5jCzXhCXNHORqRm7TIZqL4jndYI/vsqsqRWQSFkCTJGrK9chmxUKCt5YzDP6x8g7OX5Gq3QGo/Z+p9Z0JoBXB+7H8dlYOEpz8Nbz8ctSLtT3w7t+yWwybqmVjEmwElu5T3KfoK9Tzqv38g+8HjD+4THJpacUyFGwBEDIX6F1yBcAvVadQqjge+yG8vHoWHg0+orG44XPvTl6mtORCHeKcqykP1hBdYII8oxSRCDBQZBMpbx5zF7To57CRViHo1qNufWoiaWQy+DY/5szNrQ+GvXZyKVWFVzCbcz/+GP+ndw//pF7BywQNLAscbcr8Km9ZY+BN396LSNod3KjWj2j2rzIo/JvMFfzMnXyVr8y5HDZfDaTz2VWy5bPqPjtsyAD2FAqmJ5IGI/uynQgYOOMEnq6rJ/9bUXceaxr9L5cmMMmEDJEmGW1dPrsXcqAarpNbagx+e0Gq99Q4zNb7W59+r4F3Zq2cz3JR6BLSXQeDDhnjAadhxTOpneLeQDafqqyAWpIbLOWMpEekqpkqmGGOU6FyeuvhAZr6m7cqHu7/saN+rch1vpfZevjZ7ZrNlxJIpfAvDDNzzHcNiViCWjzrlpL5UFw+S7S9r8kuL5ysAh58K5/Ic9oEoIgu1UMNaQjrdAo9BUJBgs245xE38/RqfaMpjsQ90OyDqG4HI7lXdlWDZwCAnqUThutt3niK/IgqumyanSLxVi9jr7vOM4pxMJZ5rDOonq8junWz/zfItQDmLvoTNgxrr0Rx5Y1JBwJZuT//vf8j/l//Sv/IxTnPbp97cuis4sTdpvLHF4mjrEYoD49cWFhrmquRCOcbgD/Hh9EPiJ4kPfFczVqxXyZUkIJ8uK8MOUfafBGBnkKpJGnoEwuMQpuRF+JcBjZlZbEQ8a4zKqvsWlrzWs8Ijnf3+YzAD0zxU+Is7xz1ggh/Li0meVj1gsXVnkuOHmOS17kOjAjf3L4N23CewaPoboSO8FFTLJbz8f/4s84+/0ZsCj/2Wf5/8t99lnu/yA3ciU9EUzJIuMzne0cQD2BLALt331Xd+3a+NUzajNjvi3cDk4h48EpqDsYaYDz6CsSCCAvG83IHoMBiGTCWPOoUFsgC6cCbfWLjKMSyF/rNjc0FFHFzsBnYQXuyfKwKmkwAPzOUZAHcEQwvTaCxQNMtO2MGb13WDeDa4gnrwjUBcPmxsMGaN05obc2z2uSSauQZ6Fvw3c6w8YdQW/2AV8KsYANIWckcD47LouctTh4RHIDCVVlYpDIFrlnDsOPojJFXeIy+6UT1A+uj5roRYaA4vs8Bl4K94k30qTQ81qN+Ui9rWOP8/Pd5ZzyDJc2ozZEoKkSbPCBbVu0oUEU22cHJ1MBlzwhTGFlbOfzsXDskTFpfQunqqku2tnaCFXK6yQf2OZbCh/Bm2HkCa1+LkbOg9pFO+GHYBluHdwC/1AxhHJxAAKkeKQHWHN4ZCukI4HFb1VJjll9XBGLN26nYePTzcgRsB55DdiQ+8HoOjAa/Z8N/XIDstzkdi9WGuXzrfaNY9Xrjs811jx/PZMsd9JYVH+llLbHF006enLhcdHu8FR4Urg7Oi48wcdPS8P8OE/lEcRNnUs7rDjD6l74Cs7CgWGMtQ5Y9MMoqm/RMTeCW29wBfoTsxhgQ5GwAd5+b3vHYfOoJUZLWkKFeLW1MW8t+63M+96Y/e77xRFT697CQVEmbfE6s5vkTyxj0RNVggalv0qtqRHU2tVf39NpbFA6uNPyjc1NUXVS61zbMnXL2knazlV7egFYB/cmN/BnXI639DrT8SuaFDpnxwMhR/qJ+mybv1K7KNHYWV9hCKmNUaPx/cuXU71thilJbJ/LUMvoEViE2u5Y1xOGD13iM8I3tWZI29pAt8ZAVghrYoE5Q9ICxdX2DEFaGgwaFv8NdIVvVymqY2x3oDA/vlh+Bjz3GkP+iXLSvmWSGRtaJc8LQzIlMyTW6EEhFvv+uWrzbrMBZol4zNkbpT9vRx4Aa6to6UomWIjsgGwRzXixzjRu0j7Z8T8lzKAzTiRQ+HwQgJBHjQZO+SHjTGcoJNc7412N+rDcl6pBnUk/00CToDY1hNxAzmwKpKqMFDoge6tZVV21xkRuRthWWy5pDEMJO8PH9ShtHlnUuGayotjzsQe+BOvLaKhmV+CsRsPjDgpd0QUvsgOUyAFKZ2HkaajV9U/RQBofnyBw8dGXX8588cWLSHiFZH5GsmJ5Ot2e9pnUKd6M50j8Bh2/1s7icSjTdsp7n84iV8BaOkRMV9LAfOR2azQ3Vu8Z331CefZ6Sgu+XxdcDa8IrguNoQXlEUfsdRiZdG2c3SjNyRDhqWiSzK8upzMqvBQmc6HPG7dM9sdAkMQuFydizR592m3yBPVZ2+4VKsz3NaKy/Cj0jyE4N56ySFkZC2fMwI1khaa/4qoU5+MNQVPE1F2pQxzXd3iKEX1/49vIz7AM+fntQgCId+xI7t79xx073tw9pzY/9SR70e/T1w+J/m/hti654XNQJWfVs9gQE5mp9wmRL/m85VD9lFhsyocfTjk2Fbve6/ZIa3OWGHpMMmKtQaANBD16jl4Z7OUGjVqJHJWjGvSk34M+BRn3AUrIS8MYpgYAlrBIH2koxFLRmoaeQ5oaoYbG1wGtPJQSOJ1Cq1tgfv6c/thDWRiCm9Gb5qFIpFoWS2tVEcsh6Awih4yFN+v8MYUCp4ly2R6YerQuH193oEe3VA/rluvr3NCrUhlmDRNYQoMPsyJ5fbvgUzhKlLQsMwQl6tZskJr/ghE1OP7i6OFK5P00uJxFYnxvaHZoRbzd767JaFhfAQcvmFZDYnIV2ealiEVUl1G2cbF10TI7AcrDULWtnMPj8WQ8YgUEnUUEkK3wxkPRlRvush46dLpNkdqweE8m88y9t43xtzmVMiytZg6cbL8rH8lsOrwsvAl+qSMM/VnIq8DsfbrQFi0yMe6Bz8ASnJ2go9g/1Q/dirG0DjlZbLxiDdNjv1ixEZBY/QtWel4X6GIGxMxUJOSJKcnbdoDe3vSqVWDrdqJiLB+sQL7KgDPZA6QKstWFPbPDLF87wzF7sROGs+gz0Gp4CiZTLiRU8FQTDU3rW23xeb3tOV5NW+4ofDjXVsPLufRr9dB4dD6shTfS48wqHCXL6js/bm86mFl/dIVtD6RfbqjPEd5Q8rG3mAKXr4i/eTdcBztLKCouvHN7sMe2GIYb0mNLLjXGYYutwdxpDyZ5iMNwreA6eo3LIXTLxeVf5X6kuGpiDgfHwLe82JFh8MEsmxX5rSkMMlYrsvTLL0HNV1/lvoRB7VeQuvAvk4FLIuUIcCVXmHr22cD0mDHUvaDjfSXLf2S/VK4MxhxznT5rGPlo/vz5yPs9MrO6p6cHtXu5qIV/HjaWaVCLN4vz884tW1S2DKvCcP7XfuGBNg1eEWRacQvcIww8xtMPGgU4/QAMw3HEcNbwgW5icDk/m6bUyFgyEb09PJosl0XksmqjPTJLmWRwHjVYavgVpDlgIwXm1NiVXItEUAHBRHAnRKpOpJDXdfo9qYmtu9vbobmPx196aRaHHeCbqsIEWlv8nnsQSivY0w7dM7/wpkxKIRJCBJjFW/bEE3Vzg5JQ1/Kp71tsobub6Frd94paj14WuqgzsAhwBJtQPtvD4okj3a6/+m2zkL9hE/hE7LnnYiuDZm7NRk8lxzMVmhxfaZ1rsHLmzp1bVlZRJu47Cj8JW9FZxbr5syXe47F4fvl/mdd+wP4h2JWD0JXOAWRKTWl64cEpPBKcQFGqlVy1iN7ibydKpFGptEphCY4Xxyv5D4GPyOz3zlRs9O/dGz94cLlM4BMmqAWORLMj9Lf2Q2MQZcuOlhZ/C7izBdo7ufAHqZRGJIYJMJW79fjxpjlxXrCrd84bGntoVwNd5Lh5XRblVifKCW+AdQ/C9yMbrld21PK9l1zQn2vsk8b8hF2xRYsWIR8uqrGw0U+wGEkN6medxFkLsEijYHiHGQ4pgmE0DOUgP3lzJzjOpOepAuQOaG1hY+l+MQttziEU8ANCgR5B/XYDVd50ILE/gUhAI/KIP7FjB95bdgKvxySj+k7Rz7JY/DtYhgNL34P+shkX9jXgClq0LvVYHmgF5ci/Gn/6qRGZ9bDoVSXfzq7e8S7kNc4yWFTzNAfqESH4oh5k4IJ9Y/5ugcBL57PA4jq8BvQI/BgsL2OiFoahxNUylJ6Y2T8KFo885C8z4Mf8M7eoRLetD87fFMoD+v7Cx7ypKqdqOt8qcI0jGe2Mqu1vKYJTPt+75dMVvvHP9j26ErqD/QXya3DNsEppky/VIL0NNe1Eo4ch5oNUHbIVm28bqoM6YR46Lhqu8VFDHyMA0vySAAigXwMnYyhbqApmpgu/sxoZWabJ+pqynRfmjlKB7zKF+347hqdrAUKGjV69Yjy8GL65S5xdcPEsyMLI05eeXd8Ab1TM1fstC1Q3f4T58M0bEA25ra1OmQEcrpsq4IB8EWHscfgYzERXx4L6loPcf1jsZ6jCRrXCsGAlll/EBkoaHOglyRhekD1aCbjg98ihaoXOL5H4Lah1QmggUElsR02k1hnzuLlgCrIBOfX6Uo5kvIzFtbMqt8JM6RKNX79MA9B3flTLq2ECgcASybNkYT4oEDMJRCKB6/GAOV9dQronNHJSfJrQz2SzwHx0di19B+HLMBvX8GbUb0oM7jFPP4pdP4UuztEND11xzyAvByZDB5l0K6VNKo9qDP8lf9prsdJAG1s2rmKOt+bxnjMCQQ2nauufVkOUh+avOqc/2zM2bgRvAf+syfcjAX9dmwcy2OeoLPI5Gop7ntkrdfrMk05L2CCtt24uPLKexfOxOajlnUYmTkJ+io7rDiZrW7p2JZNbptb7wIJl2aYebNeY+u6DH8ZXpogsXTvImAGKZwejLMe9CtaIFl+4dJ7wR/xOlJH4RQ1cMAtIkE/rkC8B/yOI9aVfEWCEaWE5ci8nxgmxYrxVc5X7eFy7aOVzUI19utIgn61BXskiT4BsFizOZpEvHStqBaZ1nh/Vt9uUjjvUhZtd8RVMgY+nAYvy6HglfRdQLWbA2aHMZUEsVqXpNy506FB1PCy7zy2W2Q7lfR48iqShK9MP5Fl8RA7GlcTkCn0hg9xQjvwGRIkZ4gfvVcjFVFalhFpNlDOzQiO3jlPo4YyWecRjeGytaAyVJbDRqGueByfg0Ovx8kBmCTAt6LYsbHWEOzPI67nnCFdzr3wSFKO2pA38RZRl2+gZ/mrtQplFNFeNtPqlkyhMuYuu4oEJdcgCop6uq8iSKaA8nf4Puxr1ZMR9Z+H78FpzC951918xnYeRTg7QQAxdpv6TB9937+bN/FAwwE+rlVXIbtCDLAGUP/+5/rPPgLCQZDVJvOIWtr+du4IptMvWvPhGP4Lz0RnJ1y01XJiQJ0AUseTx5IzEmgzquGTWNOiWyE3SHlXh89GjZtOkbrESLKpDvh6C3GzBMTt0OA5ooMRSMlhoMZx4odSEjS0cpi9YQ/0yfOFAqZSo5PvD55DfShvkr+g10ey1u83j1tZc4ynYbHaFtE78LmCKGTmysRyJtplD9rxNyXFx+SQpxUGjrHwW2jCu1blaVZPatfqy9alvxkNHE/YZcrYnqbz9lQ6/e5KbDZGTxKoK6QRLokEpqJoqmLXaaKqZgaTTrFo2nyil+1giBuisQ1aCsi2tmqmqeG7x3OZI4+/vQW1HG6ojLsAsnFNWUmIpGjhhRLyx1VmqfMYccJ4KNQmGyTt0zYboyM85zWqXqo0LiUirC2v2c9dsZT8MeZGrrKsvc99DyDOkrG4xU2RnVS17+uMceKMeeRYrb4CMljlqi3KmTvGbZHJtdEEisSC6FnlhTILRzKVIPGxUHSxLFS6DJuSSP7Z7d7EG/m5U3inQ0WLZ05GsoP19ehjGSjGWRe7HKnTiMP2/ZAUtEpINX0P0L1DI9hopjS51GucSzO15R6ZeA83ZTA8I/Y0i3xZZhhmleUSbb2NKmeWVdAkbddEKC1mjJH5xCwt8i5wEXUiOLZtEpEqczOoVV+eEgzIxloHXO/8zddPEmqC5fm4nqFeNUWqnOi3GFXqVvNuAPPqRhI79EIWn9YOHtAvkBslcReszh9oEzYQqmZslZIKOHLIcr1p+ALUq5LhstJXyyLfg1ikGFIYcuOHr999aW7cAVWE9xqzz44/pn3/+rLCakRf5BQ2s2laRMC2kicxUytoXtoM/sWscUo5WKiQjj4E8dkO8SCAQ8QUDY6DRgaCPoV8i10kXqQrf1Se5IX61xE0V0UFPunANXEHOqzQMAuyD4QomW3wHCIVCgVAI82osffvgBTAHRza24+g5mcGd6VEMMV1L48d0HG9khy+6olgfRHE9Neg3MSrk95iNkoCwmR2CxOg+8PKDFikyh6JSZQ3qqgnbly+PrV69C6lUmaUKDscqmnEeEAqF6Nq1UK1uoUIvnqfaWLCaLGwCIUWAeTJoPfL+llNrUrLM8gN3hyKT/G1Qi39S5LjbrlTxBU6pErRmkc33/RRci+3bmr6d8BbYXsZGbTIcRZo1LG7vLLqkLNwtgznsAXOtJBcvK+Tezv3ODIMDJrljT9UjpoYD3iwIueM9ud9eVp8/72trfzutSbzWBX4UC2pD50YLJIpkJoEsBDnkMUiYjdd2ID8uGLdpfm3GPGZmS8+/FHOsTa4FWmxsjL7d6I6Xo/LPVqzlH8xHlzq5isU4jKGZaTAw9zidNuZZlxpH4Mv27c2jjzjOdmjtNJHCk/x1AiRmBetFTOBrpQWdzQhBO2F87dhxUvC8zlR9hVxt6RM6DPp4yOKfNnve7OD0ReEd7XaL7zvwJcKG7Mj19f8kTa1NbXqhuQfSIm90rl6cdoZmz8gCB7I1dWo+c9JR5JLOpa0N4Mgk6r5j8HG4GrXtNXg3eBlrYKB4HohAJnJGcrXyOKyBOueBYv3Pec6atNPB2Q3uvY+6HendAF1B/vCXHLIr+y7yVyDIw0Ryas8d0vXrfWQIhLNPRST+p+rA//f2HfBxFNfDN7tXVK533Z2uV52u6ZqkO11vala1ZEuyZVsuci+yjXvFxpZxwRjbgI2NKcaAKcaF3kkgQAgltED4U5JAaCGAA8Ha+2b37qSTLCf5/vl+3652tbc7OzvvzZs37828ee+ha+4fbNN1rLtpPbCiMk6SKSX3RWZjv//LF8AyOzIF7cJ+SE1ZXK+PqvwTa3nexyQtqqi2Q0YiosoeRg9C3obLyZpsNI38lcgckUCXqQgNmod9+Dw3oYse/OSB5N+TO1LYuaejIBENans6rBPalSD6979/q+wXevkzFMia5HNYRY0fvAoeRO6QYSgSG3oaPIG90L52ecxXNXteAviGfg3It0kXyrzyJaX4zAGXWCmtIDnx+Shd1scuPs6ebX3DPnbHsaCCPJeHIzlvSt+Ts8fNm31G9uw8SN+zrWNOx0CrpFgtjegM/AQoYJUrX3/qlluS+/bdc9PevY5JTR9j34JO7FKxTM6QlDBMWkoREkMLaQWuoJHHN1rsAqQgVUChyCPV1slVwsZF23rRxoArJgQ9sR3xtcjq+I7Y4fhRJoUMvrsngb30mLIU956Lcrl6u7jUJxbLKQhCFrkrAJsY1z4Oe8lSkoPwlYGP6ef5Fx7jXnh80NGMzECjCoYHKLx4+yFCf8FUyC2rDnNXbuq5ZtVmA9cW1erYIAIoTJPytUdvvDGxYcPGBWvWOFNrtsaChdeAYzQKInK67ZJKuZyB0LYzwxPADOwImJl87z1KQYpGoSTaJswV1i/d3Eeu83nqxaAvtCu8Br0qvCt0OHGShVLAo741seBmP7vcDAkohseBka1s2dUI+2NN6FZiNcAxCLGS4ANLYV1nQ3uK+IT4KsrOsmRqkVj4QqwwG1YicjoRyLKCPFLJUAr/X6ML/IpVfDcZxCkvvlDMNuvd0ko1pVDA5TJoVB+FTjcp5E4RqOkyL68uZcxv5YsbS9hsMJUV4Ja5zB+tu4XAZNvCOinPUaPScmsQhkn14tkDB2Lbth3YPDDgbrz2RZZQADbO9KHJiaHds+uW8ptWucRSv0viVOktFWXOBFI7wdFXv+ZF7O2GMD8iZHDBD/wku8zsGQriGCarEzUTl/LrFkO6MviDEyWgI7orsh5dE9kVvS52Jxcl4zxIlH4ePYr8AGWrrL2lTkTLyvMijpczEjTG4/XivTaHmMXi4PIz4UDxYaTZ8FkVS2sId+4AovqrriqbMB+sw3zgMWwPCA99um8feOcXtYJB1dFiKBXMQrA7GOAocGCv3RB5jMpadk8CVaZuwO4Dv9yPXXr2WchbpFALP4P8FXIWX65PzQQLu7xEFHwGDa9JD21EXlDlB3YVojmXL7hNxB1o6POJ7GCoaQMQdSxb1lOCcBwTl7eVxA8wKY3qGq5QpObTwQ0vSbSaZolZ2KnXTJ2O/ePXBw6A32H/AIUqCUNHDxaAWSh2kg6O4F57bwxfYFNbfM7+3X3Yw8k4omFJC+jseDGbi3yOdXf6hDGprSRVYoog6oGBpXcULctEJrkbPYm6SWLCU3Nl1r/sFefJRePA7kVxmDImVBnhVoNPvqEn5Yd7pu7X7WgPWJRak3eqNMETgQLfpE5sIzj368KawKQdQNA4f/6SGYcOgYkN3s/pjkgErIp+//33YHaoMpzwhu2VnoRe66ncEWGayyKrW6qwE4pSWbwATEWwexngehzsg+EzPKT7hCI4gztpaCuYjd1UGbzvvsz82kn0FGrJ+gnLxKAYtZydQkx5O7O2cnhPbcjZQeN+mk8Fpstqkwl5t62c9Q22SAlm/8/QB1sekXPbipXAE7Y/PsoJ7pqW5MN2VwmK4rqUQjX/wKza+vUR8LingiUNYMs8/h1tbQfaD+Bu20jh9I3oIaJkJN1wDBOV2zNmxWR2uhY9hO1twuaBg9g71clXvyljTeAqwMuYIOZ5uQmIsC9uSj3ySOq6ZMv+5AybyFGb3N9yO/l48jrYA5VCfeVJ1AHh7yFkftzgI2sZN/ItYoFBjqt4CZslfCR/rEuFbPeT3/uMxGQCj8pnJ6bN4ET3nTAapgyIimNM9v3PK8onJhYvFswC79bu1FQtqPVtNOoshyPFcgVLVsq0KKmF5BSNXuCvKRMKyp1Ood7gaLjG1KDd37qDyn3zRTa9gSrY2jBtQ+0kJzPsr5171b3I3XWrUO4jsTtb1i9EH9O0KWPqqdotMlkx3huxSowJabtNqcTVAb7LCY7plf6aMz1TL/iI2B9HiHWrDJIHX4sHsnjGF71QaegVcDMaOR6vgJJn8UQYpOOsGRyfXpHkSEBlW6ge+1HnQYMdiSMeZuueUyZj/zo2M17Aor7ycZl2emLjxolh8JGrdbO6dG1fxeAaBMQAYO8FD518rSjYmHxN+lDvNOxnBuvVZ8TUeIHoYGLKtmR1vFhXJUzu7rgbuSu+i8WQvxQO3NnbfWuDb+Z71/PbkXa+oGjz+xBCRfo29HYoLeNWMAvweau8niezTDkrPoxa3jw6eJTTYFAgqmEHuxAD4+Al41J6mGQgWtDbsS8ZkqgtrKmzsVksEZPBLKRQIgiVyrTp1G5JMaO6y7UgWsYe+tsX588n77//A4SWKkSAZJ6iVW4pbVJj5wSLS1N3ziroeOIJben83Sx+XPJP7M9yxdzUzTeL213gm+PLpg1Ku3cH7GqlRGOVeEtFBnnCY3GLNaH66tYJh14Id9fMQHtrul2vou/qFaZWoYVfWzb0MFqEDl7NQsOAVVfj9QSlFo43WOmsRRPBGFJAlRN4O4feAyVIPIof5H663DTY2Mh1PFxPzg1BZWImaLLiHDHk5OTIEdgZlzc062kn7qTWIxTAJ7MoZFVtvEwStBtZKP9XBea2hkFBp7K6tLME7F6/ldd/fWDl5nluid3i7HQtuGDr6u9XbAst2rO8YVqI3FpXj6XrvdUSCtpKRhkqPXBsvG1dErytX6SySPu1Q7cVNFIQltOrcpldTVGgjmLXlBuhaEZ4nTmPnkONhMcqfz5UGeYyYrw3GqKs1JEPkGXK3ArqZ38GLQDQsIsow39B7zEcDCgGZixUtkEOOkUCNuzawrmrPbxm/VyPaYJ7mmXBWVv34umyzYEV27trK/eTf1WbcFc85q6pPFGdXJsAf3DO0lQo5+pg+RsosOE6PLbmyskuIEpihyzlbFh+XCM5jz4AZaqMF9VAxgY5Q3J5CvhwxOfcaPiI7IT3VDkYkKexm8Gs1K5d4lgqLuuymBhYUDBJ6VH0CFeppouqBVPUYPLCRczpq9dMT3XXagdtN2x9WR5sTy5CzLX3oqdqsYd81RIUbSQjLJUO6I1r1BblSl2rdovJZdmux+yQ65NRgdO+IbEB0OqwB+wOPooSswoPoQ+hxbB/xaVDvBZGgpCoMiriZUQ1pvDAaytjDHw6Q9j5Si94/HTjcwjfal0hmKRxqyeLwIKd2zl3NYZWbp7rucq9e8F5W9fiadMDkwcWf0nTSmvFatpNtfjCna5lvWHwpWGB2q6aox46RaCd7fJsrbwOsJPYTVYzGyFiNj2CXoBaID6yXzsyfoAOlxov9DhuEfGBP0oe5jMiUg75P/Kb1W5Zp1BgdghWYQsY9/8E9pRNWuYst6/u3V2xfeb0gME3v16NPUGuDoJ525azN3WXNW9YMsXDEbiUzl1XPWVvmT29FbHo5motsvlqjO5btnvWS+QSXlJNXxpfNXt2IBJaPrWxKja10+oo627v3nJ2eoiWoiBkhqOaX1KpqNkDGEnsmMPCRhBiNOxRSFm87Ci5Nw/O7OJrTdbGLGcWyBuvWoQXBZM1VYqpQvnc2wLYT4jtTbG4YfYgWOna6HJ6NtqVV2/hnJwwXDFn7V1Le2VIqWmVzi5fqcV2T3pjU12dsxwrABtuWA0i9mvCweR1Fqy+oG5M1ZRziPagTp9B70bFBJey4bWjyy7BGWPXl7Xty6MqIvafZgSI0bUD2qrKqDuvXbQoea5206bjx2sfIYst5tuFkxReebfwU3D+3N3LduQgkVTqcrAoG6MtwWTNYOI25NbbkROJXyd/+qm6KV4BLppWqazyAe1dVv6vh16nZcFRBPQQoMIkdquVaODEGsqzsG0ghJ2fEx/7HxmvEqhEmSF8fA4mY2BATCVpiOHK3KjDlUD6WFEn98gniuvBVxi/ez/S/RJHohNwC1Ay1BLJPIO20WFaBsiKqN9d5StBP9sNmVdHOA8+gnkhMtdslbl0keFg4ot4/DM5F0EKhBKVnqewG0wcBCmv+r5s0kCH1VVW19uALc01qQygeM1lOBlK0qcfhHCW5zwH6rJj++NIe8RQv2AkHua4/ECINGIfAs3HBu/Vt8q4SaYEtGDXu/R76996CxRjP2JtvA5FlXwyH2xdu4dzV0t4NAUaNseujsZWx2IuVlkwtiZyNQpvxDaDv5k3aszqtfqhM7Q8AuRBhpytL9wP5ln0LOTI+PyvgtAVSLpcrJHM7BI1p8PmRvrB+DWUm7gA9Ccnf/b5BIBg2ATD/CbwOjcqtpcEBUN3RFrtfRVg4/7tnJOd+TVj7146ta/6mjKXdav3zKnnUo+Sz6cwJuiP72wAP5Q0iEyiSMnK7gnWKZGhowWjSA+CcqPVCtvSE57dTn/weieEiAUhOknIhPjamUw8EIEq52kcAmUYjj2rEoymtpEOEp+oQhOY/KiY1cwWfIEte48/UeOSd0nAJ9gTHxyCEPREchD0Whect3ct7t2HO6MCU35BeryuIqvzp7nP6hfqrLKFhoaBgaF/5Bd8UlW2EjjIHctxjU0Cy3wv7FFo2agzlaTESMvhZdVOlSAzH5yLNTR+NaB59m9awx9ltSq3vF3UIeMzwLPY1nuZy30yJZiHL9PpvrwiIDFBUX9WylTbtkqrs2BpA2KzTdFYZLN0Qy8EizlMZAa266eKiJJLK0C0kyeHJk8e+tNlVUIABrpF/upYRbCiubTG8JAoMx75JJReGBBKRSYiCG+kJtyqvJWEhAEchBiMGmPKgIhrLnjt/E04RVWhmi4GPOxnQFu0nDEAgjOKGg4DDvbt05gXTN4yhbli7twVc1Z6DL3W3aueKV/Y17sHuLBXkFLjVSq7Yqnmz8tjqwrJQVTKDjKYG2LLsW8AF7uOnKBQyG6feUJkNSiCvb7PTSbftoNEyJQX0AdRDZS8ooRPzfFtaMbjcFbCAik3UKnT/6t2BN46MrRJKEmpbEXJAsaC5NtvA/AMW1ou5BUg5AhCpvAM5ja1mtkjqa2zR2uE2E/imMIbCIHrYX2OZnn27iW9YEXkQLiqxL87ybA6biBfFz0QeUTORxAaT2SXCMq0Bg2DjHKNxpd4tVMnOqvKAg3Rl8qnqU2R6UPHChIjNbsHCJPYAauFg8sUsvQT6ONEbxskdeZR6rhr3rNr3XNEabhsrTwlX0gdxsPrvAaFW9Yq4r68nl6w8piscZ+Hw1s6Q9F4KPBXxPWZrtormzWhfGLfzTFXfGFBiT9oF3nMBiYtum82aL8dknZ/bNXGuZ7KKvc1GcpGDMalpjLFUiPW0nu1ntuXCqo6bApxfVlIPqkiGlWWJ2sT3ZZpqa0N1V1zXKlIWFZAjVPIHLOl0hKZ6VxIYIPl9ISrK68ZJnO89cohXZxHJcR8t4PwB9md8ePuJOAVXDYXnBn0G4l5IlJBdF2p49ON9dvNnHOzJd73ujHgPPTLL1y7zVLilQip//zniTJXB6dJ7pO2CPaCOev80a3XwT6wKzJCEGdsPUunybCzhrZSl7S9HBzXzBY7xDPUSIlna+q6uSGNtmZO6IJax8UXdCKFfNHh0BxLaWmtcbnGKBvQ2yZ1zRgaHN3cGSnsCNHcl6t7rRrrDOM78n6117CoFNKGGOLlHMHVMrF1MpZXw9Siy/jEERFGWKPs9PAh/owUSsutb78CJ0Cz8YHeZ9fLKqWNPPBbbBlCXptCKC9aAkaBQySgHYveHHs3FNYGGqum3fzHY8ciazcyN65ZN3HelnJzq337kofVq+d03n5z9BgiNa3XaxVrDfMD/sllCA2bXWGkkvHABAKRYteug+CiTVWhdCg/bW1txTgUSBrkmqB9QmQtYNRh9warKGQwtQVuhF+o01CuUw/H84ric+k52W7EZh9Xe3A6QPM8ouKWvlciBV6WAhS1m8rOvpYmAVI9IGOX3nyzvm33TmZMGhAnuMC4c+e7u60r94wW7x6y9SyZJpu0JWIoW2a6WjfL+2VrdAraFW39Env78/428K5plVarXKmfPDAwgK2+XMCzWHDvLvqemqB5ugTWqBBygJOonLBI8RIeo/BI4iTgJgz3c9b7omzkn5wAO6za5WI3ZiJ/cDT4GmkdZJoeLzqig+f3avgEwSt7O4qKK67mMsI0JmONkz9p/44d4U3YBnG90q2sk/ZJLD6X+0/3kIsefXX/YuCgFwZYtHv3neCuvV23eeUsb9Bn3bn0rH3ynAXJyZMBa32oty4UVBRzbKbQqdD66K23RkGpuV9jUE8rw37XHlckHpnyEfatvRL7GLy0e3dH+8RJLUPXFsYpCL2iOlrtHQSCOHaDo5yOgqo7oNxRlr4RvRE1QKnDRtgQ1BBjk4T5QAYhOU9BFJEcyXMz6YK6CDGXJaAQCOBl50PAKyzxVgzZy+A2vkTjk5NoScG9wEiXqiV8sy4m82mUPnvPyRRwD7WKaP0iVg92EMxLfvABMqd+Viw2tTUmSxUxqZPksefYuqp2l7O6lFKYpJKlmsRyP6Bc+hmtj1Wtd/a0D80AE8NvZMbqb0IPQVlQNby+KDeQCPtiWn6s9+G1RGAksvUoUHKuN5CKmsjVj5QF3sLuDnPLTsz+00PXXRdfu9Y0qRrUecpKfS4H32dRmyubjiZB2VDrW2+9hfxm88Sg1YmtAGVmetW0acF1gWXo4sC6OTuwJxsW+L2BUgolQSbrKxxzo0Bw6Tu0rQ4rnn1i/vyMNHsz7KEpkD5ZhB5YORLJCx0TZ4oyapAhzwV0rnmiPXuw1LGi28CZPR+pJohiwnrdY2y3JCz2MbHfshOScEmK80nixQHzN4N1secGjGuejWAPgoE6sAx5WqBEkqicjz1s3OaQO7ZWmMr6dGrVTNUk0xqNTrlKd6Zxuzm0+BD2DAjW76yI2jfXJWegvUnCRvA59CTyfX78QV3eUmxiKSauTIwJXYqwwOFLO8ANeI7Yb5FT2FsgjC3/Eng+/hj7zZf1H29dH42ujy8Gj2OxxXFwZu3atY/BY23GvuxR9DTKzIvVRsSn5gwvKRr59FgxjTI2Nu5prA/osfcBbi52zaVT4BrsEZDE/gB02Exw5L4byEfBnduKuj4HRzHJhwjyAfb+h7UfII4E9rtYddLvT1bHgD1R3UhDQii3KEylN1+Kws2Ln3BLXguUku9EkSv5Q8lGTcfFenRUwYkFFSrdGJQdQ24Ymo/UYQjAhmLo6skQdVsvPQiuxp4GIexd5CAEI4it/hDo/vAH7A8fpv6AIn8ZLC+3WCzPuN3Y/Cq3u8pd/fe/V7/scDimwcORWdHyIvoYqoK6B67RO3K+JDKjy9pRsT+ykUpUOf9WOXpE2IkPdhrX/CUReefacmC8BhyASsXGS+fBZuwsaPgQAe+Dxp+hWFQl6FRgt/LbSh2yDiGqmnKzNWE/3tl+Yyi8+uGhd7+JRr+Jr04kVn9fMkdr1swvJev6ZVbJbDW+vlKaPgfllfLs2hMpYRddT6y/yZsZ0uGLkeCREzt4hGQrynE0PDIXAQQBmDPTiHS4HINmfOdDFON5IVaLym9pFNVzpJBTnUsknotGkVL5VEm5aKpqyuOgen55qft3l379OtfONfWD6se7lyuA+IZo7e/2K1dMguS04+pE4k6Bny1cl1ot4Ps5yPqUQefeHmCUVSTuRrF7QABgjz0g7Cz1KieJsSeTIZXZFw5LKjnaUNJapo1N2BaeaYjoDIX+QDBN4idFgmuu4fGSEhJCYqSPw17aBakIj3qcv8guw+doIyEQiGiLRDemc2ZG+Ah7ZeZxJmPQALsuPnvv3m6m2OuZI0uwlJ9gP0sswHTtnXeCxz7+uOGVVxqUXfXUpIDHiTKEvBcTm6t5CnPgsU6eIx63h2ObE3+tx0Tgi3rQguJURCdW+hphuTL26riFTIYPZ3vSPLvgEVkSX4lOBOTgDLthzE1WEqJ3buX29xzh6ZcV2h9X7NixhiGfy+WJDTzm6tUJGep1dvNRsmX3rWX1x5nCew3FagEDPPRHqbmxyZSaWKsiGjI80NKAN+L3RjZHXm9JcIP0Yp6Py2O9EdnsNpAtgQdaL/02nLqwH3uqsbagkUuLF3PYyJ+x9vagtd4TdjcjxStWhAcy85Sn0BOoFbaUJsInfzfhAwpX/cYu3Bj2Pg87npxnIUoWFYR103Cc97yoFfgpx6FoOQ51Avvx9yy9wSXyCDjUffHBxO8++CB+qNRTwatkOBYNxVev7uNyJphsWh4D6empEVZ5W4VhjmDnKa3iY4AOgt59rw3G9yEzp2FMvZ5LocYoUE4WB8+ceQrpnhbdQFlt9Ji4Po7p51XxV3zhAkeJsqaYz307vqpSbkjc0SJ1OuMxW6xzLtwi8+dnei1G+mH0LKzvIsL6sIk0J2sTlYEDZCG7wuQefuSkKlSUC3Odo4th5z0j8nO+QHlAbfUu0EWFwlvAtGefPSLXdC1i8gMMzicXlcrJocHBO+/EHi5y8iv57uL7BD16qqhAzSpauDD0+46BAaSyJ8YOTmwP1U8yLzStat4vLfO5osicaFR771XFEXts6PGt0a3BhsVxSzPd44vPad2DXBuGtxCqaaNerFmrw8zBuITCL/DQBdzXEpsjkc2Jp23kKJlMtoVW1qwHzCR2j80qQFFIK/z0XogjE9Sx7MQo1QTC4lE0psGOrvxsY8kGOMSnsXljXAGieU4deVlf5xNE+8VsPYe+bFlA4nFNEUZ5JfvPSo1/Xbpx4+0vxl6KYWdUkOtWlLSLQa+4XeYsbRM+hKCufbs1GzfZyOjc0LYK66TDmyK9PGYlh89+KbauUmdO3ZVkVbljFTXxdbGnk2AnUCLYJ9hV+DpxcEo7r9RaMlu1Qt8vLpfM1mL7au19G/or6gxtc9v1Tdgv2l57clY3PgJRCDnDBdhiDESEhozdAvXfo+BfW4ZeZho6MjfsxjtS0MZkzyqhiYv13GLIJ0TVji5eiqM+/ZpCdXHxpk3I2+QiqtkuYzBlFeaZaHlnc3l9vRaZuY5VKa4UhVietbIoJ8JwS1atLuQKmDQaUyFAC2ZjT4LIhqbCOI/CK/SzeezX4huiWm3j6SjDnYz5nbEN8edq260KET7vq3Nemr2xy+m3pObitqJTlCppr8JoXGVQKXBj0T/xuFSYjEwXeRxg1zOQWtjp29HbUT3B2fGVPjMIv06jPVs5M8Et8pST7PP80DejR6Dy1gnijTHnVBsqZtlQFiB/7e7oFoiIlwwOLl4cPurzHT116tlnwwcPrlixBFut0VUZo9wwS7AP/NbVXxxtrwlMWF6uDDkTBn2JmyuUF6xcPv++pYsL5OLUnkBPLxFpchqrMCEokRbqmcz+fscrPVOngkebq1orJ6Mdg1WDjdUN1Z2d8NT49YS4JnZzqshTGRzaT/aTUbKzsqbd3Nxav4Q/wdO9ouatQPDNUMe26nkFKHKwdWcz1p+g2VkcUYG/WMh+O7AlAP9ex+3eqtIH0HvQUkKuIQHIO3KmMVTaKFNa2NSg+JVtXojE2HdgmWvlsSXWm36icAflVQKtXMfj3n57IzJ/eu+fZ+r6PpkJeiev7TXWVSy/YR52uncC1UsX0RiCtiIhE9TVgwEU21cPOmoWaVOKhWG8DSxMn0TnoJrsWOnwShXR6GiM+AqaexR9EmdJr+oH8JPY4+sUdxpUdGwihtWhmpI+ZUTXL2UNtXtcfEpBExUpVmiR2iEh8gx5KAr74EXpY2g/5Df4V1yEHnGZ3S3xHcoobwWjVAgn0EARQVgyQ12hmiVRgiGxP2CV+vSwEM1g36Cw2lctTWiVxf6dM7yLdjux76AyMDj0VEMD0qaZKXVJeuXNQ02VlSUUciMZZaj1SMvn2Dm3W4TiIdMYchWgzTwQCET3TopvQTcO3Yf8BueTCyDlzxvGjoKQka+EIxSWDw/FCzLxi++FUplD3KP8E1JQ4g85S4IGNR2L31NfvwYsxfYC82efoRpxryKknSlhDDV73GIqpR4WDOKtdYiDPI82Y2rA3b49SfiqmA614TuhJFwMKYaYVQBX9vGQaZG6MU40iQCVzhzaEbtSGRPIfa4uKXhqntjndUuiahX9j39MYvJwvchWpueViUuKWxNLYj+DCnqNKCjyM1DhmpahVkRislmTHy16JYUVlFlFZNw3HqNUCt5NPYk+1vLnNfO8PgmNmqCS2RpNy+rvL32Ptg8967zFIjXfZIO9c0/6KHo/8hWBTwvhaZXkHVZ3M1E0BbSMGoxrIZQxoKlys/I5C5MfjQKLRq401Q9GAKe+XFFSsZ2Ien4JEqnTLvEppIV/RWw7tN38KHeS9tnSCYZwWZMoQa0jo2abtct3EaruTamvErPcHp8U2VP3FTbfWM4nk+vJCF1cAq6qO179dI029FxVYduDcVXydC2sjZkQhntRJxEVqpKIdTbKGMw74k+NsCsZpdLngMxYg4ERdpkfzBrdfbZr3j2q6/rdNlOZYzAUKmEDSaizZ//QE80UulRG12r8IptCJCyVdWyOAAoQN1X+o8ABKl/87LPEF9ao4djvf594EfS5Kvyuap3XUGPVlK8dVNpE/umBch2gfFfMd7WGzRVySmGERinROBpdZf/ExzDedqeKY9jZzZGDB/2zwNTNuF8SXIaeCnvKc8iPJHE2wjoJ50u0DGyjQdONcLJxpOZhsXkqKG5myRSaCgiHUojDsQ3lWaetbyudeEexe7lUCSufAc6+rVB3R83NbbrZM7B3gRE/JqGNsR9KXV3RGhetIEqhionSD136R1vQMW/3bOxCY1RqpzOLw7ig/DnW1e3xhJ1Je1kU0Q4MhJeRiPo7gD6JCklGqKsl8frTjT+e7MlqYnpDVl8BWVDHEKp3TOQWdNl7ogq7XmSVSYtee22X0WN/oqeh/HCPfdbV5vhM0LLzvaFtWqFFJaqvXRUDaL1BLbT81TDFUmXvUYJy9VyZRzpT88u3RhOXApkTWiQU/b5uhc9gqNl0pumWULhjV+3KqbEV2D+o+MiNq3fB95d+QickPw/P81b5JSsSW62O8g0BVL/Panfu1UMe3we52BIo5zBJuuw41LBeCgECI4DQ8uADOUv2nC0GMRuTQQ5S5q+r9PfLm/gloGB59dShbkBr1KlFNiPkG2pJXcNG8PWHSey+SNkyq1DbpbzhBtC6f/9BZNuMdlvwtgnF9vLg/ZqdQxq0Ifmlf1Gly1dKoSbJZI29a+nPl35GeENf+HwItcjAD3PUBRvDBw6Et+MazhTY7s6iWpIa1lyE1EOaRsRVyMVZyxPU0NHLkNGMzXCWFWZH1Zw5+qVSRhkTj4jzaG7UzSXTWKa7521m02NM+kc/scRfoUyD0SCwSjlngjvMJq/ekjZxywT8Io0yuTD4dYwhEgmM4G/NS3iJ9np1RbzFYQ05t9ddWx6wGisbz5w5A+4pK7Mv2hKpqOJ4tBGdA1uo0XDI5CAZESuNdyDoyrqS5JKhS7QwFS0US5IzKgCAjLQ5elFa3t5gdQqn0upQAFgVruqAYxfwxLABs6EIRcHxxh0NDbC3aoeY2o58SxKSJCQ5xJcT4gtff0YbM76Y6RVEGReIAnwKAeWMWQmjy0pzWRnOkJs3iUdSQqtRISxTleg10ZWB77RIKSYAR7C7gAD7cgBc4lnMZp5dI8C2gSmbaq4+JnIwXTLTlJ9YlqLyojIOcvrLNQsrQzIymkBQrdO8sPrnS39DW4PB4NCTT1bVDS0BL2NH8VgTaA0ZEWqABFv6+OnTPlmbXOL17+YFeQZhWIjre/z0CfQkaoZQVmWjgmcsRkf8XI4MFo9IqGAcGx3cy56TWJhORJBAT2K1US3fVTNRlOLLThVKC+NFioIjZ2+HG7Zd7JmsCSpD3r7okki8sspcpWe9AUr2nMxs5ZEUUhEo9bY9M4femNJO5DNEfcroNeEt0T1I+8MHz83R9V679gbD8RO7JynCC1atS2E/XYOd3/LCHhwiavo44VtOlY2l2XYFiEYDNMbsayQGH+H9MBPLV5QP3ilseqSQX+VJ8qNs6TG6pDBcZLr+nqNwwxa0tvJtdrfArZAWyweayuJXSa6hllBC6tWvgmUTD2c2VTiE1LDkhoYT0wva48YWCUM4GN8e3hq5HtnwfRQ7V1bGhxo9FS0SlQBJ2z1NntCp+rBwu5b68Pfx+J+2Y+e3vnA9bNUpyJ12Ib/kjdHGiXELzchgo4DgRIbseBENUiMFHiJVJiT3KIcD2fGNjINf8CvsoxiYhT2KvIk9AmbFsI8S3z/xBFj8+ONn4L9Fjz++G1tFLgE9WldAaFdxr41sD+9KAQaLju1Fo0hy65MBny/w5NbnD9psth6r1XqUEX/FbKBQw2SUJd3wFty+hl2/uQq2OFX6OvSBUVAQs3P/Bg4fIsj5KMqpOTkFFE+Ouwgc7YFHh3sZex17Lw4WYOeQ32MXwNw49kH42/PnwawLF+4/f/6BCxfeOYfo15tEBqGIPrXYY/cFHMinQ9MR5By2pbJ+Rl2po65ta8n9HzaCnUPnkd7ND7q9XveDmx/bD4FssVqxVw9rKmmSQgrTWUQvOhRZGtQ17Zy7t2IhR+n0qQwWd6lCTA+IZvXe5HAQ68/uhLSqIryQWYgx2tFjxcP+tK4Y8JINbry0AxzCXgZufH1jCkzDjoPKoaXIfJ7FHuGHZeJCKAr/ET+QkrDfH672+zrJbT5/9dBucAE7ZzSwKTQfFS3gCwXXAn8wWBkM4jqWN30QvRmVk1iwNkg6Avuc4YlCgAdp1wwvIVYhK/CR9tpaQMX++cMPQ/8DCurqsPeB/uJF7Ke7G15Ed6B7k7clgWMXemnHsw0PJm/D+yM8gvwB5IesX9lSYnZylAfsLBXCJofzFbxHBbnGdwBbwYXiZWroTAoISrjYZrRn6N7NmxNPPw1omzZhPz+Nb8gDAd/QkqpKZG9lOIalMQuYuRie3sQ+WnJmScY+7AR6G/I5iZtdY0fQ2/CqP9xKx6tBR6345uCOkYeXAQ5bGW1CNOli9tu12DOpe6ls6js8cuQ3HqZr8hJgWJg0Aofr2q3mzWuNU6xnxEb3fjvyedwfwTrBHOwmcJcopRj6Scd1FDdAgfYftbWYlMv4201d6+e5o/aJszt3Y9+W7hRFnCtUmdn9W9DDxCpM3N6znIiZO+y9jpK1cBgGgJZ7MFJk2hhhC/Q4DtSYa3ZZAYdT/D+I/LvSNxPYrxIO596IOQzvzvPu2mLYsN78XsXRbkvnYQeYUX2dRW/b7UO+Dh+0VJfvCHwb98Xjm7AOMBc7DE4lY4e8PufeYOeNXRvmeWrsk+d17Plj4221gdCNjXO0/YaQeb4BYr4camR3wLrXQ4kYH+8n6fDOdLQalulWRvwgQekExaHLrx8NJb82spXhd81mm8wBSUgioB1/ypWyqhRiD/tvIDzZzGQrzjLBT38gcx9OYVhyVxHjd4BnWLnWsnyBcvK6iQbTlAlP8G/DbjcbOWRqkoIWCCQgFm9s0WgMpfWSSN1GO0dcEgUb4oKpWB1Yie0EF8ypr0/MXjfX762csqD3IPZsd2vANsEH+yFD+gb0Pti2SyFt+YjYnMM1RYgExEDgyLgp7iZ42B9b1tG6aAS6sUElwaeVTx419V9tCbzXHuqKLFmy9VCl9jVe4aPg5VfY9Ptjf41+4F47Tz97kRFrEgSVVaXVfCRk3ysyaLdYgOXgI7Uhe4fnUhQgSJoEWpCN0d3Ri4nZP1a7Y7FGNeYFV2PrwEtrn2pZP98eKe+eEX5yq2uDW1O+0vM7xQJRSN+P21RwYAs+DWsRzbZgUyZOEz5prLsMFkNGsaeMwISOXrGYC0AhyjpXyK49y62TXgyi2BMIl0U/C+49X8Q5Gvp96JbHHgOmGkNfn2pyl1y68SHuHQNr14U7o1KGVlZZUUELkouEFvnvwf0Hd+zQiPvAKm6fRW2ZIUZ+wB7Z7a4KBLxe7BAox94E8yqam73NzQvBlpa+Zlu1trYjht1NS9CoqKjKZUjaFC3bZ5ArXK4qJmDW1PTXrCMDCEi7pqK0UZyZxboJfRh1EHXtJiJW4dEt8ai+gpy7jzxLBLz3woXtyys8Y3YwTnvNzRjrxpDB7TJTTC6n97LpnU8xOEEW/+ZQcRFj2u304pPg5gcLmMeib0ew12j8eg4TLDcsWmxfOEv1afm6kDyy2vCnyM5ynX0wCrTBO1rVrUfCwFC2uNxiXmAAjw5ee/uMEt/sbQvOdDmitnKGMRS1Wm3h7e7qaNQexJJgFbYLnE/IFwYaXzg+c93cgMfTvXj6gTZ1rCQgCCmwb8XNOrupQ1bonqkKlnZ7xIoufbW1RwpxJUjfBfV/O4lBWN4FoGSNx9zAYwqOirghugw56GXuuJ0EYzAQrqWEeYwZzZot6DJI2up7oJgdpPMO+b9mF58Gdz1EZ54MfxsMVszuvklzbXul3VvumSqtYnJfNHo6PM9b1HfT2G7wd9O8OaaZ0+TfY28Aa/CBB8DGq6MG4zw7cnjazUYTXR4cbOosqwsG4zYsDLZgG8GT2CFrPBWr9AW0JU6rfplLVCLzR91u81aTo5ArZdzYt3leld/as3jKPgwFjJobBmfGA9Y+A+xtNVCKewC2JA1hwz+8hEafWUyfWVEMr4aX2aDjyN/oA4Ucuk0qKaez2BjPG407KtjINha1kFpEL2AUvF/ZEp4eqOqcPq/qqr7+qurKyVH77kjYZi8zOq9dAdZgpza93aXxb9jcCW7GZrwZk4jFUlsQHBvcOfu4a+a+Q/0VK46cbDI17hpYh68wa0ufRm9EPsH9BunyxvMJV655Xj+z0clHohjeWCRiyBsmJ/0ubAb4MrhD69WuqK7apDMZ9/mZ5HKLsAKqlXQGFwxoEtJI54Qvnr6p8S9k21Umv66vXNEqbzL0q4u2nfCVygRSeYoK6akEyo7HUQWUVOTESjwn5LZ4+8PXc+Q5OBGoDHn2kbjqnnWWBahZhycioncniM5NyZuMGV76EQfkV1+NvP46YA7da1guCVbaEuwUS3A47H1371v7sdfWcEpE+tKwJYDQwtivo4CEUCO71whXrLVRkHbXGalacK8XPBJ/cwJa/2Y89Jv6a7RTXuotjMWSD/F+nIZvGKuLzhP6S9XgMIIt1Nnu/8eFR36eoRRHp9RqU6X+qI2v3CKYzA2xYUMiVpzdD6VHBZQFXLiPOV0uXCgxEpan4eicVOpoT2w82JvyIKToSDQr5Imvhr7+49mzz71sThQafvW78+ex49VoIYKUeJzTuN16NRNBacj3oihvSclXwJNCycziJ1zFpsdtvEQCoIkPE9dDDQb+mxZ4I2C18VFKiowUSuWWgxYQRX8GhuTQy1qAAAU5CUqKoSzjTd+B3oqWZz1+Zewn8nx+gctVakLy5RDhZnDnZrdeOghuZNHjBSLsMcSOSSDdzroT+QvHbK0VJSXCgqH7loJl2J7UJ58gr/j9ThVdWIe9cOGCu3HoenAKe8Vi5pFpcSpC4wv/jl0HrE9VNsGy8GGfth11koyQM2Xi1c8kzSUtIi3D6QkdhcScGTcx60BoUcRt3XAYCO9IGAinc5zgEAYiNgRubJYlMMKzZuYk0CBbAUpHJIHqSlHKoGGhCAUMtfILw8W83TQEmNw6Xhke5YwMTmDHdCa70C7mII0UFVSrVaxvnjE4ZSKNnNOElqq8pZKiuXV4KAQrx80y051cjFFX91Vj45EvvwQp7H+sDjGKhvAYLTL+ESP4tbe80OD8WGbTUclBMsqVyeeqeodMNgeZHCAjQvk9EzdO5IbnHB8E04c0dnMBOYSi/NIHp26rY4dmHrlh4MwZ9Ny5hdyEyFhSy8d+c3qv/J7d1xI+RErSR9DTqBa21BQxD9aPr2Uf60uBohHleNvw8GFGZsoNVbmHm7EgP8QabzjWWt74lYiC+2Eg3hx2to2e/s21wedCyyPYSo2lqGmdZvJKW1RQUajnuvml1YrEMROrbqP+qo57fxtfRG7/ZWJB+7RXX5XoBhQy5WI9WaacL1NpepVco7GS69Hwg4D93HPb1T6tw/g4XXCtqlR3HRuZH38Kc1dXg5fBE+j5NwRMU4e3yW8zc6xFZkEFk6OsUiy1TWyNep1Ta5qptCBawggyCjpr6m0MH79KXM3CVljZQb5bWsN2a/VsMiVKgfXwTzQNSM36MovcfEDEaWRWsupZkGID6T3ocQTL6s549E/nsLw5nrVWNlaDaKx/rjG/DWP+I0yw/9ItYBd2D5iIPY88gr0IWoZW/Bj/7rsyYZjt4gYF2HPCGpab6Rc9KQ6xQqwaMXKLNMAKsnySa3mmwniBnjNIl1JqKaIiUNwRDneE28FU7ER7GJz5AG63iroVetUU0SOSLplFOUU2ZFX2a8WGpZrX1FOUVt0sdYmmWy7X9Kq4qulKoX6mApe7ZkIe8iCxhk8Dtec6KEd0Qbqah/vbzPpFyR94dY/ylSQCmZDLuV95K1f1bpFo2CdYDiG5/5Qxv9HyoZaH17Kv2vrNN1B/+u5n7IN7yIYVBhOjhFeYBLrwesS8zuyFPxLghQJ6EUOlEDiZmgIkigIxTVTIptPRoV3iiSVSYasMBEtaJBJhmwS7qJzAlwhbZKBG1iqUClplyNfYadAgVsfk/FRNU1PNhJohni1SJKczKcFiOgNchWBbeNpokYouIH6vQLA3TRUiuUwrb7yxfSp656oQW2goM3xfbOf4BE56RbGN4+c56ZM4FrZf4GY4GDa2T+BikPCNTjoI+xdALoTXO0ik7DWA2uaO7DVCYpKez16jUO5/I3tNJlUCdfaaQhKDruw1leQBy7LXNNIScFf2uoDkQsTZ6yKSGGnIXrNJemRm9ppD4iODkKIXk5aQVkNOPJc0B/KO5VADPgWPCpKdOCzZKwe8FyYtgKlmQAkcP5SQm0fhGzgfnw61FCWRlxXqz0pSA8xnJrzOvLMA/h/Jf4D4NQv+n0X4Pp1FpBybdzNpBeRnK+C9dnjg5bHCciihHuCG51b41hz4dAFMu2zMrxQ8L4IQzb2sxJYxueKwWYgcLWPyUMJyZb5o/w9KNn6pOgj4BmCaxbA8yivkNzq3Xpiql8itd0xuY0sxl8AjfrUcPp0OcTiLtJBIOR/eW0yaPU59JeHTxTDHJfA6Ba8WZHvhOUSNzYXvz4W5jV8fMaLG8DpcBPlgPo4TBHx4vSZJEUgnlRBG5zDl/GcYxDEzHg5Rot2Q0udgmvE2QALpNKRwAK+LYB4hEjmWaGgnSfpWL1tAksxZNms+SbJg+vJFJAlsQ3hOaSItmD9r2SLYSvAxOTwXhEQFa+C5AH6RTqoA5fAem3gDhW9KYLnwFYEofM7Gr9Iv4s/TO+Ab04hUa0j3wXYJ80v/Ot2YX8D0NHgsT7+Tfi+9I70je+/B9AujU4x9Iw++YuKrDNi7S0kyyIMHIKZXQOpEiLsMmIIFd0A8ReDzefB6AO4oTLcclm0F3FGYfiW8RiBsOBQAvlsAz/j7CPE+QuLCHYUyrximwyGmEHkhRF5UIi8akReVyIsGn8gIyPEVMbi9Lil9NH0ULz08AyI/MR7jAK8hEr5690plxeEgQ65XRr2b/iT8zSRyRUhCuONPzbDmATzDL1Ii+DPKJMp+2Ctr4Le+gsfF9LvZqy9J/6st/Vvi/CmR10U8p7xnVennYc09/x/m9Mlld9LEeXn6UXh+h6hPWE58H05xcfjqHeJ8JP1V+gFYjkfhd++H17BExJ0HSP+ftwwm0h/gcKW/xrGc9+wFolTv/T/6FO+/Kud0ggJeyGD3P3znx/89vfzHG/j3GIZ4fY/YcQjeg3WdpbT013mp8OcQ/6NrYPjpUVgXD8LnD8JUR3KUBKkItkUSf5z0X2Lpy+7htP8d/MJFSJkXs3T41QhljirxV8M0yx+3PGmCwi9msJtOZ6noq3HTXiRSjC0PcllqfobS0rPxVgDbwtdZGnwBts4H8V8Qdvgl+PtXGc6aj7/xv3ulsl927wo5we/idfbuCF7GgzHbQkB+3REYSmfupAfS98PzzVnO8Dzcn8s+eQem+Rqe34XH8/kt8r/YcD6N2ymQID+1QI6K+5zB+0415Pd4T0vG53nh/QIiNS45FhNXFJiGAvsOBuTOeF/Bhk84kMMDopdB8vLPbazsMd6mxv0nDW9soo/NbJn/guFnaPYoHS4Z3nNxRuXGhYeQ2AuhpsYnySE34cPyKeAuhP22kISP5BSTSmD5JbDfoeOeyfM2aRbW3H55qXGo8QMhn8f7H/IbFD0xsjJSo89Din8O7z3+V/zrvWwbeQHm8jzRJt7939c0Tv9ZCvrqSm30X2wC4jDCXZDhX5BaBbAN4DJDTfpTeAUIbkTsRP2brszn0r/KcLX/gmJNUNb66jIqRsZNK/z3vdl/3Se+N16OWa54GaeDLfhfwA4xePE/LWV6xficKY878f9r2O4cacPp14jaJf273HMwZGn36/93mP6/7UvzyvTuv+P//0kNj9R0Fi+Z6w//M2oezuXr0VLmleTEf9+m/wueT4ZaWRReJaB+hpBqSd3wziyod4nw2NQkQxa3yJgegAx3XHbP9AI53k+DZ/Y4X6EQmhOF0CrwPoGRxz1JxJu4fpY5xttwbp3ZyP8xZBTIzamwbACWKr//yPQpHGLnEr2BAJafT/QGuBcUFTxwb9Ji2K8UkAoJDSTTI5Vk35dne5bcfnmpJbDfwA8E+PESg6ngPEyV6zv8/0V9Nf/Lumy6Io0cvQJX/L+gsvElzMvbFyFb5n4dGWl1o1LdT7TD+6/w9AF4B9cGUaIGign9Vgnx1kOMM47ouExCXyUT+ioZpivG11LBnUpoklSiRvHxMz9M2wN3FL4/A9IDrltSCd21gNBdCwndtYDQXQsJicdB0DY52+tn/hcPSwHk7IGPr+OxvOgkUlYqIo2ibAqx4xSOEPSHZGmFkj0y4xLtpMOjxiX0xLhEBTEuERg1LjFyDfKukbxriI0Fc+dMJ0mIs5I4lxPnymE+Sc6OaZDzrtG8a7yNM/P2zH287XqI/xSivcgIWbEfvpkk1UF+gf9vJM2B7ych/0Dgvdnw3EiUNZn5NvgBg5hCPydx0r8hyy/j2wA+WYC2ko6QuuARJO2He1dmB27kTfAL8j5pA7x3hHhyhPhPXAM73A1gGzCQDpCuH36S//9I3m/8uG7M/cx3jqDvkqaDcvi9zNGB/ycthDtehvL8nXQeeEb2bCnfIF0PTOAl4AdiUkduR94Hdlh6O6kZPAzbbzMYykGFvIm8QGogfUMcg6T1aCu4g7STZINUuBTW1xTSVFIF5MD4+Go5SUeqgnI5HjPaQloF/y+BdKuDNVANn0ZIZSQXfGon0thJXpi+DO6ZsdkKkhPufvgb901qgrKpC+5GWEMeUg38bSTSzCfGZu0kLRFDywhT22BuWpjCBf8HiTzE8Es2uONer2zwugU+w0d+baRemM9CeDZCai6HJU+R9sI78+A9Bfw9jaSHZZ0Lc6slIv2ZIW80wu9ZYWvsJWalekmdxEifmfCD1g6/VwXL2Q0h0RIQ4fbAq2FZ7LBc+JylGX5ZD/PQwHxFxJvlBIewwbymkqYTeXbB1APwS4thOhtMYSRst/DoWvjX6+EzG8TyDJjfLGJc0k+MSTrgYSLGJXFsWOFXcNyXkfCVhzYS7nXVTpSoHtYt/tsK77tIbgLbTmI1ugemt8K89LD0VcTosRfeN8AczAT2cHzjsTFxnCyEfMcOWw3OneQQmmkwdQvEXxnxTgVRbhuBKXw1uQueZ8GvWGGtG4l7auKuFfZZNgJKfGRWCZ/qidFwP2x5FtgGHYSffTspBsuqgr16KXwvDL9WBu91wPzK4a4l4asK8Zl8N0xvgt8vI10Fcd4Hc50Dc6mCtdkJz+XwPQ3MoR/WkRu+E4M9oB3WdzkxptsLc9aRFsHe1AzzaoS5WuCO279r4bsumCuO1zZY1k6YDseeG34rAH9XEbXsJajUBHmHAD6bA58aiHmClQSeq4iS4tqplfC0g8+6OYh3cL7eB1MrYE74ClG8Fn2kEMw5RGDODEuL36uB36iAso6DgLMC0kk/4YlSR6xrw7GJ12MSpghCLDZDGHBqSJLiEAtBSCNJwo8NXjONENYYTIHjVg7f0mZppBzmayOo2AGhUMC69BO47YOQlEOoO4kamwqxWQPPDnio4HenwvaMtzA9fMMK6b/i/wCI22dc",
    "s": "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",
    "h": "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",
    "t": "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",
}
_UI_FONT_DEC: Dict[str, Optional[bytes]] = {}

def _ui_font_bytes(weight: str):
    b = _UI_FONT_DEC.get(weight)
    if b is None:
        try:
            b = zlib.decompress(base64.b64decode(_UI_FONT_B64.get(weight, "")))
        except Exception:
            b = None
        if not b:
            b = None
        _UI_FONT_DEC[weight] = b
    return b


def _ui_font_ready() -> bool:
    for w in ("r", "s", "h", "t"):
        if not _ui_font_bytes(w):
            return False
    return True


def _find_cjk_font() -> Optional[str]:
    fp = CONFIG.get("FONT_PATH", "")
    if fp and Path(fp).exists() and _font_is_good_cjk(fp):
        return fp
    for path in _collect_font_candidates():
        if path and Path(path).exists() and _font_is_good_cjk(path):
            return path
    bundled = _bundled_font()
    if bundled and _font_is_good_cjk(bundled):
        print(f"[font] using bundled font: {bundled}")
        return bundled
    return None


_FB_PATH_SENTINEL = [None]


def _cjk_fallback_path() -> Optional[str]:
    if _FB_PATH_SENTINEL[0] is None:
        _FB_PATH_SENTINEL[0] = _find_cjk_font() or ""
    return _FB_PATH_SENTINEL[0] or None


_FB_BYTES_SENTINEL = [None]


def _cjk_fallback_bytes() -> Optional[bytes]:
    if _FB_BYTES_SENTINEL[0] is None:
        data = None
        try:
            data = _ui_font_bytes("r")
        except Exception:
            data = None
        if not data:
            fp = _cjk_fallback_path()
            if fp:
                try:
                    data = Path(fp).read_bytes()
                except Exception:
                    data = None
        _FB_BYTES_SENTINEL[0] = data or b""
    return _FB_BYTES_SENTINEL[0] or None


class FTFont:
    _CACHE_LIMIT = 800
    _ADV_LIMIT = 400

    def __init__(self, path, size: int, bold: bool = False,
                 weight: Optional[str] = None) -> None:
        self.ft = pygame.freetype.Font(path, size)
        if bold:
            self.ft.style = pygame.freetype.STYLE_STRONG
        self.size = size
        self.path = path
        self.bold = bold
        self.weight = weight
        self._cache: "OrderedDict[Tuple, pygame.Surface]" = OrderedDict()
        self._cw: Dict[str, int] = {}
        self._adv: Dict[Tuple, List[float]] = {}
        self._glyph_cache: "OrderedDict[Tuple, Tuple[pygame.Surface, int]]" = OrderedDict()
        self._fbft = None
        self._fbtried = False
        self._miss: Dict[str, bool] = {}

    def _fb(self):
        if self._fbft is None and not self._fbtried:
            self._fbtried = True
            data = _cjk_fallback_bytes()
            if data:
                try:
                    g = pygame.freetype.Font(io.BytesIO(bytes(data)), self.size)
                    if self.bold:
                        g.style = pygame.freetype.STYLE_STRONG
                    self._fbft = g
                except Exception:
                    self._fbft = None
        return self._fbft

    def _usable(self, ft, ch: str) -> bool:
        try:
            m = ft.get_metrics(ch)
        except Exception:
            return False
        if not m or not m[0]:
            return False
        return True

    def _is_missing(self, ch: str) -> bool:
        v = self._miss.get(ch)
        if v is None:
            v = not self._usable(self.ft, ch)
            self._miss[ch] = v
        return v

    def _pick(self, ch: str):
        if not self._is_missing(ch):
            return self.ft
        fb = self._fb()
        if fb is not None and self._usable(fb, ch):
            return fb
        return self.ft

    def glyph(self, ch: str, color: Tuple[int, int, int]) -> Tuple[pygame.Surface, int]:
        key = (ch, tuple(color))
        got = self._glyph_cache.get(key)
        if got is not None:
            self._glyph_cache.move_to_end(key)
            return got
        ft = self._pick(ch)
        try:
            s, _r = ft.render(ch, fgcolor=color)
            s = s.convert_alpha()
        except Exception:
            s = self._render_raw(ch, color, None)
        off = None
        try:
            m = ft.get_metrics(ch)
            if m and m[0]:
                off = int(round(float(m[0][3])))
        except Exception:
            off = None
        if off is None:
            off = s.get_height()
        got = (s, off)
        if len(self._glyph_cache) >= FTFont._CACHE_LIMIT:
            self._glyph_cache.popitem(last=False)
        self._glyph_cache[key] = got
        return got

    def render(self, text: Any, antialias: bool = True,
               color: Tuple[int, int, int] = (255, 255, 255),
               bgcolor: Optional[Tuple[int, int, int]] = None) -> pygame.Surface:
        text = str(text)
        key = (text, tuple(color) if color else None,
               tuple(bgcolor) if bgcolor else None)
        surf = self._cache.get(key)
        if surf is None:
            surf = self._render_raw(text, color, bgcolor)
            if len(self._cache) >= self._CACHE_LIMIT:
                self._cache.popitem(last=False)
            self._cache[key] = surf
        else:
            self._cache.move_to_end(key)
        return TextSurf(surf, _cur_scale())

    def char_w(self, ch: str) -> float:
        try:
            s = round(float(_cur_scale()), 4)
        except Exception:
            s = 1.0
        key = (ch, s)
        w = self._cw.get(key)
        if w is None:
            try:
                m = self._pick(ch).get_metrics(ch)
                w = (m[0][4] if m and m[0] else 0) / (s if s else 1.0)
            except Exception:
                w = self.render(ch, True, (255, 255, 255)).get_width()
            self._cw[key] = w
        return w

    def advances(self, text: str) -> List[float]:
        try:
            s = round(float(_cur_scale()), 4)
        except Exception:
            s = 1.0
        key = (text, s)
        v = self._adv.get(key)
        if v is not None:
            return v
        v = None
        mixed = any(self._is_missing(c) for c in text)
        try:
            if not mixed:
                m = self.ft.get_metrics(text)
                if m and len(m) == len(text):
                    sc = s if s else 1.0
                    v = [(mm[4] if mm else 0) / sc for mm in m]
        except Exception:
            v = None
        if v is None:
            v = [self.char_w(c) for c in text]
        if len(self._adv) >= self._ADV_LIMIT:
            self._adv.clear()
        self._adv[key] = v
        return v

    def _render_mixed(self, text: str,
                      color: Tuple[int, int, int],
                      bgcolor: Optional[Tuple[int, int, int]]) -> pygame.Surface:
        fb = self._fb()
        if fb is not None and all(self._usable(fb, c) for c in text):
            try:
                s, _ = fb.render(text, fgcolor=color, bgcolor=bgcolor)
                return s.convert_alpha()
            except Exception:
                pass
        gs: List[pygame.Surface] = []
        bs: List[int] = []
        total_w = 0
        for ch in text:
            ft = self._pick(ch)
            try:
                s, _ = ft.render(ch, fgcolor=color, bgcolor=bgcolor)
                s = s.convert_alpha()
            except Exception:
                s = pygame.Surface((max(1, self.size // 3), 1), pygame.SRCALPHA)
            b = s.get_height()
            try:
                m = ft.get_metrics(ch)
                if m and m[0]:
                    b = int(round(float(m[0][3])))
            except Exception:
                pass
            gs.append(s)
            bs.append(b)
            total_w += s.get_width()
        asc = max(bs) if bs else 1
        desc = max((g.get_height() - b for g, b in zip(gs, bs)), default=1)
        out = pygame.Surface((max(1, total_w), max(1, asc + desc)),
                             pygame.SRCALPHA)
        x = 0
        for s, b in zip(gs, bs):
            out.blit(s, (x, asc - b))
            x += s.get_width()
        return out.convert_alpha()

    def _render_raw(self, text: str,
                    color: Tuple[int, int, int],
                    bgcolor: Optional[Tuple[int, int, int]]) -> pygame.Surface:
        try:
            if any(self._is_missing(c) for c in text):
                return self._render_mixed(text, color, bgcolor)
            s, _ = self.ft.render(text, fgcolor=color, bgcolor=bgcolor)
            return s.convert_alpha()
        except Exception:
            pass
        try:
            pieces: List[Tuple[pygame.Surface, int]] = []
            total_w = 0
            for ch in text:
                try:
                    s, _ = self.ft.render(ch, fgcolor=color, bgcolor=bgcolor)
                    pieces.append((s, total_w))
                    total_w += s.get_width()
                except Exception:
                    total_w += max(3, self.size // 3)
            h = max(1, self.size + 4)
            out = pygame.Surface((max(1, total_w), h), pygame.SRCALPHA)
            for s, x in pieces:
                out.blit(s, (x, 0))
            return out.convert_alpha()
        except Exception:
            return pygame.Surface((1, max(1, self.size + 4)), pygame.SRCALPHA).convert_alpha()



_REAL_DRAW = pygame.draw
try:
    import pygame.gfxdraw as _GFX
except Exception:
    _GFX = None
_AA_OK = True


def _set_aa(flag: bool) -> None:
    global _AA_OK
    _AA_OK = bool(flag)

_SCALE_GETTER = lambda: 1.0
_NO_SCALE = False
_VIEW_OX = 0.0
_VIEW_OY = 0.0
_S_CACHE = None
_O_CACHE = None


def _invalidate_view_cache() -> None:
    global _S_CACHE, _O_CACHE
    _S_CACHE = None
    _O_CACHE = None


def _set_view_offset(ox: float, oy: float) -> None:
    global _VIEW_OX, _VIEW_OY
    _VIEW_OX, _VIEW_OY = float(ox), float(oy)
    _invalidate_view_cache()


def _view_offset() -> Tuple[float, float]:
    if _NO_SCALE:
        return 0.0, 0.0
    return _VIEW_OX, _VIEW_OY


def _set_scale_getter(fn) -> None:
    global _SCALE_GETTER
    _SCALE_GETTER = fn
    _invalidate_view_cache()


class _no_scale:

    def __enter__(self):
        global _NO_SCALE
        self._old = _NO_SCALE
        _NO_SCALE = True
        _invalidate_view_cache()
        return self

    def __exit__(self, *a):
        global _NO_SCALE
        _NO_SCALE = self._old
        _invalidate_view_cache()
        return False


def _raw(surf):
    if isinstance(surf, ScaledSurf):
        return surf._surf
    if isinstance(surf, TextSurf):
        return object.__getattribute__(surf, "_surf")
    return surf


def _cur_scale() -> float:
    try:
        return 1.0 if _NO_SCALE else float(_SCALE_GETTER())
    except Exception:
        return 1.0


class TextSurf:

    __slots__ = ("_surf", "_s")

    def __init__(self, surf: pygame.Surface, s: float) -> None:
        object.__setattr__(self, "_surf", surf)
        object.__setattr__(self, "_s", float(s) if s else 1.0)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_surf"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_surf"), name, value)

    def get_width(self) -> float:
        return object.__getattribute__(self, "_surf").get_width() / self._s

    def get_height(self) -> float:
        return object.__getattribute__(self, "_surf").get_height() / self._s

    def get_size(self):
        w, h = object.__getattribute__(self, "_surf").get_size()
        s = self._s
        return (w / s, h / s)

    def get_rect(self, **kwargs):
        w, h = object.__getattribute__(self, "_surf").get_size()
        s = self._s
        r = pygame.Rect(0, 0, int(round(w / s)), int(round(h / s)))
        for k, v in kwargs.items():
            setattr(r, k, v)
        return r

    def copy(self) -> "TextSurf":
        return TextSurf(object.__getattribute__(self, "_surf").copy(), self._s)


_FILM_DITH = (0.0, 0.020, -0.014, 0.009, -0.021, 0.015, -0.007, 0.018)


def _film_hsv(h: float, s: float, v: float) -> Tuple[int, int, int]:
    h = h - math.floor(h)
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i = i % 6
    if i == 0:
        c = (v, t, p)
    elif i == 1:
        c = (q, v, p)
    elif i == 2:
        c = (p, v, t)
    elif i == 3:
        c = (p, q, v)
    elif i == 4:
        c = (t, p, v)
    else:
        c = (v, p, q)
    return (int(c[0] * 255.0), int(c[1] * 255.0), int(c[2] * 255.0))


class ScaledSurf:

    __slots__ = ("_surf",)

    def __init__(self, surf: pygame.Surface) -> None:
        object.__setattr__(self, "_surf", surf)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_surf"), name)

    def __setattr__(self, name, value):
        if name == "_surf":
            object.__setattr__(self, "_surf", value)
        else:
            setattr(object.__getattribute__(self, "_surf"), name, value)

    def blit(self, src, dest, *args, **kwargs):
        s = _SCALE_GETTER()
        real = object.__getattribute__(self, "_surf")
        ox, oy = _view_offset()
        if s != 1.0 or ox or oy:
            if isinstance(dest, pygame.Rect):
                dest = (dest.x * s + ox, dest.y * s + oy)
            elif isinstance(dest, (tuple, list)):
                if len(dest) == 2:
                    dest = (dest[0] * s + ox, dest[1] * s + oy)
                elif len(dest) == 4:
                    dest = pygame.Rect(dest[0] * s + ox, dest[1] * s + oy, dest[2], dest[3])
        return real.blit(_raw(src), dest, *args, **kwargs)


class _ScaledDraw:

    @staticmethod
    def _s() -> float:
        global _S_CACHE
        v = _S_CACHE
        if v is None:
            v = 1.0 if _NO_SCALE else _SCALE_GETTER()
            _S_CACHE = v
        return v

    @staticmethod
    def _w(width: int, s: float) -> int:
        if width == 0:
            return 0
        return max(1, int(round(width * s)))

    @classmethod
    def _off(cls):
        global _O_CACHE
        v = _O_CACHE
        if v is None:
            v = _view_offset()
            _O_CACHE = v
        return v

    @classmethod
    def circle(cls, surf, color, center, radius, width=0):
        s = cls._s(); ox, oy = cls._off()
        rs = _raw(surf)
        cx, cy = center[0] * s + ox, center[1] * s + oy
        r = max(1.0, radius * s)
        if not _AA_OK or r < float(CONFIG["AA_MIN_R"]):
            return _REAL_DRAW.circle(rs, color, (cx, cy), r, cls._w(width, s))
        ca = color[3] if len(color) > 3 else 255
        has_a = bool(rs.get_flags() & pygame.SRCALPHA)
        if (r >= float(CONFIG["AA_GFX_R"]) and ca >= 255 and width == 0
                and _GFX is not None):
            ic = (int(color[0]), int(color[1]), int(color[2]))
            _GFX.filled_circle(rs, int(round(cx)), int(round(cy)),
                               int(round(r)), ic)
            _GFX.aacircle(rs, int(round(cx)), int(round(cy)), int(round(r)), ic)
            return pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
        if has_a:
            if len(color) > 3:
                soft = (color[0], color[1], color[2], int(ca * float(CONFIG["AA_EDGE_A"])))
            else:
                soft = (color[0], color[1], color[2], int(255 * float(CONFIG["AA_EDGE_A"])))
            w = cls._w(width, s)
            if w == 0:
                _REAL_DRAW.circle(rs, soft, (cx, cy), r + 1.0, 0)
            else:
                _REAL_DRAW.circle(rs, soft, (cx, cy), r + 1.0, w)
                if r > 2.0:
                    _REAL_DRAW.circle(rs, soft, (cx, cy), r - 1.0, w)
        return _REAL_DRAW.circle(rs, color, (cx, cy), r, cls._w(width, s))

    @classmethod
    def rect(cls, surf, color, rect, width=0, **kw):
        s = cls._s(); ox, oy = cls._off()
        r = pygame.Rect(rect[0] * s + ox, rect[1] * s + oy,
                        rect[2] * s, rect[3] * s)
        return _REAL_DRAW.rect(_raw(surf), color, r, cls._w(width, s), **kw)

    @classmethod
    def line(cls, surf, color, start, end, width=1):
        s = cls._s(); ox, oy = cls._off()
        p0 = (start[0] * s + ox, start[1] * s + oy)
        p1 = (end[0] * s + ox, end[1] * s + oy)
        w = cls._w(width, s)
        rs = _raw(surf)
        if _AA_OK and w <= 1:
            return _REAL_DRAW.aaline(rs, color, p0, p1, 1)
        res = _REAL_DRAW.line(rs, color, p0, p1, w)
        if _AA_OK and w > 1:
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            n = math.hypot(dx, dy)
            if n > 1e-6:
                nx, ny = -dy / n * (w / 2.0), dx / n * (w / 2.0)
                ea = float(CONFIG.get("AA_EDGE_A", 0.34)) * 1.55
                if len(color) > 3:
                    e = (color[0], color[1], color[2],
                         int(min(255, int(color[3]) * ea)))
                else:
                    e = color
                _REAL_DRAW.aaline(rs, e, (p0[0] + nx, p0[1] + ny),
                                  (p1[0] + nx, p1[1] + ny), 1)
                _REAL_DRAW.aaline(rs, e, (p0[0] - nx, p0[1] - ny),
                                  (p1[0] - nx, p1[1] - ny), 1)
        return res

    @classmethod
    def lines(cls, surf, color, closed, points, width=1):
        s = cls._s(); ox, oy = cls._off()
        pts = [(p[0] * s + ox, p[1] * s + oy) for p in points]
        return _REAL_DRAW.lines(_raw(surf), color, closed, pts, cls._w(width, s))

    @classmethod
    def polygon(cls, surf, color, points, width=0):
        s = cls._s(); ox, oy = cls._off()
        pts = [(p[0] * s + ox, p[1] * s + oy) for p in points]
        rs = _raw(surf)
        res = _REAL_DRAW.polygon(rs, color, pts, cls._w(width, s))
        if _AA_OK and len(pts) >= 3:
            ea = float(CONFIG.get("AA_EDGE_A", 0.34)) * 1.60
            if len(color) > 3:
                e = (color[0], color[1], color[2],
                     int(min(255, int(color[3]) * ea)))
            else:
                e = color
            try:
                _REAL_DRAW.aalines(rs, e, True, pts)
            except Exception:
                pass
        return res

    @classmethod
    def arc(cls, surf, color, rect, start_angle, stop_angle, width=1):
        s = cls._s(); ox, oy = cls._off()
        rs = _raw(surf)
        r = pygame.Rect(rect[0] * s + ox, rect[1] * s + oy,
                        rect[2] * s, rect[3] * s)
        w = cls._w(width, s)
        if not _AA_OK or w < 1:
            return _REAL_DRAW.arc(rs, color, r, start_angle, stop_angle, w)
        if rs.get_flags() & pygame.SRCALPHA:
            ca = color[3] if len(color) > 3 else 255
            if len(color) > 3:
                soft = (color[0], color[1], color[2], int(ca * float(CONFIG["AA_ARC_A"])))
            else:
                soft = (color[0], color[1], color[2], int(255 * float(CONFIG["AA_ARC_A"])))
            _REAL_DRAW.arc(rs, soft, r, start_angle, stop_angle, w + 1)
        return _REAL_DRAW.arc(rs, color, r, start_angle, stop_angle, w)

    @classmethod
    def ellipse(cls, surf, color, rect, width=0):
        s = cls._s(); ox, oy = cls._off()
        r = pygame.Rect(rect[0] * s + ox, rect[1] * s + oy,
                        rect[2] * s, rect[3] * s)
        return _REAL_DRAW.ellipse(_raw(surf), color, r, cls._w(width, s))

    @classmethod
    def aaline(cls, surf, color, start, end, blend=1):
        s = cls._s(); ox, oy = cls._off()
        return _REAL_DRAW.aaline(_raw(surf), color,
                                  (start[0] * s + ox, start[1] * s + oy),
                                  (end[0] * s + ox, end[1] * s + oy), blend)


_BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6],
                     [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0)


def _make_aura(size: int, peak: int, ring_at: float, ring_w: float,
               tail: int) -> np.ndarray:
    xx, yy = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    ring = np.exp(-((r - ring_at) / max(1e-3, ring_w)) ** 2)
    cut = float(CONFIG["AURA_AMB_CUT"])
    amb = np.clip(1.0 - r / max(1e-6, cut), 0.0, 1.0) ** 3.0 * float(tail)
    out = ring * peak + amb
    e0 = min(0.995, max(cut, ring_at + 2.5 * float(ring_w)))
    w = np.clip((1.0 - r) / max(1e-6, 1.0 - e0), 0.0, 1.0)
    return np.clip(out * w, 0, 255).astype(np.uint8)



def _tint_alpha(color, alpha: np.ndarray) -> pygame.Surface:
    W, H = alpha.shape
    rgb = np.zeros((W, H, 3), dtype=np.uint8)
    rgb[..., 0] = color[0]; rgb[..., 1] = color[1]; rgb[..., 2] = color[2]
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.surfarray.blit_array(surf, rgb)
    pa = pygame.surfarray.pixels_alpha(surf)
    pa[:] = alpha
    del pa
    return surf.convert_alpha()


def _make_beep(freq: float, dur: float, vol: float) -> pygame.mixer.Sound:
    sr = 44100
    n = int(sr * dur)
    t = np.arange(n) / sr
    env = np.exp(-t * 8)
    wave = np.sin(2 * np.pi * freq * t) * env * vol
    snd = np.int16(wave * 32767)
    stereo = np.stack([snd, snd], axis=1).copy()
    return pygame.sndarray.make_sound(stereo)


class Game:
    def __init__(self) -> None:
        _enable_dpi_awareness()
        _set_sdl_env()
        pygame.init()
        pygame.freetype.init()
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        self.W, self.H = W, H
        self.fullscreen = bool(CONFIG["START_FULLSCREEN"])
        self._fs_mode = "borderless"
        self.window_scale = float(CONFIG["WINDOW_SCALE"])
        self._vignette_merged = False
        self.vignette = None
        self.static_bg = None

        pygame.draw = _ScaledDraw
        _set_aa(bool(CONFIG.get("AA_ENABLE", True)))
        self.ssaa = 1.0
        self.rscale = 1.0
        self.cw = self.ch = 0
        self.aw = self.ah = 0
        self.real = None
        _set_scale_getter(lambda: self.rscale)

        self.desktop_w, self.desktop_h = self._query_desktop_size()
        self.window_scale = float(CONFIG["WINDOW_SCALE"])
        self._pending_frames = 0
        self._resize_target = None
        self._resize_win = None
        self._snapshot = None
        self._snap_tick = 0
        self._create_display(self.fullscreen)

        pygame.display.set_caption("糖浆 / SYRUP")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        self.anim_t = 0.0

        cjk_path = _find_cjk_font()
        self.font_path = cjk_path
        self._ui_font_cache = {}
        self.use_cjk = _ui_font_ready() or cjk_path is not None
        if _ui_font_ready():
            pass
        elif self.use_cjk:
            print(f"[font] using CJK font: {cjk_path}")
        else:
            print("!! 未找到中文字体，界面已降级为英文。")
            print("   请在 CONFIG['FONT_PATH'] 手动指定一个 .ttf / .otf / .ttc 文件。")
            _dump_cjk_fonts()
        self.zh_available = bool(self.use_cjk)

        self.f_big   = self._mkfont(self._fs(54), "s")
        self.f_med   = self._mkfont(self._fs(22), "s")
        self.f_small = self._mkfont(self._fs(14), "s")
        self.f_tag   = self._mkfont(self._fs(CONFIG["MENU_TAG_SIZE"]), "s")
        self.f_tiny  = self._mkfont(self._fs(11), "s")
        self.f_menu  = self._mkfont(self._fs(CONFIG["FONT_MENU"]), "s")
        self.f_over  = self._mkfont(self._fs(68), "h")
        self.f_chain = self._mkfont(self._fs(32), "h")
        self._poem_cache = {}
        self._poem_fonts = {}
        self.poem_font_path, self._poem_font_bytes = _find_poem_font()
        self.f_title = self._mkfont(self._fs(62), "t")
        self.f_head  = self._mkfont(self._fs(CONFIG["FONT_HEAD"]), "s")

        self.save_data = load_save(CONFIG["SAVE_PATH"], CONFIG["SAVE_VERSION"])
        self._apply_lang(str(self.save_data.get("lang", "en")))
        self.text_scale = float(CONFIG["TEXT_SIZE_SCALES"][0])
        self.body_size = int(CONFIG["FONT_BODY_STD"])
        self._apply_text_size(self._saved_text_size_index())
        self._rebuild_fonts()

        try:
            sk = int(self.save_data.get("skin", 0))
        except Exception:
            sk = 0
        self.skin = sk if 0 <= sk < len(CONFIG["SKINS"]) else 0
        self.fx_trail = int(self.save_data.get("fx_trail", 0)) % len(CONFIG["TRAIL_STYLES"])
        self.fx_afterimage = bool(self.save_data.get("fx_afterimage", True))
        self.fx_energy_glow = bool(self.save_data.get("fx_energy_glow", False))
        self.fx_detonate_self = bool(self.save_data.get("fx_detonate_self", False))
        self.fx_swap_ghost = bool(self.save_data.get("fx_swap_ghost", False))
        self.fx_poem = bool(self.save_data.get("fx_poem", True))
        self.appear_sel = 0
        self.appear_open = False
        self.gallery_sel = 0
        self.gallery_open = False
        self.ms_open = False
        self.ms_scroll = 0.0
        self.ms_sel = -1
        self.ms_flags = set()
        self._ptr_prev = None
        self._ptr_speed = 0.0
        self.swap_cd_max = int(CONFIG["SWAP_CD_FRAMES"])
        self._refresh_ms_flags()
        self._film_tmp = None
        if not self._skin_unlocked(self.skin):
            self.skin = self._skin_cycle(1)
            if not self._skin_unlocked(self.skin):
                self.skin = 0
            self.save_data["skin"] = self.skin

        self._tracked_cache: Dict[Any, List[pygame.Surface]] = {}
        self._big_font_cache: Dict[Tuple[int, int], FTFont] = {}
        self._logo_cache: Dict[float, List[pygame.Surface]] = {}
        self._mech_wrap_cache: Dict[Tuple[int, int], List[Tuple[str, int]]] = {}

        try:
            rs = float(self.save_data.get("render_scale",
                                          CONFIG["RENDER_SCALE_PRESET"]))
        except Exception:
            rs = float(CONFIG["RENDER_SCALE_PRESET"])
        if rs <= 0.05:
            rs = 1.0
        CONFIG["RENDER_SCALE_PRESET"] = rs
        try:
            CONFIG["RENDER_SCALE_AUTO"] = bool(
                self.save_data.get("render_auto", CONFIG.get("RENDER_SCALE_AUTO", True)))
        except Exception:
            pass
        self._rs_sync_idx()
        if abs(rs - float(self.ssaa or 1.0)) > 0.001:
            self._apply_render_scale()

        self._build_scaled_assets()

        self.snd_ok = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.snd_complete = _make_beep(880, 0.16, 0.35)
            self.snd_cancel   = _make_beep(1240, 0.07, 0.22)
            self.snd_detonate = _make_beep(560, 0.14, 0.30)
            self.snd_ok = True
        except Exception:
            self.snd_ok = False

        self.mode = "MENU"
        self.menu_sel = 0
        self.menu_stage = int(self.save_data["training_unlocked_stage"])
        self.menu_arrow_hover = None
        self._txt_w_cache = {}
        self.c_hold_frames = 0
        self.c_hold2_frames = 0
        self.paused = False
        self.pause_sel = 0
        self.gameover_sel = 0
        self.stage = 1
        self.fade_timer = 0.0
        self.shake_level = 1.0
        self.toast_timer = 0.0
        self.toast_text = ""

        self._reset_esc_state()
        self._mech_wrap_cache: Dict[Tuple[int, int], List[Tuple[str, int]]] = {}

        self._init_tweens()

        self._build_icon()

        self._setup_game()

    def _init_tweens(self) -> None:
        rects = self._menu_options_rects()
        init_y = float(rects[self.menu_sel][1])
        self.menu_sel_y = ValueTween(init_y, CONFIG["UI_TWEEN_NORMAL"], ease_out_back)

        self.esc_anim = ValueTween(0.0, 0.18, ease_out_cubic)

        self.energy_tween = ValueTween(CONFIG["MAX_ENERGY"], CONFIG["UI_TWEEN_NORMAL"], ease_out_cubic)
        self.swap_cd_tween = ValueTween(1.0, CONFIG["UI_TWEEN_NORMAL"], ease_out_cubic)
        self.chain_bar_tween = ValueTween(1.0, CONFIG["UI_TWEEN_FAST"], ease_out_cubic)

        self.gameover_anim = ValueTween(0.0, CONFIG["UI_TWEEN_SLOW"], ease_out_back)
        self.stage_complete_anim = ValueTween(0.0, CONFIG["UI_TWEEN_SLOW"], ease_out_back)

        gr = self._gameover_options_rects()
        self.gameover_sel_x = ValueTween(float(gr[0][0]), CONFIG["UI_TWEEN_NORMAL"], ease_out_back)

        self._ms_exp_d: Dict[int, ValueTween] = {}
        self._set_exp_d: Dict[int, ValueTween] = {}
        self._ms_exp_idx = -1
        self._set_exp_idx = -1
        self._ms_cand = -1
        self._ms_dwell = 0.0
        self._ms_watch = -1
        self._set_cand = -1
        self._set_dwell = 0.0
        self._set_watch = -1
        self._ms_hi_y = ValueTween(0.0, CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
        self._ms_hi_h = ValueTween(0.0, CONFIG["UI_TWEEN_NORMAL"], ease_out_cubic)
        self._set_hi_y = ValueTween(0.0, CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
        self._set_hi_h = ValueTween(0.0, CONFIG["UI_TWEEN_NORMAL"], ease_out_cubic)
        self._ms_hi_idx = -1
        self._set_hi_idx = -1

    def _hi_track(self, pairs, animate: bool = False) -> None:
        for tw, val in pairs:
            v = float(val)
            if abs(float(tw.target) - v) <= 0.5:
                continue
            if animate:
                tw.set_target(v, CONFIG["UI_TWEEN_NORMAL"])
            elif tw.done:
                tw.value = v
                tw.from_value = v
                tw.target = v
            else:
                tw.target = v

    def _ptr_track(self, dt: float) -> None:
        try:
            p = self.mouse_pos()
        except Exception:
            return
        prev = getattr(self, "_ptr_prev", None)
        self._ptr_prev = p
        if prev is None:
            self._ptr_speed = 0.0
            return
        inst = math.hypot(float(p[0]) - float(prev[0]),
                          float(p[1]) - float(prev[1])) / max(1e-4, float(dt))
        s = float(getattr(self, "_ptr_speed", 0.0))
        self._ptr_speed = 0.5 * inst + 0.5 * s

    def _hover_dwell(self) -> float:
        slow = max(0.0, float(CONFIG.get("UI_HOVER_DWELL", 0.042)))
        fast = max(slow, float(CONFIG.get("UI_HOVER_DWELL_MOVE", 0.085)))
        vs = float(CONFIG.get("UI_HOVER_V_SLOW", 45.0))
        vf = max(vs + 1.0, float(CONFIG.get("UI_HOVER_V_FAST", 620.0)))
        k = (float(getattr(self, "_ptr_speed", 0.0)) - vs) / (vf - vs)
        k = 0.0 if k < 0.0 else (1.0 if k > 1.0 else k)
        return slow + (fast - slow) * k

    def _dwell_step(self, cand: int, cur: int, dt: float, dwell_attr: str,
                    watch_attr: str) -> bool:
        d = self._hover_dwell()
        watch = int(getattr(self, watch_attr, -2))
        if cand != watch:
            setattr(self, watch_attr, cand)
            setattr(self, dwell_attr, 0.0)
            return False
        if cand == cur:
            setattr(self, dwell_attr, 0.0)
            return False
        v = float(getattr(self, dwell_attr, 0.0)) + float(dt)
        setattr(self, dwell_attr, v)
        return v >= d

    def _tick_hover(self, dt: float) -> None:
        self._ptr_track(dt)
        cand = int(getattr(self, "_ms_cand", -1))
        cur = int(getattr(self, "ms_sel", -1))
        if self._dwell_step(cand, cur, dt, "_ms_dwell", "_ms_watch"):
            self.ms_sel = cand
            self._ms_dwell = 0.0
            self._ms_exp_apply()
        cand = int(getattr(self, "_set_cand", -1))
        if not (self.esc_open and self.esc_page == "SETTINGS"):
            cand = -1
            self._set_cand = -1
        cur = int(getattr(self, "esc_sub_sel", -1))
        if self._dwell_step(cand, cur, dt, "_set_dwell", "_set_watch"):
            self.esc_sub_sel = cand
            self._set_dwell = 0.0
            self._set_exp_apply()

    def _set_sel(self, i: int) -> None:
        self.esc_sub_sel = int(i)
        self._set_cand = int(i)
        self._set_watch = int(i)
        self._set_dwell = 0.0
        self._set_exp_apply()

    def _exp_tween(self, store: str, i: int) -> ValueTween:
        d = getattr(self, store, None)
        if not isinstance(d, dict):
            d = {}
            setattr(self, store, d)
        tw = d.get(int(i))
        if tw is None:
            tw = ValueTween(0.0, CONFIG["UI_EXP_TWEEN"], ease_in_out_cubic)
            d[int(i)] = tw
        return tw

    def _tick_ui_exp(self, dt: float) -> None:
        self._tick_hover(dt)
        self._ms_exp_apply()
        self._set_exp_apply()
        for store in ("_ms_exp_d", "_set_exp_d"):
            d = getattr(self, store, None)
            if isinstance(d, dict):
                for tw in d.values():
                    tw.update(dt)
        for nm in ("_ms_hi_y", "_ms_hi_h", "_set_hi_y", "_set_hi_h"):
            tw = getattr(self, nm, None)
            if tw is not None:
                tw.update(dt)

    def _ms_exp(self, idx) -> float:
        try:
            i = int(idx)
        except Exception:
            return 0.0
        if i < 0:
            return 0.0
        return float(np.clip(self._exp_tween("_ms_exp_d", i).value, 0.0, 1.0))

    def _ms_exp_apply(self) -> None:
        try:
            cur = int(self.ms_sel)
        except Exception:
            cur = -1
        if cur == int(getattr(self, "_ms_exp_idx", -1)):
            return
        self._ms_exp_idx = cur
        try:
            n = len(CONFIG["MILESTONES"])
        except Exception:
            n = 0
        for i in range(n):
            self._exp_tween("_ms_exp_d", i).set_target(
                1.0 if i == cur else 0.0, CONFIG["UI_EXP_TWEEN"], ease_in_out_cubic)

    def _set_exp(self, idx) -> float:
        try:
            i = int(idx)
        except Exception:
            return 0.0
        if i < 0:
            return 0.0
        return float(np.clip(self._exp_tween("_set_exp_d", i).value, 0.0, 1.0))

    def _set_exp_apply(self) -> None:
        cur = -1
        if self.esc_open and self.esc_page == "SETTINGS":
            try:
                cur = int(self.esc_sub_sel)
            except Exception:
                cur = -1
        if cur == int(getattr(self, "_set_exp_idx", -1)):
            return
        self._set_exp_idx = cur
        for i in range(12):
            self._exp_tween("_set_exp_d", i).set_target(
                1.0 if i == cur else 0.0, CONFIG["UI_EXP_TWEEN"], ease_in_out_cubic)

    def mouse_pos(self):
        x, y = pygame.mouse.get_pos()
        s = self.scale
        ox, oy = getattr(self, "ox_win", 0.0), getattr(self, "oy_win", 0.0)
        x = (x - ox) / s if s != 1.0 else (x - ox)
        y = (y - oy) / s if s != 1.0 else (y - oy)
        return (x, y)

    def ev_pos(self, pos):
        s = self.scale
        return (pos[0] / s, pos[1] / s) if s != 1.0 else (pos[0], pos[1])

    def _fs(self, size: float) -> int:
        return max(1, int(round(size * float(self.rscale))))

    def _query_desktop_size(self) -> Tuple[float, float]:
        W, H = self.W, self.H
        try:
            if sys.platform == "win32":
                x, y, w, h = _win_monitor_rect(0)
                if w > 1 and h > 1:
                    return float(w), float(h)
                import ctypes
                u = ctypes.windll.user32
                for a, b in ((0, 1), (76, 77)):
                    try:
                        w = int(u.GetSystemMetrics(a)); h = int(u.GetSystemMetrics(b))
                        if w > 0 and h > 0:
                            return float(w), float(h)
                    except Exception:
                        continue
        except Exception:
            pass
        try:
            info = pygame.display.Info()
            dw, dh = float(info.current_w), float(info.current_h)
            if dw > 0 and dh > 0:
                return dw, dh
        except Exception:
            pass
        try:
            modes = pygame.display.list_modes()
            if modes:
                return float(modes[0][0]), float(modes[0][1])
        except Exception:
            pass
        return float(W), float(H)

    def _compute_fit(self, fullscreen: bool) -> float:
        W, H = self.W, self.H

        try:
            fw, fh = CONFIG.get("FORCE_RENDER_SIZE", [0, 0]) or [0, 0]
            fw, fh = int(fw), int(fh)
            if fw > 0 and fh > 0:
                return max(0.25, min(fw / W, fh / H))
        except Exception:
            pass

        rt = getattr(self, "_resize_target", None)
        if rt is not None and not fullscreen:
            return max(0.4, min(float(rt), float(CONFIG["RENDER_MAX_SCALE"])))

        dw, dh = getattr(self, "desktop_w", None), getattr(self, "desktop_h", None)
        if not dw or not dh or dw <= 0 or dh <= 0:
            try:
                info = pygame.display.Info()
                dw, dh = float(info.current_w), float(info.current_h)
            except Exception:
                dw, dh = float(W), float(H)
            if dw <= 0 or dh <= 0:
                dw, dh = float(W), float(H)

        if fullscreen:
            s = min(dw / W, dh / H)
        else:
            fit = float(CONFIG["WINDOW_SCREEN_FIT"])
            s = min(float(CONFIG["WINDOW_SCALE"]),
                    min(dw * fit / W, dh * fit / H))
            s = math.floor(s * 4.0) / 4.0

        lo = 1.0 if fullscreen else 0.4
        return max(lo, min(float(s), float(CONFIG["RENDER_MAX_SCALE"])))

    def _rs_levels(self) -> List[float]:
        lv = CONFIG.get("RENDER_SCALE_LEVELS") or [1.0]
        try:
            lv = [float(x) for x in lv]
        except Exception:
            lv = [1.0]
        return [x for x in lv if x > 0.05] or [1.0]

    def _rs_sync_idx(self) -> None:
        lv = self._rs_levels()
        tgt = float(CONFIG.get("RENDER_SCALE_PRESET", 1.0) or 1.0)
        try:
            self.rs_target_idx = min(range(len(lv)), key=lambda i: abs(lv[i] - tgt))
        except ValueError:
            self.rs_target_idx = min(1, len(lv) - 1)
        cur = int(getattr(self, "rs_idx", -1))
        if cur < 0 or cur >= len(lv):
            cur = self.rs_target_idx
        self.rs_idx = max(0, min(len(lv) - 1, cur))
        if self.rs_target_idx < self.rs_idx:
            self.rs_idx = self.rs_target_idx
        if not bool(CONFIG.get("RENDER_SCALE_AUTO", True)):
            self.rs_idx = self.rs_target_idx

    def _rs_level_value(self) -> float:
        lv = self._rs_levels()
        try:
            return float(lv[int(getattr(self, "rs_idx", 1))])
        except Exception:
            return 1.0

    def _rs_auto_on(self) -> bool:
        return bool(CONFIG.get("RENDER_SCALE_AUTO", True))

    def _rs_pen_until(self, idx: int) -> float:
        pen = getattr(self, "_rs_pen", None)
        if not isinstance(pen, dict):
            pen = self._rs_pen = {}
        return float(pen.get(int(idx), 0.0))

    def _rs_pen_add(self, idx: int, now: float) -> None:
        pen = getattr(self, "_rs_pen", None)
        if not isinstance(pen, dict):
            pen = self._rs_pen = {}
        n = int(pen.get(int(idx) + 1000, 0)) + 1
        pen[int(idx) + 1000] = n
        step = float(CONFIG.get("RENDER_SCALE_PEN", 25.0) or 25.0)
        cap = float(CONFIG.get("RENDER_SCALE_PEN_MAX", 240.0) or 240.0)
        pen[int(idx)] = now + min(step * (2 ** (n - 1)), cap)

    def _rs_reset_adapt(self) -> None:
        self._rs_pen = {}
        self._rs_samples = []
        self._rs_last_change = 0.0

    def _rs_adapt(self, ms: float) -> None:
        if not self._rs_auto_on():
            return
        now = time.time()
        hold = float(CONFIG.get("RENDER_SCALE_HOLD", 2.0) or 2.0)
        if now - float(getattr(self, "_rs_last_change", 0.0)) < hold:
            return
        buf = getattr(self, "_rs_samples", None)
        if buf is None:
            buf = self._rs_samples = []
        buf.append(float(ms))
        if len(buf) > 120:
            del buf[0]
        if len(buf) < 45:
            return
        s = sorted(buf)
        p95 = s[min(len(s) - 1, int(len(s) * 0.95))]
        budget = float(CONFIG.get("RENDER_SCALE_BUDGET", 13.0) or 13.0)
        lv = self._rs_levels()
        lo_i = min(range(len(lv)), key=lambda i: abs(lv[i] - 1.0))
        lo_i = min(lo_i, self.rs_target_idx)
        cur = int(getattr(self, "rs_idx", 1))
        if p95 > budget:
            if cur > lo_i:
                self._rs_pen_add(cur, now)
                self._rs_apply(cur - 1)
                buf.clear()
            return
        if cur >= self.rs_target_idx:
            return
        if len(buf) < 90:
            return
        if now < self._rs_pen_until(cur + 1):
            return
        if p95 < budget * float(CONFIG.get("RENDER_SCALE_UP", 0.45) or 0.45):
            self._rs_apply(cur + 1)
            buf.clear()

    def _rs_apply(self, idx: int) -> None:
        lv = self._rs_levels()
        idx = max(0, min(len(lv) - 1, int(idx)))
        if idx == int(getattr(self, "rs_idx", -1)):
            return
        self.rs_idx = idx
        self._rs_last_change = time.time()
        self._apply_render_scale()

    def _compute_rel(self, w: int, h: int) -> float:
        lv = self._rs_levels()
        base = self._rs_level_value()
        try:
            base = min(lv, key=lambda x: abs(x - base))
        except Exception:
            base = 1.0
        px = float(max(1, int(w))) * float(max(1, int(h)))
        cap = float(CONFIG.get("SSAA_MAX_PIXELS", 6_000_000) or 6_000_000)
        if base > 1.0 and px > 0.0 and px * base * base > cap:
            s = math.sqrt(cap / px)
            s = math.floor(s * 4.0) / 4.0
            base = min(base, max(1.0, s))
        return max(float(CONFIG.get("RENDER_MIN_SCALE", 0.5)),
                   min(float(base), float(CONFIG["RENDER_MAX_SCALE"])))

    def _queue_resize(self, w: int, h: int) -> None:
        if self.fullscreen or w <= 0 or h <= 0:
            return
        try:
            real = pygame.display.set_mode((w, h), pygame.RESIZABLE)
            self.screen = ScaledSurf(real)
            self.win_w, self.win_h = int(w), int(h)
        except Exception:
            return
        self._stretch_last_frame(int(w), int(h))
        self._resize_win = (int(w), int(h))
        self._apply_viewport(int(w), int(h))
        s = max(0.4, min(w / self.W, h / self.H))
        self._resize_target = s
        self._pending_frames = int(CONFIG["RESIZE_SETTLE_FRAMES"])

    def _stretch_last_frame(self, w: int, h: int) -> None:
        snap = getattr(self, "_snapshot", None)
        if snap is None:
            return
        try:
            real = _raw(self.screen)
            real.blit(pygame.transform.smoothscale(snap, (w, h)), (0, 0))
            pygame.display.flip()
        except Exception:
            pass

    def _consume_resize(self) -> None:
        if getattr(self, "_pending_frames", 0) <= 0:
            return
        self._pending_frames -= 1
        if self._pending_frames > 0:
            return
        self._pending_frames = 0
        try:
            self._apply_fullscreen(False)
        finally:
            self._resize_win = None
            self._resize_target = None

    def _intended_window_size(self, fullscreen: bool) -> Tuple[int, int]:
        dw, dh = self._desktop_size()
        if fullscreen:
            fx, fy, fw, fh = self._fullscreen_rect()
            if fw > 1 and fh > 1:
                return int(fw), int(fh)
            return int(dw), int(dh)
        if getattr(self, "_resize_win", None):
            return self._resize_win
        user = float(CONFIG["WINDOW_SCALE"])
        fit = float(CONFIG["WINDOW_SCREEN_FIT"])
        h = min(float(CONFIG["VIEWPORT_BASE_H"]) * user, dh * fit)
        w = h * (float(dw) / max(1.0, float(dh)))
        if sys.platform == "win32":
            try:
                _wx, _wy, _ww, _wh = _win_work_rect(_win_hwnd())
                if _wh > 240 and _ww > 320:
                    k = min(1.0, float(_wh) * fit / max(1.0, h),
                            float(_ww) * fit / max(1.0, w))
                    if k < 1.0:
                        h *= k
                        w *= k
            except Exception:
                pass
        return int(round(w)), int(round(h))

    def _apply_viewport(self, target_w: int, target_h: int) -> None:
        if not CONFIG.get("ADAPTIVE_VIEWPORT", True):
            self.W = int(CONFIG.get("BASE_WIDTH", 1280))
            self.H = int(CONFIG.get("BASE_HEIGHT", 720))
            CONFIG["WIDTH"], CONFIG["HEIGHT"] = self.W, self.H
            return
        ar = float(target_w) / max(1.0, float(target_h))
        base_h = float(CONFIG["VIEWPORT_BASE_H"])
        lw = base_h * ar
        lh = base_h
        w_min = float(CONFIG["VIEWPORT_W_MIN"]); w_max = float(CONFIG["VIEWPORT_W_MAX"])
        if lw > w_max:
            lw = w_max; lh = lw / ar
        elif lw < w_min:
            lw = w_min; lh = lw / ar
        lw = int(round(lw)); lh = int(round(lh))
        CONFIG["WIDTH"] = lw
        CONFIG["HEIGHT"] = lh
        self.W, self.H = lw, lh

    def _verify_fullscreen(self, fr, borderless: bool) -> bool:
        if sys.platform != "win32":
            return True
        try:
            hwnd = _win_hwnd()
            if not hwnd:
                return not borderless
            x, y, w, h = _win_monitor_rect(hwnd)
            if w <= 1 or h <= 1:
                return False
            if borderless:
                _win_set_borderless(hwnd, True)
                _win_place(hwnd, int(fr[0]), int(fr[1]),
                           int(fr[2]), int(fr[3]), True)
            rx, ry, rw, rh = _win_window_rect(hwnd)
            if rw <= 1 or rh <= 1:
                return False
            tol = max(3, int(min(w, h) * 0.01))
            if abs(rw - w) > tol or abs(rh - h) > tol:
                return False
            if borderless and (abs(rx - x) > tol or abs(ry - y) > tol):
                return False
            return True
        except Exception:
            return False

    def _create_fullscreen(self, fr):
        tw = max(320, int(fr[2]))
        th = max(240, int(fr[3]))
        strategies = []
        if CONFIG.get("FULLSCREEN_BORDERLESS", True):
            strategies.append((pygame.NOFRAME, True))
        strategies.append((pygame.FULLSCREEN, False))
        real = None
        for flags, borderless in strategies:
            try:
                if borderless:
                    os.environ["SDL_VIDEO_WINDOW_POS"] = "%d,%d" % (
                        int(fr[0]), int(fr[1]))
                else:
                    os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
            except Exception:
                pass
            cand = None
            try:
                cand = pygame.display.set_mode((tw, th), flags)
            except Exception:
                cand = None
            if cand is None or cand.get_width() <= 0 or cand.get_height() <= 0:
                continue
            real = cand
            self._fs_mode = "borderless" if borderless else "fullscreen"
            try:
                pygame.event.pump()
            except Exception:
                pass
            if self._verify_fullscreen(fr, borderless):
                return real
            if not borderless:
                return real
        if real is None:
            real = pygame.display.set_mode((tw, th))
            try:
                pygame.event.pump()
            except Exception:
                pass
        try:
            _force_window_full(fr[2], fr[3])
        except Exception:
            pass
        return real

    def _create_windowed(self):
        W, H = self.W, self.H
        fit0 = self._compute_fit(False)
        tw = max(320, int(round(W * fit0)))
        th = max(240, int(round(H * fit0)))
        try:
            os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
        except Exception:
            pass
        real = None
        try:
            real = pygame.display.set_mode((tw, th), pygame.RESIZABLE)
        except Exception:
            real = None
        if real is None or real.get_width() <= 0 or real.get_height() <= 0:
            real = pygame.display.set_mode((max(320, int(W)), max(240, int(H))))
        try:
            pygame.event.pump()
        except Exception:
            pass
        _restore_windowed(0, tw, th)
        return real

    def _create_display(self, fullscreen: bool) -> None:
        self.fullscreen = bool(fullscreen)
        tw0, th0 = self._intended_window_size(self.fullscreen)
        self._apply_viewport(tw0, th0)
        W, H = self.W, self.H

        if self.fullscreen:
            real = self._create_fullscreen(self._fullscreen_rect())
        else:
            real = self._create_windowed()

        self.win_w, self.win_h = int(real.get_width()), int(real.get_height())
        self._apply_viewport(self.win_w, self.win_h)
        W, H = self.W, self.H

        fit = min(self.win_w / float(W), self.win_h / float(H))
        if self.fullscreen:
            fit = max(fit, 0.25)
        else:
            fit = max(0.25, min(fit, float(CONFIG["RENDER_MAX_SCALE"])))
        self.scale = float(fit)
        pwf, phf = float(W) * fit, float(H) * fit
        self.pw, self.ph = int(round(pwf)), int(round(phf))
        self.ox_win = (self.win_w - pwf) / 2.0
        self.oy_win = (self.win_h - phf) / 2.0

        self._setup_canvas(real)

    def _fullscreen_rect(self) -> Tuple[int, int, int, int]:
        try:
            if sys.platform == "win32":
                x, y, w, h = _win_monitor_rect(_win_hwnd())
                if w > 1 and h > 1:
                    return (int(x), int(y), int(w), int(h))
        except Exception:
            pass
        dw, dh = self._desktop_size()
        return (0, 0, int(dw), int(dh))

    def _fs_watchdog(self) -> None:
        if not self.fullscreen or sys.platform != "win32":
            return
        self._fs_tick = getattr(self, "_fs_tick", 0) + 1
        if self._fs_tick % 30 != 0:
            return
        if getattr(self, "_fs_mode", "borderless") != "borderless":
            return
        if self._verify_fullscreen(self._fullscreen_rect(), True):
            return
        try:
            hwnd = _win_hwnd()
            if not hwnd:
                return
            x, y, w, h = _win_monitor_rect(hwnd)
            if w > 1 and h > 1:
                _win_set_borderless(hwnd, True)
                _win_place(hwnd, x, y, w, h, True)
        except Exception:
            pass

    def _setup_canvas(self, real) -> None:
        self._rs_sync_idx()
        rel = self._compute_rel(self.win_w, self.win_h)
        self.ssaa = float(rel)
        self.rscale = float(self.scale) * float(rel)
        self.cw, self.ch = int(round(self.pw * rel)), int(round(self.ph * rel))
        self.aw, self.ah = int(round(self.win_w * rel)), int(round(self.win_h * rel))
        _set_view_offset(self.ox_win * rel, self.oy_win * rel)
        if abs(float(rel) - 1.0) > 0.001:
            self.real = real
            self.screen = ScaledSurf(
                pygame.Surface((max(1, self.aw), max(1, self.ah))).convert())
        else:
            self.real = None
            self.screen = ScaledSurf(real)
        self.fx = ScaledSurf(pygame.Surface(
            (max(1, self.cw), max(1, self.ch)), pygame.SRCALPHA).convert_alpha())

    def _apply_render_scale(self) -> None:
        real = getattr(self, "real", None)
        if real is None:
            real = pygame.display.get_surface()
        if real is None:
            return
        self.win_w, self.win_h = int(real.get_width()), int(real.get_height())
        self._setup_canvas(real)
        self._rebuild_fonts()
        self._build_scaled_assets()
        self._build_icon()

    def _present(self) -> None:
        self._fs_watchdog()
        real = getattr(self, "real", None)
        if real is not None:
            _src = _raw(self.screen)
            if _src.get_size() == real.get_size():
                real.blit(_src, (0, 0))
            else:
                try:
                    pygame.transform.smoothscale(_src, real.get_size(), real)
                except Exception:
                    real.blit(pygame.transform.smoothscale(_src, real.get_size()), (0, 0))
        pygame.display.flip()
        t0 = getattr(self, "_frame_t0", None)
        if t0 is not None and self.mode in ("RUN", "TRAINING"):
            if not self.paused and not self.esc_open:
                try:
                    self._rs_adapt((time.perf_counter() - t0) * 1000.0)
                except Exception:
                    pass

    def _desktop_size(self) -> Tuple[float, float]:
        dw, dh = getattr(self, "desktop_w", 0), getattr(self, "desktop_h", 0)
        if dw and dh and dw > 0 and dh > 0:
            return float(dw), float(dh)
        try:
            info = pygame.display.Info()
            dw, dh = float(info.current_w), float(info.current_h)
            if dw > 0 and dh > 0:
                return dw, dh
        except Exception:
            pass
        return float(self.W), float(self.H)

    def _build_scaled_assets(self) -> None:
        s = self.scale
        rs = float(getattr(self, "rscale", s))
        W, H = self.W, self.H

        self.glow_player  = _tint_alpha(self.pcol, _make_aura(
            int(CONFIG["GLOW_SIZE_P"] * rs), CONFIG["GLOW_PEAK_P"],
            CONFIG["GLOW_RING_AT_P"], CONFIG["GLOW_RING_W_P"], CONFIG["GLOW_TAIL_P"]))
        self.glow_threat  = _tint_alpha(CONFIG["C_THREAT"], _make_aura(
            int(CONFIG["GLOW_SIZE_T"] * rs), CONFIG["GLOW_PEAK_T"],
            CONFIG["GLOW_RING_AT_T"], CONFIG["GLOW_RING_W_T"], CONFIG["GLOW_TAIL_T"]))
        self.glow_spitter = _tint_alpha(CONFIG["C_SPITTER"], _make_aura(
            int(CONFIG["GLOW_SIZE_S"] * rs), CONFIG["GLOW_PEAK_S"],
            CONFIG["GLOW_RING_AT_S"], CONFIG["GLOW_RING_W_S"], CONFIG["GLOW_TAIL_S"]))

        rs = float(getattr(self, "rscale", s))
        pw, ph = int(round(W * rs)), int(round(H * rs))
        reach = float(CONFIG["VIGNETTE_REACH"])
        peak = float(CONFIG["VIGNETTE_PEAK"])
        expo = float(CONFIG["VIGNETTE_EXPO"])
        xs, ys = np.mgrid[0:pw, 0:ph].astype(np.float32)
        d = np.sqrt(((xs - pw / 2) / (pw / 2)) ** 2 + ((ys - ph / 2) / (ph / 2)) ** 2)
        t = np.clip(d / max(1e-6, reach), 0.0, 1.0)
        af = peak * np.power(t, expo)
        dit = np.tile(_BAYER4, (pw // 4 + 1, ph // 4 + 1))[:pw, :ph]
        vig = np.clip(af + dit - 0.5, 0, 255).astype(np.uint8)
        self.vignette = _tint_alpha(CONFIG["VIGNETTE"], vig)

        self._vignette_merged = (s >= float(CONFIG["VIGNETTE_MERGE_SCALE"]))
        self.static_bg = self._build_static_bg()
        self._logo_cache.clear()
        self._title_grad_cache = {}
        self._tracked_cache.clear()
        self._big_font_cache.clear()
        self._mech_wrap_cache.clear()

    def _apply_fullscreen(self, fullscreen: bool) -> None:
        self._create_display(fullscreen)
        self._rebuild_fonts()
        self._build_scaled_assets()
        self._build_icon()

    def _mkfont(self, size: int, weight: str = "s", bold: bool = False) -> FTFont:
        key = (weight, int(size), bool(bold))
        cache = self._cache("_ui_font_cache")
        f = cache.get(key)
        if f is not None:
            return f
        f = None
        data = _ui_font_bytes(weight)
        if data:
            try:
                f = FTFont(io.BytesIO(bytes(data)), int(size), bold, weight)
            except Exception:
                f = None
        if f is None:
            f = FTFont(self.font_path, int(size), bold or weight != "r", weight)
        cache[key] = f
        return f

    def _rebuild_fonts(self) -> None:
        ts = float(self.text_scale or 1.0)
        self._txt_w_cache = {}
        self.f_big   = self._mkfont(self._fs(54), "s")
        self.f_med   = self._mkfont(self._fs(22 * ts), "s")
        self.f_small = self._mkfont(self._fs(14 * ts), "s")
        self.f_tag   = self._mkfont(self._fs(CONFIG["MENU_TAG_SIZE"] * ts), "s")
        self.f_tiny  = self._mkfont(self._fs(11 * ts), "s")
        self.f_menu  = self._mkfont(self._fs(CONFIG["FONT_MENU"] * ts), "s")
        self.f_over  = self._mkfont(self._fs(68), "h")
        self.f_chain = self._mkfont(self._fs(32), "h")
        self.f_title = self._mkfont(self._fs(62), "t")
        self.f_head  = self._mkfont(self._fs(CONFIG["FONT_HEAD"] * ts), "s")
        self.f_body  = self._mkfont(self._fs(CONFIG["FONT_BODY_STD"] * ts), "r")
        self.poem_glyphs = []
        self._poem_cache = {}
        self.pv_gly = []
        self.pv_gly_t = -1.0
        self.pv_gly_cd = 0.0
        self.pv_gly_i = 0
        self._pv_gly_cache = {}

    def _build_static_bg(self) -> pygame.Surface:
        ss = float(self.ssaa or 1.0)
        ww = int(round((getattr(self, "win_w", 0) or self.pw) * ss))
        wh = int(round((getattr(self, "win_h", 0) or self.ph) * ss))
        bg = pygame.Surface((ww, wh))
        bg.fill(CONFIG["BG"])
        ga = int(CONFIG.get("BG_GLOW_A", 0))
        if ga > 0 and ww > 4 and wh > 4:
            yy, xx = np.mgrid[0:wh, 0:ww].astype(np.float32)
            u = (xx / float(max(1, ww - 1)) - 0.5) * 2.0
            v = (yy / float(max(1, wh - 1)) - 0.5) * 2.0
            rr = np.sqrt(u * u + v * v) / 1.41421356
            aa = np.clip(1.0 - rr, 0.0, 1.0) ** float(
                CONFIG.get("BG_GLOW_EXPO", 2.6)) * float(ga)
            tint = tuple(min(255, int(c) + int(CONFIG.get("BG_GLOW_LIFT", 26)))
                         for c in CONFIG["BG"])
            bg.blit(_tint_alpha(tint, aa.astype(np.uint8)), (0, 0))
        s = float(self.rscale)
        step = max(4, int(round(CONFIG["GRID_STEP"] * s)))
        cw = int(round(self.pw * ss))
        ch = int(round(self.ph * ss))
        ox = int(round((ww - cw) / 2.0))
        oy = int(round((wh - ch) / 2.0))
        with _no_scale():
            x = ox % step - step
            while x <= ww:
                pygame.draw.line(bg, CONFIG["GRID"], (x, 0), (x, wh))
                x += step
            y = oy % step - step
            while y <= wh:
                pygame.draw.line(bg, CONFIG["GRID"], (0, y), (ww, y))
                y += step
            if getattr(self, "_vignette_merged", False) and self.vignette is not None:
                bg.blit(_raw(self.vignette) if isinstance(self.vignette, ScaledSurf)
                        else self.vignette, (ox, oy))
        return bg.convert()

    def _text_size_index(self) -> int:
        vals = list(CONFIG.get("TEXT_SIZE_SCALES") or [1.0, 1.18])
        ts = float(self.text_scale or 1.0)
        best, bd = 0, None
        for i, v in enumerate(vals):
            d = abs(float(v) - ts)
            if bd is None or d < bd:
                best, bd = i, d
        return best

    def _saved_text_size_index(self) -> int:
        vals = list(CONFIG.get("TEXT_SIZE_SCALES") or [1.0, 1.18])
        try:
            idx = int(self.save_data.get("text_size", 0))
        except Exception:
            idx = 0
        if not (0 <= idx < len(vals)):
            try:
                bs = int(self.save_data.get("body_size", CONFIG["FONT_BODY_STD"]))
            except Exception:
                bs = int(CONFIG["FONT_BODY_STD"])
            idx = 1 if bs >= int(CONFIG["FONT_BODY_LARGE"]) else 0
        return max(0, min(len(vals) - 1, idx))

    def _apply_text_size(self, idx: int) -> None:
        vals = list(CONFIG.get("TEXT_SIZE_SCALES") or [1.0, 1.18])
        idx = max(0, min(len(vals) - 1, int(idx)))
        self.text_scale = float(vals[idx])
        self.body_size = [int(CONFIG["FONT_BODY_STD"]),
                          int(CONFIG["FONT_BODY_LARGE"])][min(idx, 1)]

    def _apply_lang(self, lang: str) -> None:
        lang = str(lang or "en").lower()
        if lang not in ("zh", "en"):
            lang = "en"
        if lang == "zh" and not self.zh_available:
            lang = "en"
        self.lang = lang
        self.use_cjk = (lang == "zh")
        self.S = STR_ZH if self.use_cjk else STR_EN
        if hasattr(self, "save_data"):
            self.save_data["lang"] = lang
        for attr in ("_mech_wrap_cache", "_tracked_cache", "_mech_line_cache"):
            if hasattr(self, attr):
                setattr(self, attr, {})

    def _build_icon(self) -> None:
        try:
            old_s = self.scale
            old_r = self.rscale
            try:
                self.scale = 1.0
                self.rscale = 1.0
                with _no_scale():
                    ico = pygame.Surface((64, 64), pygame.SRCALPHA)
                    self._draw_logo(ico, 32, 32, scale=0.40, alpha=255)
            finally:
                self.scale = old_s
                self.rscale = old_r
            pygame.display.set_icon(ico)
        except Exception:
            pass

    def _write_save(self) -> None:
        if self.mode == "RUN":
            total = self.score_detonate + self.score_perfect + self.score_kill
            sd = self.save_data
            sd["best_score"] = max(sd["best_score"], total)
            sd["best_chain"] = max(sd["best_chain"], self.chain_max)
            sd["best_wave"] = max(sd["best_wave"], self.wave)
            sd["best_time"] = max(sd["best_time"], self.t)
        sd = self.save_data
        sd["body_size"] = self.body_size
        sd["text_size"] = self._text_size_index()
        sd["lang"] = self.lang
        sd["render_scale"] = float(CONFIG.get("RENDER_SCALE_PRESET", 1.0) or 1.0)
        sd["skin"] = self.skin
        sd["fx_trail"] = self.fx_trail
        sd["fx_afterimage"] = bool(self.fx_afterimage)
        sd["fx_energy_glow"] = bool(self.fx_energy_glow)
        sd["fx_detonate_self"] = bool(self.fx_detonate_self)
        sd["fx_swap_ghost"] = bool(self.fx_swap_ghost)
        sd["fx_poem"] = bool(self.fx_poem)
        save_now(CONFIG["SAVE_PATH"], sd)

    def _finalize_run(self) -> None:
        if self._finalized: return
        self._finalized = True
        sd = self.save_data
        total = self.score_detonate + self.score_perfect + self.score_kill
        sd["best_score"] = max(sd["best_score"], total)
        sd["best_chain"] = max(sd["best_chain"], self.chain_max)
        sd["best_wave"] = max(sd["best_wave"], self.wave)
        sd["best_time"] = max(sd["best_time"], self.t)
        sd["total_detonate"] = int(sd["total_detonate"]) + self.detonate_count
        sd["total_perfect"] = int(sd["total_perfect"]) + self.perfect_count
        sd["total_kill"] = int(sd["total_kill"]) + self.kill_count
        sd["total_runs"] = int(sd["total_runs"]) + 1
        sd["body_size"] = self.body_size
        save_now(CONFIG["SAVE_PATH"], sd)

    def _clear_save(self) -> None:
        self.save_data = dict(SAVE_DEFAULTS)
        self.save_data["version"] = CONFIG["SAVE_VERSION"]
        self.save_data["body_size"] = self.body_size
        self.save_data["lang"] = getattr(self, "lang", "en")
        save_now(CONFIG["SAVE_PATH"], self.save_data)
        self._apply_lang(self.save_data.get("lang", "en"))
        self.menu_stage = 1
        self.c_hold_frames = 0
        self.c_hold2_frames = 0
        self.toast_text = self.S["clear_success"]
        self.toast_timer = CONFIG["TOAST_DURATION"]

    def _quit_program(self) -> None:
        if self.mode == "RUN" and not self._finalized:
            self._finalize_run()
        self._write_save()
        pygame.quit()
        sys.exit()

    def _reset_esc_state(self) -> None:
        self.esc_open = False
        self.esc_page = "ROOT"
        self.esc_sel = 0
        self.esc_sub_sel = 0
        self.esc_mech_tab = 0
        self.esc_mech_scroll = 0.0
        self.esc_mech_max_scroll = 0.0
        self.esc_mech_fade = 0.0
        self.esc_ctrl_hover = -1
        self.esc_set_arrow_hover = None
        self.c_hold_frames = 0
        self.c_hold2_frames = 0
        self._set_cand = -1
        self._set_dwell = 0.0

    def _back_to_menu(self) -> None:
        if self.mode == "RUN" and not self._finalized:
            self._finalize_run()
        self._write_save()
        self.mode = "MENU"
        self.menu_sel = 0
        self.menu_stage = int(self.save_data["training_unlocked_stage"])
        self.menu_arrow_hover = None
        self.paused = False
        self.pause_sel = 0
        self.game_over = False
        self.particles = []
        self.rings = []
        self.slashes = []
        self.popups = []
        self.projectiles = []
        self._reset_esc_state()
        self.menu_sel_y.snap(float(self._menu_options_rects()[0][1]))
        self.esc_anim.snap(0.0)
        self.appear_open = False
        self.ms_open = False
        self._start_fade()

    def _start_fade(self) -> None:
        self.fade_timer = CONFIG["TRANSITION_DURATION"]

    def _tick_fade(self, dt: float) -> None:
        if self.fade_timer > 0:
            self.fade_timer = max(0.0, self.fade_timer - dt)

    def _add_trauma(self, amount: float) -> None:
        self.trauma = min(CONFIG["SHAKE_MAX_TRAUMA"], self.trauma + amount)

    def _shake_offset(self) -> Tuple[float, float]:
        t = self.trauma
        if t <= 0 or self.shake_level <= 0:
            return 0.0, 0.0
        amp = (t ** 2) * CONFIG["SHAKE_MAX_OFFSET"] * self.shake_level
        at = self.anim_t * 60.0
        ox = math.sin(at * 0.06) * amp + math.sin(at * 0.17) * amp * 0.4
        oy = math.cos(at * 0.08) * amp + math.cos(at * 0.19) * amp * 0.4
        return ox, oy

    def _add_hitstop(self, frames: int) -> None:
        self.hitstop_frames = max(self.hitstop_frames, frames)

    def _marks_on(self) -> bool:
        return self.mode == "RUN" or (self.mode == "TRAINING" and self.stage >= 2)
    @property
    def pcol(self) -> Tuple[int, int, int]:
        return tuple(CONFIG["SKINS"][self.skin]["color"])

    @property
    def pskin(self) -> dict:
        return CONFIG["SKINS"][self.skin]

    def _skin_text_color(self, i: int, default):
        sk = CONFIG["SKINS"][i]
        if sk.get("top"):
            return tuple(sk.get("gold", (231, 190, 112)))
        try:
            col = tuple(sk["color"])
        except Exception:
            return default
        r, g, b = float(col[0]), float(col[1]), float(col[2])
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        if lum >= 140.0:
            return (int(r), int(g), int(b))
        k = 140.0 / max(1.0, lum)
        return (int(min(255, r * k)), int(min(255, g * k)), int(min(255, b * k)))

    @property
    def trail_style(self) -> str:
        m = CONFIG["TRAIL_STYLES"][self.fx_trail]
        if m == "材质":
            return str(self.pskin["trail"])
        if m == "线":
            return "line"
        return "off"

    def _skin_glyph(self, i: int, rad: int, t: float = 0.0) -> pygame.Surface:
        s = max(0.001, float(self.rscale))
        old_g = _SCALE_GETTER
        _set_scale_getter(lambda: 1.0)
        side = max(4, int(round(rad * 2 * s)))
        surf = pygame.Surface((side, side), pygame.SRCALPHA)
        try:
            col = self._skin_text_color(i, CONFIG["G_80"])
        except Exception:
            col = tuple(CONFIG["G_80"])
        sk = CONFIG["SKINS"][i] if 0 <= i < len(CONFIG["SKINS"]) else {}
        kind = str(sk.get("body", ""))
        c = side / 2.0
        R = rad * s
        rr = R * 0.70
        lw = max(1, int(round(R * 0.15)))
        if kind == "drip":
            pygame.draw.circle(surf, (*col, 255), (c, c), max(1, int(round(rr))), lw)
            pygame.draw.arc(surf, (*col, 205), (c - rr, c - rr, rr * 2, rr * 2),
                            math.radians(24.0), math.radians(156.0),
                            max(1, int(round(lw + R * 0.10))))
        elif kind == "spec":
            for k in (-1, 0, 1):
                pygame.draw.circle(surf, (*col, 235 if k == 0 else 145),
                                   (c + k * rr * 0.66, c),
                                   max(1, int(round(R * (0.29 if k == 0 else 0.19)))))
        elif kind == "iris":
            pygame.draw.circle(surf, (*col, 255), (c, c), max(1, int(round(rr))), lw)
            for k in range(3):
                a0 = k * (2.0 * math.pi / 3.0) + 0.45
                cc2 = tuple(self._shift_hue(col, -0.10 * k))
                pygame.draw.arc(surf, (*cc2, 225),
                                (c - rr, c - rr, rr * 2, rr * 2),
                                a0, a0 + 0.92, lw)
        elif kind == "film":
            pygame.draw.circle(surf, (*col, 255), (c, c), max(1, int(round(rr))), lw)
            pygame.draw.circle(surf, (*col, 175), (c - rr * 0.36, c - rr * 0.36),
                               max(1, int(round(R * 0.13))))
        elif kind == "poem":
            inkg = (104, 126, 168)
            gold = tuple(sk.get("gold", (216, 178, 108)))
            br = 0.5 + 0.5 * math.sin(t * 1.7)
            ss = 4
            big = side * ss
            bs = pygame.Surface((big, big), pygame.SRCALPHA)
            bc = big / 2.0
            RB = R * ss
            pr = RB * 0.48
            for li, (lb, la, lwv) in enumerate(
                    ((0.34, int(18 + 20 * br), 0.26),
                     (0.16, int(36 + 26 * br), 0.14),
                     (0.06, int(74 + 32 * br), 0.06))):
                ws = pygame.Surface((big, big), pygame.SRCALPHA)
                npts = 40
                pts = []
                for k in range(npts):
                    a = k * (2.0 * math.pi / npts)
                    w1 = math.sin(a * 3.0 + t * (0.80 + 0.22 * li))
                    w2 = math.sin(a * 5.0 - t * (0.50 + 0.30 * li) + li * 1.7)
                    rad2 = pr + RB * lwv * (1.0 + 0.55 * w1 * w1 + 0.28 * w2)
                    pts.append((bc + math.cos(a) * rad2,
                                bc + math.sin(a) * rad2))
                pygame.draw.polygon(ws, (*inkg, 255), pts)
                ws.set_alpha(la)
                bs.blit(ws, (0, 0))
            head = -t * 0.62
            span = 2.45
            npt = 46
            for k in range(npt + 1):
                f = k / float(npt)
                ang = head + f * span
                lift = 0.5 + 0.5 * math.sin(f * 7.4 + t * 2.1)
                dry = math.sin(f * 12.0 + t * 1.3) > 0.74
                wd = RB * (0.15 + 0.11 * lift) * (0.28 if dry else 1.0)
                rad2 = pr * (1.0 + 0.05 * math.sin(f * 4.0))
                aa = int(24 + 176 * (1.0 - f) ** 0.85)
                pygame.draw.circle(bs, (*inkg, aa),
                                   (bc + math.cos(ang) * rad2,
                                    bc + math.sin(ang) * rad2),
                                   max(1, int(round(wd))))
            for q in range(2):
                ang = -t * (0.85 + 0.26 * q) + q * 2.25
                rr2 = pr * (1.14 + 0.07 * q)
                for d in range(3):
                    aa2 = ang + d * 0.26 * (1 if q % 2 == 0 else -1)
                    al = int((176 - 56 * q) * (1.0 - 0.36 * d))
                    pygame.draw.circle(bs, (*inkg, max(0, al)),
                                       (bc + math.cos(aa2) * rr2,
                                        bc + math.sin(aa2) * rr2),
                                       max(1, int(round(RB * 0.105
                                                        * (1.0 - 0.24 * d)))))
            sweep = -t * 1.05
            for k in range(14):
                f = k / 13.0
                ang = sweep + f * 0.90
                rad2 = pr - RB * 0.24
                aa = int(104 * (1.0 - f) ** 1.30)
                pygame.draw.circle(bs, (*gold, aa),
                                   (bc + math.cos(ang) * rad2,
                                    bc + math.sin(ang) * rad2),
                                   max(1, int(round(RB * 0.062
                                                    * (1.0 - 0.40 * f)))))
            rim = RB * 0.78
            pygame.draw.circle(bs, (*col, int(126 + 58 * br)), (bc, bc),
                               max(1, int(round(rim))),
                               max(1, int(round(RB * 0.095))))
            pygame.draw.circle(bs, (*gold, int(70 + 52 * br)), (bc, bc),
                               max(1, int(round(rim))),
                               max(1, int(round(RB * 0.035))))
            pygame.draw.circle(bs, (*col, int(150 + 62 * br)),
                               (bc, bc), max(1, int(round(RB * 0.17))))
            mk = pygame.Surface((big, big), pygame.SRCALPHA)
            steps = 22
            for k in range(steps, 0, -1):
                f = k / float(steps)
                aa = int(round(255.0 * min(1.0, max(0.0, (1.0 - f) / 0.38))))
                pygame.draw.circle(mk, (255, 255, 255, aa), (bc, bc),
                                   max(1, int(round(RB * 1.18 * f))))
            bs.blit(mk, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(pygame.transform.smoothscale(bs, (side, side)), (0, 0))

        else:
            pygame.draw.circle(surf, (*col, 255), (c, c), max(1, int(round(rr))), lw)
        _set_scale_getter(old_g)
        return surf

    def _skin_label(self, i: int) -> str:
        sk = CONFIG["SKINS"][i]
        base = sk["name"] if self.use_cjk else sk["en"]
        if sk.get("top"):
            base = base + (" ◆ 极" if self.use_cjk else " ◆ MAX")
        return base

    def _skin_unlocked(self, i: int) -> bool:
        sk = CONFIG["SKINS"][i] if 0 <= i < len(CONFIG["SKINS"]) else {}
        if CONFIG.get("SKIN_UNLOCK_ALL"):
            return True
        req = sk.get("req")
        if not req:
            return True
        try:
            kind, val = req[0], req[1]
        except Exception:
            return True
        if kind == "train":
            return bool(self.save_data.get("training_done", False))
        if kind == "score":
            try:
                return int(self.save_data.get("best_score", 0)) >= int(val)
            except Exception:
                return False
        return True

    def _skin_req_text(self, i: int) -> str:
        sk = CONFIG["SKINS"][i] if 0 <= i < len(CONFIG["SKINS"]) else {}
        req = sk.get("req")
        if not req:
            return self.S["skin_default"]
        try:
            kind, val = req[0], req[1]
        except Exception:
            return ""
        if kind == "train":
            return self.S["skin_req_train"]
        return self.S["skin_req_score"].replace("{n}", str(int(val)))

    def _ink_index(self) -> int:
        for i, sk in enumerate(CONFIG["SKINS"]):
            if sk.get("poem"):
                return i
        return len(CONFIG["SKINS"]) - 1

    def _skin_cycle(self, d: int) -> int:
        n = len(CONFIG["SKINS"])
        if n <= 0:
            return 0
        i = self.skin
        for _ in range(n):
            i = (i + d) % n
            if self._skin_unlocked(i):
                return i
        return self.skin if self._skin_unlocked(self.skin) else 0

    def _fx_label(self, i: int) -> str:
        return (CONFIG["FX_NAMES"][i] if self.use_cjk
                else CONFIG["FX_NAMES_EN"][i])

    def _shadows_on(self) -> bool:
        return self.mode == "RUN" or (self.mode == "TRAINING" and self.stage >= 3)
    def _cancel_on(self) -> bool:
        return self.mode == "RUN" or (self.mode == "TRAINING" and self.stage >= 4)
    def _perfect_on(self) -> bool:
        return self.mode == "RUN" or (self.mode == "TRAINING" and self.stage >= 5)

    def _setup_game(self) -> None:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        self.player_pos = np.array([W / 2, H / 2], dtype=np.float64)
        self.player_prev_pos = self.player_pos.copy()
        self.player_vel = np.zeros(2, dtype=np.float64)
        self.aim_dir = np.array([1.0, 0.0])
        self.player_trail: List[np.ndarray] = []
        self.afterimages: List[Dict[str, Any]] = []
        self.sword_qi: List[Dict[str, Any]] = []
        self.poem_glyphs: List[Dict[str, Any]] = []
        self.poem_line: int = 0
        self.poem_pos: int = 0
        self.pv_gly: List[Dict[str, Any]] = []
        self.pv_gly_t: float = -1.0
        self.pv_gly_cd: float = 0.0
        self.pv_gly_i: int = 0
        self._pv_gly_cache: Dict[str, Any] = {}

        self.player_state = "IDLE"
        self.state_frame = 0
        self.dash_dir = np.array([1.0, 0.0])
        self.dash_total_frames = CONFIG["DASH_FRAMES"]
        self.dash_hits: Set[int] = set()
        self.phase_grace_indices: Set[int] = set()
        self.phase_grace_timer = 0
        self.iframe_frames = 0
        self.did_cancel_this_backswing = False
        self.consecutive_cancels = 0

        self.buf_dash = 0
        self.buf_swap = 0
        self.free_cancel_left = int(CONFIG["DASH_CANCEL_FREE_CHAIN"])
        self.no_energy_cd = 0

        self.shadows: List[Dict[str, Any]] = []
        self.swap_cd_frames = 0
        self.energy = CONFIG["MAX_ENERGY"]

        self.chain_count = 0
        self.chain_timer = 0
        self.chain_break_flash = 0
        self.chain_max = 0
        self.discovered = set()

        self.score_detonate = 0
        self.score_perfect = 0
        self.score_kill = 0
        self.detonate_count = 0
        self.perfect_count = 0
        self.kill_count = 0

        self.bullet_time_frames = 0
        self.invert_frames = 0

        self.frame = 0
        self.t = 0.0
        self.trauma = 0.0
        self.hitstop_frames = 0
        self.death_slowmo_timer = 0.0
        self.lives = int(CONFIG["RUN_LIVES"]) + (int(CONFIG["MS_EXTRA_LIVES"])
                                                 if self._has_ms("extra_life") else 0)

        self.rings: List[Dict[str, Any]] = []
        self.popups: List[Dict[str, Any]] = []
        self.particles: List[Dict[str, Any]] = []
        self.slashes: List[Dict[str, Any]] = []
        self.slimes: List[Dict[str, Any]] = []

        self.ai_positions: List[np.ndarray] = []
        self.ai_velocities: List[np.ndarray] = []
        self.ai_trails: List[List[np.ndarray]] = []
        self.ai_marks: List[int] = []
        self.ai_trap_frames: List[int] = []
        self.ai_stun_frames: List[int] = []
        self.ai_exec_frames: List[int] = []
        self.ai_flash_frames: List[int] = []
        self.ai_types: List[int] = []
        self.wave_event: str = ""
        self.pending_spawns: List[Dict[str, Any]] = []

        self.spitters: List[Dict[str, Any]] = []
        self.projectiles: List[Dict[str, Any]] = []

        self.wave = 1
        self.wave_event = ""
        self.wave_flash = 0.0
        self.ai_spawn_timer = CONFIG["AI_SPAWN_INTERVAL"]
        self.game_over = False
        self.flash = 0.0
        self.practice_mode = False
        self._finalized = False

        self.paused = False
        self.pause_sel = 0
        self.gameover_sel = 0
        if getattr(self, "gameover_sel_x", None) is not None:
            self.gameover_sel_x.snap(float(self._gameover_options_rects()[0][0]))

        self._reset_esc_state()

        self.stage_progress = 0
        self.hint_timer = 0.0
        self.stage_complete_timer = 0.0
        self.stage_complete_flash = 0.0

        self.energy_tween.snap(CONFIG["MAX_ENERGY"])
        self.swap_cd_tween.snap(1.0)
        self.chain_bar_tween.snap(1.0)
        self.gameover_anim.snap(0.0)
        self.stage_complete_anim.snap(0.0)

        if self.mode == "TRAINING":
            n = CONFIG["STAGE_ENEMIES"][self.stage - 1]
            for _ in range(n):
                self._spawn_enemy_away()
            self.hint_timer = CONFIG["TRAINING_HINT_DURATION"]
        else:
            for _ in range(max(1, int(CONFIG["RUN_START_ENEMIES"]))):
                self._spawn_enemy_away()

    def _wave_cfg(self, wave: int) -> dict:
        tbl = CONFIG["WAVE_TABLE"]
        if not tbl:
            return {"dur": CONFIG["WAVE_DURATION"], "spawn": CONFIG["AI_SPAWN_INTERVAL"],
                    "batch": 1, "max": CONFIG["AI_MAX_COUNT"], "spitter": 0}
        i = max(0, wave - 1)
        if i >= len(tbl):
            cfg = dict(tbl[-1])
            over = i - len(tbl) + 1
            cfg["spawn"] = max(2.0, cfg["spawn"] * (0.90 ** over))
            cfg["max"] = min(12, cfg["max"] + over)
            cfg["batch"] = min(3, cfg["batch"] + over // 3)
            base_iv = float(cfg.get("spit_interval") or CONFIG["SPITTER_INTERVAL"])
            base_sp = float(cfg.get("spit_speed") or CONFIG["SPITTER_PROJ_SPEED"])
            cfg["spit_interval"] = max(CONFIG["SPITTER_INTERVAL_MIN"],
                                       base_iv * (0.95 ** over))
            cfg["spit_speed"] = min(CONFIG["SPITTER_SPEED_MAX"],
                                    base_sp + 12.0 * over)
        else:
            cfg = dict(tbl[i])
        cfg["spit_interval"] = float(cfg.get("spit_interval") or CONFIG["SPITTER_INTERVAL"])
        cfg["spit_speed"] = float(cfg.get("spit_speed") or CONFIG["SPITTER_PROJ_SPEED"])
        ev = self._wave_event_of(wave)
        if ev == "ELITE":
            cfg["spawn"] = max(2.0, float(cfg["spawn"]) * 0.85)
            cfg["batch"] = min(4, int(cfg["batch"]) + 1)
            cfg["max"] = min(14, int(cfg["max"]) + 1)
            cfg["spit_interval"] = max(CONFIG["SPITTER_INTERVAL_MIN"],
                                       float(cfg["spit_interval"]) * 0.88)
        elif ev == "SAFE":
            cfg["spawn"] = float(cfg["spawn"]) * float(CONFIG["SAFE_SPAWN_MUL"])
            cfg["max"] = max(2, int(round(int(cfg["max"]) * float(CONFIG["SAFE_MAX_MUL"]))))
        if str(getattr(self, "mode", "")) != "TRAINING":
            lo = self._ms_load()
            cfg["spawn"] = max(1.4, float(cfg["spawn"]) * float(lo["spawn"]))
            cfg["max"] = min(20, int(round(float(cfg["max"]) + float(lo["max_add"]))))
            cfg["batch"] = min(6, int(cfg["batch"]) + int(lo["batch_add"]))
            cfg["spit_interval"] = max(CONFIG["SPITTER_INTERVAL_MIN"],
                                       float(cfg["spit_interval"]) * float(lo["spit_interval"]))
            cfg["spit_speed"] = min(CONFIG["SPITTER_SPEED_MAX"],
                                    float(cfg["spit_speed"]) + float(lo["spit_speed_add"]))
        return cfg

    def _spit_interval(self, wave: int) -> float:
        v = self._wave_cfg(wave).get("spit_interval")
        return float(v) if v else float(CONFIG["SPITTER_INTERVAL"])

    def _spit_speed(self, wave: int) -> float:
        v = self._wave_cfg(wave).get("spit_speed")
        return float(v) if v else float(CONFIG["SPITTER_PROJ_SPEED"])

    def _next_wave_in(self) -> float:
        tbl = CONFIG["WAVE_TABLE"]
        if not tbl:
            return CONFIG["WAVE_DURATION"] - (self.t % CONFIG["WAVE_DURATION"])
        acc = 0.0
        for row in tbl:
            acc += float(row["dur"])
            if self.t < acc:
                return acc - self.t
        d = float(tbl[-1]["dur"])
        return d - ((self.t - acc) % d)

    def _wave_intro_line(self) -> str:
        wc = self._wave_cfg(self.wave)
        bits = []
        pv = self._wave_cfg(self.wave - 1) if self.wave > 1 else None
        mx = int(wc.get("max", CONFIG["AI_MAX_COUNT"]))
        if pv is None:
            bits.append((f"敌人上限 {mx}" if self.use_cjk else f"ENEMY CAP {mx}"))
        elif mx > int(pv.get("max", 0)):
            bits.append((f"敌人上限 {mx}" if self.use_cjk else f"ENEMY CAP {mx}"))
        sp = min(int(wc.get("spitter", 0)), CONFIG["SPITTER_MAX"])
        sp_prev = min(int(pv.get("spitter", 0)), CONFIG["SPITTER_MAX"]) if pv else 0
        if sp > sp_prev:
            bits.append((f"新增喷浆口 ×{sp - sp_prev}" if self.use_cjk
                         else f"+{sp - sp_prev} SPITTER"))
        iv = self._spit_interval(self.wave)
        iv_prev = self._spit_interval(self.wave - 1) if self.wave > 1 else iv
        if sp > 0 and iv < iv_prev - 1e-6:
            bits.append("炮台攻速 ↑" if self.use_cjk else "FIRE RATE UP")
        spd = self._spit_speed(self.wave)
        spd_prev = self._spit_speed(self.wave - 1) if self.wave > 1 else spd
        if sp > 0 and spd > spd_prev + 1e-6:
            bits.append("弹速 ↑" if self.use_cjk else "BOLT SPEED UP")
        bt = int(wc.get("batch", 1))
        if bt > 1 and (pv is None or bt > int(pv.get("batch", 1))):
            bits.append("成组出现" if self.use_cjk else "IN GROUPS")
        return "   ·   ".join(bits) if bits else ("" if self.use_cjk else "")

    def _wave_of_time(self, t: float) -> int:
        tbl = CONFIG["WAVE_TABLE"]
        if not tbl:
            return int(t / CONFIG["WAVE_DURATION"]) + 1
        acc = 0.0
        for i, row in enumerate(tbl):
            acc += float(row["dur"])
            if t < acc:
                return i + 1
        extra = int((t - acc) // float(tbl[-1]["dur"])) + 1
        return len(tbl) + extra

    def _wave_event_of(self, wave: int) -> str:
        tbl = CONFIG["WAVE_TABLE"]
        if not tbl:
            return ""
        start = max(1, int(CONFIG.get("WAVE_EVENT_FROM", 5)))
        if int(wave) < start:
            return ""
        cyc = max(3, int(CONFIG.get("WAVE_EVENT_CYCLE", 4)))
        c = (int(wave) - start) % cyc
        if c == cyc - 2:
            return "ELITE"
        if c == cyc - 1:
            return "SAFE"
        return ""

    def _score_mul(self) -> float:
        ev = float(CONFIG["ELITE_SCORE_MUL"]) if self.wave_event == "ELITE" else 1.0
        return ev * self._ms_score_mul()

    def _roll_enemy_type(self) -> int:
        if int(getattr(self, "wave", 1)) < int(CONFIG["SPLIT_FROM_WAVE"]):
            return 0
        if self.wave_event == "ELITE":
            return 1
        if self.wave_event == "SAFE":
            return 0
        return 1 if float(np.random.random()) < float(CONFIG["SPLIT_CHANCE"]) else 0

    def _split_ray_room(self, pos: np.ndarray, dv: np.ndarray, margin: float) -> float:
        w = float(CONFIG["WIDTH"])
        h = float(CONFIG["HEIGHT"])
        best = 1e9
        if dv[0] > 1e-6:
            best = min(best, (w - margin - float(pos[0])) / float(dv[0]))
        elif dv[0] < -1e-6:
            best = min(best, (margin - float(pos[0])) / float(dv[0]))
        if dv[1] > 1e-6:
            best = min(best, (h - margin - float(pos[1])) / float(dv[1]))
        elif dv[1] < -1e-6:
            best = min(best, (margin - float(pos[1])) / float(dv[1]))
        return max(0.0, float(best))

    def _spawn_split_child(self, pos: np.ndarray, k: int) -> None:
        margin = 30.0
        dmin = float(CONFIG["SPLIT_MIN_DIST"])
        pp = np.array([float(self.player_pos[0]), float(self.player_pos[1])], dtype=np.float64)
        rad = np.array([float(pos[0]) - pp[0], float(pos[1]) - pp[1]], dtype=np.float64)
        rl = float(np.linalg.norm(rad))
        if rl < 1e-3:
            a0 = float(np.random.uniform(0.0, 2.0 * math.pi))
            rad = np.array([math.cos(a0), math.sin(a0)], dtype=np.float64)
        else:
            rad = rad / rl
        perp = np.array([-float(rad[1]), float(rad[0])], dtype=np.float64)
        side = 1.0 if (int(k) % 2 == 0) else -1.0
        jit = float(CONFIG["SPLIT_SPREAD_JIT"])
        best_dv = None
        best_room = -1.0
        for _ in range(6):
            j = float(np.random.uniform(-jit, jit))
            cj = math.cos(j)
            sj = math.sin(j)
            cand = np.array([perp[0] * cj - perp[1] * sj,
                             perp[0] * sj + perp[1] * cj], dtype=np.float64) * side
            room = self._split_ray_room(pos, cand, margin)
            if room > best_room:
                best_room = room
                best_dv = cand
        if best_dv is None:
            best_dv = perp * side
            best_room = self._split_ray_room(pos, best_dv, margin)
        wlim = float(CONFIG["WIDTH"]) - margin
        hlim = float(CONFIG["HEIGHT"]) - margin
        if best_room >= dmin:
            d = dmin * (1.0 + float(np.random.uniform(0.0, float(CONFIG["SPLIT_SPREAD_VAR"]))))
            d = float(min(d, best_room))
            dv = best_dv
            np_pos = np.array([float(pos[0]) + dv[0] * d,
                               float(pos[1]) + dv[1] * d], dtype=np.float64)
        else:
            dv = best_dv
            np_pos = None
            for ang in (1.25, 1.10, 0.95, 0.80, 0.65, 0.50, 0.35, 0.20, 0.0):
                df = dmin * (1.0 + float(np.random.uniform(0.0, 0.35)))
                for sgn in (side, -side):
                    ca = math.cos(ang)
                    sa = math.sin(ang) * sgn
                    cand = np.array([rad[0] * ca - rad[1] * sa,
                                     rad[0] * sa + rad[1] * ca], dtype=np.float64)
                    cand_pos = pp + cand * df
                    if margin <= float(cand_pos[0]) <= wlim and margin <= float(cand_pos[1]) <= hlim:
                        dv = cand
                        np_pos = cand_pos
                        break
                if np_pos is not None:
                    break
            if np_pos is None:
                np_pos = pp + rad * dmin
                dv = rad
        np_pos[0] = float(np.clip(np_pos[0], margin, wlim))
        np_pos[1] = float(np.clip(np_pos[1], margin, hlim))
        away = np_pos - pp
        ad = float(np.linalg.norm(away))
        for _ in range(3):
            if ad >= dmin or ad < 1e-3:
                break
            np_pos = pp + away / ad * dmin
            np_pos[0] = float(np.clip(np_pos[0], margin, wlim))
            np_pos[1] = float(np.clip(np_pos[1], margin, hlim))
            away = np_pos - pp
            ad = float(np.linalg.norm(away))
        self.ai_positions.append(np_pos)
        self.ai_velocities.append(dv * float(CONFIG["SPLIT_BURST_SPEED"])
                                  * float(np.random.uniform(0.85, 1.20)))
        self.ai_trails.append([])
        self.ai_marks.append(0)
        self.ai_trap_frames.append(0)
        self.ai_stun_frames.append(int(CONFIG["SPLIT_STUN_FRAMES"]))
        self.ai_exec_frames.append(0)
        self.ai_flash_frames.append(int(CONFIG["SPLIT_FLASH_FRAMES"]))
        self.ai_types.append(0)
        self._ring(np_pos, 34, CONFIG["C_SPLIT"], 2, 0.35)
        self._ring(pos, 62, CONFIG["C_SPLIT"], 3, 0.45)
        self._burst(np_pos, CONFIG["C_SPLIT"], 14, 300)

    def _draw_splitter(self, x: float, y: float, flash: bool) -> None:
        col = (255, 255, 255) if flash else CONFIG["C_SPLIT"]
        r = float(CONFIG["SPLIT_RADIUS"])
        rot = self.anim_t * 2.0 * math.pi * 0.35
        pts = [(x + math.cos(rot + k * math.pi / 3.0) * r,
                y + math.sin(rot + k * math.pi / 3.0) * r) for k in range(6)]
        pygame.draw.polygon(self.fx, (*col, 235), pts, 0)
        inner = [(x + math.cos(-rot + k * math.pi / 3.0) * r * 0.52,
                  y + math.sin(-rot + k * math.pi / 3.0) * r * 0.52) for k in range(6)]
        pygame.draw.polygon(self.fx, (18, 8, 22, 220), inner, 0)
        for k in range(3):
            a = rot * 2.0 + k * (2.0 * math.pi / 3.0)
            self._soft_dot(x + math.cos(a) * r * 0.66, y + math.sin(a) * r * 0.66,
                           1.5, col, 190, 1)

    def _spawn_enemy_away(self) -> None:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        pos = np.array([W / 2, H / 2], dtype=np.float64)
        for _ in range(60):
            ang = float(np.random.uniform(0, 2 * np.pi))
            r = float(np.random.uniform(280, 380))
            pos = np.array([W / 2 + math.cos(ang) * r, H / 2 + math.sin(ang) * r])
            pos[0] = float(np.clip(pos[0], 60, W - 60))
            pos[1] = float(np.clip(pos[1], 60, H - 60))
            if vlen(pos - self.player_pos) > 260:
                break
        self.ai_positions.append(pos)
        self.ai_velocities.append(np.zeros(2))
        self.ai_trails.append([])
        self.ai_marks.append(0)
        self.ai_trap_frames.append(0)
        self.ai_stun_frames.append(0)
        self.ai_exec_frames.append(0)
        self.ai_flash_frames.append(0)
        self.ai_types.append(self._roll_enemy_type())

    def _in_slime_mask(self, pts: np.ndarray) -> np.ndarray:
        if not self.slimes or len(pts) == 0:
            return np.zeros(len(pts), dtype=bool)
        mask = np.zeros(len(pts), dtype=bool)
        for s in self.slimes:
            d = pts - s["pos"]
            r2 = s["radius"] ** 2
            mask |= (d * d).sum(axis=1) < r2
        return mask

    def _pick_spawn_pos(self) -> np.ndarray:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        edge = int(np.random.randint(4)); m = 44
        if edge == 0: return np.array([np.random.uniform(m, W - m), m], dtype=np.float64)
        if edge == 1: return np.array([np.random.uniform(m, W - m), H - m], dtype=np.float64)
        if edge == 2: return np.array([m, np.random.uniform(m, H - m)], dtype=np.float64)
        return np.array([W - m, np.random.uniform(m, H - m)], dtype=np.float64)

    def _burst(self, pos, color, count=20, speed=260.0, life=0.55) -> None:
        for _ in range(count):
            ang = float(np.random.uniform(0, 2 * np.pi))
            spd = float(np.random.uniform(0.25, 1.0)) * speed
            self.particles.append({
                "pos": pos.copy(), "vel": np.array([math.cos(ang), math.sin(ang)]) * spd,
                "life": life, "maxlife": life, "color": color,
            })

    def _ring(self, pos, max_r, color, width=2, life=0.5) -> None:
        self.rings.append({"pos": pos.copy(), "max_r": max_r, "color": color,
                           "width": width, "life": life, "maxlife": life})

    def _popup(self, pos, text, color=(255, 255, 255)) -> None:
        self.popups.append({"pos": pos.copy(), "text": text, "color": color,
                            "life": 0.8, "maxlife": 0.8})

    def _slash(self, pos, direction) -> None:
        self.slashes.append({"pos": pos.copy(), "dir": direction.copy(),
                             "life": 0.30, "maxlife": 0.30})

    def _play(self, snd) -> None:
        if self.snd_ok:
            try: snd.play()
            except Exception: pass

    def try_dash(self) -> bool:
        if self.player_state in ("DASHING", "RECOVERY"): return False
        free = (self.mode == "TRAINING" and self.stage == 4)
        is_cancel = (self.player_state == "BACKSWING")
        cancel_free = (is_cancel and CONFIG["DASH_CANCEL_FREE"]
                       and self.free_cancel_left > 0)
        if not free and not cancel_free and self.energy < CONFIG["DASH_COST"]:
            if self.no_energy_cd <= 0:
                self.no_energy_cd = CONFIG["NO_ENERGY_HINT_CD"]
                self._popup(self.player_pos + np.array([0, -34]),
                            "无能量" if self.use_cjk else "NO ENERGY",
                            CONFIG["C_THREAT"])
            return False

        if self._shadows_on():
            if len(self.shadows) >= CONFIG["SHADOW_MAX"]:
                self.shadows.pop(0)
            self.shadows.append({
                "pos": self.player_pos.copy(),
                "drift_dir": -self.aim_dir.copy(),
                "frames_left": CONFIG["SHADOW_LIFE_FRAMES"],
            })

        if not free and not cancel_free:
            self.energy -= CONFIG["DASH_COST"]
        if cancel_free:
            self.free_cancel_left -= 1
        else:
            self.free_cancel_left = int(CONFIG["DASH_CANCEL_FREE_CHAIN"])
        self._update_aim()
        self.dash_dir = self.aim_dir.copy()
        self.dash_total_frames = CONFIG["DASH_FRAMES"]
        self.dash_hits = set()
        self.phase_grace_indices = set()
        self.phase_grace_timer = 0

        if is_cancel:
            self.dash_total_frames = int(CONFIG["DASH_FRAMES"] * CONFIG["CANCEL_BONUS_MULT"])
            self.iframe_frames = CONFIG["CANCEL_IFRAME_FRAMES"]
            self.did_cancel_this_backswing = True
            self.consecutive_cancels += 1
            if self.mode == "RUN" and "cancel" not in self.discovered:
                self.discovered.add("cancel")
                self._popup(self.player_pos + np.array([0, -52]),
                            "取消后摇" if self.use_cjk else "CANCEL", self.pcol)
            self._burst(self.player_pos, self.pcol, 12, 220)
            self._ring(self.player_pos, 44, self.pcol, 2, 0.3)
            self._play(self.snd_cancel)
            self._add_hitstop(CONFIG["HITSTOP_CANCEL"])
            if self.mode == "TRAINING" and self.stage == 4:
                self.stage_progress = self.consecutive_cancels
                self._check_stage_goal()

        self.player_state = "DASHING"
        self.state_frame = 0
        return True

    def try_swap(self) -> bool:
        if not self._shadows_on(): return False
        if self.swap_cd_frames > 0: return False

        if not self.shadows:
            self.swap_cd_frames = CONFIG["SWAP_EMPTY_CD_FRAMES"]
            self._ring(self.player_pos, 44, CONFIG["G_60"], 1, 0.3)
            self._popup(self.player_pos + np.array([0, -30]),
                        "空放" if self.use_cjk else "whiff", CONFIG["G_60"])
            return True

        mx, my = self.mouse_pos()
        mouse = np.array([mx, my], dtype=np.float64)
        best_i = min(range(len(self.shadows)),
                     key=lambda i: vlen(self.shadows[i]["pos"] - mouse))
        target = self.shadows[best_i]
        old_pos = self.player_pos.copy()
        new_pos = target["pos"].copy()

        if self.fx_swap_ghost:
            self.afterimages.append({
                "pos": old_pos.copy(),
                "life": float(self.pskin["ai_life"]) * 2.2,
                "maxlife": float(self.pskin["ai_life"]) * 2.2})
            if self.pskin.get("poem"):
                try:
                    d = new_pos - old_pos
                    ln = vlen(d)
                    dv = d / ln if ln > 1e-6 else self.aim_dir
                except Exception:
                    dv = self.aim_dir
                self._spawn_sword_qi(dv, 2, 1.35, 0.46, old_pos)
        self.player_pos = new_pos
        self.player_vel = np.zeros(2)
        target["pos"] = old_pos

        perfect = False
        if self._perfect_on():
            for i, ap in enumerate(self.ai_positions):
                to_p = old_pos - ap
                dn = vlen(to_p)
                if dn < 1e-3: continue
                to_p_n = to_p / dn
                if dn < self._perfect_dist() and \
                   float(np.dot(self.ai_velocities[i], to_p_n)) > 15.0:
                    perfect = True; break

        self._ring(old_pos, CONFIG["SWAP_IMPACT_RADIUS"], self.pcol, 3, 0.5)
        self._ring(new_pos, CONFIG["SWAP_IMPACT_RADIUS"], self.pcol, 3, 0.5)
        self._burst(old_pos, self.pcol, 10, 200)
        self._burst(new_pos, self.pcol, 10, 200)

        trapped_any = False
        for i, ap in enumerate(self.ai_positions):
            d1 = vlen(ap - old_pos)
            d2 = vlen(ap - new_pos)
            if d1 < CONFIG["SWAP_IMPACT_RADIUS"] or d2 < CONFIG["SWAP_IMPACT_RADIUS"]:
                self.ai_trap_frames[i] = max(self.ai_trap_frames[i], CONFIG["SWAP_TRAP_FRAMES"])
                trapped_any = True

        self.swap_cd_frames = self._swap_cd_max()

        if self.player_state in ("BACKSWING", "RECOVERY"):
            self.iframe_frames = max(self.iframe_frames, CONFIG["CANCEL_IFRAME_FRAMES"])
        self.player_state = "IDLE"
        self.state_frame = 0
        self.did_cancel_this_backswing = False

        if trapped_any and self.mode == "TRAINING" and self.stage == 3:
            self.stage_progress += 1
            self._check_stage_goal()

        if perfect:
            if self.mode == "RUN" and "perfect" not in self.discovered:
                self.discovered.add("perfect")
                self._popup(self.player_pos + np.array([0, -72]),
                            "完美换位" if self.use_cjk else "PERFECT SWAP", self.pcol)
            self.bullet_time_frames = CONFIG["PERFECT_BULLET_FRAMES"]
            self.invert_frames = 1
            self.perfect_count += 1
            self.score_perfect += CONFIG["PERFECT_SWAP_SCORE"]
            for i in [j for j in range(len(self.ai_marks)) if self.ai_marks[j] > 0]:
                self._do_detonate(i)
            self._ring(self.player_pos, 220, (255, 255, 255), 3, 0.6)
            self._popup(self.player_pos + np.array([0, -46]),
                        "见影" if self.use_cjk else "PERFECT", (255, 255, 255))
            self._add_trauma(0.7)
            self._add_hitstop(CONFIG["HITSTOP_PERFECT"])
            if self.mode == "TRAINING" and self.stage == 5:
                self.stage_progress += 1
                self._check_stage_goal()
        return True

    def _do_detonate(self, i: int) -> None:
        if i >= len(self.ai_positions): return
        pos = self.ai_positions[i].copy()
        self.ai_marks[i] = 0
        self.detonate_count += 1
        self.energy = min(CONFIG["MAX_ENERGY"],
                          self.energy + CONFIG["DETONATE_ENERGY_GAIN"]
                          * (float(CONFIG["MS_KILL_ENERGY"])
                             if self._has_ms("kill_hud") else 1.0))

        kb = pos - self.player_pos
        kn = vlen(kb)
        if kn > 1e-3: kb = kb / kn
        else: kb = np.array([1.0, 0.0])
        self.ai_velocities[i] = kb * CONFIG["DETONATE_KNOCKBACK"]
        self.ai_stun_frames[i] = CONFIG["DETONATE_STUN_FRAMES"]
        self.ai_exec_frames[i] = (CONFIG["DETONATE_STUN_FRAMES"]
                                  + CONFIG["DETONATE_EXEC_FRAMES"])
        self.ai_flash_frames[i] = 6

        if self.chain_timer <= 0: self.chain_count = 0
        self.chain_count += 1
        self.chain_timer = CONFIG["CHAIN_WINDOW_FRAMES"]
        self.chain_max = max(self.chain_max, self.chain_count)
        if self.mode == "RUN" and self.chain_count >= 2 and "chain" not in self.discovered:
            self.discovered.add("chain")
            self._popup(pos + np.array([0, -52]),
                        f"连锁 ×{self.chain_count}" if self.use_cjk
                        else f"CHAIN x{self.chain_count}", self.pcol)

        idx = min(self.chain_count - 1, len(self._chain_mults()) - 1)
        mult = self._chain_mults()[idx]
        gained = int(CONFIG["DETONATE_BASE_SCORE"] * mult * self._score_mul())
        if self._has_ms("det_bonus") and self.chain_count >= int(CONFIG["MS_DET_BONUS_MIN"]):
            gained += int((self.chain_count - (int(CONFIG["MS_DET_BONUS_MIN"]) - 1))
                          * int(CONFIG["MS_DET_BONUS"]) * self._score_mul())
        self.score_detonate += gained

        _dr = self._det_radius()
        self.slimes.append({"pos": pos, "age": 0.0,
                            "life": CONFIG["DETONATE_SLIME_FRAMES"] / 60.0,
                            "radius": _dr, "is_burst": True})

        self._burst(pos, CONFIG["C_THREAT"], 24, 400)
        self._burst(pos, (255, 255, 255), 10, 300)
        self._ring(pos, _dr, CONFIG["C_THREAT"], 3, 0.6)
        mult_str = f"x{mult}" if mult > 1 else ""
        self._popup(pos + np.array([0, -30]), f"+{gained} {mult_str}".strip(), CONFIG["C_THREAT"])
        self._play(self.snd_detonate)
        self._add_trauma(0.5)
        self._add_hitstop(CONFIG["HITSTOP_DETONATE"])
        if self.fx_detonate_self:
            self._ring(self.player_pos, 56, self.pcol, 2, 0.45)
            self._burst(self.player_pos, self.pcol, 14, 260)
            self._burst(self.player_pos, self.pskin.get("ink", (72, 92, 130)), 24, 330)
            if self.pskin.get("poem"):
                self._spawn_sword_qi(self.dash_dir, 3, 1.15, 0.42)
            if self.fx_poem and self.pskin.get("poem"):
                self._spawn_poem(self.player_pos, 3)

        if self.mode == "TRAINING" and self.stage == 2:
            self.stage_progress += 1
            self._check_stage_goal()

    def _check_dash_hits(self, prev_pos, curr_pos) -> None:
        if not self._marks_on(): return
        for i in range(len(self.ai_positions)):
            if i in self.dash_hits: continue
            p = self.ai_positions[i]
            AB = curr_pos - prev_pos; AP = p - prev_pos
            AB2 = float(AB[0] * AB[0] + AB[1] * AB[1])
            if AB2 < 1e-6:
                dist = vlen(AP)
            else:
                t = max(0.0, min(1.0, float(AP[0] * AB[0] + AP[1] * AB[1]) / AB2))
                closest = prev_pos + AB * t
                dist = vlen(p - closest)
            if dist < CONFIG["MARK_HIT_RADIUS"]:
                self.dash_hits.add(i)
                self.ai_flash_frames[i] = 8
                self._slash(p, self.dash_dir)
                if self.ai_marks[i] > 0:
                    self._do_detonate(i)
                else:
                    self.ai_marks[i] = CONFIG["MARK_LIFE_FRAMES"]
                    self._ring(p, 34, CONFIG["C_MARK"], 2, 0.35)
                    self._popup(p + np.array([0, -24]),
                                "标记" if self.use_cjk else "MARK", CONFIG["C_MARK"])

    def _kill_ai(self, i: int) -> None:
        pos = self.ai_positions[i].copy()
        _ks = int(CONFIG["KILL_SCORE"] * self._score_mul()
                  * ((1.0 + float(CONFIG["MS_KILL_BONUS"]))
                     if self._has_ms("kill_bonus") else 1.0))
        self.score_kill += _ks
        self.kill_count += 1
        _tp = self.ai_types[i] if i < len(self.ai_types) else 0
        self._burst(pos, CONFIG["C_THREAT"], 22, 340)
        self._ring(pos, 80, CONFIG["C_THREAT"], 3, 0.5)
        self._popup(pos + np.array([0, -30]), f"+{_ks}", CONFIG["C_THREAT"])
        self.ai_positions.pop(i); self.ai_velocities.pop(i); self.ai_trails.pop(i)
        self.ai_marks.pop(i); self.ai_trap_frames.pop(i); self.ai_stun_frames.pop(i)
        self.ai_exec_frames.pop(i); self.ai_flash_frames.pop(i)
        if i < len(self.ai_types): self.ai_types.pop(i)
        if _tp == 1:
            for k in range(int(CONFIG["SPLIT_CHILDREN"])):
                self._spawn_split_child(pos, k)
        def fix(s: Set[int]) -> Set[int]:
            return {j - 1 if j > i else j for j in s if j != i}
        self.dash_hits = fix(self.dash_hits)
        self.phase_grace_indices = fix(self.phase_grace_indices)

    def _death_collision(self, arr: np.ndarray) -> bool:
        if len(arr) == 0: return False
        if self.player_state == "DASHING" and CONFIG["DASH_PHASE_ON_MARK"]:
            exempt = self.dash_hits
        elif self.phase_grace_timer > 0:
            exempt = self.phase_grace_indices
        else:
            exempt = set()
        exempt |= {i for i in range(len(self.ai_trap_frames))
                   if self.ai_trap_frames[i] > 0 or self.ai_exec_frames[i] > 0}

        prev = self.player_prev_pos
        curr = self.player_pos
        AB = curr - prev
        AB2 = float(AB[0] * AB[0] + AB[1] * AB[1])
        N = len(arr)
        DR = CONFIG["DEATH_RADIUS"]

        if AB2 < 1e-6:
            for i in range(N):
                if i in exempt: continue
                if vlen(arr[i] - curr) < DR:
                    return True
            return False

        AP = arr - prev
        t = np.clip((AP[:, 0] * AB[0] + AP[:, 1] * AB[1]) / AB2, 0.0, 1.0)
        closest = prev[None, :] + t[:, None] * AB[None, :]
        dist = np.linalg.norm(arr - closest, axis=1)
        for i in range(N):
            if i in exempt: continue
            if dist[i] < DR:
                return True
        return False

    def _check_stage_goal(self) -> None:
        if self.mode != "TRAINING": return
        if self.stage_complete_timer > 0: return
        goal = CONFIG["STAGE_GOALS"][self.stage - 1]
        if self.stage_progress >= goal:
            self.stage_complete_timer = CONFIG["TRAINING_COMPLETE_HOLD"]
            self.stage_complete_flash = 1.0
            self.stage_complete_anim.snap(0.0)
            self.stage_complete_anim.set_target(1.0, CONFIG["UI_TWEEN_SLOW"], ease_out_back)
            self._play(self.snd_complete)
            self._ring(self.player_pos, 240, self.pcol, 3, 1.0)
            self._burst(self.player_pos, self.pcol, 30, 400)
            self._start_fade()

            st = self.stage
            sd = self.save_data
            new_unlocked = 5 if st >= 5 else (st + 1)
            sd["training_unlocked_stage"] = max(int(sd["training_unlocked_stage"]), new_unlocked)
            if st >= 5:
                sd["training_done"] = True
            try:
                par = float(CONFIG["STAGE_PAR"][st - 1])
            except Exception:
                par = 20.0
            tt = float(self.t)
            if tt <= par * 0.62:
                rk = "S"
            elif tt <= par * 0.85:
                rk = "A"
            elif tt <= par * 1.15:
                rk = "B"
            else:
                rk = "C"
            order = {"S": 4, "A": 3, "B": 2, "C": 1}
            lst = sd.get("stage_rank")
            if not isinstance(lst, list) or len(lst) < 5:
                lst = [None] * 5
            prev = lst[st - 1]
            if prev is None or order.get(rk, 0) > order.get(str(prev), 0):
                lst[st - 1] = rk
            sd["stage_rank"] = lst
            self._check_milestones()
            save_now(CONFIG["SAVE_PATH"], sd)

    def _refresh_ms_flags(self) -> None:
        got = self.save_data.get("milestones")
        if not isinstance(got, list):
            got = []
        on = self.save_data.get("ms_on")
        if not isinstance(on, list):
            on = list(got)
            self.save_data["ms_on"] = on
        f = set()
        for idx, row in enumerate(CONFIG["MILESTONES"]):
            if idx in got and idx in on and len(row) > 4:
                f.add(row[4])
        self.ms_flags = f
        self._ms_load_cache = None

    def _has_ms(self, tag: str) -> bool:
        return tag in self.ms_flags

    def _ms_w_of(self, row) -> int:
        return int(row[7]) if len(row) > 7 else 1

    def _ms_weight(self) -> Tuple[int, int]:
        total = sum(self._ms_w_of(r) for r in CONFIG["MILESTONES"])
        cur = sum(self._ms_w_of(r) for r in CONFIG["MILESTONES"]
                  if len(r) > 4 and r[4] in self.ms_flags)
        return cur, total

    def _ms_score_mul(self) -> float:
        w, _t = self._ms_weight()
        return 1.0 + float(w) * float(CONFIG["MS_SCORE_PER_LOAD"])

    def _ms_load(self) -> dict:
        c = getattr(self, "_ms_load_cache", None)
        if isinstance(c, dict):
            return c
        n = len(self.ms_flags)
        out = {
            "max_add": float(n) * float(CONFIG["MS_LOAD_MAX"]),
            "spawn": float(CONFIG["MS_LOAD_SPAWN"]) ** n,
            "speed": 1.0 + float(n) * float(CONFIG["MS_LOAD_SPEED"]),
            "spit_interval": float(CONFIG["MS_LOAD_SPIT"]) ** n,
            "spit_speed_add": float(n) * float(CONFIG["MS_LOAD_BOLT"]),
            "batch_add": 0.0,
        }
        foc = CONFIG["MS_FOCUS"]
        wmap = {}
        for row in CONFIG["MILESTONES"]:
            if len(row) > 4:
                wmap[row[4]] = self._ms_w_of(row)
        for tag in sorted(self.ms_flags):
            f = foc.get(tag) or {}
            w = float(wmap.get(tag, 1))
            for k, share in f.items():
                amt = float(share) * w
                if k == "max":
                    out["max_add"] += amt * float(CONFIG["MS_UNIT_MAX"])
                elif k == "speed":
                    out["speed"] *= 1.0 + amt * float(CONFIG["MS_UNIT_SPEED"])
                elif k == "spawn":
                    out["spawn"] *= 1.0 - amt * float(CONFIG["MS_UNIT_SPAWN"])
                elif k == "spit_interval":
                    out["spit_interval"] *= 1.0 - amt * float(CONFIG["MS_UNIT_SPIT"])
                elif k == "spit_speed":
                    out["spit_speed_add"] += amt * float(CONFIG["MS_UNIT_BOLT"])
                elif k == "batch":
                    out["batch_add"] += amt * float(CONFIG["MS_UNIT_BATCH"])
        self._ms_load_cache = out
        return out

    def _ms_done_count(self) -> Tuple[int, int]:
        got = self.save_data.get("milestones")
        if not isinstance(got, list):
            got = []
        n = len(CONFIG["MILESTONES"])
        return len([i for i in got if 0 <= i < n]), n

    def _ms_state(self, idx: int) -> Dict[str, Any]:
        row = CONFIG["MILESTONES"][idx]
        key, need = row[0], int(row[1])
        got = self.save_data.get("milestones")
        got = got if isinstance(got, list) else []
        cur = int(self.save_data.get(key, 0) or 0)
        done = idx in got or cur >= need
        on = self.save_data.get("ms_on")
        if not isinstance(on, list):
            on = list(got)
        return {
            "key": key, "need": need, "cur": cur, "done": done,
            "name": row[2] if self.use_cjk else row[3],
            "reward": row[5] if self.use_cjk else row[6],
            "tag": row[4],
            "w": self._ms_w_of(row),
            "sp": int(row[8]) if len(row) > 8 else 0,
            "on": (idx in on) and done,
            "prog": float(np.clip(float(cur) / float(need), 0.0, 1.0)) if need > 0 else 1.0,
        }

    def _ms_panel_w(self) -> int:
        W = CONFIG["WIDTH"]
        return int(min(620, W * 0.86))

    def _ms_detail_lines(self, idx: int) -> List[str]:
        st = self._ms_state(idx)
        zh = bool(self.use_cjk)
        nm = (CONFIG["MS_STAT_NAME"].get(st["key"]) or ("", ""))[0 if zh else 1]
        goal = nm or st["key"]
        left = max(0, int(st["need"]) - int(st["cur"]))
        if zh:
            g = f"{self.S['ms_goal']} · {goal} {st['cur']} / {st['need']}"
            if not st["done"]:
                g += f"（还差 {left}）"
        else:
            g = f"{self.S['ms_goal']} · {goal} {st['cur']} / {st['need']}"
            if not st["done"]:
                g += f" ({left} to go)"
        gain = f"{self.S['ms_gain']} · {st['reward']}"
        foc = CONFIG["MS_FOCUS"].get(st["tag"]) or {}
        ds = []
        for k in ("max", "speed", "spawn", "spit_interval", "spit_speed", "batch"):
            if k in foc:
                d = CONFIG["MS_FOCUS_DESC"].get(k) or ("", "")
                v = d[0 if zh else 1]
                if v:
                    ds.append(v)
        if zh:
            cost = f"{self.S['ms_cost']} · 负重 +{st['w']}　分数 +{st['sp']}%"
        else:
            cost = f"{self.S['ms_cost']} · LOAD +{st['w']}  SCORE +{st['sp']}%"
        if ds:
            cost += " · " + ("、".join(ds) if zh else ", ".join(ds))
        return [g, gain, cost]

    def _ms_wrapped_detail(self, idx: int) -> List[str]:
        out = []
        maxw = self._ms_panel_w() - 44
        for t in self._ms_detail_lines(idx):
            out.extend(self._wrap_text(t, self.f_tiny, maxw))
        return out

    def _ms_detail_h(self, idx: int) -> int:
        if idx is None or idx < 0:
            return 0
        n = len(self._ms_wrapped_detail(idx))
        if n <= 0:
            return 0
        return int(CONFIG["MS_DETAIL_PAD"]) + n * int(CONFIG["MS_DETAIL_LH"])

    def _ms_items(self):
        items = []
        for _gk, zh, en, keys in CONFIG["MILESTONE_GROUPS"]:
            idxs = [i for i, r in enumerate(CONFIG["MILESTONES"]) if r[0] in keys]
            if not idxs:
                continue
            items.append(("head", (zh if self.use_cjk else en), -1))
            for i in idxs:
                items.append(("row", "", i))
        return items

    def _ms_view_top(self) -> int:
        return 152

    def _ms_view_h(self) -> int:
        H = CONFIG["HEIGHT"]
        return max(80, (H - 84) - self._ms_view_top())

    def _ms_content_h(self, items=None) -> float:
        if items is None:
            items = self._ms_items()
        tot = 0.0
        for it in items:
            if it[0] == "head":
                tot += float(int(CONFIG["MS_HEAD_H"]))
            else:
                tot += float(int(CONFIG["MS_ROW_H"]))
                tot += float(self._ms_detail_h(it[2])) * float(self._ms_exp(it[2]))
        return tot

    def _ms_max_scroll(self) -> float:
        return max(0.0, self._ms_content_h() - float(self._ms_view_h()))

    def _ms_clamp_scroll(self) -> None:
        self.ms_scroll = float(np.clip(float(self.ms_scroll), 0.0, self._ms_max_scroll()))

    def _ms_row_rects(self):
        W = CONFIG["WIDTH"]
        w = self._ms_panel_w()
        x = int(W // 2 - w // 2)
        y = float(self._ms_view_top()) - float(self.ms_scroll)
        out = []
        for it in self._ms_items():
            h = int(CONFIG["MS_HEAD_H"]) if it[0] == "head" else int(CONFIG["MS_ROW_H"])
            if it[0] == "row":
                h += self._ms_detail_h(it[2]) * self._ms_exp(it[2])
            out.append((x, y, w, h, it))
            y += h
        return out

    def _ms_row_settled(self, idx: int):
        y = float(self._ms_view_top()) - float(self.ms_scroll)
        for it in self._ms_items():
            if it[0] == "row" and int(it[2]) == int(idx):
                return (y, float(int(CONFIG["MS_ROW_H"]))
                        + float(self._ms_detail_h(int(idx))))
            y += float(int(CONFIG["MS_HEAD_H"]) if it[0] == "head"
                       else int(CONFIG["MS_ROW_H"]))
        return None

    def _ms_back_rect(self):
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        return (int(W // 2 - 100), int(H - 68), 200, 34)

    def _on_ms_key(self, e) -> None:
        step = int(CONFIG["MS_ROW_H"])
        if e.key == pygame.K_UP:
            self.ms_scroll -= step
        elif e.key == pygame.K_DOWN:
            self.ms_scroll += step
        elif e.key == pygame.K_PAGEUP:
            self.ms_scroll -= self._ms_view_h()
        elif e.key == pygame.K_PAGEDOWN:
            self.ms_scroll += self._ms_view_h()
        elif e.key == pygame.K_HOME:
            self.ms_scroll = 0.0
        elif e.key == pygame.K_END:
            self.ms_scroll = self._ms_max_scroll()
        elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            if self.ms_sel >= 0:
                self._ms_toggle(self.ms_sel)
            return
        elif e.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER,
                       pygame.K_SPACE, pygame.K_BACKSPACE):
            self.ms_open = False
            self.ms_sel = -1
            self._ms_cand = -1
            self._ms_dwell = 0.0
            return
        self._ms_clamp_scroll()

    def _on_ms_click(self, mx: float, my: float) -> None:
        bx, by, bw, bh = self._ms_back_rect()
        if bx <= mx <= bx + bw and by <= my <= by + bh:
            self.ms_open = False
            self.ms_sel = -1
            self._ms_cand = -1
            self._ms_dwell = 0.0
            return
        top = float(self._ms_view_top())
        bot = top + float(self._ms_view_h())
        for x, y, w, h, it in self._ms_row_rects():
            if y + h < top or y > bot:
                continue
            if x <= mx <= x + w and max(top, y) <= my <= min(bot, y + h):
                if it[0] == "row":
                    self.ms_sel = it[2]
                    self._ms_cand = it[2]
                    self._ms_dwell = 0.0
                    self._ms_toggle(it[2])
                return

    def _ms_toggle(self, idx: int) -> None:
        st = self._ms_state(idx)
        if not st["done"]:
            return
        on = self.save_data.get("ms_on")
        if not isinstance(on, list):
            on = [i for i in self.save_data.get("milestones", [])
                  if isinstance(i, int)]
        if idx in on:
            on.remove(idx)
        else:
            on.append(idx)
        self.save_data["ms_on"] = on
        self._refresh_ms_flags()
        save_now(CONFIG["SAVE_PATH"], self.save_data)

    def _ms_hit(self, pos) -> int:
        top = float(self._ms_view_top())
        bot = top + float(self._ms_view_h())
        base = int(CONFIG["MS_ROW_H"])
        sel = int(getattr(self, "ms_sel", -1))
        rects = self._ms_row_rects()
        for x, y, w, h, it in rects:
            if it[0] != "row" or int(it[2]) != sel:
                continue
            if y + h < top or y > bot:
                continue
            hh = base + self._ms_detail_h(sel)
            if (x <= pos[0] <= x + w
                    and max(top, y) <= pos[1] <= min(bot, y + float(hh))):
                return sel
        for x, y, w, h, it in rects:
            if it[0] != "row" or int(it[2]) == sel:
                continue
            if y + h < top or y > bot:
                continue
            if (x <= pos[0] <= x + w
                    and max(top, y) <= pos[1] <= min(bot, y + float(base))):
                return int(it[2])
        return -1

    def _sync_ms_hover(self, pos) -> None:
        self._ms_cand = int(self._ms_hit(pos))

    def _draw_check(self, x: float, y: float, s: float, col) -> None:
        pygame.draw.lines(self.screen, col, False,
                          [(x - s * 0.40, y),
                           (x - s * 0.08, y + s * 0.36),
                           (x + s * 0.44, y - s * 0.38)], 2)

    def _tint_full(self, rgba) -> None:
        ov = getattr(self, "_tint_ov", None)
        if ov is None or ov.get_width() != self.cw or ov.get_height() != self.ch:
            ov = pygame.Surface((self.cw, self.ch), pygame.SRCALPHA)
            self._tint_ov = ov
        ov.fill((int(rgba[0]), int(rgba[1]), int(rgba[2]),
                 max(0, min(255, int(rgba[3])))))
        self.screen.blit(ov, (0, 0))

    def _head2(self, W: int, title: str, sub: str, y1: int, y2: int) -> None:
        t = self.f_head.render(title, True, (235, 240, 248))
        self.screen.blit(t, t.get_rect(center=(W // 2, y1)))
        s = self.f_small.render(sub, True, CONFIG["G_60"])
        self.screen.blit(s, s.get_rect(center=(W // 2, y2)))

    def _hint(self, txt: str, cx: int, cy: int, col=None, a: float = 1.0) -> None:
        s = self.f_tiny.render(txt, True,
                               CONFIG["G_60"] if col is None else col)
        if a < 1.0:
            s.set_alpha(int(255 * a))
        self.screen.blit(s, s.get_rect(center=(cx, cy)))

    def _draw_ms(self, W: int, H: int) -> None:
        self._tint_full((11, 15, 20, 212))

        done, total = self._ms_done_count()
        self._head2(W, self.S["milestones"],
                    f"{self.S['ms_sub']}   ·   {done}/{total}", 98, 124)
        cw, tw = self._ms_weight()
        if self.use_cjk:
            lt = f"负重 {cw} / {tw}     分数 ×{self._ms_score_mul():.2f}"
        else:
            lt = f"LOAD {cw} / {tw}     SCORE x{self._ms_score_mul():.2f}"
        lb = self.f_small.render(lt, True, CONFIG["C_PLAYER"] if cw > 0 else CONFIG["G_60"])
        self.screen.blit(lb, lb.get_rect(center=(W // 2, 142)))

        top = float(self._ms_view_top())
        bot = top + float(self._ms_view_h())
        self._ms_clamp_scroll()

        ms_rows = self._ms_row_rects()
        sel_idx = int(getattr(self, "ms_sel", -1))
        if sel_idx >= 0:
            sp = self._ms_row_settled(sel_idx)
            if sp is not None:
                self._hi_track(((self._ms_hi_y, float(sp[0])),
                                (self._ms_hi_h, float(sp[1]))),
                               int(getattr(self, "_ms_hi_idx", -1)) >= 0
                               and sel_idx != int(getattr(self, "_ms_hi_idx", -1)))
        self._ms_hi_idx = sel_idx
        if sel_idx >= 0 and float(self._ms_hi_h.value) > 1.0:
            _ds = float(self.rscale) or 1.0
            pw = float(self._ms_panel_w())
            px = int(W // 2 - pw // 2)
            hy0 = max(top, float(self._ms_hi_y.value))
            hy1 = min(bot, float(self._ms_hi_y.value) + float(self._ms_hi_h.value))
            if hy1 - hy0 > 1.0:
                hhv = hy1 - hy0
                hl = pygame.Surface((max(1, int(pw * _ds)), max(1, int(hhv * _ds))),
                                    pygame.SRCALPHA)
                hl.fill((*CONFIG["G_20"], 255))
                self.screen.blit(hl, (px, int(round(hy0))))
                pygame.draw.rect(self.screen, CONFIG["C_PLAYER"],
                                 (px, int(round(hy0)), 4, int(round(hhv))))

        for x, y, w, h, it in ms_rows:
            if y + h < top - 0.5 or y > bot + 0.5:
                continue
            if it[0] == "head":
                yy = max(top, y)
                lbl = self.f_small.render(it[1], True, CONFIG["G_60"])
                self.screen.blit(lbl, (x + 4, yy + 6))
                lx = x + 4 + lbl.get_width() + 12
                pygame.draw.line(self.screen, CONFIG["G_20"],
                                 (lx, yy + 15), (x + w - 4, yy + 15))
                continue

            idx = it[2]
            st = self._ms_state(idx)
            active = bool(st["on"])
            nc = CONFIG["C_PLAYER"] if active else (CONFIG["G_80"] if st["done"] else CONFIG["G_60"])
            nm = self.f_med.render(st["name"], True, nc)
            self.screen.blit(nm, (x + 16, y + 5))
            if active:
                self._draw_check(x + 22 + nm.get_width() + 12, y + 14, 15,
                                 CONFIG["C_PLAYER"])
            pv = self.f_small.render(f"{st['cur']}/{st['need']}", True,
                                     CONFIG["C_PLAYER"] if st["done"] else CONFIG["G_60"])
            self.screen.blit(pv, (x + w - 16 - pv.get_width(), y + 6))
            if self.use_cjk:
                wt = f"负重 +{st['w']}  ·  分数 +{st['sp']}%"
            else:
                wt = f"LOAD +{st['w']}  ·  SCORE +{st['sp']}%"
            wlc = CONFIG["C_PLAYER"] if active else CONFIG["G_40"]
            wl = self.f_tiny.render(wt, True, wlc)
            self.screen.blit(wl, (x + w - 16 - wl.get_width(), y + 30))
            if not st["done"]:
                pre = self.S["ms_unlock"]
            elif active:
                pre = self.S["ms_unlocked"]
            else:
                pre = "已关闭" if self.use_cjk else "OFF"
            rc = CONFIG["G_80"] if active else CONFIG["G_40"]
            full = f"{pre} · {st['reward']}"
            room = w - 32 - wl.get_width() - 18
            def _tw(v):
                try:
                    return float(sum(self.f_tiny.advances(v)))
                except Exception:
                    return 0.0
            if _tw(full) > room and room > 24:
                cut = full
                while len(cut) > 2 and _tw(cut + "…") > room:
                    cut = cut[:-1]
                full = cut + "…"
            rl = self.f_tiny.render(full, True, rc)
            self.screen.blit(rl, (x + 16, y + 30))
            bx0 = x + 16
            bwv = w - 32
            pygame.draw.rect(self.screen, CONFIG["G_40"], (bx0, y + 45, bwv, 3), 0)
            if st["prog"] > 0.0:
                pygame.draw.rect(self.screen,
                                 CONFIG["C_PLAYER"] if st["done"] else CONFIG["G_80"],
                                 (bx0, y + 45, max(1, int(bwv * st["prog"])), 3), 0)
            exp = self._ms_exp(idx) if idx == self.ms_sel else 0.0
            if exp > 0.01:
                dy = y + int(CONFIG["MS_ROW_H"]) + 3
                al = int(255.0 * float(np.clip(exp, 0.0, 1.0)))
                for ln in self._ms_wrapped_detail(idx):
                    ls = self.f_tiny.render(ln, True, CONFIG["G_80"])
                    if al < 255:
                        ls = ls.copy()
                        ls.set_alpha(al)
                    self.screen.blit(ls, (x + 16, dy))
                    dy += int(CONFIG["MS_DETAIL_LH"])

        if self._ms_max_scroll() > 0.5:
            _ds = float(self.rscale) or 1.0
            pw = int(min(620, W * 0.86))
            px0 = int(W // 2 - pw // 2)
            fh = 40
            fw = max(1, int(pw * _ds))
            fhx = max(1, int(fh * _ds))
            if self.ms_scroll > 0.5:
                gr = np.linspace(255.0, 0.0, fhx).reshape(fhx, 1).repeat(fw, axis=1)
                self.screen.blit(_tint_alpha((11, 15, 20), gr), (px0, int(top)))
            if self.ms_scroll < self._ms_max_scroll() - 0.5:
                gr = np.linspace(0.0, 255.0, fhx).reshape(fhx, 1).repeat(fw, axis=1)
                self.screen.blit(_tint_alpha((11, 15, 20), gr), (px0, int(bot) - fh))
            frac = float(self.ms_scroll) / float(self._ms_max_scroll())
            tx = int(W // 2 + pw / 2 + 10)
            ty = top
            th = self._ms_view_h()
            pygame.draw.rect(self.screen, CONFIG["G_40"], (tx, ty, 3, th), 0)
            kh = max(18, int(th * float(self._ms_view_h()) / self._ms_content_h()))
            ky = ty + int((th - kh) * frac)
            pygame.draw.rect(self.screen, CONFIG["G_80"], (tx, ky, 3, kh), 0)

        bx, by, bw, bh = self._ms_back_rect()
        lbl = self.f_med.render(self.S["back"], True, CONFIG["G_80"])
        pygame.draw.rect(self.screen, CONFIG["G_20"], (bx, by, bw, bh), 1)
        self.screen.blit(lbl, lbl.get_rect(center=(bx + bw // 2, by + bh // 2)))
        self._hint(self.S["ms_hint"], W // 2, H - 22, CONFIG["G_40"])

    def _det_radius(self) -> float:
        r = float(CONFIG["DETONATE_RADIUS"])
        if self._has_ms("det_ring"):
            r *= float(CONFIG["MS_DET_RADIUS_MUL"])
        return r

    def _perfect_dist(self) -> float:
        d = float(CONFIG["PERFECT_THREAT_DIST"])
        if self._has_ms("perfect_range"):
            d += float(CONFIG["MS_PERFECT_ADD"])
        return d

    def _chain_mults(self):
        m = list(CONFIG["CHAIN_MULTS"])
        if self._has_ms("chain_bonus"):
            m = list(m) + [float(CONFIG["MS_CHAIN_EXTRA"])]
        return m

    def _swap_cd_max(self) -> int:
        base = int(CONFIG["SWAP_CD_FRAMES"])
        if self._has_ms("swap_cd"):
            base = max(1, int(round(base * float(CONFIG["MS_SWAP_CD_MUL"]))))
        self.swap_cd_max = base
        return base

    def _check_milestones(self) -> None:
        got = self.save_data.get("milestones")
        if not isinstance(got, list):
            got = []
        on = self.save_data.get("ms_on")
        if not isinstance(on, list):
            on = list(got)
        for idx, row in enumerate(CONFIG["MILESTONES"]):
            if idx in got:
                continue
            try:
                key, need, zh, en = row[0], int(row[1]), row[2], row[3]
            except Exception:
                continue
            if int(self.save_data.get(key, 0) or 0) >= need:
                got.append(idx)
                if idx not in on:
                    on.append(idx)
                self._popup(np.array([CONFIG["WIDTH"] / 2.0,
                                      CONFIG["HEIGHT"] * 0.34]),
                            (f"里程碑 · {zh}" if self.use_cjk else f"MILESTONE · {en}"),
                            CONFIG["C_PLAYER"])
        self.save_data["milestones"] = got
        self.save_data["ms_on"] = on
        self._refresh_ms_flags()

    def _die(self, source: str = "threat") -> None:
        if self.mode == "TRAINING":
            self._on_stage_fail()
            return
        self._check_milestones()
        if self.lives > 1:
            self.lives -= 1
            self._respawn()
            return
        self.game_over = True
        self.flash = 1.0
        self._add_trauma(1.0)
        self.death_slowmo_timer = CONFIG["DEATH_SLOWMO_DURATION"]
        self.gameover_anim.snap(0.0)
        if source == "projectile":
            self._burst(self.player_pos, CONFIG["C_SPITTER"], 24, 300)
        else:
            self._burst(self.player_pos, CONFIG["C_THREAT"], 40, 420)
            self._burst(self.player_pos, (255, 255, 255), 12, 300)
        self._finalize_run()

    def _respawn(self) -> None:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        R = float(CONFIG["RESPAWN_CLEAR_RADIUS"])

        self.player_pos = np.array([W / 2, H / 2], dtype=np.float64)
        self.player_prev_pos = self.player_pos.copy()
        self.player_vel = np.zeros(2)
        self.player_state = "IDLE"
        self.state_frame = 0
        self.dash_hits = set()
        self.phase_grace_indices = set()
        self.phase_grace_timer = 0
        self.buf_dash = 0
        self.buf_swap = 0
        self.shadows = []

        self.iframe_frames = int(CONFIG["RESPAWN_IFRAMES"])
        self.energy = CONFIG["MAX_ENERGY"]
        self.chain_count = 0
        self.chain_timer = 0

        cleared = 0
        keep = [i for i, ap in enumerate(self.ai_positions)
                if vlen(ap - self.player_pos) > R]
        for i in reversed(range(len(self.ai_positions))):
            if i not in keep:
                pos = self.ai_positions[i]
                self._burst(pos, CONFIG["C_THREAT"], 14, 260)
                self._ring(pos, 60, CONFIG["C_THREAT"], 2, 0.4)
                self.ai_positions.pop(i); self.ai_velocities.pop(i)
                self.ai_trails.pop(i); self.ai_marks.pop(i)
                self.ai_trap_frames.pop(i); self.ai_stun_frames.pop(i)
                self.ai_exec_frames.pop(i); self.ai_flash_frames.pop(i)
                if i < len(self.ai_types): self.ai_types.pop(i)
                cleared += 1
        self.pending_spawns = [sp for sp in self.pending_spawns
                               if vlen(sp["pos"] - self.player_pos) > R]
        self.projectiles = [p for p in self.projectiles
                            if vlen(p["pos"] - self.player_pos) > R]

        self.flash = 0.8
        self._add_trauma(0.8)
        self._add_hitstop(int(CONFIG["RESPAWN_HITSTOP"]))
        self.death_slowmo_timer = float(CONFIG["RESPAWN_SLOWMO"])
        self._ring(self.player_pos, 200, self.pcol, 3, 0.7)
        self._burst(self.player_pos, self.pcol, 30, 380)
        self._popup(self.player_pos + np.array([0, -46]),
                    f"{self.lives}" if not self.use_cjk else f"剩 {self.lives} 命",
                    CONFIG["C_PLAYER"])

    def _on_stage_fail(self) -> None:
        self.stage_complete_flash = 0.5
        self._burst(self.player_pos, CONFIG["C_THREAT"], 24, 300)
        self._start_fade()
        self._setup_game()

    def _open_esc(self) -> None:
        if self.mode == "MENU":
            self.esc_open = True
            self.esc_page = "ROOT"
            self.esc_sel = 2
            self.esc_sub_sel = 0
            self._set_cand = -1
            self._set_dwell = 0.0
            self.c_hold_frames = 0
            self.c_hold2_frames = 0
            self.esc_anim.set_target(1.0, 0.18, ease_out_cubic)
        elif not self.game_over:
            self.esc_open = True
            self.esc_page = "ROOT"
            self.esc_sel = 0
            self.esc_sub_sel = 0
            self._set_cand = -1
            self._set_dwell = 0.0
            self.paused = False
            self.c_hold_frames = 0
            self.c_hold2_frames = 0
            self.esc_anim.set_target(1.0, 0.18, ease_out_cubic)
        else:
            self._back_to_menu()

    def _esc_back(self) -> None:
        self.c_hold_frames = 0
        self.c_hold2_frames = 0
        if self.esc_page == "ROOT":
            self.esc_anim.set_target(0.0, 0.12, ease_out_cubic)
        elif self.esc_page in ("MECHANICS", "SETTINGS"):
            self.esc_page = "ROOT"
            self.esc_sel = 0
            self._set_sel(0)
        elif self.esc_page == "CLEAR_CONFIRM":
            self.esc_page = "SETTINGS"
            self._set_sel(0)

    def _esc_root_options(self) -> List[Tuple[str, str]]:
        if self.mode == "MENU":
            return [
                (self.S["mech"], "mech"),
                (self.S["settings"], "settings"),
                (self.S["close_menu"], "close"),
                (self.S["quit_game"], "quit"),
            ]
        else:
            return [
                (self.S["continue"], "resume"),
                (self.S["restart_run"] if self.mode == "RUN" else self.S["restart_stage"], "restart"),
                (self.S["mech"], "mech"),
                (self.S["settings"], "settings"),
                (self.S["exit_run"], "menu"),
            ]

    def _esc_confirm_root(self) -> None:
        opts = self._esc_root_options()
        if self.esc_sel >= len(opts): return
        _, action = opts[self.esc_sel]
        if action == "close":
            self.esc_anim.set_target(0.0, 0.12, ease_out_cubic)
        elif action == "resume":
            self.esc_anim.set_target(0.0, 0.12, ease_out_cubic)
        elif action == "restart":
            if self.mode == "RUN" and not self._finalized:
                self._finalize_run()
            self.esc_open = False
            self.esc_anim.snap(0.0)
            self._start_fade()
            self._setup_game()
        elif action == "mech":
            self.esc_page = "MECHANICS"
            self.esc_sel = 0
            self.esc_mech_tab = 0
            self.esc_mech_scroll = 0.0
            self.esc_mech_fade = CONFIG["MECH_TAB_FADE"]
        elif action == "settings":
            self.esc_page = "SETTINGS"
            self._set_sel(0)
        elif action == "menu":
            self._back_to_menu()
        elif action == "quit":
            self._quit_program()

    def _settings_count(self) -> int:
        return len(self._esc_settings_rects())

    def _settings_specs(self) -> List[Tuple[str, str, int, int, bool]]:
        rs_vals = [float(x) for x in (CONFIG.get("RENDER_SCALE_LEVELS")
                                      or [0.75, 1.0, 1.25, 1.5, 2.0])]
        cur_rs = float(CONFIG.get("RENDER_SCALE_PRESET", 1.0) or 1.0)
        try:
            ridx = min(range(len(rs_vals)), key=lambda i: abs(rs_vals[i] - cur_rs))
        except ValueError:
            ridx = 1
        names = self.S["rs_names"]
        aidx = int(getattr(self, "rs_idx", ridx))
        auto = self._rs_auto_on()
        shown = aidx if auto else ridx
        n_act = names[min(shown, len(names) - 1)]
        n_tgt = names[min(ridx, len(names) - 1)]
        res = f"({int(self.cw)}x{int(self.ch)})"
        act = float(self.ssaa or 1.0)
        narrow = float(CONFIG["WIDTH"]) < float(CONFIG.get("RS_NARROW_W", 1200))
        if auto and aidx != ridx:
            kt = "rs_target_s" if narrow else "rs_target"
            ka = "rs_actual_s" if narrow else "rs_actual"
            rs_txt = (f"{self.S[kt]} {n_tgt} \u00b7 {self.S[ka]} {n_act}")
        else:
            rs_txt = f"{n_act}"
        if not narrow:
            rs_txt += f" {res}"
        if not auto and abs(act - float(rs_vals[ridx])) > 0.01:
            rs_txt += " \u00b7 " + self.S["rs_capped"]
        px = self.cw * self.ch
        if not narrow:
            if px > 8_000_000:
                rs_txt += " \u00b7 " + self.S["rs_heavy"]
            elif px > 4_000_000:
                rs_txt += " \u00b7 " + self.S["rs_mid"]

        levels = [0.0, 0.5, 1.0]
        try:
            sidx = levels.index(round(self.shake_level, 1))
        except ValueError:
            sidx = 2
        size_names = [self.S["text_size_std"], self.S["text_size_large"]]
        tsidx = self._text_size_index()
        langs = ["en", "zh"]
        try:
            lidx = langs.index(self.lang)
        except ValueError:
            lidx = 0
        fs_txt = self.S["fs_on"] if self.fullscreen else self.S["fs_off"]
        res = f"{int(self.win_w)}x{int(self.win_h)}"
        return [
            (self.S["fullscreen_title"], f"{fs_txt}   \u00b7   {res}",
             1 if self.fullscreen else 0, 2, True),
            (self.S["render_scale_title"], rs_txt, ridx, len(rs_vals), True),
            (self.S["shake_title"],
             [self.S["shake_0"], self.S["shake_5"], self.S["shake_10"]][sidx],
             sidx, 3, True),
            (self.S["text_size_title"], size_names[tsidx], tsidx, 2, True),
            (self.S["auto_title"],
             self.S["auto_on"] if self._rs_auto_on() else self.S["auto_off"],
             1 if self._rs_auto_on() else 0, 2, True),
            (self.S["lang_title"],
             self.S["lang_zh"] if self.lang == "zh" else self.S["lang_en"],
             lidx, 2, bool(self.zh_available)),
        ]

    def _esc_set_tip_lines(self, i: int) -> List[str]:
        keys = CONFIG.get("SET_TIP_KEYS") or []
        try:
            k = keys[int(i)]
        except Exception:
            return []
        txt = self.S.get(k, "") if isinstance(self.S, dict) else ""
        if not txt:
            return []
        maxw = 600 - 2 * int(CONFIG["SET_PAD"])
        try:
            return self._wrap_text(txt, self.f_tiny, maxw)
        except Exception:
            return [txt]

    def _esc_set_tip_h(self, i: int) -> float:
        n = len(self._esc_set_tip_lines(i))
        if n <= 0:
            return 0.0
        return float(int(CONFIG["SET_TIP_PAD"]) + n * int(CONFIG["SET_TIP_LH"]))

    def _esc_settings_geom_row(self, i: int) -> Tuple[int, int, int, int, int, int, int]:
        r = self._esc_settings_rects()[i]
        aw = max(15, min(int(CONFIG["SET_ARROW_W"]), r[3] - int(CONFIG["SET_ARROW_INSET"])))
        ag = int(CONFIG["SET_ARROW_GAP"])
        vw = max(70, min(int(r[2] * float(CONFIG["SET_VALUE_W"])), int(CONFIG["SET_VALUE_MAX"])))
        return r[0], r[1], r[2], r[3], aw, ag, vw

    def _esc_settings_arrows(self, i: int) -> Tuple[Optional[Tuple[int,int,int,int]],
                                                    Optional[Tuple[int,int,int,int]]]:
        specs = self._settings_specs()
        rects = self._esc_settings_rects()
        if i < 0 or i >= len(specs) or i >= len(rects):
            return (None, None)
        if not specs[i][4]:
            return (None, None)
        _rx, _ry, _rw, _rh, aw, ag, vw = self._esc_settings_geom_row(i)
        cx = self._esc_settings_cluster_x(i, aw, ag, vw)
        cy = rects[i][1] + (rects[i][3] - aw) // 2
        return ((cx, cy, aw, aw), (cx + aw + ag + vw + ag, cy, aw, aw))

    def _esc_settings_cluster_x(self, i: int, aw: int, ag: int, vw: int) -> int:
        r = self._esc_settings_rects()[i]
        pad = int(CONFIG["SET_PAD"])
        return r[0] + r[2] - pad - (aw * 2 + ag * 2 + vw)

    def _draw_step_arrow(self, rect, direction: int, enabled: bool,
                         hovered: bool, a: float, y_off: int) -> None:
        x, y, w, h = rect[0], rect[1] + y_off, rect[2], rect[3]
        xf, yf, wf, hf = float(x), float(y), float(w), float(h)
        if enabled and hovered:
            pygame.draw.rect(self.screen, CONFIG["G_40"],
                             (xf - 1.0, yf - 1.0, wf + 2.0, hf + 2.0))
        cx = xf + wf * 0.5
        cy = yf + hf * 0.5
        hw = wf * 0.19
        hh = hf * 0.28
        tip = hw * 1.15
        if direction < 0:
            pts = [(cx + hw, cy - hh), (cx + hw, cy + hh), (cx - tip, cy)]
        else:
            pts = [(cx - hw, cy - hh), (cx - hw, cy + hh), (cx + tip, cy)]
        base = (CONFIG["C_PLAYER"] if (enabled and hovered)
                else (CONFIG["G_80"] if enabled else CONFIG["G_60"]))
        col = (int(base[0] * a), int(base[1] * a), int(base[2] * a))
        pygame.draw.polygon(self.screen, col, pts, 0)
        if _AA_OK:
            pygame.draw.aaline(self.screen, col, pts[0], pts[1], 1)
            pygame.draw.aaline(self.screen, col, pts[1], pts[2], 1)
            pygame.draw.aaline(self.screen, col, pts[2], pts[0], 1)

    def _settings_arrow_at(self, pos, i: int) -> int:
        l, rr = self._esc_settings_arrows(i)
        pad = int(CONFIG["SET_HIT_PAD"])
        for side, rect in ((0, l), (1, rr)):
            if rect is None:
                continue
            x, y, w, h = rect
            if (x - pad <= pos[0] <= x + w + pad and y - pad <= pos[1] <= y + h + pad):
                return side
        return -1

    def _settings_adjust(self, idx: int, delta: int) -> None:
        specs = self._settings_specs()
        if idx < 0 or idx >= len(specs):
            return
        _t, _v, cur, count, adjustable = specs[idx]
        if not adjustable or count <= 1:
            return
        new = max(0, min(count - 1, cur + delta))
        if new == cur:
            return
        if idx == 0:
            self._apply_fullscreen(not self.fullscreen)
        elif idx == 1:
            levels = [float(x) for x in (CONFIG.get("RENDER_SCALE_LEVELS")
                                         or [0.75, 1.0, 1.25, 1.5, 2.0])]
            CONFIG["RENDER_SCALE_PRESET"] = levels[new]
            self.save_data["render_scale"] = float(levels[new])
            self._rs_sync_idx()
            self._rs_reset_adapt()
            self._apply_render_scale()
            self._write_save()
        elif idx == 2:
            self.shake_level = [0.0, 0.5, 1.0][new]
        elif idx == 3:
            self._apply_text_size(new)
            self.save_data["text_size"] = int(max(0, new))
            self.save_data["body_size"] = int(self.body_size)
            self._rebuild_fonts()
            try:
                self._mech_wrap_cache.clear()
            except Exception:
                pass
            self._write_save()
        elif idx == 4:
            CONFIG["RENDER_SCALE_AUTO"] = bool(new)
            self.save_data["render_auto"] = bool(new)
            self._rs_reset_adapt()
            self._rs_sync_idx()
            self._apply_render_scale()
            self._write_save()
        elif idx == 5:
            new_lang = ["en", "zh"][new]
            if new_lang != self.lang:
                self._apply_lang(new_lang)
                self._write_save()

    def _settings_confirm(self) -> None:
        last = len(self._esc_settings_rects()) - 1
        if self.esc_sub_sel == 0:
            self._apply_fullscreen(not self.fullscreen)
        elif self.esc_sub_sel == last:
            self.esc_page = "ROOT"
            self.esc_sel = 0
            self._set_sel(0)
            self.c_hold_frames = 0

    def _on_esc_key(self, e) -> None:
        if self.esc_page == "ROOT":
            n = len(self._esc_root_options())
            if e.key == pygame.K_UP:
                self.esc_sel = (self.esc_sel - 1) % n
            elif e.key == pygame.K_DOWN:
                self.esc_sel = (self.esc_sel + 1) % n
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._esc_confirm_root()
        elif self.esc_page == "SETTINGS":
            n = self._settings_count()
            if e.key == pygame.K_UP:
                self._set_sel((self.esc_sub_sel - 1) % n)
                self.c_hold_frames = 0
            elif e.key == pygame.K_DOWN:
                self._set_sel((self.esc_sub_sel + 1) % n)
                self.c_hold_frames = 0
            elif e.key == pygame.K_LEFT:
                self._settings_adjust(self.esc_sub_sel, -1)
            elif e.key == pygame.K_RIGHT:
                self._settings_adjust(self.esc_sub_sel, 1)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._settings_confirm()
        elif self.esc_page == "MECHANICS":
            tabs = len(self.S["mech_tabs"])
            if e.key == pygame.K_UP:
                self.esc_mech_tab = (self.esc_mech_tab - 1) % tabs
                self.esc_mech_scroll = 0.0
                self.esc_mech_fade = CONFIG["MECH_TAB_FADE"]
            elif e.key == pygame.K_DOWN:
                self.esc_mech_tab = (self.esc_mech_tab + 1) % tabs
                self.esc_mech_scroll = 0.0
                self.esc_mech_fade = CONFIG["MECH_TAB_FADE"]

    def _on_esc_click(self, pos) -> None:
        if self.esc_page == "ROOT":
            rects = self._esc_root_rects()
            for i, r in enumerate(rects):
                if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                    self.esc_sel = i
                    self._esc_confirm_root()
                    return
        elif self.esc_page == "SETTINGS":
            rects = self._esc_settings_rects()
            last = len(rects) - 1
            cur = int(getattr(self, "esc_sub_sel", -1))
            if 0 <= cur < len(rects):
                r = rects[cur]
                if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]+self._esc_set_tip_h(cur)*self._set_exp(cur):
                    if pos[1] > r[1] + r[3]:
                        return
                    self._set_sel(cur)
                    side = self._settings_arrow_at(pos, cur)
                    if side >= 0:
                        self._settings_adjust(cur, -1 if side == 0 else 1)
                        return
                    if cur == 0 or cur == last:
                        self._settings_confirm()
                    return
            for i, r in enumerate(rects):
                if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                    self._set_sel(i)
                    side = self._settings_arrow_at(pos, i)
                    if side >= 0:
                        self._settings_adjust(i, -1 if side == 0 else 1)
                        return
                    if i == 0 or i == last:
                        self._settings_confirm()
                    return
        elif self.esc_page == "MECHANICS":
            for i, r in enumerate(self._esc_mech_tab_rects()):
                if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                    if self.esc_mech_tab != i:
                        self.esc_mech_tab = i
                        self.esc_mech_scroll = 0.0
                        self.esc_mech_fade = CONFIG["MECH_TAB_FADE"]
                    return

    def _sync_esc_hover(self, pos) -> None:
        if self.esc_page == "ROOT":
            rects = self._esc_root_rects()
            for i, r in enumerate(rects):
                if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                    self.esc_sel = i; return
        elif self.esc_page == "SETTINGS":
            rects = self._esc_settings_rects()
            self.esc_set_arrow_hover = None
            self._set_cand = -1
            cur = int(getattr(self, "esc_sub_sel", -1))
            if 0 <= cur < len(rects):
                r = rects[cur]
                hh = r[3] + self._esc_set_tip_h(cur) * self._set_exp(cur)
                if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+hh:
                    self._set_cand = cur
                    side = self._settings_arrow_at(pos, cur)
                    if side >= 0:
                        self.esc_set_arrow_hover = (cur, side)
                    return
            for i, r in enumerate(rects):
                if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                    self._set_cand = i
                    if self.esc_sub_sel != i:
                        self.c_hold_frames = 0
                    side = self._settings_arrow_at(pos, i)
                    if side >= 0:
                        self.esc_set_arrow_hover = (i, side)
                    return

    def _esc_root_rects(self) -> List[Tuple[int,int,int,int]]:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        opts = self._esc_root_options()
        n = len(opts)
        cx = W // 2
        gap = 50
        extra = CONFIG["ESC_ROOT_EXIT_GAP"]
        block = (n - 1) * gap + 42 + extra
        start_y = H // 2 - block // 2
        out = [(cx - 200, start_y + i * gap, 400, 42) for i in range(n - 1)]
        out.append((cx - 200, start_y + (n - 1) * gap + extra, 400, 42))
        return out

    def _esc_has_clear(self) -> bool:
        return self.mode == "MENU"

    def _esc_settings_geom(self):
        H = CONFIG["HEIGHT"]
        n = 8 if self._esc_has_clear() else 7
        top = 172
        bottom_limit = H - 62
        avail = max(120, bottom_limit - top)
        gap = 10
        back_gap = 14
        row_h = min(48, max(30, (avail - back_gap - (n - 1) * gap) // n))
        total = n * row_h + (n - 1) * gap + back_gap
        start_y = int(top + max(0, (avail - total) // 2))
        return n, start_y, row_h, gap, back_gap

    def _esc_settings_rects(self, settled: bool = False) -> List[Tuple[int,int,int,int]]:
        W = CONFIG["WIDTH"]
        cx = W // 2
        n, start_y, row_h, gap, back_gap = self._esc_settings_geom()
        nrows = n - 1
        bh = min(row_h, 42)
        sel = int(getattr(self, "esc_sub_sel", -1))
        if settled:
            exps = [self._esc_set_tip_h(i) if i == sel else 0.0
                    for i in range(nrows)]
        else:
            exps = [self._esc_set_tip_h(i) * self._set_exp(i)
                    for i in range(nrows)]
        ys = []
        acc = 0.0
        for i in range(nrows):
            ys.append(float(start_y) + i * (row_h + gap) + acc)
            acc += exps[i]
        tail = exps[nrows - 1] if nrows > 0 else 0.0
        by = (ys[-1] + row_h + tail + gap + back_gap) if ys else float(start_y)
        shift = min(max(0.0, (by + bh) - float(CONFIG["HEIGHT"] - 62)),
                    max(0.0, float(start_y) - 158.0))
        out = [(cx - 300, int(round(y - shift)), 600, row_h) for y in ys]
        out.append((cx - 200, int(round(by - shift)), 400, bh))
        return out

    def _esc_mech_tab_rects(self) -> List[Tuple[int,int,int,int]]:
        tabs = self.S["mech_tabs"]
        n = len(tabs)
        x = 80
        y0 = 160
        return [(x, y0 + i * 56, 200, 44) for i in range(n)]

    def _mech_ctrl_geom(self):
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        cx0 = 360
        cw = W - cx0 - 60
        cy0 = 150
        row_h = 40
        gap = 6
        bottom = H - 150
        return cx0, cw, cy0, row_h, gap, bottom

    def _mech_ctrl_rects(self) -> List[Tuple[int,int,int,int]]:
        cx0, cw, cy0, row_h, gap, _b = self._mech_ctrl_geom()
        n = len(self.S["ctrl_rows"])
        return [(cx0, cy0 + i * (row_h + gap), cw, row_h) for i in range(n)]

    def _update_esc_hover(self) -> None:
        if not self.esc_open or self.esc_page != "MECHANICS" or self.esc_mech_tab != 1:
            self.esc_ctrl_hover = -1
            return
        mx, my = self.mouse_pos()
        cy = my + self.esc_mech_scroll
        self.esc_ctrl_hover = -1
        for i, r in enumerate(self._mech_ctrl_rects()):
            if r[0] <= mx <= r[0]+r[2] and r[1] <= cy <= r[1]+r[3]:
                self.esc_ctrl_hover = -1 if self._ctrl_row_locked(i) else i
                return

    def _draw_mech_controls(self, cx0: int, cw: int, H: int, a: float, y_off: int) -> None:
        rows = self.S["ctrl_rows"]
        rects = self._mech_ctrl_rects()
        hov = self.esc_ctrl_hover
        btn_w = 150
        scr = int(self.esc_mech_scroll)
        _cx, _cw, _cy0, _rh, _g, bottom = self._mech_ctrl_geom()
        for i, (key, word, _desc) in enumerate(rows):
            r = rects[i]
            ry = r[1] - scr + y_off
            if ry + r[3] > bottom + y_off or ry < 140 + y_off:
                continue
            active = (i == hov)
            locked = self._ctrl_row_locked(i)
            if locked:
                lk = max(11.0, r[3] * 0.42)
                self._draw_padlock(r[0] + 18, ry + (r[3] - lk * 1.32) / 2, lk,
                                   CONFIG["G_40"], a)
                req = CTRL_STAGE_REQ[i] if i < len(CTRL_STAGE_REQ) else 1
                lt = self.f_body.render(self._mech_lock_text(req), True,
                                        CONFIG["G_40"])
                lt.set_alpha(int(255 * a))
                self.screen.blit(lt, (r[0] + 18 + int(lk * 1.6),
                                      ry + (r[3] - lt.get_height()) // 2))
                continue
            if active:
                pygame.draw.rect(self.screen, CONFIG["G_20"], (r[0], ry, r[2], r[3]))
            kc = CONFIG["C_PLAYER"] if active else CONFIG["G_80"]
            ks = self.f_body.render(key, True, kc)
            ks.set_alpha(int(255 * a))
            self.screen.blit(ks, (r[0] + 18, ry + (r[3] - ks.get_height()) // 2))
            br = (r[0] + r[2] - btn_w - 4, ry + 5, btn_w, r[3] - 10)
            pygame.draw.rect(self.screen, CONFIG["G_20"], br)
            bc = CONFIG["C_PLAYER"] if active else CONFIG["G_40"]
            pygame.draw.rect(self.screen, bc, br, 2 if active else 1)
            ws = self.f_med.render(word, True, kc)
            ws.set_alpha(int(255 * a))
            self.screen.blit(ws, ws.get_rect(center=(br[0] + br[2] // 2, br[1] + br[3] // 2)))
        if 0 <= hov < len(rows):
            dy = bottom + 16 + y_off
            pygame.draw.line(self.screen, CONFIG["G_20"], (cx0, dy - 12), (cx0 + cw, dy - 12))
            for line in self._wrap_text(rows[hov][2], self.f_body, cw)[:3]:
                s = self.f_body.render(line, True, CONFIG["G_60"])
                s.set_alpha(int(255 * a))
                self.screen.blit(s, (cx0, dy))
                dy += CONFIG["BODY_LINE_H"]

    def handle_events(self) -> None:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self._quit_program()

            if e.type == pygame.VIDEORESIZE:
                self._queue_resize(e.w, e.h)
                continue

            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_F11, pygame.K_f) and (pygame.key.get_mods() & pygame.KMOD_ALT or e.key == pygame.K_F11):
                    self._apply_fullscreen(not self.fullscreen)
                    continue
                if self.ms_open:
                    self._on_ms_key(e)
                    continue
                if self.appear_open and self.gallery_open:
                    self._on_gallery_key(e)
                elif self.appear_open:
                    self._on_appear_key(e)
                elif e.key == pygame.K_ESCAPE:
                    if self.esc_open:
                        if self.esc_anim.target < 0.5:
                            self.esc_anim.set_target(1.0, 0.18, ease_out_cubic)
                        else:
                            self._esc_back()
                    else:
                        self._open_esc()
                elif self.esc_open:
                    self._on_esc_key(e)
                elif e.key == pygame.K_p:
                    if self.mode in ("TRAINING", "RUN") and not self.game_over:
                        self.paused = not self.paused
                        if self.paused: self.pause_sel = 0
                elif self.paused:
                    self._on_pause_key(e)
                elif self.mode == "MENU":
                    self._on_menu_key(e)
                elif self.game_over:
                    self._on_gameover_key(e)
                else:
                    self._on_play_key(e)

            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.ms_open and e.button in (4, 5):
                    self.ms_scroll += (46 if e.button == 5 else -46)
                    self._ms_clamp_scroll()
                    continue
                if e.button == 1:
                    if self.ms_open:
                        self._on_ms_click(*self.ev_pos(e.pos))
                    elif self.appear_open and self.gallery_open:
                        self._on_gallery_click(*self.ev_pos(e.pos))
                    elif self.appear_open:
                        self._on_appear_click(*self.ev_pos(e.pos))
                    elif self.esc_open:
                        self._on_esc_click(self.ev_pos(e.pos))
                    elif self.paused:
                        self._on_pause_click(self.ev_pos(e.pos))
                    elif self.mode == "MENU":
                        self._on_menu_click(self.ev_pos(e.pos))
                    elif self.game_over:
                        self._on_gameover_click(self.ev_pos(e.pos))
                    else:
                        if not self.try_dash():
                            self.buf_dash = CONFIG["INPUT_BUFFER_FRAMES"]
                elif e.button == 4 and self.esc_open and self.esc_page == "MECHANICS":
                    self.esc_mech_scroll = max(0.0, self.esc_mech_scroll - 40)
                elif e.button == 5 and self.esc_open and self.esc_page == "MECHANICS":
                    self.esc_mech_scroll = min(self.esc_mech_max_scroll, self.esc_mech_scroll + 40)

            if e.type == pygame.MOUSEMOTION:
                if self.ms_open:
                    self._sync_ms_hover(self.ev_pos(e.pos))
                elif self.esc_open:
                    self._sync_esc_hover(self.ev_pos(e.pos))
                elif self.paused:
                    self._sync_pause_hover(self.ev_pos(e.pos))
                elif self.mode == "MENU":
                    self._sync_menu_hover(self.ev_pos(e.pos))
                elif self.game_over:
                    self._sync_gameover_hover(self.ev_pos(e.pos))

    def _on_play_key(self, e) -> None:
        if e.key == pygame.K_SPACE:
            if not self.try_dash(): self.buf_dash = CONFIG["INPUT_BUFFER_FRAMES"]
        elif e.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            if not self.try_swap(): self.buf_swap = CONFIG["INPUT_BUFFER_FRAMES"]
        elif e.key == pygame.K_r:
            self._start_fade()
            self._setup_game()
        elif e.key == pygame.K_TAB:
            self.practice_mode = not self.practice_mode

    def _gameover_options_rects(self) -> List[Tuple[int, int, int, int]]:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        bw, bh, gap = 200, 52, 20
        total = bw * 2 + gap
        x0 = int(W / 2 - total / 2)
        y = int(H / 2 + 128)
        return [(x0, y, bw, bh), (x0 + bw + gap, y, bw, bh)]

    def _sync_gameover_hover(self, pos) -> None:
        for i, r in enumerate(self._gameover_options_rects()):
            if r[0] <= pos[0] <= r[0] + r[2] and r[1] <= pos[1] <= r[1] + r[3]:
                if self.gameover_sel != i:
                    self.gameover_sel = i
                    self.gameover_sel_x.set_target(
                        float(self._gameover_options_rects()[i][0]),
                        CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
                return

    def _gameover_confirm(self) -> None:
        self.gameover_anim.snap(0.0)
        if self.gameover_sel == 0:
            self._start_fade()
            self._setup_game()
        else:
            self._back_to_menu()

    def _on_gameover_click(self, pos) -> None:
        for i, r in enumerate(self._gameover_options_rects()):
            if r[0] <= pos[0] <= r[0] + r[2] and r[1] <= pos[1] <= r[1] + r[3]:
                self.gameover_sel = i
                self.gameover_sel_x.set_target(float(r[0]),
                                               CONFIG["UI_TWEEN_FAST"], ease_out_cubic)
                self._gameover_confirm()
                return

    def _on_gameover_key(self, e) -> None:
        if e.key == pygame.K_r:
            self.gameover_anim.snap(0.0)
            self._start_fade()
            self._setup_game()
        elif e.key in (pygame.K_LEFT, pygame.K_UP):
            self.gameover_sel = (self.gameover_sel - 1) % 2
            self.gameover_sel_x.set_target(
                float(self._gameover_options_rects()[self.gameover_sel][0]),
                CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
        elif e.key in (pygame.K_RIGHT, pygame.K_DOWN):
            self.gameover_sel = (self.gameover_sel + 1) % 2
            self.gameover_sel_x.set_target(
                float(self._gameover_options_rects()[self.gameover_sel][0]),
                CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
        elif e.key in (pygame.K_1, pygame.K_KP1):
            self.gameover_sel = 0; self._gameover_confirm()
        elif e.key in (pygame.K_2, pygame.K_KP2):
            self.gameover_sel = 1; self._gameover_confirm()
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._gameover_confirm()

    def _on_pause_key(self, e) -> None:
        if e.key == pygame.K_UP:
            self.pause_sel = (self.pause_sel - 1) % 3
        elif e.key == pygame.K_DOWN:
            self.pause_sel = (self.pause_sel + 1) % 3
        elif e.key in (pygame.K_1, pygame.K_KP1):
            self.pause_sel = 0; self._pause_confirm()
        elif e.key in (pygame.K_2, pygame.K_KP2):
            self.pause_sel = 1; self._pause_confirm()
        elif e.key in (pygame.K_3, pygame.K_KP3):
            self.pause_sel = 2; self._pause_confirm()
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._pause_confirm()

    def _pause_confirm(self) -> None:
        if self.pause_sel == 0:
            self.paused = False
        elif self.pause_sel == 1:
            if self.mode == "RUN" and not self._finalized:
                self._finalize_run()
            self.paused = False
            self._start_fade()
            self._setup_game()
        elif self.pause_sel == 2:
            self._back_to_menu()

    def _pause_options_rects(self) -> List[Tuple[int, int, int, int]]:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        cx = W // 2
        cy = H - 110
        return [(cx - 340 + i * 230, cy, 210, 34) for i in range(3)]

    def _on_pause_click(self, pos) -> None:
        for i, r in enumerate(self._pause_options_rects()):
            if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                self.pause_sel = i
                self._pause_confirm()
                return

    def _sync_pause_hover(self, pos) -> None:
        for i, r in enumerate(self._pause_options_rects()):
            if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                self.pause_sel = i
                return

    def _menu_sel_target_y(self) -> float:
        return float(self._menu_options_rects()[self.menu_sel][1])

    def _on_menu_key(self, e) -> None:
        if e.key == pygame.K_UP:
            self.menu_sel = (self.menu_sel - 1) % 4
            self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                       CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
        elif e.key == pygame.K_DOWN:
            self.menu_sel = (self.menu_sel + 1) % 4
            self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                       CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
        elif e.key == pygame.K_LEFT and self.menu_sel == 0:
            self.menu_stage = max(1, self.menu_stage - 1)
        elif e.key == pygame.K_RIGHT and self.menu_sel == 0:
            unlocked = int(self.save_data["training_unlocked_stage"])
            self.menu_stage = min(unlocked, self.menu_stage + 1)
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._menu_confirm()
        elif e.key in (pygame.K_1, pygame.K_KP1):
            self.menu_sel = 0
            self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                       CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
            self._menu_confirm()
        elif e.key in (pygame.K_2, pygame.K_KP2):
            self.menu_sel = 1
            self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                       CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
            self._menu_confirm()
        elif e.key in (pygame.K_3, pygame.K_KP3):
            self.menu_sel = 2
            self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                       CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
            self._menu_confirm()
        elif e.key in (pygame.K_4, pygame.K_KP4):
            self.menu_sel = 3
            self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                       CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
            self._menu_confirm()

    def _menu_confirm(self) -> None:
        if self.menu_sel == 0:
            self.mode = "TRAINING"
            self.stage = self.menu_stage
            self._start_fade()
            self._setup_game()
        elif self.menu_sel == 1:
            if bool(self.save_data.get("training_done", False)):
                self.mode = "RUN"
                self._start_fade()
                self._setup_game()
        elif self.menu_sel == 2:
            self.ms_open = True
            self.ms_scroll = 0.0
            self.ms_sel = -1
            self._ms_cand = -1
            self._ms_dwell = 0.0
            self._check_milestones()
        elif self.menu_sel == 3:
            self.appear_open = True
            self.appear_sel = 0

    def _menu_row_metrics(self) -> Tuple[int, int]:
        try:
            lh = float(self.f_menu.render("训", True, CONFIG["G_80"]).get_height())
        except Exception:
            lh = 35.0
        return int(round(lh + 20)), int(CONFIG["MENU_ROW_GAP"])

    def _menu_block_offset(self) -> float:
        row_h, gap = self._menu_row_metrics()
        rows_h = row_h * 4 + gap * 3
        origin = float(CONFIG["MENU_BLOCK_ORIGIN"])
        block_h = (float(CONFIG["MENU_ROW_Y0"]) + rows_h + 95.0) - origin
        H = CONFIG["HEIGHT"]
        free = H - float(CONFIG["MENU_BOTTOM_RESERVE"])
        top = (H - block_h) / 2.0
        lo = float(CONFIG["MENU_BLOCK_TOP_MIN"])
        hi = max(lo, free - block_h)
        return max(lo, min(top, hi)) - origin

    def _menu_options_rects(self) -> List[Tuple[int, int, int, int]]:
        row_h, gap = self._menu_row_metrics()
        W = CONFIG["WIDTH"]
        y0 = int(round(CONFIG["MENU_ROW_Y0"] + self._menu_block_offset()))
        w = int(min(CONFIG["MENU_ROW_W"], W * CONFIG["MENU_ROW_W_MAXF"]))
        return [(W // 2 - w // 2, y0 + i * (row_h + gap), w, row_h)
                for i in range(4)]

    def _measure_w(self, font, text: str) -> int:
        cache = self._cache("_txt_w_cache")
        key = (id(font), text)
        v = cache.get(key)
        if v is None:
            v = font.render(text, True, (255, 255, 255)).get_width()
            cache[key] = v
        return v

    def _menu_arrow_geom(self) -> Tuple[int, int, int, int]:
        r = self._menu_options_rects()[0]
        aw = max(12, min(int(CONFIG["MENU_ARROW_W"]), r[3] - 8))
        ag = int(CONFIG["MENU_ARROW_GAP"])
        probe = f"{self.S['stage']} 5/5  \u00b7  S"
        vw = int(max(60, self._measure_w(self.f_med, probe) + 8))
        return aw, ag, vw, r[1] + (r[3] - aw) // 2

    def _menu_arrows(self) -> Tuple[Tuple[int, int, int, int],
                                    Tuple[int, int, int, int], int, int]:
        r = self._menu_options_rects()[0]
        aw, ag, vw, cy = self._menu_arrow_geom()
        total = aw * 2 + ag * 2 + vw
        cx = int(round(r[0] + r[2] - int(CONFIG["MENU_ARROW_PAD"]) - total))
        left = (cx, cy, aw, aw)
        right = (cx + aw + ag + vw + ag, cy, aw, aw)
        return left, right, cx + aw + ag, vw

    def _menu_arrow_at(self, pos) -> int:
        l, rr, _vx, _vw = self._menu_arrows()
        pad = int(CONFIG["MENU_ARROW_HIT_PAD"])
        for side, rect in ((0, l), (1, rr)):
            x, y, w, h = rect
            if (x - pad <= pos[0] <= x + w + pad
                    and y - pad <= pos[1] <= y + h + pad):
                return side
        return -1

    def _menu_stage_step(self, d: int) -> None:
        unlocked = max(1, int(self.save_data["training_unlocked_stage"]))
        new = max(1, min(unlocked, self.menu_stage + d))
        if new == self.menu_stage:
            return
        self.menu_stage = new
        self.menu_sel = 0
        self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                   CONFIG["UI_TWEEN_NORMAL"], ease_out_back)

    def _draw_chevron(self, rect, a: float, y_off: int = 0) -> None:
        x, y, w, h = rect[0], rect[1] + y_off, rect[2], rect[3]
        cx = float(x) + float(w) * 0.5
        cy = float(y) + float(h) * 0.5
        hw = float(w) * 0.17
        hh = float(h) * 0.26
        base = CONFIG["G_60"]
        col = (int(base[0] * a), int(base[1] * a), int(base[2] * a))
        pts = [(cx - hw, cy - hh), (cx + hw, cy), (cx - hw, cy + hh)]
        pygame.draw.lines(self.screen, col, False, pts, 2)

    def _sync_menu_hover(self, pos) -> None:
        for i, r in enumerate(self._menu_options_rects()):
            if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                if self.menu_sel != i:
                    self.menu_sel = i
                    self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                               CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
                return

    def _on_menu_click(self, pos) -> None:
        side = self._menu_arrow_at(pos)
        if side >= 0:
            self._menu_stage_step(-1 if side == 0 else 1)
            return
        for i, r in enumerate(self._menu_options_rects()):
            if r[0] <= pos[0] <= r[0]+r[2] and r[1] <= pos[1] <= r[1]+r[3]:
                if i == 0:
                    self.menu_sel = 0
                    self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                               CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
                    self._menu_confirm()
                else:
                    self.menu_sel = i
                    self.menu_sel_y.set_target(self._menu_sel_target_y(),
                                               CONFIG["UI_TWEEN_NORMAL"], ease_out_back)
                    self._menu_confirm()
                return

    def update(self, dt: float) -> None:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        self.frame += 1
        self._tick_fade(dt)
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)

        if self.appear_open:
            self.anim_t = (self.anim_t + dt) % 3600.0
            return

        if self.mode == "MENU":
            self.anim_t = (self.anim_t + dt) % 3600.0
            return
        if self.paused or self.esc_open:
            return

        if self.hitstop_frames > 0:
            self.hitstop_frames -= 1
            return

        if self.trauma > 0:
            self.trauma = max(0.0, self.trauma - CONFIG["SHAKE_DECAY"] * dt)

        if self.stage_complete_timer > 0:
            self.stage_complete_timer -= dt
            for p in self.particles:
                p["pos"] = p["pos"] + p["vel"] * dt
                p["vel"] = p["vel"] * (1.0 - 3.0 * dt); p["life"] -= dt
            self.particles = [p for p in self.particles if p["life"] > 0]
            for r in self.rings: r["life"] -= dt
            self.rings = [r for r in self.rings if r["life"] > 0]
            for sl in self.slashes: sl["life"] -= dt
            self.slashes = [sl for sl in self.slashes if sl["life"] > 0]
            if self.stage_complete_timer <= 0:
                if self.mode == "TRAINING":
                    self.stage += 1
                    if self.stage > 5:
                        self.mode = "MENU"
                        self.menu_sel = 0
                        self.menu_stage = int(self.save_data["training_unlocked_stage"])
                    else:
                        self._start_fade()
                        self._setup_game()
            return

        if self.hint_timer > 0: self.hint_timer -= dt
        if self.wave_flash > 0: self.wave_flash = max(0.0, self.wave_flash - dt * 0.7)

        if self.bullet_time_frames > 0:
            self.bullet_time_frames -= 1
            world_scale = CONFIG["PERFECT_WORLD_SCALE"]
        else:
            world_scale = 1.0

        if self.swap_cd_frames > 0: self.swap_cd_frames -= 1
        if self.no_energy_cd > 0: self.no_energy_cd -= 1
        if self.iframe_frames > 0: self.iframe_frames -= 1
        if self.chain_timer > 0:
            self.chain_timer -= 1
            if self.chain_timer == 0 and self.chain_count >= 3:
                self.chain_break_flash = 18
        if self.chain_break_flash > 0: self.chain_break_flash -= 1
        if self.invert_frames > 0: self.invert_frames -= 1
        if self.phase_grace_timer > 0:
            self.phase_grace_timer -= 1
            if self.phase_grace_timer <= 0:
                self.phase_grace_indices = set()

        if self.buf_dash > 0:
            self.buf_dash -= 1
            if self.buf_dash > 0 and self.try_dash(): self.buf_dash = 0
        if self.buf_swap > 0:
            self.buf_swap -= 1
            if self.buf_swap > 0 and self.try_swap(): self.buf_swap = 0

        alive = []
        for s in self.shadows:
            s["frames_left"] -= 1
            if s["frames_left"] > 0:
                s["pos"] = s["pos"] + s["drift_dir"] * CONFIG["SHADOW_DRIFT_SPEED"] * (1.0 / 60.0)
                alive.append(s)
        self.shadows = alive

        for i in range(len(self.ai_marks)):
            if self.ai_marks[i] > 0: self.ai_marks[i] -= 1
        for i in range(len(self.ai_trap_frames)):
            if self.ai_trap_frames[i] > 0: self.ai_trap_frames[i] -= 1
        for i in range(len(self.ai_exec_frames)):
            if self.ai_exec_frames[i] > 0: self.ai_exec_frames[i] -= 1
        for i in range(len(self.ai_flash_frames)):
            if self.ai_flash_frames[i] > 0: self.ai_flash_frames[i] -= 1

        self.player_prev_pos = self.player_pos.copy()

        self._update_aim()

        if self.player_state == "IDLE":
            self._player_idle(dt)
        elif self.player_state == "DASHING":
            self._player_dashing()
        elif self.player_state == "BACKSWING":
            self.state_frame += 1
            if self.state_frame >= CONFIG["CANCEL_WINDOW_FRAMES"]:
                self.player_state = "RECOVERY"; self.state_frame = 0
                if not self.did_cancel_this_backswing:
                    self.consecutive_cancels = 0
                    if self.mode == "TRAINING" and self.stage == 4:
                        self.stage_progress = 0
            self._player_drift()
        elif self.player_state == "RECOVERY":
            self.state_frame += 1
            if self.state_frame >= CONFIG["RECOVERY_FRAMES"]:
                self.player_state = "IDLE"; self.state_frame = 0
            self._player_drift()

        self.player_trail.append(self.player_pos.copy())
        maxlen = max(CONFIG["PLAYER_TRAIL_LEN"], int(self.pskin["tlen"]))
        if len(self.player_trail) > maxlen:
            self.player_trail.pop(0)

        if self.player_state == "DASHING" and self.frame % 2 == 0:
            self.afterimages.append({
                "pos": self.player_pos.copy(),
                "life": float(self.pskin["ai_life"]),
                "maxlife": float(self.pskin["ai_life"])})
        if (self.player_state == "DASHING" and self.fx_poem
                and self.pskin.get("poem") and self.frame % 4 == 0):
            self._spawn_poem(self.player_pos, 1)
        if (self.player_state == "DASHING" and self.fx_afterimage
                and self.pskin.get("poem") and self.frame % 3 == 0):
            self._spawn_sword_qi(self.dash_dir, 1)
        self._update_poem(dt)
        for im in self.afterimages:
            im["life"] -= dt
        if self.afterimages:
            self.afterimages = [im for im in self.afterimages if im["life"] > 0]
            cap = int(self.pskin["ai_n"]) * 6
            if len(self.afterimages) > cap:
                self.afterimages = self.afterimages[-cap:]
        for q in self.sword_qi:
            q["life"] -= dt
        if self.sword_qi:
            self.sword_qi = [q for q in self.sword_qi if q["life"] > 0]
            if len(self.sword_qi) > int(CONFIG["QI_CAP"]):
                self.sword_qi = self.sword_qi[-int(CONFIG["QI_CAP"]):]

        for s in self.slimes: s["age"] += dt
        self.slimes = [s for s in self.slimes if s["age"] < s["life"]]

        self.t += dt

        if self.mode == "TRAINING":
            if self.stage == 1:
                self.stage_progress = self.t
                self._check_stage_goal()
        else:
            new_wave = self._wave_of_time(self.t)
            if new_wave > self.wave:
                self.wave = new_wave
                self.wave_flash = 1.0
                self.wave_event = self._wave_event_of(self.wave)
                iv_new = self._spit_interval(self.wave)
                for sp in self.spitters:
                    sp["timer"] = min(float(sp["timer"]), iv_new)
                if self.wave_event:
                    self._popup(np.array([CONFIG["WIDTH"] / 2.0, CONFIG["HEIGHT"] * 0.28]),
                                ("精英波" if self.wave_event == "ELITE" else "休整波")
                                if self.use_cjk else
                                ("ELITE WAVE" if self.wave_event == "ELITE" else "SAFE WAVE"),
                                CONFIG["C_SPLIT"] if self.wave_event == "ELITE"
                                else CONFIG["C_MARK"])

            wc = self._wave_cfg(self.wave)
            want_sp = int(wc.get("spitter", 0))
            iv_now = self._spit_interval(self.wave)
            while len(self.spitters) < min(want_sp, CONFIG["SPITTER_MAX"]):
                placed = False
                for _ in range(40):
                    p = np.array([np.random.uniform(80, W - 80),
                                  np.random.uniform(80, H - 80)], dtype=np.float64)
                    if vlen(p - self.player_pos) < 260: continue
                    if all(vlen(p - sp["pos"]) > 200 for sp in self.spitters):
                        lo, hi = CONFIG["SPITTER_PHASE"]
                        self.spitters.append({"pos": p, "timer": iv_now * np.random.uniform(lo, hi)})
                        placed = True
                        break
                if not placed: break

            self.ai_spawn_timer -= dt
            total = len(self.ai_positions) + len(self.pending_spawns)
            cap = int(wc.get("max", CONFIG["AI_MAX_COUNT"]))
            if self.ai_spawn_timer <= 0 and total < cap:
                self.ai_spawn_timer = float(wc.get("spawn", CONFIG["AI_SPAWN_INTERVAL"]))
                n = int(wc.get("batch", 1))
                for k in range(min(n, cap - total)):
                    pos = self._pick_spawn_pos()
                    if k > 0:
                        a = np.random.uniform(0, 2 * np.pi)
                        pos = pos + np.array([math.cos(a), math.sin(a)]) * np.random.uniform(60, 140)
                        pos[0] = float(np.clip(pos[0], 44, W - 44))
                        pos[1] = float(np.clip(pos[1], 44, H - 44))
                    self.pending_spawns.append({"pos": pos,
                                                "type": int(self._roll_enemy_type()),
                                                "timer": CONFIG["WARN_TIME"],
                                                "total": CONFIG["WARN_TIME"]})

        still = []
        for sp in self.pending_spawns:
            sp["timer"] -= dt
            if sp["timer"] <= 0:
                _st = int(sp.get("type", 0))
                self.ai_positions.append(sp["pos"].copy())
                self.ai_velocities.append(np.zeros(2)); self.ai_trails.append([])
                self.ai_marks.append(0); self.ai_trap_frames.append(0)
                self.ai_types.append(_st)
                self.ai_stun_frames.append(0); self.ai_exec_frames.append(0)
                self.ai_flash_frames.append(0)
                self._burst(sp["pos"],
                            CONFIG["C_SPLIT"] if _st == 1 else CONFIG["C_THREAT"], 10, 200)
            else:
                still.append(sp)
        self.pending_spawns = still

        sim_dt = dt * world_scale
        if self.ai_positions:
            arr = np.stack(self.ai_positions)
            vel = np.stack(self.ai_velocities)
            N = len(arr)

            if self.mode == "TRAINING":
                speed = CONFIG["AI_BASE_SPEED"]
            else:
                cap = CONFIG["AI_MAX_SPEED"] + (self.wave - 1) * CONFIG["WAVE_AI_SPEED_ADD"]
                speed = min(CONFIG["AI_BASE_SPEED"] + self.t * CONFIG["AI_SPEED_RAMP"]
                            + (self.wave - 1) * CONFIG["WAVE_AI_SPEED_ADD"], cap)
                speed *= float(self._ms_load()["speed"])

            pred = self.player_pos + self.player_vel * CONFIG["AI_PREDICT"]
            to_p = pred - arr
            dist_arr = np.maximum(np.linalg.norm(to_p, axis=1, keepdims=True), 1e-3)
            desired = to_p / dist_arr * speed
            in_slime = self._in_slime_mask(arr)
            a_alpha = 1.0 - math.exp(-CONFIG["AI_SMOOTH"] * sim_dt)

            for i in range(N):
                if self.ai_stun_frames[i] > 0:
                    self.ai_stun_frames[i] -= 1
                    vel[i] = vel[i] * 0.88
                    continue
                trapped = False
                if self.ai_trap_frames[i] > 0:
                    trapped = True
                elif in_slime[i]:
                    self.ai_trap_frames[i] = CONFIG["SLIME_TRAP_FRAMES"]
                    trapped = True
                d = desired[i]
                if (self.ai_types[i] if i < len(self.ai_types) else 0) == 1:
                    d = d * float(CONFIG["SPLIT_SPEED_MUL"])
                if self.wave_event == "ELITE":
                    d = d * float(CONFIG["ELITE_SPEED_MUL"])
                if trapped: d = d * CONFIG["TRAP_SLOW"]
                vel[i] = vel[i] + (d - vel[i]) * a_alpha

            arr = arr + vel * sim_dt
            self.ai_positions = [arr[i] for i in range(N)]
            self.ai_velocities = [vel[i] for i in range(N)]
            for i in range(len(self.ai_trails)):
                self.ai_trails[i].append(arr[i].copy())
                if len(self.ai_trails[i]) > CONFIG["AI_TRAIL_LEN"]:
                    self.ai_trails[i].pop(0)

            if self.iframe_frames <= 0 and self._death_collision(arr):
                self._die("threat"); return

            d_player = np.linalg.norm(arr - self.player_pos, axis=1)
            killed = [i for i in range(len(self.ai_positions))
                      if (self.ai_trap_frames[i] > 0
                          or (self.ai_exec_frames[i] > 0
                              and self.ai_stun_frames[i] <= 0))
                      and d_player[i] < CONFIG["TRAP_KILL_DIST"]]
            for i in reversed(killed): self._kill_ai(i)

            if self.mode == "TRAINING":
                n_want = CONFIG["STAGE_ENEMIES"][self.stage - 1]
                while len(self.ai_positions) < n_want:
                    self._spawn_enemy_away()

        sp_interval = self._spit_interval(self.wave) if self.mode != "TRAINING" else CONFIG["SPITTER_INTERVAL"]
        sp_speed = self._spit_speed(self.wave) if self.mode != "TRAINING" else CONFIG["SPITTER_PROJ_SPEED"]
        for sp in self.spitters:
            sp["timer"] -= sim_dt
            if sp["timer"] <= 0:
                sp["timer"] = sp_interval
                d = self.player_pos - sp["pos"]
                dd = vlen(d)
                if dd > 1.0: d = d / dd
                self.projectiles.append({"pos": sp["pos"].copy(),
                                         "vel": d * sp_speed,
                                         "life": CONFIG["SPITTER_PROJ_LIFE"]})
                self._ring(sp["pos"], 40, CONFIG["C_SPITTER"], 2, 0.35)
                self._burst(sp["pos"], CONFIG["C_SPITTER"], 6, 150)

        alive_p = []
        for p in self.projectiles:
            p["pos"] = p["pos"] + p["vel"] * sim_dt
            p["life"] -= sim_dt
            if p["life"] <= 0: continue
            if not (-40 < p["pos"][0] < W + 40 and -40 < p["pos"][1] < H + 40): continue
            if self.iframe_frames <= 0 and vlen(p["pos"] - self.player_pos) < CONFIG["SPITTER_PROJ_R"] + 12:
                self._die("projectile"); return
            alive_p.append(p)
        self.projectiles = alive_p

        for p in self.particles:
            p["pos"] = p["pos"] + p["vel"] * sim_dt
            p["vel"] = p["vel"] * (1.0 - 3.0 * sim_dt)
            p["life"] -= sim_dt
        self.particles = [p for p in self.particles if p["life"] > 0]
        for r in self.rings: r["life"] -= sim_dt
        self.rings = [r for r in self.rings if r["life"] > 0]
        for sl in self.slashes: sl["life"] -= sim_dt
        self.slashes = [sl for sl in self.slashes if sl["life"] > 0]
        for pop in self.popups:
            pop["pos"] = pop["pos"] + np.array([0.0, -46.0]) * sim_dt
            pop["life"] -= sim_dt
        self.popups = [p for p in self.popups if p["life"] > 0]

        if self.flash > 0: self.flash = max(0.0, self.flash - dt * 2.5)
        if self.stage_complete_flash > 0:
            self.stage_complete_flash = max(0.0, self.stage_complete_flash - dt * 1.8)

        if self.mode == "TRAINING":
            regen = CONFIG["TRAINING_ENERGY_REGEN"]
        else:
            regen = CONFIG["ENERGY_REGEN"]
        if regen > 0.0:
            self.energy = min(CONFIG["MAX_ENERGY"],
                              self.energy + regen * dt
                              * (float(CONFIG["MS_REGEN_MUL"])
                                 if self._has_ms("regen") else 1.0))

    def _update_gameover(self, dt: float) -> None:
        self.frame += 1
        self._tick_fade(dt)
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)

        if self.trauma > 0:
            self.trauma = max(0.0, self.trauma - CONFIG["SHAKE_DECAY"] * dt)

        if self.death_slowmo_timer > 0:
            self.death_slowmo_timer -= dt
            wdt = dt * CONFIG["DEATH_SLOWMO_SCALE"]
        else:
            wdt = dt
            if self.gameover_anim.target < 0.5 and self.gameover_anim.value < 0.01:
                self.gameover_anim.set_target(1.0, CONFIG["UI_TWEEN_SLOW"], ease_out_back)

        for p in self.particles:
            p["pos"] = p["pos"] + p["vel"] * wdt
            p["vel"] = p["vel"] * (1.0 - 3.0 * wdt); p["life"] -= wdt
        self.particles = [p for p in self.particles if p["life"] > 0]
        for r in self.rings: r["life"] -= wdt
        self.rings = [r for r in self.rings if r["life"] > 0]
        for sl in self.slashes: sl["life"] -= wdt
        self.slashes = [sl for sl in self.slashes if sl["life"] > 0]
        if self.flash > 0: self.flash = max(0.0, self.flash - dt * 2.5)

    def _update_aim(self) -> None:
        mx, my = self.mouse_pos()
        to_m = np.array([mx - self.player_pos[0], my - self.player_pos[1]])
        d = vlen(to_m)
        if d > 4.0:
            self.aim_dir = to_m / d

    def _player_idle(self, dt: float) -> None:
        mx, my = self.mouse_pos()
        to_m = np.array([mx - self.player_pos[0], my - self.player_pos[1]])
        d = vlen(to_m)
        if d > 4.0:
            self.aim_dir = to_m / d
            tv = self.aim_dir * CONFIG["PLAYER_SPEED"]
        else:
            tv = np.zeros(2)
        alpha = 1.0 - math.exp(-CONFIG["PLAYER_SMOOTH"] * dt)
        self.player_vel += (tv - self.player_vel) * alpha
        slow = CONFIG["SLIME_PLAYER_SLOW"] if self._in_slime_mask(self.player_pos[None, :])[0] else 1.0
        self.player_pos = self.player_pos + self.player_vel * dt * slow
        self._clamp_player()

    def _player_drift(self) -> None:
        dt = 1.0 / 60.0
        scale = float(CONFIG["RECOVERY_MOVE_SCALE"])
        if scale > 0.0:
            mx, my = self.mouse_pos()
            to_m = np.array([mx - self.player_pos[0], my - self.player_pos[1]])
            dn = vlen(to_m)
            if dn > 4.0:
                steer = (to_m / dn) * CONFIG["PLAYER_SPEED"] * scale
                a = 1.0 - math.exp(-CONFIG["PLAYER_SMOOTH"] * dt)
                self.player_vel += (steer - self.player_vel) * a
            slow = CONFIG["SLIME_PLAYER_SLOW"] \
                if self._in_slime_mask(self.player_pos[None, :])[0] else 1.0
            self.player_pos = self.player_pos + self.player_vel * dt * slow
        else:
            self.player_pos = self.player_pos + self.player_vel * dt * 0.15
        self.player_vel = self.player_vel * 0.90
        self._clamp_player()

    def _player_dashing(self) -> None:
        prev = self.player_pos.copy()
        step = self.dash_dir * (CONFIG["DASH_SPEED"] / 60.0)
        self.player_pos = self.player_pos + step
        self._clamp_player()
        self._check_dash_hits(prev, self.player_pos)
        self.state_frame += 1
        if self.state_frame >= self.dash_total_frames:
            if CONFIG["DASH_PHASE_ON_MARK"] and self.dash_hits:
                self.phase_grace_indices = set(self.dash_hits)
                self.phase_grace_timer = CONFIG["PHASE_GRACE_FRAMES"]
            if self._cancel_on():
                self.player_state = "BACKSWING"
                self.did_cancel_this_backswing = False
            else:
                self.player_state = "IDLE"
            self.state_frame = 0

    def _clamp_player(self) -> None:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]; m = CONFIG["PLAYER_MARGIN"]
        self.player_pos[0] = float(np.clip(self.player_pos[0], m, W - m))
        self.player_pos[1] = float(np.clip(self.player_pos[1], m, H - m))

    def _stage_goal_line(self) -> str:
        st = self.stage
        goal = CONFIG["STAGE_GOALS"][st - 1]
        desc = (CONFIG["STAGE_DESCS"][st - 1] if self.use_cjk else STAGE_DESCS_EN[st - 1])
        if st == 1:
            prog = f"{self.stage_progress:.1f} / {goal:.0f}"
        else:
            prog = f"{int(self.stage_progress)} / {int(goal)}"
        return f"{desc}   {prog}"

    def _draw_top_goal(self, W: int, H: int) -> None:
        if self.mode == "TRAINING":
            line = self._stage_goal_line()
        else:
            nxt = self._next_wave_in()
            _ev = ""
            if self.wave_event == "ELITE":
                _ev = "   ·   精英" if self.use_cjk else "  ·  ELITE"
            elif self.wave_event == "SAFE":
                _ev = "   ·   休整" if self.use_cjk else "  ·  SAFE"
            line = (f"WAVE {self.wave:02d}   ·   下一波 {nxt:.0f}s" + _ev
                    if self.use_cjk else
                    f"WAVE {self.wave:02d}  ·  NEXT IN {nxt:.0f}s")
        if self.hint_timer > 0:
            a = 1.0
            if self.hint_timer < CONFIG["TOPGOAL_FADE"]:
                a = self.hint_timer / CONFIG["TOPGOAL_FADE"]
            base = self.f_med.render(line, True, CONFIG["G_80"])
            surf = base.copy(); surf.set_alpha(int(230 * a))
            self.screen.blit(surf, surf.get_rect(center=(W // 2, 58)))
        else:
            surf = self.f_tiny.render(line, True, CONFIG["G_60"])
            self.screen.blit(surf, surf.get_rect(center=(W // 2, 22)))

    def _cursor_hovering_clickable(self, mx: int, my: int) -> bool:
        if self.esc_open:
            if self.esc_page == "ROOT":
                for r in self._esc_root_rects():
                    if r[0] <= mx <= r[0]+r[2] and r[1] <= my <= r[1]+r[3]:
                        return True
            elif self.esc_page == "SETTINGS":
                for r in self._esc_settings_rects():
                    if r[0] <= mx <= r[0]+r[2] and r[1] <= my <= r[1]+r[3]:
                        return True
            elif self.esc_page == "MECHANICS":
                for r in self._esc_mech_tab_rects():
                    if r[0] <= mx <= r[0]+r[2] and r[1] <= my <= r[1]+r[3]:
                        return True
                if self.esc_mech_tab == 1:
                    for r in self._mech_ctrl_rects():
                        if r[0] <= mx <= r[0]+r[2] and r[1] <= my <= r[1]+r[3]:
                            return True
        elif self.mode == "MENU":
            for r in self._menu_options_rects():
                if r[0] <= mx <= r[0]+r[2] and r[1] <= my <= r[1]+r[3]:
                    return True
        elif self.paused:
            for r in self._pause_options_rects():
                if r[0] <= mx <= r[0]+r[2] and r[1] <= my <= r[1]+r[3]:
                    return True
        return False

    def _draw_cursor(self) -> None:
        mx, my = self.mouse_pos()
        if self.esc_open or self.mode == "MENU" or self.paused or self.game_over:
            if self._cursor_hovering_clickable(mx, my):
                radius, col, thick = 15, self.pcol, 2
            else:
                radius, col, thick = 9, CONFIG["G_80"], 1
        elif self.iframe_frames > 0:
            radius, col, thick = 12, (255, 255, 255), 2
        elif self.player_state == "DASHING":
            frac = self.state_frame / max(1, self.dash_total_frames)
            radius = int(10 + 9 * frac)
            col, thick = self.pcol, 2
        elif self.energy < CONFIG["DASH_COST"]:
            radius, col, thick = 6, CONFIG["G_60"], 1
        else:
            radius, col, thick = 10, self.pcol, 1

        pygame.draw.circle(self.screen, col, (mx, my), radius, thick)
        pygame.draw.line(self.screen, col, (mx - radius - 5, my), (mx - 3, my), 1)
        pygame.draw.line(self.screen, col, (mx + 3, my), (mx + radius + 5, my), 1)
        pygame.draw.line(self.screen, col, (mx, my - radius - 5), (mx, my - 3), 1)
        pygame.draw.line(self.screen, col, (mx, my + radius + 5), (mx, my + 3), 1)
        pygame.draw.circle(self.screen, col, (mx, my), 1)

    def _draw_fade(self, W: int, H: int) -> None:
        if self.fade_timer > 0:
            a = int(230 * (self.fade_timer / CONFIG["TRANSITION_DURATION"]))
            ov = pygame.Surface((self.cw, self.ch))
            ov.fill((0, 0, 0)); ov.set_alpha(a)
            self.screen.blit(ov, (0, 0))

    def _shift_hue(self, col, t: float) -> Tuple[int, int, int]:
        r, g, b = [float(c) / 255.0 for c in col]
        mx, mn = max(r, g, b), min(r, g, b)
        d = mx - mn
        if d < 1e-6:
            return tuple(int(c) for c in col)
        if mx == r:   h = ((g - b) / d) % 6.0
        elif mx == g: h = (b - r) / d + 2.0
        else:         h = (r - g) / d + 4.0
        h = (h / 6.0 + t) % 1.0
        s = 0.0 if mx == 0 else d / mx
        v = mx
        i = int(h * 6.0); f = h * 6.0 - i
        p = v * (1.0 - s); q = v * (1.0 - f * s); u = v * (1.0 - (1.0 - f) * s)
        tab = [(v, u, p), (q, v, p), (p, v, u), (p, q, v), (u, p, v), (v, p, q)]
        rr, gg, bb = tab[i % 6]
        return (int(rr * 255), int(gg * 255), int(bb * 255))

    def _smooth_path(self, pts, sub=3):
        m = len(pts)
        if m < 3:
            return [(float(q[0]), float(q[1])) for q in pts]
        P = np.asarray(pts, dtype=np.float64).reshape(m, 2)
        idx = np.arange(m - 1)
        p0 = P[np.maximum(idx - 1, 0)]
        p1 = P[idx]
        p2 = P[idx + 1]
        p3 = P[np.minimum(idx + 2, m - 1)]
        p1b = p1[None, :, :]
        c0 = (p2 - p0)[None, :, :]
        c1 = (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3)[None, :, :]
        c2 = (-p0 + 3.0 * p1 - 3.0 * p2 + p3)[None, :, :]
        ts = np.arange(sub, dtype=np.float64) / float(sub)
        t1 = ts[:, None, None]
        t2 = t1 * t1
        t3 = t2 * t1
        pts_out = 0.5 * (2.0 * p1b + c0 * t1 + c1 * t2 + c2 * t3)
        A = np.concatenate(
            (pts_out.transpose(1, 0, 2).reshape((m - 1) * sub, 2),
             P[m - 1:]))
        n = A.shape[0]
        if n > 4:
            for _ in range(2):
                K = A.copy()
                A[2:n - 2] = (K[1:n - 3] + 2.0 * K[2:n - 2] + K[3:n - 1]) * 0.25
        return A.tolist()

    def _ribbon(self, sp, wf, cf, af, segs=18, off=0.0, wmul=1.0, feather=2):
        n = len(sp)
        if n < 2:
            return
        lx, ly, rx, ry, nxv, nyv, kk = [], [], [], [], [], [], []
        for k in range(n):
            t = k / float(n - 1)
            px, py = sp[k]
            qa = sp[max(0, k - 1)]
            qb = sp[min(n - 1, k + 1)]
            dx = qb[0] - qa[0]
            dy = qb[1] - qa[1]
            ln = math.hypot(dx, dy)
            if ln < 0.001:
                continue
            nx, ny = -dy / ln, dx / ln
            hwc = float(wf(t)) * 0.5
            oc = hwc * off
            hw = hwc * wmul
            lx.append(px + nx * (oc + hw))
            ly.append(py + ny * (oc + hw))
            rx.append(px + nx * (oc - hw))
            ry.append(py + ny * (oc - hw))
            nxv.append(nx)
            nyv.append(ny)
            kk.append(k)
        m = len(lx)
        if m < 2:
            return
        nb = max(1, int(segs)) if segs else 1
        step = max(1, int(math.ceil((m - 1) / float(nb))))
        bands = []
        i = 0
        while i + step <= m - 1:
            j = i + step
            bands.append([i, j])
            i = j
        if not bands:
            bands = [[0, m - 1]]
        if bands[-1][1] != m - 1:
            bands[-1][1] = m - 1
        last = len(bands) - 1

        def cappts(cx, cy, ux, uy, tx, ty, hw, forward):
            out = []
            seq = (0.25, 0.50, 0.75) if forward else (0.75, 0.50, 0.25)
            for u in seq:
                a2 = u * math.pi
                ox = ux * math.cos(a2) + tx * math.sin(a2)
                oy = uy * math.cos(a2) + ty * math.sin(a2)
                out.append((cx + ox * hw, cy + oy * hw, ox, oy))
            return out

        for bi, (i0, i1) in enumerate(bands):
            tm = (kk[i0] + kk[i1]) * 0.5 / float(n - 1)
            a = int(af(tm))
            if a < 3 or float(wf(tm)) <= 0.05:
                continue
            col = cf(tm)
            span = i1 - i0
            vst = max(1, int(math.ceil(span / 5.0)))
            qs = list(range(i0, i1 + 1, vst))
            if qs[-1] != i1:
                qs.append(i1)
            verts = []
            for q in qs:
                verts.append((lx[q], ly[q], nxv[q], nyv[q]))
            if bi == last:
                cx = (lx[m - 1] + rx[m - 1]) * 0.5
                cy = (ly[m - 1] + ry[m - 1]) * 0.5
                ux = lx[m - 1] - cx
                uy = ly[m - 1] - cy
                hw = math.hypot(ux, uy)
                if hw > 0.05:
                    tx = lx[m - 1] - lx[max(0, m - 2)]
                    ty = ly[m - 1] - ly[max(0, m - 2)]
                    tl = math.hypot(tx, ty)
                    if tl > 0.001:
                        verts += cappts(cx, cy, ux / hw, uy / hw,
                                        tx / tl, ty / tl, hw, True)
            for q in reversed(qs):
                verts.append((rx[q], ry[q], -nxv[q], -nyv[q]))
            if bi == 0:
                cx = (lx[0] + rx[0]) * 0.5
                cy = (ly[0] + ry[0]) * 0.5
                ux = lx[0] - cx
                uy = ly[0] - cy
                hw = math.hypot(ux, uy)
                if hw > 0.05:
                    tx = lx[0] - lx[min(m - 1, 1)]
                    ty = ly[0] - ly[min(m - 1, 1)]
                    tl = math.hypot(tx, ty)
                    if tl > 0.001:
                        verts += cappts(cx, cy, ux / hw, uy / hw,
                                        tx / tl, ty / tl, hw, False)
            if len(verts) < 3:
                continue
            if feather > 0:
                for k in range(feather, 0, -1):
                    aa = int(a * (0.30 / k))
                    if aa < 3:
                        continue
                    ext = [(x + ox * 1.1 * k, y + oy * 1.1 * k)
                           for (x, y, ox, oy) in verts]
                    pygame.draw.polygon(self.fx, (*col, aa), ext)
            pygame.draw.polygon(self.fx, (*col, a),
                                [(x, y) for (x, y, ox, oy) in verts])

    @staticmethod
    def _hval(i: float, salt: float = 0.0) -> float:
        v = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
        return v - math.floor(v)

    @staticmethod
    def _densify(sp, want: int):
        n = len(sp)
        if n < 2 or n >= want:
            return sp
        reps = 1
        while n * (2 ** reps) < want:
            reps += 1
        cur = [tuple(float(v) for v in p) for p in sp]
        for _ in range(reps):
            out = [cur[0]]
            for i in range(1, len(cur)):
                a2, b2 = cur[i - 1], cur[i]
                out.append(((a2[0] + b2[0]) * 0.5, (a2[1] + b2[1]) * 0.5))
                out.append(b2)
            cur = out
        return cur

    def _arc_pts(self, sp, step: float, cnt_max: int, cnt_min: int = 1,
                 hwf=None):
        n = len(sp)
        cum = [0.0]
        for q in range(1, n):
            cum.append(cum[-1] + math.hypot(sp[q][0] - sp[q - 1][0],
                                            sp[q][1] - sp[q - 1][1]))
        total = cum[-1]
        if total < 1.0:
            return []
        cnt = max(cnt_min, min(cnt_max,
                               int(total / max(0.5, float(step))) + 1))
        out = []
        j = 0
        for ci in range(cnt + 1):
            tgt = ci / float(cnt) * total
            while j < n - 2 and cum[j + 1] < tgt:
                j += 1
            if j > n - 2:
                j = n - 2
            seg = cum[j + 1] - cum[j]
            f = 0.0 if seg <= 1e-6 else (tgt - cum[j]) / seg
            f = max(0.0, min(1.0, f))
            px = sp[j][0] + (sp[j + 1][0] - sp[j][0]) * f
            py = sp[j][1] + (sp[j + 1][1] - sp[j][1]) * f
            qa = sp[max(0, j)]
            qb = sp[min(n - 1, j + 2)]
            dx = qb[0] - qa[0]
            dy = qb[1] - qa[1]
            ln = math.hypot(dx, dy)
            t = tgt / total
            if ln < 0.001:
                if hwf is not None:
                    continue
                nx, ny = 0.0, 0.0
            else:
                nx, ny = -dy / ln, dx / ln
            out.append((px, py, nx, ny, t) if hwf is None
                       else (px, py, nx, ny, hwf(t), t))
        return out if len(out) >= 2 else []

    def _trail_ink(self, sp0, alpha: float, fade: float, w: float) -> None:
        sp = self._densify(sp0, 72)
        n = len(sp)
        if n < 2:
            return
        m = float(n - 1)
        moon = self.pskin.get("ink_white", (250, 250, 253))
        inkc = self.pskin.get("ink", (12, 12, 14))
        indigo = self.pskin.get("indigo", (228, 228, 232))
        gold = self.pskin.get("gold", (255, 214, 122))
        at = float(self.anim_t)
        s = float(self.rscale)
        ox, oy = _view_offset()
        SS = 2

        PTS = self._arc_pts(sp, 3.5, 50, 6)
        if not PTS:
            return

        def pressf(t):
            oi = t * m
            return (0.74 + 0.14 * (0.5 + 0.5 * math.sin(oi * 0.85 + 0.35))
                    + 0.07 * (0.5 + 0.5 * math.sin(oi * 1.90 + 1.10)))

        tl = float(self.pskin.get("ink_tlift", 0.90))
        te = float(self.pskin.get("ink_texp", 0.18))
        tp0 = max(0.01, float(self.pskin.get("ink_tip", 0.14)))
        tw0 = float(self.pskin.get("ink_tw", 0.20))
        twe = float(self.pskin.get("ink_twexp", 0.62))

        def halfw(t):
            return max(0.50, w * pressf(t) * (tw0 + (0.69 - tw0) * (t ** twe)))

        def tailprof(t):
            if t <= 0.0:
                return 0.0
            p = t ** fade
            q = tl * (t ** (fade * te))
            v = p if p > q else q
            u = t / tp0
            if u < 1.0:
                v *= u * u * (3.0 - 2.0 * u)
            return v

        def drymod(t):
            oi = t * m
            v = (0.58 * (0.5 + 0.5 * math.sin(oi * 0.58 + 0.40))
                 + 0.42 * (0.5 + 0.5 * math.sin(oi * 1.45 + 2.10 + at * 0.16)))
            return 0.54 + 0.46 * v

        gexp = float(self.pskin.get("ink_gexp", 0.80))
        gfl = float(self.pskin.get("ink_gfloor", 0.18))
        bwv = float(self.pskin.get("ink_bodywarm", 0.50))
        bfl = float(self.pskin.get("ink_bwflat", 0.78))
        dk = float(self.pskin.get("ink_deco", 0.74))
        cbo = float(self.pskin.get("ink_cboost", 0.85))
        dex = float(self.pskin.get("ink_dexp", 1.7))
        dey = float(self.pskin.get("ink_dexp2", 0.60))
        gvn = float(self.pskin.get("ink_gvein", 1.20))
        gwid = float(self.pskin.get("ink_gw", 0.16))
        gflw = float(self.pskin.get("ink_gflow", 6.2))
        gvn2 = float(self.pskin.get("ink_gvein2", 0.62))
        gwid2 = float(self.pskin.get("ink_gw2", 0.12))
        gflw2 = float(self.pskin.get("ink_gflow2", 4.3))
        gspd = float(self.pskin.get("ink_gspd", 2.35))

        def wetf(t):
            if t <= 0.0:
                return 0.0
            if t >= 1.0:
                return 1.0
            return gfl + (1.0 - gfl) * (t ** gexp)

        hwmax = 0.0
        for p in PTS:
            v = halfw(p[4])
            if v > hwmax:
                hwmax = v
        pad = hwmax * 1.42 + 7.0
        xs = [p[0] for p in PTS]
        ys = [p[1] for p in PTS]
        cwl = self.cw / max(0.001, s)
        chl = self.ch / max(0.001, s)
        lx0 = max(0.0, min(xs) - pad)
        ly0 = max(0.0, min(ys) - pad)
        lx1 = min(cwl, max(xs) + pad)
        ly1 = min(chl, max(ys) + pad)
        ow = int(math.ceil((lx1 - lx0) * s))
        oh = int(math.ceil((ly1 - ly0) * s))
        if ow < 4 or oh < 4:
            return
        tw = ow * SS
        th = oh * SS
        if tw > 2600 or th > 2600:
            return
        tmp = getattr(self, "_ink_tmp", None)
        if tmp is None or tmp.get_width() != tw or tmp.get_height() != th:
            tmp = pygame.Surface((tw, th), pygame.SRCALPHA)
            self._ink_tmp = tmp
        else:
            tmp.fill((0, 0, 0, 0))
        dst = getattr(self, "_ink_dst", None)
        if dst is None or dst.get_width() != ow or dst.get_height() != oh:
            dst = pygame.Surface((ow, oh), pygame.SRCALPHA)
            self._ink_dst = dst

        k0 = s * SS
        hw_avg = sum(halfw(p[4]) for p in PTS) / float(len(PTS))
        SPAN = 1.30
        N = int(2.0 * SPAN * hw_avg * k0 / 2.2)
        N = max(10, min(22, N))
        vs = []
        vc = []
        for jj in range(N):
            v0 = -SPAN + 2.0 * SPAN * jj / float(N)
            v1 = -SPAN + 2.0 * SPAN * (jj + 1) / float(N)
            vs.append((v0 - 0.025, v1 + 0.025))
            vc.append((v0 + v1) * 0.5)

        sheen_col = (moon[0] * 0.82 + gold[0] * 0.18,
                     moon[1] * 0.82 + gold[1] * 0.18,
                     moon[2] * 0.82 + gold[2] * 0.18)

        for k in range(len(PTS) - 1):
            A = PTS[k]
            B = PTS[k + 1]
            tm = (A[4] + B[4]) * 0.5
            mass = alpha * tailprof(tm) * drymod(tm)
            if mass < 3.0:
                continue
            wt = wetf(tm)
            dm = drymod(tm)
            ax = (A[0] - lx0) * k0
            ay = (A[1] - ly0) * k0
            bx = (B[0] - lx0) * k0
            by = (B[1] - ly0) * k0
            ex = bx - ax
            ey = by - ay
            el = math.hypot(ex, ey)
            if el > 1e-6:
                ov = 0.85 * SS / max(1e-6, el)
                bx = bx + ex * ov
                by = by + ey * ov
            hwA = halfw(A[4]) * k0
            hwB = halfw(B[4]) * k0
            anx = A[2] * hwA
            any_ = A[3] * hwA
            bnx = B[2] * hwB
            bny = B[3] * hwB
            for jj in range(N):
                v0, v1 = vs[jj]
                c = vc[jj]
                av = c if c >= 0.0 else -c
                if av <= 1.0:
                    d = (1.0 - av ** dex) ** dey
                else:
                    u = (av - 1.0) / (SPAN - 1.0)
                    d = 0.18 * (1.0 - u) ** 1.6
                if d <= 0.0:
                    continue
                d *= 1.0 - 0.34 * av * (1.0 - dm)
                a = mass * d
                if a < 3.0:
                    continue
                u = av ** 0.85
                if u > 1.0:
                    u = 1.0
                deep = 0.62 + 0.50 * av
                r0 = inkc[0] * deep
                g0 = inkc[1] * deep
                b0 = inkc[2] * deep
                mix = u * 0.82
                cr = r0 + (indigo[0] - r0) * mix
                cg = g0 + (indigo[1] - g0) * mix
                cb = b0 + (indigo[2] - b0) * mix
                if wt > 0.0:
                    bwd = wt * bwv * (bfl + (1.0 - bfl) * d)
                    if bwd > 0.0:
                        cr += (gold[0] - cr) * bwd
                        cg += (gold[1] - cg) * bwd
                        cb += (gold[2] - cb) * bwd
                    if -0.85 <= c <= -0.05:
                        sh = wt * 0.55 * (1.0 - abs(c + 0.45) / 0.40)
                        if sh > 0.0:
                            cr += (sheen_col[0] - cr) * sh
                            cg += (sheen_col[1] - cg) * sh
                            cb += (sheen_col[2] - cb) * sh
                    gc1 = 0.24 + 0.13 * math.sin(tm * gflw - at * gspd)
                    gc2 = -0.26 + 0.10 * math.sin(tm * gflw2 + at * gspd * 0.72)
                    if abs(c - gc1) <= gwid:
                        fv = (0.55 + 0.45 * tm) * gvn * (0.92 + 0.08 * math.sin(
                            tm * (gflw + 2.10) - at * (gspd + 0.90)))
                        fv *= (1.0 - abs(c - gc1) / gwid)
                        if fv > 1.0:
                            fv = 1.0
                        if fv > 0.0:
                            cr += (gold[0] - cr) * fv
                            cg += (gold[1] - cg) * fv
                            cb += (gold[2] - cb) * fv
                            if fv > 0.28:
                                af = 150.0 + 95.0 * (fv if fv < 1.0 else 1.0)
                                if a < af:
                                    a = af
                    if abs(c - gc2) <= gwid2:
                        fv2 = (0.45 + 0.35 * tm) * gvn2 * (0.66 + 0.16 * math.sin(
                            tm * (gflw2 + 1.70) + at * (gspd * 0.80)))
                        fv2 *= (1.0 - abs(c - gc2) / gwid2)
                        if fv2 > 1.0:
                            fv2 = 1.0
                        if fv2 > 0.0:
                            cr += (gold[0] - cr) * fv2
                            cg += (gold[1] - cg) * fv2
                            cb += (gold[2] - cb) * fv2
                if cbo > 0.0:
                    an = a / 255.0
                    if an < 0.0:
                        an = 0.0
                    elif an > 1.0:
                        an = 1.0
                    a = 255.0 * (an + cbo * an * (1.0 - an) * (2.0 * an - 1.0))
                    if a < 0.0:
                        a = 0.0
                    elif a > 255.0:
                        a = 255.0
                ai = int(a)
                if ai > 255:
                    ai = 255
                _REAL_DRAW.polygon(
                    tmp,
                    (int(cr) if cr > 0 else 0,
                     int(cg) if cg > 0 else 0,
                     int(cb) if cb > 0 else 0, ai),
                    [(ax + anx * v0, ay + any_ * v0),
                     (ax + anx * v1, ay + any_ * v1),
                     (bx + bnx * v1, by + bny * v1),
                     (bx + bnx * v0, by + bny * v0)])

        try:
            pygame.transform.smoothscale(tmp, (ow, oh), dst)
        except Exception:
            dst.fill((0, 0, 0, 0))
            dst.blit(tmp, (0, 0))


        dx0 = int(round(lx0 * s + ox))
        dy0 = int(round(ly0 * s + oy))
        try:
            _raw(self.fx).blit(dst, (dx0, dy0))
        except Exception:
            pass

        ex2, ey2 = sp[-1]
        self._soft_dot(ex2, ey2, w * 0.25 + 1.1,
                       (int(inkc[0] * 0.85), int(inkc[1] * 0.85),
                        int(inkc[2] * 0.85)), int(alpha * 0.78), 1)
        self._soft_dot(ex2, ey2, w * 0.10 + 0.6, moon, int(alpha * 0.92), 1)
        iend = max(3, int(m * 0.30))
        for i in range(2, iend, 9):
            t = i / m
            hv = self._hval(i, 13.7)
            if hv < 0.55:
                continue
            a = int(alpha * (t ** fade) * 0.30 * hv)
            if a < 4:
                continue
            px, py = sp[i]
            qa = sp[max(0, i - 1)]
            qb = sp[min(n - 1, i + 1)]
            dx = qb[0] - qa[0]
            dy = qb[1] - qa[1]
            ln = math.hypot(dx, dy)
            if ln < 0.001:
                continue
            L = halfw(t) * (1.15 + hv * 0.85)
            sd = 1.0 if self._hval(i, 5.1) > 0.5 else -1.0
            self._soft_dot(px + (-dy / ln) * L * sd, py + (dx / ln) * L * sd,
                           0.5 + hv * 0.9, inkc, a, 0)

        DENSE = []
        for k in range(len(PTS) - 1):
            A2 = PTS[k]
            B2 = PTS[k + 1]
            for q in range(3):
                fq = q / 3.0
                DENSE.append((A2[0] + (B2[0] - A2[0]) * fq,
                              A2[1] + (B2[1] - A2[1]) * fq,
                              A2[2], A2[3],
                              A2[4] + (B2[4] - A2[4]) * fq))
        if len(DENSE) < 3:
            DENSE = list(PTS)
        DENSE.append(PTS[-1])
        nd = len(DENSE)

        hot = (int(min(255, gold[0] * 0.30 + 255 * 0.70)),
               int(min(255, gold[1] * 0.30 + 250 * 0.70)),
               int(min(255, gold[2] * 0.30 + 226 * 0.70)))

        ra0 = float(self.pskin.get("ink_rim_a", 0.26))
        ra1 = float(self.pskin.get("ink_rim_b", 0.58))
        for ci in range(nd):
            p = DENSE[ci]
            tv = p[4]
            rf = (tv - ra0) / max(0.01, ra1 - ra0)
            if rf <= 0.0:
                continue
            if rf > 1.0:
                rf = 1.0
            rf = rf * rf * (3.0 - 2.0 * rf)
            hww = halfw(tv)
            rv = alpha * tailprof(tv) * 1.02 * rf * dk * (
                0.72 + 0.28 * (0.5 + 0.5 * math.sin(tv * 7.4 + at * 1.15)))
            if rv < 4.0:
                continue
            self._soft_dot(p[0] + p[2] * hww * 0.92,
                           p[1] + p[3] * hww * 0.92,
                           1.16, moon, int(rv), 1)


        for si in range(6):
            h1 = self._hval(si * 3.7 + 1.3, 21.1)
            h2 = self._hval(si * 5.3 + 2.7, 7.4)
            h3 = self._hval(si * 2.1 + 0.9, 33.5)
            idx = int(min(1.0, 0.40 + 0.60 * h1) * (len(PTS) - 1))
            p = PTS[idx]
            tv = p[4]
            hww = halfw(tv)
            side = 1.0 if self._hval(si + 0.5, 3.3) > 0.5 else -1.0
            age = (at * 0.40 + h2) % 1.0
            env = math.sin(math.pi * age)
            if env <= 0.03:
                continue
            dist = hww * (1.30 + 0.90 * h3 + 2.35 * h3 * age)
            dr = (0.48 + 1.10 * h3) * (1.0 - 0.48 * age)
            dv = alpha * (tv ** fade) * (0.58 + 0.42 * h2) * env
            if dv < 4.0:
                continue
            sx = p[0] + p[2] * side * dist
            sy = p[1] + p[3] * side * dist
            self._soft_dot(sx, sy, max(0.9, dr), inkc, int(dv * 0.95), 1)
            self._soft_dot(sx - dr * 0.28, sy - dr * 0.28,
                           max(0.9, dr * 0.58), hot, int(min(255.0, dv * 1.10)), 1)

        hxp, hyp = PTS[-1][0], PTS[-1][1]
        flr = 0.58 + 0.42 * (0.5 + 0.5 * math.sin(at * 1.85))
        for q in range(2):
            rr2 = hwmax * (0.95 + 0.80 * q)
            aa = alpha * (0.52 if q == 0 else 0.26) * flr
            if aa < 4.0:
                continue
            self._soft_dot(hxp, hyp, rr2, hot if q == 0 else gold, int(aa), 2)
    def _walk(self, sp, step):
        if isinstance(sp, np.ndarray):
            xl = sp[:, 0].tolist()
            yl = sp[:, 1].tolist()
        else:
            xl = [q[0] for q in sp]
            yl = [q[1] for q in sp]
        out = []
        acc = 0.0
        n = len(xl)
        for i in range(1, n):
            acc += math.hypot(xl[i] - xl[i - 1], yl[i] - yl[i - 1])
            if acc >= step:
                acc = 0.0
                out.append((xl[i], yl[i], i / float(n - 1)))
        return out

    def _cache(self, name):
        c = getattr(self, name, None)
        if c is None:
            c = {}
            setattr(self, name, c)
        return c

    def _dot_patch(self, size: int, col, aq: int, inner: float) -> pygame.Surface:
        key = (int(size), col, int(aq), int(round(inner * 40.0)))
        cache = self._cache("_dot_cache")
        got = cache.get(key)
        if got is not None:
            return got
        n = max(3, int(size))
        iv = float(min(0.97, max(0.30, inner)))
        amax = float(aq) / 48.0 * 255.0
        ss = 2 if n <= 26 else 1
        m = int(n * ss)
        bx = np.arange(m, dtype=np.float64) - (m - 1) / 2.0
        d = np.sqrt(bx[:, None] ** 2 + bx[None, :] ** 2) / (m / 2.0)
        core = np.clip((iv * 1.06 - d) / max(1e-6, iv * 0.34), 0.0, 1.0)
        fall = np.clip(1.0 - (d - iv) / max(1e-6, 1.0 - iv), 0.0, 1.0)
        fall = fall ** float(CONFIG["DOT_FALL"])
        arr = np.zeros((m, m, 4), dtype=np.uint8)
        arr[..., 0] = col[0]
        arr[..., 1] = col[1]
        arr[..., 2] = col[2]
        arr[..., 3] = np.clip(np.maximum(core, fall * float(CONFIG["DOT_EDGE_A"]))
                              * amax, 0, 255).astype(np.uint8)
        surf = pygame.image.frombuffer(arr.tobytes(), (m, m), "RGBA").copy()
        if ss > 1:
            surf = pygame.transform.smoothscale(surf, (n, n)).convert_alpha()
        if len(cache) > 900:
            cache.clear()
        cache[key] = surf
        return surf

    def _sphere_sprite(self, r_dev: float, col, phase: int) -> pygame.Surface:
        ri = max(2, int(round(float(r_dev))))
        ct = tuple(int(max(0, min(255, c))) for c in tuple(col)[:3])
        key = (ri, ct, int(phase))
        cache = self._cache("_sph_cache")
        got = cache.get(key)
        if got is not None:
            return got
        nph = max(1, int(CONFIG.get("SUBPIX_STEPS", 4)))
        fx = float(int(phase) % nph) / float(nph)
        fy = float((int(phase) // nph) % nph) / float(nph)
        n = 2 * ri + 2
        cx = (n - 1) / 2.0 + fx
        cy = (n - 1) / 2.0 + fy
        X = np.arange(n, dtype=np.float64)[None, :] - cx
        Y = np.arange(n, dtype=np.float64)[:, None] - cy
        dx = X / float(ri)
        dy = Y / float(ri)
        d2 = dx * dx + dy * dy
        d = np.sqrt(d2)
        cov = np.clip((1.0 - d) * float(ri) + 0.5, 0.0, 1.0)
        nz = np.sqrt(np.maximum(0.0, 1.0 - np.minimum(d2, 1.0)))
        lx, ly, lz = -0.42, -0.52, 0.745
        lam = np.clip(dx * lx + dy * ly + nz * lz, 0.0, None)
        hx, hy, hz = -0.36, -0.44, 0.82
        spec = np.clip(dx * hx + dy * hy + nz * hz, 0.0, None) ** 44.0 * float(
            CONFIG.get("SPHERE_SPEC", 0.80))
        rim = (1.0 - nz) ** 3.2 * float(CONFIG.get("SPHERE_RIM", 0.26))
        sh = float(CONFIG.get("SPHERE_AMB", 0.36)) + float(
            CONFIG.get("SPHERE_DIF", 0.84)) * lam + rim
        arr = np.zeros((n, n, 4), dtype=np.uint8)
        arr[..., 0] = np.clip(ct[0] * sh + 255.0 * spec, 0, 255).astype(np.uint8)
        arr[..., 1] = np.clip(ct[1] * sh + 255.0 * spec, 0, 255).astype(np.uint8)
        arr[..., 2] = np.clip(ct[2] * sh + 255.0 * spec, 0, 255).astype(np.uint8)
        arr[..., 3] = (cov * 255.0).astype(np.uint8)
        surf = pygame.image.frombuffer(arr.tobytes(), (n, n), "RGBA").copy()
        if len(cache) > 900:
            cache.clear()
        cache[key] = surf
        return surf

    def _sphere(self, x: float, y: float, r_logic: float, col) -> None:
        s = float(_ScaledDraw._s())
        ox, oy = _ScaledDraw._off()
        rd = float(r_logic) * s
        if rd < 2.0:
            pygame.draw.circle(self.fx, col, (float(x), float(y)), max(1.0, float(r_logic)))
            return
        dx_dev = float(x) * s + ox
        dy_dev = float(y) * s + oy
        nph = max(1, int(CONFIG.get("SUBPIX_STEPS", 4)))
        fxq = int(round((dx_dev - math.floor(dx_dev)) * nph)) % nph
        fyq = int(round((dy_dev - math.floor(dy_dev)) * nph)) % nph
        sp = self._sphere_sprite(rd, col, fyq * nph + fxq)
        w = sp.get_width()
        _raw(self.fx).blit(sp, (int(math.floor(dx_dev)) - w // 2,
                                int(math.floor(dy_dev)) - w // 2))

    def _soft_dot(self, x, y, r, col, a, feather=2):
        if a < 3:
            return
        r = max(0.85, float(r))
        s = max(0.001, float(_ScaledDraw._s()))
        ox, oy = _ScaledDraw._off()
        rad = r * s
        pad = float(max(0, feather))
        outer = rad + pad
        size = max(3, int(round(outer * 2.0)))
        ct = tuple(int(max(0, min(255, c))) for c in col)
        aq = max(1, min(48, int(round(float(a) / 255.0 * 48.0))))
        patch = self._dot_patch(size, ct, aq, rad / outer)
        _raw(self.fx).blit(patch, (int(round(x * s + ox - size * 0.5)),
                                    int(round(y * s + oy - size * 0.5))))

    def _soft_ring(self, x, y, r, col, a):
        r = int(max(1, round(r)))
        cx, cy = int(round(x)), int(round(y))
        for k in (1, -1, 0):
            aa = a if k == 0 else int(a * 0.36)
            if aa < 3: continue
            pygame.draw.circle(self.fx, (*col, aa), (cx, cy), max(1, r + k), 1)

    def _crescent(self, x, y, r, a0, a1, wmax, col, a, head=0.42, feather=1) -> None:
        span = a1 - a0
        n = max(7, int(abs(span) * 12))
        hd = min(0.92, max(0.06, float(head)))
        for k in range(n + 1):
            f = k / float(n)
            if f <= hd:
                e = (f / hd) ** 0.60
            else:
                d = 1.0 - hd
                e = (max(0.0, 1.0 - (f - hd) / d)) ** 1.35 if d > 1e-6 else 0.0
            aa = int(a * e)
            if aa < 3:
                continue
            ang = a0 + span * f
            self._soft_dot(x + math.cos(ang) * r, y + math.sin(ang) * r,
                           max(0.55, wmax * e), col, aa, feather)

    def _bead_patch(self, col, ab: int):
        key = (tuple(col), int(ab))
        cache = self._cache("_bead_cache")
        got = cache.get(key)
        if got is not None:
            return got
        n = 28
        rad = n / 2.0
        ax = np.arange(n, dtype=np.float64) - (n - 1) / 2.0
        dx = ax[None, :] / rad
        dy = ax[:, None] / rad
        d2 = dx * dx + dy * dy
        d = np.sqrt(d2)
        f = np.clip((1.02 - d) / 0.10, 0.0, 1.0)
        top = np.clip(0.56 - dy * 2.05, 0.0, 1.0) ** 0.55
        band = np.exp(-(((dy + 0.12) / 0.13) ** 2.0))
        bnc = np.exp(-(((dx - 0.26) ** 2 + (dy - 0.55) ** 2) / 0.045))
        lum = 0.08 + 0.80 * top + 0.30 * band + 0.30 * bnc
        lr = lum * col[0]
        lg = lum * col[1]
        lb = lum * col[2]
        edge = np.clip((d - 0.70) / 0.30, 0.0, 1.0)
        k = 1.0 - 0.55 * edge
        lr *= k
        lg *= k
        lb *= k
        arr = np.zeros((n, n, 4), dtype=np.uint8)
        arr[..., 0] = np.clip(lr, 0, 255).astype(np.uint8)
        arr[..., 1] = np.clip(lg, 0, 255).astype(np.uint8)
        arr[..., 2] = np.clip(lb, 0, 255).astype(np.uint8)
        arr[..., 3] = np.clip(f * (float(ab) / 15.0) * 252.0, 0, 255).astype(np.uint8)
        surf = pygame.image.frombuffer(arr.tobytes(), (n, n), "RGBA").copy()
        if len(cache) > 200:
            cache.clear()
        cache[key] = surf
        return surf

    def _blit_bead(self, x, y, r, a, col) -> None:
        s = max(0.001, float(_ScaledDraw._s()))
        ox, oy = _ScaledDraw._off()
        ab = int(round(float(a) / 255.0 * 15.0))
        if ab < 1:
            return
        ab = 15 if ab > 15 else ab
        src = self._bead_patch(tuple(col), ab)
        size = max(3, int(round(float(r) * 2.0 * s)))
        k2 = (size, ab, tuple(col))
        cache = self._cache("_bead_sc_cache")
        got = cache.get(k2)
        if got is None:
            got = pygame.transform.smoothscale(src, (size, size))
            if len(cache) > 400:
                cache.clear()
            cache[k2] = got
        dst = _raw(self.fx)
        dst.blit(got, (int(round(float(x) * s + ox - size / 2.0)),
                       int(round(float(y) * s + oy - size / 2.0))))

    def _trail_color(self, t: float) -> Tuple[int, int, int]:
        if self.pskin.get("hue"):
            return self._shift_hue(self.pcol, -0.20 * t)
        return self.pcol

    def _draw_player_trail(self) -> None:
        st = self.trail_style
        if st == "off":
            return
        sk = self.pskin
        raw = self.player_trail[-int(sk["tlen"]):]
        if len(raw) < 2:
            return
        alpha = float(sk["talpha"]); fade = float(sk["tfade"]); w = float(sk["twidth"])
        m = len(raw)
        sp = self._smooth_path(raw, 3)
        n = len(sp)
        if n < 2:
            return
        if st == "line":
            self._ribbon(sp, lambda t: max(0.6, w * t),
                         lambda t: self._trail_color(t),
                         lambda t: 170 * (t ** fade), segs=7)
        elif st == "ribbon":
            self._ribbon(sp, lambda t: max(0.6, w * t),
                         lambda t: self._trail_color(t),
                         lambda t: alpha * (t ** fade), segs=7)
        elif st == "syrup":
            self._ribbon(sp, lambda t: max(0.6, w * (0.30 + 1.05 * t)),
                         lambda t: self._trail_color(t),
                         lambda t: alpha * (t ** fade), segs=7)
            sag = float(self.pskin.get("sag", 7.0))
            for (gx, gy, t) in self._walk(sp, 15.0):
                if t > 0.66:
                    continue
                a = int(alpha * (t ** fade) * 0.75)
                if a < 4:
                    continue
                self._soft_dot(gx, gy + (1.0 - t) * sag, 0.8 + 1.8 * t,
                               self._trail_color(t), a)
            hx, hy = sp[-1]
            ha = int(alpha * 0.95)
            self._soft_dot(hx, hy, w * 0.34 + 1.0, self._trail_color(1.0), ha)
        elif st == "mercury":
            self._trail_mercury(sp, alpha, fade, w)
        elif st == "oil":
            self._trail_oil(sp, alpha, fade, w)
        elif st == "bubble":
            rise = float(self.pskin.get("rise", 9.0))
            fhue = float(self.pskin.get("bubble_film", 0.075))
            h0 = float(self.pskin.get("bubble_h0", 0.022))
            arc = float(self.pskin.get("bubble_arc", 0.55))
            at = float(self.anim_t)
            a0 = math.radians(198.0)
            a1 = math.radians(272.0)
            for (bx, by, t) in self._walk(sp, 6.5):
                a = int(alpha * (t ** fade))
                if a < 4:
                    continue
                wob = math.sin(t * m * 1.9 + at * 1.1) * (1.0 - t) * 3.0
                rr = max(1.0, 1.2 + w * 0.55 * t + math.sin(t * m * 2.3 + at * 0.8) * 1.2)
                cx2 = bx + wob
                cy2 = by - (1.0 - t) * rise
                col = self._shift_hue(self._trail_color(t),
                                      h0 + fhue * (0.5 + 0.5 * math.sin(t * 7.0 + at * 0.9)))
                self._soft_ring(cx2, cy2, rr, col, a)
                if rr > 2.4:
                    self._crescent(cx2, cy2, rr, a0, a1, max(0.6, rr * 0.32),
                                   (255, 255, 255), int(a * arc), 0.50, 1)
        elif st == "ink":
            self._trail_ink(sp, alpha, fade, w)

    def _trail_mercury(self, sp, alpha: float, fade: float, w: float) -> None:
        n = len(sp)
        if n < 2:
            return
        m = float(n - 1)
        sk = self.pskin
        base = self._trail_color(1.0)
        dk = float(sk.get("mdark", 0.30))
        co = float(sk.get("mcore", 0.74))
        ht = float(sk.get("mhot", 0.46))
        spk = float(sk.get("mspec", 0.92))
        stw = float(sk.get("mstreak", 0.44))
        dark = tuple(int(c * dk) for c in base)
        mid = tuple(int(min(255, c * co + 24)) for c in base)
        hot = tuple(int(min(255, c * ht + 150)) for c in base)
        at = float(self.anim_t)

        def mass(t):
            return alpha * (t ** fade)

        def wbody(t):
            return max(0.5, w * (0.14 + 0.94 * t))

        self._ribbon(sp, lambda t: wbody(t) * 1.42, lambda t: dark,
                     lambda t: mass(t) * 0.70, segs=20, feather=1)
        self._ribbon(sp, wbody, lambda t: mid,
                     lambda t: mass(t) * 0.88, segs=22, feather=1)
        self._ribbon(sp, wbody, lambda t: hot,
                     lambda t: mass(t) * 0.72, segs=24, feather=1,
                     off=-0.52, wmul=stw)
        lx, ly = -0.62, -0.78
        stepi = max(1, int((n - 1) // 15))
        for i in range(1, n, stepi):
            t = i / m
            if t < 0.14:
                continue
            px, py = sp[i]
            qa = sp[max(0, i - 1)]
            qb = sp[min(n - 1, i + 1)]
            dx = qb[0] - qa[0]
            dy = qb[1] - qa[1]
            ln = math.hypot(dx, dy)
            if ln < 0.001:
                continue
            hw = wbody(t) * 0.5
            flick = 0.70 + 0.30 * math.sin(t * 20.0 + at * 3.1)
            a = int(mass(t) * spk * flick)
            if a < 4:
                continue
            self._soft_dot(px + lx * hw * 0.60, py + ly * hw * 0.60,
                           max(0.5, w * (0.05 + 0.17 * t)),
                           (255, 255, 255), min(255, a), 1)
        hx, hy = sp[-1]
        self._blit_bead(hx, hy, w * 0.44 + 0.5, int(alpha * 0.98), base)
        self._soft_dot(hx + lx * w * 0.22, hy + ly * w * 0.22,
                       max(0.45, w * 0.12), (255, 255, 255),
                       int(alpha * 0.92), 1)
        for k in range(3):
            tt = 0.050 + k * 0.058
            i2 = int(round(tt * m))
            if i2 < 1 or i2 > n - 1:
                continue
            a = int(mass(tt) * 1.25)
            if a < 4:
                continue
            self._soft_dot(sp[i2][0], sp[i2][1] + 0.8 * k,
                           0.45 + 0.22 * k, (238, 243, 252), min(255, a), 1)

    def _trail_oil(self, sp, alpha: float, fade: float, w: float) -> None:
        n = len(sp)
        if n < 2:
            return
        sk = self.pskin
        spread = float(sk.get("spread", 0.55))
        span = float(sk.get("hue_span", 0.94))
        sheen = float(sk.get("sheen", 0.62))
        dark = tuple(sk.get("film_dark", (26, 24, 46)))
        base_a = float(sk.get("film_base_a", 0.55))
        cycles = float(sk.get("film_cycles", 2.6))
        chue = float(sk.get("film_cross_hue", 0.70))
        drift = float(sk.get("film_drift", 0.34))
        silver = float(sk.get("film_silver", 0.08))
        cross = float(sk.get("film_cross", 1.7))
        head = float(sk.get("film_head", 0.34))
        gpix = float(sk.get("film_grid", 2.2))
        stepw = float(sk.get("film_step", 7.0))
        edge = float(sk.get("film_edge", 0.60))
        sat = float(sk.get("film_sat", 0.80))
        at = float(self.anim_t)

        def envf(t):
            e = math.exp(-((t - 0.38) ** 2) / (2 * 0.34 ** 2))
            tp = min(1.0, t / 0.16)
            tp = tp * tp * (3.0 - 2.0 * tp)
            return (0.60 + spread * e) * tp

        def af(t):
            return alpha * (0.24 + 0.76 * (t ** fade))

        self._ribbon(sp, lambda t: max(0.5, w * envf(t)),
                     lambda t: dark, lambda t: af(t) * base_a,
                     segs=max(10, int(n / 3)), feather=3)

        xs = [p[0] for p in sp]
        ys = [p[1] for p in sp]
        mrg = w * 1.6 + 10.0
        bx0, bx1 = min(xs) - mrg, max(xs) + mrg
        by0, by1 = min(ys) - mrg, max(ys) + mrg
        s = max(0.001, float(self.rscale))
        ox, oy = _view_offset()
        iw = int(math.ceil((bx1 - bx0) * s))
        ih = int(math.ceil((by1 - by0) * s))
        if iw < 4 or ih < 4 or iw > 1600 or ih > 1600:
            return
        tmp = getattr(self, "_film_tmp", None)
        if tmp is None or tmp.get_width() != iw or tmp.get_height() != ih:
            tmp = pygame.Surface((iw, ih), pygame.SRCALPHA)
            self._film_tmp = tmp
        else:
            tmp.fill((0, 0, 0, 0))

        step_arc = max(2.0, stepw)
        pts = self._arc_pts(sp, step_arc, 120, 1,
                            lambda t: w * envf(t) * 0.5)
        if not pts:
            return

        hwm = sum(p[4] for p in pts) / float(len(pts))
        N = int(hwm * 2.0 * s / gpix)
        N = max(4, min(24, N))
        pvs = []
        c1s = []
        s1s = []
        c2s = []
        s2s = []
        v0s = []
        v1s = []
        for jj in range(N):
            vm = -1.0 + 2.0 * (jj + 0.5) / N
            av = abs(vm)
            pvs.append(0.0 if av >= 1.0 else (1.0 - av ** cross) ** 0.55)
            b1 = vm * 1.3
            b2 = -vm * 2.0
            c1s.append(math.cos(b1))
            s1s.append(math.sin(b1))
            c2s.append(math.cos(b2))
            s2s.append(math.sin(b2))
            v0s.append(-1.0 + 2.0 * jj / N - 0.035)
            v1s.append(-1.0 + 2.0 * (jj + 1) / N + 0.035)

        cache = self._cache("_hue_cache")
        pcol = self.pcol
        pmx, pmn = max(pcol), min(pcol)
        pd = pmx - pmn
        if pd < 1e-6:
            bh = 0.0
        else:
            pr, pg, pb = pcol
            if pmx == pr:
                bh = ((pg - pb) / pd) % 6.0
            elif pmx == pg:
                bh = (pb - pr) / pd + 2.0
            else:
                bh = (pr - pg) / pd + 4.0
            bh /= 6.0
        dd1 = at * drift * 1.4
        dd2 = -at * drift * 0.9
        old_fx = self.fx
        self.fx = tmp
        try:
            with _no_scale():
                for k in range(len(pts) - 1):
                    A = pts[k]
                    B = pts[k + 1]
                    tm = (A[5] + B[5]) * 0.5
                    a_base = af(tm) * sheen
                    if a_base < 3.0:
                        continue
                    a1 = (A[0] + B[0]) * 0.0155 + (A[1] + B[1]) * 0.0120 + dd1
                    a2 = (A[0] + B[0]) * 0.0085 - (A[1] + B[1]) * 0.0145 + dd2
                    sa1 = math.sin(a1)
                    ca1 = math.cos(a1)
                    sa2 = math.sin(a2)
                    ca2 = math.cos(a2)
                    bu = head + (1.0 - head) * tm
                    ax, ay, anx, any_, ahw, _t = A
                    bx2, by2, bnx, bny, bhw, _t2 = B
                    ex = bx2 - ax
                    ey = by2 - ay
                    el = math.hypot(ex, ey)
                    if el > 1e-6:
                        ov = 0.9 / s
                        bx2 = bx2 + ex / el * ov
                        by2 = by2 + ey / el * ov
                    for jj in range(N):
                        pv = pvs[jj]
                        if pv <= 0.0:
                            continue
                        wv = (0.5 + 0.5 * (sa1 * c1s[jj] + ca1 * s1s[jj])) * 0.55
                        wv += (0.5 + 0.5 * (sa2 * c2s[jj] + ca2 * s2s[jj])) * 0.45
                        ph = (cycles * bu * (0.70 + 0.58 * wv) + chue * (1.0 - pv)
                              + _FILM_DITH[((k >> 2) * 3 + jj * 5) & 7])
                        frac = ph - math.floor(ph)
                        ck = int(frac * 255.0)
                        col = cache.get(ck)
                        if col is None:
                            col = _film_hsv(bh + frac * span, sat, 1.0)
                            cache[ck] = col
                        inten = 0.42 + 0.58 * (0.5 - 0.5 * math.cos(6.2831853 * ph))
                        kv = a_base * inten * (pv ** edge) * 0.00392157
                        if kv < 0.015:
                            continue
                        if silver > 0.0:
                            fw = frac if frac < 0.5 else 1.0 - frac
                            if fw < silver:
                                kk2 = 1.0 - fw / silver
                                col = tuple(int(c + (255 - c) * 0.55 * kk2)
                                            for c in col)
                        if kv > 0.85:
                            kv = 0.85
                        av0 = ahw * v0s[jj]
                        av1 = ahw * v1s[jj]
                        bv0 = bhw * v0s[jj]
                        bv1 = bhw * v1s[jj]
                        poly = [
                            ((ax + anx * av0 - bx0) * s, (ay + any_ * av0 - by0) * s),
                            ((ax + anx * av1 - bx0) * s, (ay + any_ * av1 - by0) * s),
                            ((bx2 + bnx * bv1 - bx0) * s, (by2 + bny * bv1 - by0) * s),
                            ((bx2 + bnx * bv0 - bx0) * s, (by2 + bny * bv0 - by0) * s),
                        ]
                        pygame.draw.polygon(
                            tmp, (int(col[0] * kv), int(col[1] * kv), int(col[2] * kv), 255),
                            poly)
        finally:
            self.fx = old_fx
        dx0 = int(round(bx0 * s + ox))
        dy0 = int(round(by0 * s + oy))
        try:
            _raw(self.fx).blit(tmp, (dx0, dy0), None, pygame.BLEND_RGBA_ADD)
        except Exception:
            _raw(self.fx).blit(tmp, (dx0, dy0))

    def _draw_afterimages(self) -> None:
        sk = self.pskin
        kind = str(sk.get("ai", "solid"))
        for im in self.afterimages:
            lt = im["life"] / im["maxlife"]
            a = int(130 * lt * lt)
            if a < 3: continue
            ix, iy = int(im["pos"][0]), int(im["pos"][1])
            if kind == "shrink":
                rr = int(11 * (1.0 - 0.45 * (1.0 - lt)))
                pygame.draw.circle(self.fx, (*self.pcol, a), (ix, iy), rr, 2)
                if lt > 0.35:
                    pygame.draw.circle(self.fx, (*self.pcol, a // 3), (ix, iy + rr // 2), 2)
            elif kind == "bead":
                rr = 2.0 + 7.0 * lt
                self._blit_bead(ix, iy, rr, a, self.pcol)
                if rr > 1.5:
                    self._soft_dot(ix - rr * 0.34, iy - rr * 0.36,
                                   max(0.55, rr * 0.24), (255, 255, 255),
                                   min(255, int(a * 0.85)), 1)
            elif kind == "iris":
                pygame.draw.circle(self.fx, (*self._shift_hue(self.pcol, -0.22 * (1.0 - lt)), a), (ix, iy), 11, 2)
            elif kind == "grow":
                rr = int(9 + 7 * (1.0 - lt))
                pygame.draw.circle(self.fx, (*self.pcol, a), (ix, iy), rr, 1)
                pygame.draw.circle(self.fx, (255, 255, 255, min(255, a // 3)),
                                   (ix - rr // 3, iy - rr // 3), 1)
            elif kind == "poem":
                gold = self.pskin.get("gold", (216, 178, 108))
                inkc = self.pskin.get("ink", (72, 92, 130))
                rr = int(11 * (0.74 + 0.26 * lt))
                pygame.draw.circle(self.fx, (*inkc, min(255, int(a * 1.15))), (ix, iy), rr + 2)
                pygame.draw.circle(self.fx, (*self.pcol, a), (ix, iy), rr, 2)
                if a > 34:
                    pygame.draw.circle(self.fx, (*gold, int(a * 0.60)), (ix, iy), rr + 3, 1)
            elif kind == "bleed":
                for k in range(7):
                    ang = k * (2.0 * math.pi / 7.0) + (1.0 - lt) * 2.1
                    dist = (1.0 - lt) * (5.0 + 4.5 * self._hval(k, 1.3))
                    ox = ix + math.cos(ang) * dist
                    oy = iy + math.sin(ang) * dist
                    aa = int(a * (0.50 - 0.055 * k) * (0.45 + 0.55 * self._hval(k, 3.7)))
                    if aa < 3: continue
                    self._soft_dot(ox, oy, 1.0 + (1.0 - lt) * 3.1 * (0.35 + self._hval(k, 2.2)),
                                   self.pcol, aa, 1)
                self._soft_dot(ix, iy, 3.0 + (1.0 - lt) * 4.0, self.pcol, int(a * 0.85), 1)
                self._soft_ring(ix, iy, 10 + 6 * (1.0 - lt), self.pcol, int(a * 0.55))
            else:
                pygame.draw.circle(self.fx, (*self.pcol, a), (ix, iy), 11, 2)

    def _spawn_sword_qi(self, direction, n: int = 1,
                        spread: float = 0.0, life: float = 0.34,
                        pos=None) -> None:
        try:
            base = math.atan2(float(direction[1]), float(direction[0]))
        except Exception:
            base = 0.0
        src = self.player_pos if pos is None else pos
        for k in range(int(n)):
            off = 0.0
            if n > 1:
                off = (k - (n - 1) / 2.0) * spread
            self.sword_qi.append({
                "pos": src.copy(),
                "ang": base + off,
                "life": float(life), "maxlife": float(life)})
        if len(self.sword_qi) > int(CONFIG["QI_CAP"]):
            self.sword_qi = self.sword_qi[-int(CONFIG["QI_CAP"]):]

    def _draw_sword_qi(self) -> None:
        if not self.sword_qi:
            return
        gold = self.pskin.get("gold", (216, 178, 108))
        moon = self.pcol
        inkc = self.pskin.get("ink", (72, 92, 130))
        for q in self.sword_qi:
            lt = q["life"] / q["maxlife"]
            u = 1.0 - lt
            a = int(float(CONFIG["QI_ALPHA"]) * lt * (0.45 + 0.55 * lt))
            if a < 4:
                continue
            x = float(q["pos"][0]) + math.cos(q["ang"]) * (2.0 + 9.0 * u)
            y = float(q["pos"][1]) + math.sin(q["ang"]) * (2.0 + 9.0 * u)
            r = 11.6 + float(CONFIG["QI_GROW"]) * u
            wd = float(CONFIG["QI_WD"]) * (1.0 - 0.50 * u)
            self._crescent(x, y, r, q["ang"] - 0.92, q["ang"] + 0.92,
                           wd, inkc, int(a * 0.85), 0.50, 0)
            self._crescent(x, y, r, q["ang"] - 0.86, q["ang"] + 0.86,
                           wd * 0.72, moon, a, 0.46, 1)
            self._crescent(x, y, r + wd * 0.62, q["ang"] - 0.62, q["ang"] + 0.62,
                           wd * 0.34, gold, int(a * 0.92), 0.42, 0)

    def _poem_next_char(self) -> str:
        lines = CONFIG["POEM_LINES"]
        ln = lines[self.poem_line % len(lines)]
        ch = ln[self.poem_pos % len(ln)]
        self.poem_pos += 1
        if self.poem_pos >= len(ln):
            self.poem_pos = 0
            self.poem_line += 1
        return ch

    def _poem_blur(self, s, k):
        w, h = s.get_width(), s.get_height()
        k = max(2, int(k))
        if w < 8 or h < 8:
            return s
        sw, sh = max(2, w // k), max(2, h // k)
        d = pygame.transform.smoothscale(s, (sw, sh))
        return pygame.transform.smoothscale(d, (w, h))

    def _poem_glyph(self, ch):
        sc = max(0.001, float(self.rscale))
        col = self.pskin.get("poem_col", (124, 156, 206))
        key = (ch, round(sc, 3), col)
        got = self._poem_cache.get(key)
        if got is not None:
            return got
        ss = max(2, int(CONFIG["POEM_SS"]))
        pad = max(1, int(CONFIG["POEM_SOFT_PAD"]))
        size = max(6, int(round(self._fs(int(CONFIG["POEM_FS"])) * ss)))
        f = self._poem_fonts.get(size)
        if f is None:
            data = getattr(self, "_poem_font_bytes", None)
            if data:
                try:
                    f = FTFont(io.BytesIO(bytes(data)), size, False)
                except Exception:
                    f = None
            if f is None and self.poem_font_path:
                try:
                    f = FTFont(str(self.poem_font_path), size, False)
                except Exception:
                    f = None
            if f is None:
                f = self.f_small
            self._poem_fonts[size] = f
        try:
            gs, _goff = f.glyph(ch, col)
            raw = _raw(gs).convert_alpha()
        except Exception:
            raw = _raw(f.render(ch, True, col)).convert_alpha()
        bw, bh = raw.get_width(), raw.get_height()
        tw = max(2, int(round(bw / float(ss))))
        th = max(2, int(round(bh / float(ss))))
        sharp = pygame.transform.smoothscale(raw, (tw, th))
        soft = self._poem_blur(sharp, int(CONFIG["POEM_BLUR"]))
        out = pygame.Surface((tw + pad * 2, th + pad * 2), pygame.SRCALPHA)
        halo = soft.copy()
        halo.set_alpha(int(255 * float(CONFIG["POEM_HALO"])))
        out.blit(halo, (pad - 1, pad + 1))
        core = sharp.copy()
        core.set_alpha(int(255 * float(CONFIG["POEM_SHARP"])))
        out.blit(core, (pad, pad))
        post = int(CONFIG["POEM_POST"])
        if post > 1:
            out = self._poem_blur(out, post)
        got = (out, float(tw + pad * 2), float(th + pad * 2))
        self._poem_cache[key] = got
        return got

    def _spawn_poem(self, pos, n: int = 1) -> None:
        sc = max(0.001, float(self.rscale))
        for _ in range(int(n)):
            ch = self._poem_next_char()
            surf, gw, gh = self._poem_glyph(ch)
            self.poem_glyphs.append({
                "s": surf.copy(),
                "x": float(pos[0]) + (self._hval(self.frame, 3.3) - 0.5) * 30.0,
                "y": float(pos[1]) - 25.0 - self._hval(self.frame, 4.4) * 12.0,
                "vx": (self._hval(self.frame, 1.1) - 0.5) * 15.0,
                "vy": -13.0 - self._hval(self.frame, 2.2) * 16.0,
                "life": 1.15, "maxlife": 1.15,
                "w": gw / sc, "h": gh / sc})
        if len(self.poem_glyphs) > 28:
            self.poem_glyphs = self.poem_glyphs[-28:]

    def _update_poem(self, dt: float) -> None:
        if not self.poem_glyphs:
            return
        out = []
        for g in self.poem_glyphs:
            g["life"] -= dt
            if g["life"] <= 0:
                continue
            g["x"] += g["vx"] * dt
            g["y"] += g["vy"] * dt
            g["vy"] *= (1.0 - 1.7 * dt)
            out.append(g)
        self.poem_glyphs = out

    def _draw_poem(self) -> None:
        peak = float(self.pskin.get("poem_a", 84))
        for g in self.poem_glyphs:
            lt = g["life"] / g["maxlife"]
            a = int(peak * min(1.0, (1.0 - lt) * 6.5) * (lt ** 0.85))
            if a < 4:
                continue
            bx = g["x"] - g["w"] * 0.5
            by = g["y"] - g["h"] * 0.5
            g["s"].set_alpha(a)
            self.fx.blit(g["s"], (bx, by))

    def _draw_debug(self, W: int, H: int) -> None:
        if CONFIG["DEBUG_ANIM"]:
            x = (self.anim_t * 60.0) % (W + 120) - 60
            pygame.draw.circle(self.screen, (255, 255, 0), (int(round(x)), H // 2 - 100), 18)
            pygame.draw.circle(self.screen, (255, 255, 0), (int(round(x)), H // 2 - 100), 18, 1)
        if CONFIG["SHOW_FPS"]:
            fps = self.clock.get_fps()
            surf = self.f_tiny.render(f"{fps:5.1f} FPS", True, CONFIG["G_60"])
            self.screen.blit(surf, (W - surf.get_width() - 16, H - 22))

    @staticmethod
    def _ss_draw(w: int, h: int, ss: int, draw_fn):
        w = max(2, int(w)); h = max(2, int(h))
        big = pygame.Surface((w * ss, h * ss), pygame.SRCALPHA)
        draw_fn(big, ss)
        return pygame.transform.smoothscale(big, (w, h))

    def _logo_variants(self, scale: float) -> List[pygame.Surface]:
        key = round(float(scale), 4)
        vs = self._logo_cache.get(key)
        if vs is None:
            ss = int(CONFIG["LOGO_SS"])
            st = int(CONFIG["SUBPIX_STEPS"])
            vs = [self._render_logo(scale, ss, i / st) for i in range(st)]
            self._logo_cache[key] = vs
        return vs

    def _draw_player_body(self, px, py):
        if self._has_ms("det_ring") and self.mode == "RUN":
            _hp = 0.5 + 0.5 * math.sin(self.anim_t * 2.0 * math.pi * 0.45)
            pygame.draw.circle(self.fx, (*self.pcol, int(22 + 10 * _hp)),
                               (px, py), int(round(self._det_radius())), 1)
        if self.fx_energy_glow and self.energy >= CONFIG["MAX_ENERGY"] - 0.001:
            gp = 0.5 + 0.5 * math.sin(self.anim_t * 2 * math.pi * 0.9)
            for k in range(3):
                rr = 11.4 + k * 0.55 + 0.5 * gp
                aa = int((52 - k * 14) * (0.55 + 0.45 * gp))
                if aa < 5:
                    continue
                pygame.draw.circle(self.fx, (*self.pcol, aa),
                                   (px, py), int(round(rr)), 1)
        kind = str(self.pskin.get("body", ""))
        bs = 1.0
        if kind == "drip":
            ph = 0.5 + 0.5 * math.sin(self.anim_t * 2.0 * math.pi * 0.55)
            pygame.draw.arc(self.fx, (*self.pcol, 170),
                            (px - 11.2, py - 11.2, 22.4, 22.4),
                            math.radians(26.0), math.radians(154.0),
                            max(1, int(round(2.0 + 1.5 * ph))))
        elif kind == "spec":
            pygame.draw.arc(self.fx, (255, 255, 255),
                            (px - 11.4, py - 11.4, 22.8, 22.8), math.radians(160), math.radians(230), 2)
        elif kind == "iris":
            bs = float(CONFIG["IRIS_BODY_SCALE"])
        elif kind == "film":
            br = 11.3 + 0.7 * math.sin(self.anim_t * 2.0 * math.pi * 0.8)
            pygame.draw.circle(self.fx, (*self.pcol, 85), (px, py), int(br), 1)
            pygame.draw.circle(self.fx, (255, 255, 255, 120),
                               (px - 5, py - 6), 2)
        elif kind == "poem":
            gold = self.pskin.get("gold", (216, 178, 108))
            inkc = self.pskin.get("ink", (72, 92, 130))
            indigo = self.pskin.get("indigo", (88, 142, 202))
            ph = self.anim_t * 2.0 * math.pi * 0.7
            for k in range(3):
                base = ph * 0.24 + k * (2.0 * math.pi / 3.0)
                span = 0.86 + 0.26 * math.sin(ph * 0.7 + k * 1.9)
                steps = 10
                for s in range(steps + 1):
                    fw = s / float(steps)
                    ang = base + fw * span
                    rr = 12.8 + 5.8 * fw + 0.9 * math.sin(fw * 5.0 + ph * 1.3 + k)
                    aa = int(46 * math.sin(math.pi * min(1.0, fw)) ** 0.9)
                    if aa < 4:
                        continue
                    self._soft_dot(px + math.cos(ang) * rr, py + math.sin(ang) * rr,
                                   0.8 + 1.1 * (1.0 - fw), indigo, aa, 1)
            for k in range(7):
                ang = ph * (0.38 + 0.12 * (k % 4)) + k * 0.90
                rr = 15.2 + 3.0 * math.sin(ph * 0.9 + k * 1.7)
                sz = 0.50 + 0.40 * math.sin(ph * 1.6 + k)
                aa = int(62 + 54 * (0.5 + 0.5 * math.sin(ph * 1.2 + k * 2.3)))
                self._soft_dot(px + math.cos(ang) * rr, py + math.sin(ang) * rr,
                               max(0.5, sz), gold, aa, 1)
            for k in range(3):
                base = 9.6 + k * 0.45 + 0.5 * math.sin(ph + k * 0.9)
                aa = 34 - k * 10
                if aa < 4:
                    continue
                for s in range(20):
                    ang = s * (2.0 * math.pi / 20.0) + k * 0.15
                    wob = math.sin(ang * 3.0 + ph * 0.8 + k * 1.7)
                    rr = base + wob * 0.45
                    self._soft_dot(px + math.cos(ang) * rr, py + math.sin(ang) * rr,
                                   1.2 + 0.3 * k, inkc,
                                   int(aa * (0.55 + 0.45 * (0.5 + 0.5 * wob))), 0)
            for k in range(4):
                a0 = k * (math.pi / 2.0) + ph * 0.32
                a1 = a0 + 0.50
                pygame.draw.arc(self.fx, (*gold, 104),
                                (px - 11.3, py - 11.3, 22.6, 22.6), a0 - 0.04, a1 + 0.04, 1)
                pygame.draw.arc(self.fx, (*gold, 200),
                                (px - 10.5, py - 10.5, 21.0, 21.0), a0, a1, 2)
                pygame.draw.line(self.fx, (*gold, 150),
                                 (px + math.cos(a1) * 10.5, py + math.sin(a1) * 10.5),
                                 (px + math.cos(a1) * 8.7, py + math.sin(a1) * 8.7), 1)
                self._soft_dot(px + math.cos(a0) * 10.5, py + math.sin(a0) * 10.5,
                               1.15, gold, 95, 0)
                am = a0 + 0.25 + math.pi / 4.0
                pygame.draw.arc(self.fx, (*indigo, 52),
                                (px - 11.4, py - 11.4, 22.8, 22.8), am - 0.30, am + 0.30, 1)
            for s in range(30):
                ang = s * (2.0 * math.pi / 30.0)
                wob = math.sin(ang * 3.0 + ph * 1.15)
                rr = 9.6 + 0.7 * wob
                dens = 0.5 + 0.5 * math.sin(ang * 2.0 + ph * 1.15)
                sz = 0.85 + 1.3 * dens
                aa = int((110 + 95 * dens) * (0.72 + 0.28 * (0.5 + 0.5 * wob)))
                if aa < 6: continue
                self._soft_dot(px + math.cos(ang) * rr, py + math.sin(ang) * rr,
                               sz, self.pcol if dens > 0.45 else indigo, aa, 1)
            full = 1.0 if self.energy >= CONFIG["MAX_ENERGY"] - 0.001 else 0.0
            spin = ph * (0.62 + 0.60 * full)
            for k in range(3):
                ang = spin + k * (2.0 * math.pi / 3.0)
                rd = 13.1 + 1.5 * math.sin(ph * 1.4 + k * 2.1)
                br2 = 0.62 + 0.38 * math.sin(ph * 1.9 + k * 1.6)
                aa = int((78 + 72 * br2) * (0.74 + 0.26 * full))
                self._crescent(px, py, rd, ang - 0.58, ang + 0.58,
                               1.55 * (0.68 + 0.32 * br2), gold, aa, 0.42, 1)
                self._crescent(px, py, rd + 1.35, ang - 0.44, ang + 0.44,
                               0.74, self.pcol, int(aa * 0.58), 0.42, 0)
            if full > 0.0:
                pygame.draw.circle(self.fx, (*indigo, 42),
                                   (px, py), int(round(14.2)), 1)
            sweep = (self.anim_t * 0.62) % 1.0
            sa = sweep * 2.0 * math.pi
            self._crescent(px, py, 11.7, sa - 0.58, sa + 0.58, 2.30,
                           gold, 122, 0.40, 1)
            self._crescent(px, py, 12.9, sa - 0.44, sa + 0.44, 0.90,
                           self.pcol, 104, 0.40, 0)
        ir = max(4, int(round(10 * bs)))
        rr = 12
        if kind == "iris":
            for k in range(6):
                a0 = k * (math.pi / 3.0) + self.anim_t * 0.5
                pygame.draw.arc(self.fx, (*self._shift_hue(self.pcol, -0.16 * (k / 5.0)), 205),
                                (px - rr, py - rr, rr * 2, rr * 2), a0, a0 + 0.86, 2)
            gr = rr - 2.6
            ga = math.radians(150.0 + 6.0 * math.sin(self.anim_t * 0.8))
            pygame.draw.arc(self.fx, (232, 244, 255, 72),
                            (px - gr, py - gr, gr * 2, gr * 2), ga - 0.12, ga + 0.66, 2)
            pygame.draw.arc(self.fx, (240, 250, 255, 232),
                            (px - gr, py - gr, gr * 2, gr * 2), ga + 0.04, ga + 0.46, 1)
        else:
            self._lit_ring(px, py, rr, 2, tuple(self.pcol))
        if kind == "iris":
            self._iris_core(px, py, ir)
            self._body_core(px, py, ir, (232, 244, 255), 0.0)
        elif kind == "poem":
            self._skin_core(px, py, ir, "poem")
        elif kind == "spec":
            self._skin_core(px, py, ir, "spec")
        elif kind == "film":
            self._skin_core(px, py, ir, "film")
        else:
            self._skin_core(px, py, ir, "drip")

    def _gloss_patch(self, size: int, col, power: float) -> pygame.Surface:
        n = max(5, int(size))
        if n % 2 == 0:
            n += 1
        key = (n, tuple(col), round(float(power), 3))
        cache = self._cache("_gloss_cache")
        s = cache.get(key)
        if s is not None:
            return s
        ax = np.arange(n, dtype=np.float64) - (n - 1) / 2.0
        d = np.sqrt(ax[:, None] ** 2 + ax[None, :] ** 2) / (n / 2.0)
        a = np.clip(1.0 - d, 0.0, 1.0) ** power
        arr = np.zeros((n, n, 4), dtype=np.uint8)
        arr[..., 0] = col[0]
        arr[..., 1] = col[1]
        arr[..., 2] = col[2]
        arr[..., 3] = (a * 255.0).astype(np.uint8)
        surf = pygame.image.frombuffer(arr.tobytes(), (n, n), "RGBA").copy()
        if len(cache) > 24:
            cache.clear()
        cache[key] = surf
        return surf

    def _lit_ring(self, px, py, r, w, col) -> None:
        sc = max(0.001, float(_ScaledDraw._s()))
        seg = int(max(10, min(26, r * sc * 2.2)))
        lx, ly = -0.40, 0.50
        step = 2.0 * math.pi / float(seg)
        for i in range(seg):
            a0 = i * step
            a1 = a0 + step * 1.12
            am = (a0 + a1) * 0.5
            k = max(0.0, min(1.0, 0.5 + 0.5 * (lx * math.cos(am)
                                               + ly * math.sin(am)))) ** 1.05
            aa = int(126 + 129 * k)
            c = tuple(int(min(255, v * (0.42 + 0.58 * k) + 76.0 * k))
                      for v in col)
            pygame.draw.arc(self.fx, (*c, aa),
                            (px - r, py - r, r * 2, r * 2), a0, a1, w)

    def _shade_patches(self, size: int, col, base_a: float):
        key = (int(size), tuple(int(c) for c in col), int(round(float(base_a) * 20.0)))
        cache = self._cache("_shade_cache")
        got = cache.get(key)
        if got is not None:
            return got
        tgt = max(8, int(size))
        k = max(1, int(math.ceil(72.0 / float(tgt))))
        n = tgt * k
        ax = np.arange(n, dtype=np.float64) - (n - 1) / 2.0
        rad = n / 2.0
        dx = ax[None, :] / rad
        dy = ax[:, None] / rad
        d2 = dx * dx + dy * dy
        d = np.sqrt(d2)
        nz = np.sqrt(np.clip(1.0 - d2, 0.0, 1.0))
        lx, ly, lz = -0.40, -0.50, 0.77
        ln = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / ln, ly / ln, lz / ln
        diff = np.clip(dx * lx + dy * ly + nz * lz, 0.0, 1.0)
        spec = diff ** 24.0
        ex, ey, ez = 0.46, 0.52, 0.30
        en = math.sqrt(ex * ex + ey * ey + ez * ez)
        ex, ey, ez = ex / en, ey / en, ez / en
        bounce = np.clip(dx * ex + dy * ey + nz * ez, 0.0, 1.0) ** 2.0 * 0.55
        band = np.exp(-(((d - 0.94) / 0.10) ** 2.0))
        low = np.clip(0.5 + 0.5 * dy, 0.0, 1.0)
        rim = band * (0.26 + 0.74 * low)
        f1 = np.clip((1.02 - d) / 0.10, 0.0, 1.0)
        f2 = np.clip((1.03 - d) / 0.05, 0.0, 1.0)
        da = ((0.80 + (1.0 - diff) ** 1.30 * 0.20) * f1
              * float(base_a) * 255.0)
        la = ((diff * 0.26 + spec * 0.85 + bounce * 0.30 + rim * 0.34)
              * f2 * 255.0)
        if k > 1:
            da = da.reshape(tgt, k, tgt, k).mean(axis=(1, 3))
            la = la.reshape(tgt, k, tgt, k).mean(axis=(1, 3))
        da = np.clip(da, 0.0, 255.0).astype(np.uint8)
        la = np.clip(la, 0.0, 255.0).astype(np.uint8)
        dc = tuple(max(0, int(c * 0.13)) for c in col)
        lc = tuple(min(255, int(c + (255 - c) * 0.74)) for c in col)
        af = la.astype(np.float64) / 255.0
        dk = np.zeros((tgt, tgt, 4), dtype=np.uint8)
        dk[..., 0], dk[..., 1], dk[..., 2] = dc[0], dc[1], dc[2]
        dk[..., 3] = da
        lt = np.zeros((tgt, tgt, 4), dtype=np.uint8)
        lt[..., 0] = np.clip(lc[0] * af, 0, 255).astype(np.uint8)
        lt[..., 1] = np.clip(lc[1] * af, 0, 255).astype(np.uint8)
        lt[..., 2] = np.clip(lc[2] * af, 0, 255).astype(np.uint8)
        lt[..., 3] = la
        sd = pygame.image.frombuffer(dk.tobytes(), (tgt, tgt), "RGBA").copy()
        sl = pygame.image.frombuffer(lt.tobytes(), (tgt, tgt), "RGBA").copy()
        if len(cache) > 96:
            cache.clear()
        cache[key] = (sd, sl)
        return cache[key]

    def _hsv_np(self, h, s, v):
        h = np.mod(h, 1.0)
        i = np.floor(h * 6.0)
        fr = h * 6.0 - i
        p = v * (1.0 - s)
        q = v * (1.0 - fr * s)
        t = v * (1.0 - (1.0 - fr) * s)
        ii = (i.astype(np.int64) % 6)
        r = np.select([ii == 0, ii == 1, ii == 2, ii == 3, ii == 4, ii == 5], [v, q, p, p, t, v])
        g = np.select([ii == 0, ii == 1, ii == 2, ii == 3, ii == 4, ii == 5], [t, v, v, q, p, p])
        b = np.select([ii == 0, ii == 1, ii == 2, ii == 3, ii == 4, ii == 5], [p, p, t, v, v, q])
        return r, g, b

    def _core_patch(self, kind, size, col, extra, ph):
        key = (kind, int(size), tuple(int(c) for c in col),
               tuple(tuple(int(x) for x in t) for t in extra), int(ph * 24.0) % 24)
        cache = self._cache("_core_cache")
        got = cache.get(key)
        if got is not None:
            return got
        n = max(8, int(size))
        rad = n / 2.0
        ax = np.arange(n, dtype=np.float64) - (n - 1) / 2.0
        dx = ax[None, :] / rad
        dy = ax[:, None] / rad
        d2 = dx * dx + dy * dy
        d = np.sqrt(d2)
        nz = np.sqrt(np.clip(1.0 - d2, 0.0, 1.0))
        ang = np.arctan2(dy, dx)
        f = np.clip((1.04 - d) / 0.09, 0.0, 1.0)
        tau = ph * 6.283185307179586
        if kind == "drip":
            sw = np.sin(ang * 2.0 + d * 7.5 - tau * 0.35)
            swh = (0.5 + 0.5 * sw) ** 1.7
            thick = np.clip(0.52 + 0.48 * dy, 0.0, 1.0)
            lum = 0.13 + 0.36 * thick * (0.32 + 0.68 * swh) + 0.14 * nz
            sp = np.exp(-(((dx + 0.36) ** 2 + (dy + 0.40) ** 2) / 0.17))
            lr = lum * col[0] + sp * 208.0
            lg = lum * col[1] + sp * 190.0
            lb = lum * col[2] + sp * 156.0
            a = (0.84 + 0.16 * thick) * f * 246.0
        elif kind == "spec":
            t = np.clip(0.52 - dy * 2.30, 0.0, 1.0) ** 0.60
            band = np.exp(-(((dy + 0.16 + 0.11 * np.sin(tau * 0.50)) / 0.11) ** 2.0))
            band2 = np.exp(-(((dy - 0.46 + 0.07 * np.cos(tau * 0.35)) / 0.09) ** 2.0))
            sp = np.exp(-(((dx + 0.44 + 0.05 * np.sin(tau * 0.40)) ** 2
                           + (dy + 0.50 + 0.04 * np.cos(tau * 0.40)) ** 2) / 0.030))
            lum = 0.07 + 0.82 * t + 0.30 * band + 0.16 * band2 + 1.05 * sp
            lr = lum * col[0]
            lg = lum * col[1]
            lb = lum * col[2]
            edge = np.clip((d - 0.80) / 0.20, 0.0, 1.0)
            lr *= (1.0 - 0.45 * edge)
            lg *= (1.0 - 0.45 * edge)
            lb *= (1.0 - 0.42 * edge)
            a = f * 250.0
        elif kind == "film":
            rim = np.exp(-(((d - 0.88) / 0.24) ** 2.0))
            hue = 0.565 + 0.095 * np.sin(ang * 2.0 + d * 3.4 + tau * 0.25)
            sat = 0.34 + 0.34 * rim
            val = 0.22 + 0.78 * rim
            hr, hg, hb = self._hsv_np(hue, sat, val)
            hr = hr * 255.0
            hg = hg * 255.0
            hb = hb * 255.0
            mix = 0.35 + 0.65 * rim
            lr = hr * mix + col[0] * (1.0 - mix) * 0.55
            lg = hg * mix + col[1] * (1.0 - mix) * 0.55
            lb = hb * mix + col[2] * (1.0 - mix) * 0.55
            sp = np.exp(-(((dx + 0.38) ** 2 + (dy + 0.44) ** 2) / 0.045))
            lr += sp * 206.0
            lg += sp * 230.0
            lb += sp * 252.0
            a = (0.14 + 0.86 * rim) * f * 255.0
        elif kind == "poem":
            inkc = extra[0] if extra else (72, 92, 130)
            gold = extra[1] if len(extra) > 1 else (216, 178, 108)
            sl = np.sin(ang * 3.0 + d * 5.0 - tau * 0.30)
            silk = (0.5 + 0.5 * sl) ** 3.0
            deep = np.clip(1.05 - d, 0.0, 1.0)
            vn = np.sin(ang * 2.0 + d * 3.2 - tau * 0.55)
            vein = np.exp(-(vn * vn) / 0.030) * deep
            lum = 0.26 + 0.62 * silk * deep + 0.26 * nz
            lr = lum * inkc[0] + vein * gold[0] * 0.40
            lg = lum * inkc[1] + vein * gold[1] * 0.40
            lb = lum * inkc[2] + vein * gold[2] * 0.40
            sp = np.exp(-(((dx + 0.10) ** 2 + (dy + 0.14) ** 2) / 0.10))
            lr += sp * gold[0] * 1.05
            lg += sp * gold[1] * 1.05
            lb += sp * gold[2] * 1.05
            a = (0.80 + 0.20 * deep) * f * 250.0
        else:
            sw = np.sin(ang * 2.0 + d * 7.5 - tau * 0.35)
            swh = (0.5 + 0.5 * sw) ** 1.7
            thick = np.clip(0.52 + 0.48 * dy, 0.0, 1.0)
            lum = 0.13 + 0.36 * thick * (0.32 + 0.68 * swh) + 0.14 * nz
            sp = np.exp(-(((dx + 0.36) ** 2 + (dy + 0.40) ** 2) / 0.17))
            lr = lum * col[0] + sp * 208.0
            lg = lum * col[1] + sp * 190.0
            lb = lum * col[2] + sp * 156.0
            a = (0.84 + 0.16 * thick) * f * 246.0
        arr = np.zeros((n, n, 4), dtype=np.uint8)
        arr[..., 0] = np.clip(lr, 0, 255).astype(np.uint8)
        arr[..., 1] = np.clip(lg, 0, 255).astype(np.uint8)
        arr[..., 2] = np.clip(lb, 0, 255).astype(np.uint8)
        arr[..., 3] = np.clip(a, 0, 255).astype(np.uint8)
        surf = pygame.image.frombuffer(arr.tobytes(), (n, n), "RGBA").copy()
        if len(cache) > 120:
            cache.clear()
        cache[key] = surf
        return surf

    def _skin_core(self, px, py, ir, kind) -> None:
        s = max(0.001, float(_ScaledDraw._s()))
        ox, oy = _ScaledDraw._off()
        half = (float(ir) + 1.8) * s
        size = int(math.ceil(half * 2.0))
        if size < 6:
            return
        ph = (int(self.anim_t * 8.0) % 24) / 24.0
        extra = ()
        if kind == "poem":
            extra = (tuple(self.pskin.get("ink", (72, 92, 130))),
                     tuple(self.pskin.get("gold", (216, 178, 108))))
        pat = self._core_patch(kind, size, tuple(self.pcol), extra, ph)
        dst = _raw(self.fx)
        dst.blit(pat, (int(round(px * s + ox - size / 2.0)),
                       int(round(py * s + oy - size / 2.0))))

    def _body_core(self, px, py, ir, core_col, base_a: float) -> None:
        s = max(0.001, float(_ScaledDraw._s()))
        ox, oy = _ScaledDraw._off()
        rad = float(ir) + 0.9
        size = int(math.ceil(rad * 2.0 * s + 2.0))
        if size < 8:
            if base_a > 0.0:
                pygame.draw.circle(self.fx, CONFIG["BG"], (px, py), ir)
            pygame.draw.circle(self.fx, core_col, (px, py), 3)
            return
        dk, lt = self._shade_patches(size, tuple(self.pcol), base_a)
        dst = _raw(self.fx)
        bx = int(round(px * s + ox - size / 2.0))
        by = int(round(py * s + oy - size / 2.0))
        if base_a > 0.0:
            dst.blit(dk, (bx, by))
        dst.blit(lt, (bx, by), None, pygame.BLEND_RGBA_ADD)
        gs = max(4, int(round(float(ir) * 0.62 * s)))
        gl = self._gloss_patch(gs, tuple(core_col), 1.90)
        dst.blit(gl, (int(round(px * s + ox - float(ir) * 0.30 * s - gs / 2.0)),
                      int(round(py * s + oy - float(ir) * 0.34 * s - gs / 2.0))))

    def _iris_core(self, px, py, ir) -> None:
        sk = self.pskin
        dark = tuple(sk.get("film_dark", (26, 24, 46)))
        s = max(0.001, float(_ScaledDraw._s()))
        ox, oy = _ScaledDraw._off()
        half = (float(ir) + 1.8) * s
        size = int(math.ceil(half * 2.0))
        if size < 6:
            return
        tmp = getattr(self, "_core_tmp", None)
        if tmp is None or tmp.get_width() != size:
            tmp = pygame.Surface((size, size), pygame.SRCALPHA)
            self._core_tmp = tmp
        else:
            tmp.fill((0, 0, 0, 0))
        c = size / 2.0
        irs = float(ir) * s
        _REAL_DRAW.circle(tmp, (*dark, 236), (c, c), irs, 0)
        _REAL_DRAW.circle(tmp, (*self._shift_hue(self.pcol, 0.10), 62),
                          (c, c), irs, max(1, int(round(s))))
        _raw(self.fx).blit(tmp, (int(round(px * s + ox - c)),
                                 int(round(py * s + oy - c))))

    def _render_logo(self, scale: float, ss: int, sub_off: float = 0.0) -> pygame.Surface:
        segs = int(CONFIG["LOGO_BEZ_SEGMENTS"])
        base_w, base_h = 120.0, 160.0
        disp_w = max(6, int(round(base_w * scale)))
        disp_h = max(6, int(round(base_h * scale)))
        col = self.pcol
        off_ss = sub_off * float(ss)

        def draw_fn(big, s):
            sc = scale * float(s)
            col_a = (col[0], col[1], col[2], 255)

            tx, ty = 26.0, -33.0
            tsz = float(CONFIG["LOGO_SHADOW_SIZE"])
            tang = math.radians(float(CONFIG["LOGO_SHADOW_ROT"]))
            ca, sa = math.cos(tang), math.sin(tang)
            tri = []
            for px, py in ((0.0, -tsz), (-tsz * 0.866, tsz * 0.5), (tsz * 0.866, tsz * 0.5)):
                tri.append((tx + px * ca - py * sa, ty + px * sa + py * ca))

            ctrl_l = (-20.0, -18.0)
            ctrl_r = (20.0, -18.0)
            xs = [0.0, -22.0, 22.0, ctrl_l[0], ctrl_r[0],
                  -22.0, 22.0,
                  -3.5, 3.5]
            xs += [q[0] for q in tri]
            cx_logic = (min(xs) + max(xs)) * 0.5
            ox = (base_w * 0.5 - cx_logic) * sc
            oy = 55.0 * sc + off_ss

            def T(lx, ly):
                return (ox + lx * sc, oy + ly * sc)

            lw = max(1, int(round(2.0 * sc)))

            top = (0.0, -40.0)
            bl = (-22.0, 4.0)
            ctrl_l = (-20.0, -18.0)
            left_pts = []
            for i in range(segs + 1):
                t = i / segs
                x = (1-t)**2 * top[0] + 2*(1-t)*t * ctrl_l[0] + t**2 * bl[0]
                y = (1-t)**2 * top[1] + 2*(1-t)*t * ctrl_l[1] + t**2 * bl[1]
                left_pts.append(T(x, y))

            ccx, ccy, rr = 0.0, 4.0, 22.0
            arc_pts = []
            for i in range(segs + 1):
                t = i / segs
                a = math.pi * (1.0 - t)
                arc_pts.append(T(ccx + rr * math.cos(a), ccy + rr * math.sin(a)))

            br = (22.0, 4.0)
            ctrl_r = (20.0, -18.0)
            right_pts = []
            for i in range(segs + 1):
                t = i / segs
                x = (1-t)**2 * br[0] + 2*(1-t)*t * ctrl_r[0] + t**2 * top[0]
                y = (1-t)**2 * br[1] + 2*(1-t)*t * ctrl_r[1] + t**2 * top[1]
                right_pts.append(T(x, y))

            pygame.draw.lines(big, col_a, False, left_pts + arc_pts + right_pts, lw)

            sy0, sy1 = 26.0, 52.0
            seg_n = 12
            for i in range(seg_n):
                t0 = i / seg_n
                t1 = (i + 1) / seg_n
                y0 = sy0 + (sy1 - sy0) * t0
                y1 = sy0 + (sy1 - sy0) * t1
                w = max(1, int(round((2.0 - t0 * 1.2) * sc)))
                pygame.draw.line(big, col_a, T(0.0, y0), T(0.0, y1), w)

            for dy, rr_, aa0 in [(62.0, 3.5, 180), (74.0, 2.5, 110), (84.0, 1.5, 60)]:
                q = T(0.0, dy)
                pygame.draw.circle(big, (col[0], col[1], col[2], aa0),
                                   (int(round(q[0])), int(round(q[1]))),
                                   max(1, int(round(rr_ * sc))))

            tpts = [(int(round(T(q[0], q[1])[0])), int(round(T(q[0], q[1])[1])))
                    for q in tri]
            if CONFIG["LOGO_SHADOW_FILL"] > 0:
                pygame.draw.polygon(big, (col[0], col[1], col[2],
                                          int(CONFIG["LOGO_SHADOW_FILL"])), tpts)
            pygame.draw.polygon(big, (col[0], col[1], col[2],
                                      int(CONFIG["LOGO_SHADOW_ALPHA"])),
                                tpts, max(1, int(round(1.5 * sc))))

        with _no_scale():
            out = self._ss_draw(disp_w, disp_h + 1, ss, draw_fn)
        return out.convert_alpha()

    def _draw_logo(self, surface, cx, cy, scale=1.0, alpha=255) -> None:
        img_scale = scale * float(self.rscale)
        vs = self._logo_variants(img_scale)
        off = breath_wave(self.anim_t * CONFIG["LOGO_ANIM_HZ"],
                          CONFIG["ANIM_DWELL"],
                          CONFIG["ANIM_WAVE"]) * CONFIG["ANIM_LOGO_BREATH_AMP"] * scale
        self._blit_shifted(surface, vs,
                           cx - 60.0 * scale, cy - 55.0 * scale + off, alpha)

    @staticmethod
    def _blit_shifted(dst: pygame.Surface, variants: List[pygame.Surface],
                      x: float, y: float, alpha: float = 255.0) -> None:
        iy = math.floor(y)
        frac = y - iy
        n = len(variants)
        idx = int(frac * n) % n
        img = variants[idx]
        if alpha >= 255.0:
            dst.blit(img, (int(x), int(iy)))
        else:
            t = img.copy()
            t.set_alpha(int(alpha))
            dst.blit(t, (int(x), int(iy)))

    def _big_font(self, font: FTFont, mul: int) -> FTFont:
        key = (id(font), mul)
        f = self._big_font_cache.get(key)
        if f is None:
            f = self._mkfont(max(4, int(font.size * mul)),
                             getattr(font, "weight", None) or "s", font.bold)
            self._big_font_cache[key] = f
        return f

    def _tracked_variants(self, text: str, font: FTFont, spacing: int,
                          color: Tuple[int, int, int],
                          space_extra: int = 0) -> List[pygame.Surface]:
        key = (text, id(font), spacing, tuple(color),
               round(float(self.rscale), 4),
               int(space_extra))
        cached = self._tracked_cache.get(key)
        if cached is not None:
            return cached
        mul = int(CONFIG["SUBPIX_STEPS"])
        sc = float(self.rscale) or 1.0
        big = self._big_font(font, mul)
        items = [big.glyph(ch, color) for ch in text]
        sp_big = int(round(spacing * sc * mul))
        se_big = int(round(space_extra * sc * mul))
        asc = max((b for _, b in items), default=1)
        desc = max((g.get_height() - b for g, b in items), default=1)
        total_big = (sum(g.get_width() for g, _ in items)
                     + sp_big * max(0, len(items) - 1)
                     + se_big * sum(1 for ch in text if ch == " "))
        h_big = max(1, asc + desc)
        line = pygame.Surface((max(1, total_big), h_big), pygame.SRCALPHA)
        x = 0
        for i, (g, b) in enumerate(items):
            line.blit(g, (x, asc - b))
            x += g.get_width() + sp_big + (se_big if text[i] == " " else 0)
        w = max(1, int(round(line.get_width() / mul)))
        h = max(1, int(round(line.get_height() / mul)) + 1)
        out = []
        for i in range(mul):
            canvas = pygame.Surface((max(1, line.get_width()),
                                     max(1, line.get_height() + mul)), pygame.SRCALPHA)
            canvas.blit(line, (0, i))
            out.append(pygame.transform.smoothscale(canvas, (w, h)).convert_alpha())
        self._tracked_cache[key] = out
        return out

    def _title_shade(self, surf: pygame.Surface, i: int) -> pygame.Surface:
        w, h = surf.get_size()
        cache = self._cache("_title_grad_cache")
        key = (int(i), int(w), int(h))
        got = cache.get(key)
        if got is not None:
            return got
        top = tuple(CONFIG["TITLE_GRAD_TOP"])
        bot = tuple(CONFIG["TITLE_GRAD_BOT"])
        if top == bot:
            cache[key] = surf
            return surf
        a = pygame.surfarray.array_alpha(surf)
        ys = (np.arange(h, dtype=np.float32) / max(1.0, float(h - 1))).reshape(1, h)
        rgb = np.zeros((w, h, 3), dtype=np.uint8)
        for c in range(3):
            rgb[..., c] = (float(top[c])
                           + (float(bot[c]) - float(top[c])) * ys).astype(np.uint8)
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.surfarray.blit_array(out, rgb)
        pa = pygame.surfarray.pixels_alpha(out)
        pa[:] = a
        del pa
        res = out.convert_alpha()
        cache[key] = res
        return res

    def _menu_title_line(self) -> List[pygame.Surface]:
        base = self._tracked_variants("SYRUP", self.f_title, 16, (235, 240, 248))
        return [self._title_shade(b, i) for i, b in enumerate(base)]



    def _menu_tagline_line(self) -> List[pygame.Surface]:
        text = self.S["tagline"]
        if self.use_cjk:
            return self._tracked_variants(text, self.f_tag,
                                          int(CONFIG["MENU_TAG_TRACK_CJK"]),
                                          CONFIG["G_60"])
        sc = float(self.rscale) or 1.0
        try:
            tw = self._menu_title_line()[0].get_width() / sc
        except Exception:
            tw = 0.0
        cap = tw * float(CONFIG["MENU_TAG_MAX_RATIO"])
        plan = [(int(a), int(b)) for a, b in CONFIG["MENU_TAG_TRACK_LATIN"]]
        for sp, se in plan[:-1]:
            line = self._tagline_line(sp, se)
            if tw <= 0 or line[0].get_width() / sc <= cap:
                return line
        sp, se = plan[-1]
        return self._tagline_line(sp, se)

    def _tagline_line(self, sp: int, se: int) -> List[pygame.Surface]:
        return self._tracked_variants(self.S["tagline"], self.f_tag, sp,
                                      CONFIG["G_60"], se)

    def draw(self) -> None:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        _invalidate_view_cache()
        if getattr(self, "_pending_frames", 0) > 0 and not self.fullscreen:
            rw = getattr(self, "_resize_win", None)
            w = rw[0] if rw else self.win_w
            h = rw[1] if rw else self.win_h
            self._stretch_last_frame(int(w), int(h))
            return
        _raw(self.screen).blit(self.static_bg, (0, 0))

        if self.mode == "MENU":
            if self.appear_open and self.gallery_open:
                self._draw_gallery(W, H)
                self._draw_cursor()
                self._draw_debug(W, H)
                self._present()
                return
            if self.appear_open:
                self._draw_appear(W, H)
                self._draw_cursor()
                self._draw_debug(W, H)
                self._present()
                return
            if self.ms_open:
                self._draw_ms(W, H)
                self._draw_cursor()
                self._draw_debug(W, H)
                self._present()
                return
            self._draw_menu()
            if self.esc_open or self.esc_anim.value > 0.001:
                self._draw_esc_panel(W, H)
            if self.toast_timer > 0:
                self._draw_toast(W, H)
            self._draw_cursor()
            self._draw_fade(W, H)
            self._draw_debug(W, H)
            self._present()
            return

        self.fx.fill((0, 0, 0, 0))

        for s in self.slimes:
            lt = 1.0 - s["age"] / s["life"]
            r = int(s["radius"] * (0.75 + 0.25 * lt))
            cx, cy = float(s["pos"][0]), float(s["pos"][1])
            col = CONFIG["SLIME_COLOR"]
            pygame.draw.circle(self.fx, (*col, int(30 * lt)), (cx, cy), r)
            pygame.draw.circle(self.fx, (*col, int(70 * lt)), (cx, cy), max(1, r * 2 // 3))
            pygame.draw.circle(self.fx, (*col, int(110 * lt)), (cx, cy), max(1, r // 3))

        for trail in self.ai_trails:
            n = len(trail)
            for i in range(1, n):
                t = i / n
                pygame.draw.line(self.fx, (*CONFIG["C_THREAT"], int(160 * t * t)),
                                 (float(trail[i-1][0]), float(trail[i-1][1])),
                                 (float(trail[i][0]), float(trail[i][1])), max(1, int(6 * t)))
        self._draw_player_trail()
        self._draw_sword_qi()
        if self.fx_afterimage:
            self._draw_afterimages()


        for sp in self.pending_spawns:
            prog = sp["timer"] / sp["total"]
            r = int(12 + 52 * prog); a = int(70 + 185 * (1.0 - prog))
            x, y = float(sp["pos"][0]), float(sp["pos"][1])
            _wc = CONFIG["C_SPLIT"] if int(sp.get("type", 0)) == 1 else CONFIG["C_THREAT"]
            pygame.draw.circle(self.fx, (*_wc, a), (x, y), r, 2)
            pygame.draw.circle(self.fx, (*_wc, min(255, a + 40)), (x, y), 3)

        _gs = float(self.rscale) or 1.0
        if CONFIG["GLOW_ENABLE_THREAT"]:
            gw, gh = self.glow_threat.get_size()
            hw, hh = gw / (2.0 * _gs), gh / (2.0 * _gs)
            for ap in self.ai_positions:
                self.fx.blit(self.glow_threat, (ap[0] - hw, ap[1] - hh))
        px, py = float(self.player_pos[0]), float(self.player_pos[1])
        if CONFIG["GLOW_ENABLE_PLAYER"]:
            gw, gh = self.glow_player.get_size()
            hw, hh = gw / (2.0 * _gs), gh / (2.0 * _gs)
            self.fx.blit(self.glow_player,
                         (self.player_pos[0] - hw, self.player_pos[1] - hh))
        if CONFIG["GLOW_ENABLE_SPITTER"]:
            gw, gh = self.glow_spitter.get_size()
            hw, hh = gw / (2.0 * _gs), gh / (2.0 * _gs)
            for sp in self.spitters:
                self.fx.blit(self.glow_spitter, (sp["pos"][0] - hw, sp["pos"][1] - hh))

        for p in self.projectiles:
            px2, py2 = float(p["pos"][0]), float(p["pos"][1])
            vx, vy = p["vel"]; nrm = math.hypot(vx, vy) + 1e-6
            pygame.draw.line(self.fx, (*CONFIG["C_SPITTER"], 160),
                             (px2 - vx / nrm * 22, py2 - vy / nrm * 22), (px2, py2), 3)

        for r in self.rings:
            tt = r["life"] / r["maxlife"]
            pygame.draw.circle(self.fx, (*r["color"], int(240 * tt)),
                               (float(r["pos"][0]), float(r["pos"][1])),
                               int(r["max_r"] * (1.0 - tt)), r["width"])

        for sl in self.slashes:
            tt = sl["life"] / sl["maxlife"]
            a = int(230 * tt)
            sx, sy = sl["pos"]; dx, dy = sl["dir"]
            nrm = math.hypot(dx, dy) + 1e-6; dx, dy = dx / nrm, dy / nrm
            length = 46 * (0.5 + 0.5 * tt)
            p1 = (sx - dx * length, sy - dy * length)
            p2 = (sx + dx * length, sy + dy * length)
            pygame.draw.line(self.fx, (255, 255, 255, a), p1, p2, 3)
            pygame.draw.line(self.fx, (*CONFIG["C_MARK"], a // 2), p1, p2, 1)

        for p in self.particles:
            lt = p["life"] / p["maxlife"]
            pygame.draw.circle(self.fx, (*p["color"], int(255 * lt)),
                               (float(p["pos"][0]), float(p["pos"][1])), max(1.0, 3.5 * lt))

        for s in self.shadows:
            sx, sy = int(s["pos"][0]), int(s["pos"][1])
            lt = s["frames_left"] / CONFIG["SHADOW_LIFE_FRAMES"]
            a = int(160 * (0.35 + 0.65 * lt))
            ang = math.atan2(s["drift_dir"][1], s["drift_dir"][0])
            sz = 11
            pts = [(sx + math.cos(ang + k * (2 * math.pi / 3) + math.pi / 2) * sz,
                    sy + math.sin(ang + k * (2 * math.pi / 3) + math.pi / 2) * sz) for k in range(3)]
            _ds = float(self.rscale)
            sh = pygame.Surface((int(sz * 3 * _ds), int(sz * 3 * _ds)), pygame.SRCALPHA)
            lp = [(p[0] - sx + sz * 3 // 2, p[1] - sy + sz * 3 // 2) for p in pts]
            pygame.draw.polygon(sh, (*self.pcol, a), lp, 2)
            self.fx.blit(sh, (sx - sz * 3 // 2, sy - sz * 3 // 2))

        for sp in self.spitters:
            x, y = float(sp["pos"][0]), float(sp["pos"][1]); r = CONFIG["SPITTER_RADIUS"]
            pts = [(x + math.cos(math.pi / 6 + k * math.pi / 3) * r,
                    y + math.sin(math.pi / 6 + k * math.pi / 3) * r) for k in range(6)]
            charge = 1.0 - min(1.0, sp["timer"] / CONFIG["SPITTER_WARN"])
            base = CONFIG["C_SPITTER"]
            bright = tuple(min(255, int(c * (0.5 + 0.5 * charge))) for c in base)
            pygame.draw.polygon(self.fx, bright, pts, 2)
            pygame.draw.circle(self.fx, base, (x, y), int(4 + 6 * (1.0 - charge)))
        for p in self.projectiles:
            self._sphere(float(p["pos"][0]), float(p["pos"][1]),
                         float(CONFIG["SPITTER_PROJ_R"]), CONFIG["C_SPITTER"])

        stun_pulse_phase = self.anim_t * 2 * math.pi * CONFIG["ANIM_STUN_PULSE_HZ"]
        stun_star_phase  = self.anim_t * 2 * math.pi * CONFIG["ANIM_STUN_STAR_HZ"]
        trap_rot_phase   = self.anim_t * 2 * math.pi * CONFIG["ANIM_TRAP_ROT_HZ"]

        for i, ap in enumerate(self.ai_positions):
            x, y = float(ap[0]), float(ap[1])
            base_color = CONFIG["C_THREAT"]
            if self.ai_flash_frames[i] > 0:
                base_color = (255, 255, 255)
            _tp = self.ai_types[i] if i < len(self.ai_types) else 0
            if _tp == 1:
                self._draw_splitter(x, y, self.ai_flash_frames[i] > 0)
            else:
                self._sphere(x, y, float(CONFIG["AI_RADIUS"]), base_color)
            if self.ai_marks[i] > 0:
                pygame.draw.circle(self.fx, CONFIG["C_MARK"], (x, y), CONFIG["AI_RADIUS"] + 5, 2)
                pygame.draw.circle(self.fx, CONFIG["C_MARK"], (x, y), 2)
            if self.ai_stun_frames[i] > 0:
                pulse = int(CONFIG["AI_RADIUS"] + 8 + 4 * math.sin(stun_pulse_phase))
                pygame.draw.circle(self.fx, CONFIG["C_SPITTER"], (x, y), pulse, 1)
                for k in range(4):
                    ang2 = stun_star_phase + k * math.pi / 2
                    r2 = CONFIG["AI_RADIUS"] + 12
                    tx = x + math.cos(ang2) * r2; ty = y + math.sin(ang2) * r2
                    pygame.draw.line(self.fx, CONFIG["C_SPITTER"], (tx - 3, ty), (tx + 3, ty), 1)
                    pygame.draw.line(self.fx, CONFIG["C_SPITTER"], (tx, ty - 3), (tx, ty + 3), 1)
            if (self.ai_trap_frames[i] > 0
                    or (self.ai_exec_frames[i] > 0 and self.ai_stun_frames[i] <= 0)):
                a0 = trap_rot_phase
                rr = CONFIG["AI_RADIUS"] + 10
                box = (x - rr, y - rr, rr * 2, rr * 2)
                pygame.draw.arc(self.fx, CONFIG["C_THREAT"], box, a0, a0 + 2.2, 2)
                pygame.draw.arc(self.fx, CONFIG["C_THREAT"], box,
                                a0 + math.pi, a0 + math.pi + 2.2, 2)

        self._draw_player_body(px, py)
        if self.fx_poem:
            self._draw_poem()
        if self.iframe_frames > 0:
            segments = 12
            for k in range(segments):
                ang_a = k * (2 * math.pi / segments)
                ang_b = ang_a + (2 * math.pi / segments) * 0.5
                pygame.draw.arc(self.fx, (255, 255, 255),
                                (px - 15, py - 15, 30, 30), ang_a, ang_b, 2)

        if self.player_state == "BACKSWING":
            frac = self.state_frame / max(1, CONFIG["CANCEL_WINDOW_FRAMES"])
            radius = int(15 + 4 * frac); alpha = int(220 * (1.0 - frac))
            _ds = float(self.rscale)
            rng = pygame.Surface((int(80 * _ds), int(80 * _ds)), pygame.SRCALPHA)
            pygame.draw.circle(rng, (*self.pcol, alpha), (40, 40), radius, 2)
            self.fx.blit(rng, (px - 40, py - 40))

        for pop in self.popups:
            t = pop["life"] / pop["maxlife"]
            alpha = int(255 * min(1.0, t * 1.6))
            base = self.f_small.render(pop["text"], True, pop["color"])
            surf = base.copy(); surf.set_alpha(alpha)
            self.fx.blit(surf, (int(pop["pos"][0]) - surf.get_width() // 2, int(pop["pos"][1])))

        ox, oy = self._shake_offset()
        self.screen.blit(self.fx, (ox, oy))
        if not self._vignette_merged:
            self.screen.blit(self.vignette, (0, 0))

        self._draw_hud(W, H)
        self._draw_top_goal(W, H)

        if self.mode == "TRAINING" and self.hint_timer > 0:
            self._draw_training_hint(W, H)

        if self.mode == "RUN" and self.wave_flash > 0:
            self._draw_wave_banner(W, H)
        if self.practice_mode:
            self._draw_practice_panel(W, H)

        if self.game_over and self.death_slowmo_timer <= 0:
            a = min(1.0, max(0.0, self.gameover_anim.value))
            if a > 0.001:
                total = self.score_detonate + self.score_perfect + self.score_kill
                self._tint_full((11, 15, 20, int(215 * a)))
                dy = int((1.0 - a) * 24)
                t1 = self.f_over.render(f"{total}", True, (235, 240, 248))
                t1.set_alpha(int(255 * a))
                self.screen.blit(t1, t1.get_rect(center=(W // 2, H // 2 - 110 + dy)))
                rows = [
                    (self.S["max_chain"], f"{self.chain_max}", (255, 255, 255)),
                    (self.S["detonate_count"], f"{self.detonate_count}", CONFIG["C_THREAT"]),
                    (self.S["perfect_count"], f"{self.perfect_count}", CONFIG["C_PLAYER"]),
                    (self.S["score_detonate"], f"{self.score_detonate}", CONFIG["G_60"]),
                    (self.S["score_perfect"], f"{self.score_perfect}", CONFIG["G_60"]),
                    (self.S["score_kill"], f"{self.score_kill}", CONFIG["G_60"]),
                ]
                y0 = H // 2 - 20 + dy
                for i, (lb, vv, cl) in enumerate(rows):
                    ls = self.f_small.render(lb, True, CONFIG["G_60"]); ls.set_alpha(int(255 * a))
                    vs = self.f_med.render(vv, True, cl); vs.set_alpha(int(255 * a))
                    self.screen.blit(ls, (W // 2 - 130, y0 + i * 24 + 3))
                    self.screen.blit(vs, (W // 2 + 20, y0 + i * 24))
                grects = self._gameover_options_rects()
                gsel_x = float(self.gameover_sel_x.value)
                gsel_w = float(grects[0][2])
                gsel_h = float(grects[0][3])
                gsel_y = float(grects[0][1])
                _ds = float(self.rscale)
                ghi = pygame.Surface((int(gsel_w * _ds), int(gsel_h * _ds)),
                                    pygame.SRCALPHA)
                ghi.fill((*CONFIG["G_20"], int(255 * a)))
                self.screen.blit(ghi, (int(round(gsel_x)), int(round(gsel_y + dy))))
                pygame.draw.rect(self.screen, CONFIG["C_PLAYER"],
                                 (int(round(gsel_x)), int(round(gsel_y + dy + 6)),
                                  4, int(gsel_h - 12)))
                gperiod = 1.0 / max(0.01, CONFIG["ANIM_MENU_SWEEP_HZ"])
                gphase = (self.anim_t % gperiod) / gperiod
                gsx = gphase * (gsel_w + 200) - 100
                if 0 < gsx < gsel_w:
                    pygame.draw.line(self.screen, CONFIG["C_PLAYER"],
                                     (int(round(gsel_x + gsx)), int(round(gsel_y + dy + 6))),
                                     (int(round(gsel_x + gsx)),
                                      int(round(gsel_y + dy + gsel_h - 6))), 1)

                for i, glabel in enumerate([self.S["restart"], self.S["menu"]]):
                    grx = grects[i][0]
                    selected = (i == self.gameover_sel)
                    col = CONFIG["C_PLAYER"] if selected else CONFIG["G_80"]
                    gsrf = self.f_med.render(glabel, True, col)
                    gsrf.set_alpha(int(255 * a))
                    self.screen.blit(gsrf, gsrf.get_rect(
                        center=(grx + grects[i][2] // 2,
                                grects[i][1] + grects[i][3] // 2 + dy)))

                t3 = self.f_tiny.render(
                    "鼠标点击  ·  ←→ 选择  ·  ENTER 确认  ·  R 重开" if self.use_cjk
                    else "click  ·  ←→ select  ·  ENTER confirm  ·  R restart",
                    True, CONFIG["G_40"])
                t3.set_alpha(int(255 * a))
                self.screen.blit(t3, t3.get_rect(center=(W // 2, H // 2 + 208 + dy)))

        if self.paused:
            self._draw_pause_panel(W, H)

        if self.esc_open or self.esc_anim.value > 0.001:
            self._draw_esc_panel(W, H)

        if self.flash > 0:
            self._tint_full((255, 107, 74, int(self.flash * 110)))

        if self.stage_complete_flash > 0:
            self._tint_full((34, 211, 238, int(self.stage_complete_flash * 70)))
        if self.stage_complete_timer > 0:
            a = min(1.0, max(0.0, self.stage_complete_anim.value))
            if a > 0.001:
                txt = "完成" if self.use_cjk else "CLEAR"
                ok = self.f_big.render(txt, True, CONFIG["C_PLAYER"])
                ok.set_alpha(int(255 * a))
                dy = int((1.0 - a) * 20)
                self.screen.blit(ok, ok.get_rect(center=(W // 2, H // 2 - 40 + dy)))

        if self.invert_frames > 0:
            inv = pygame.Surface((self.cw, self.ch)); inv.fill((255, 255, 255))
            iox, ioy = _view_offset()
            inv.blit(_raw(self.screen), (-int(round(iox)), -int(round(ioy))),
                     special_flags=pygame.BLEND_RGB_SUB)
            inv = inv.convert()
            self.screen.blit(inv, (0, 0))

        if self.toast_timer > 0:
            self._draw_toast(W, H)

        self._draw_cursor()
        self._draw_fade(W, H)
        self._draw_debug(W, H)
        self._present()
        self._maybe_snapshot()

    def _maybe_snapshot(self) -> None:
        if self.fullscreen:
            return
        self._snap_tick = (getattr(self, "_snap_tick", 0) + 1) % 8
        if self._snap_tick != 0:
            return
        try:
            self._snapshot = _raw(self.screen).copy()
        except Exception:
            self._snapshot = None

    def _draw_toast(self, W: int, H: int) -> None:
        a = min(1.0, self.toast_timer / 0.5)
        alpha = int(220 * a)
        s = self.f_med.render(self.toast_text, True, CONFIG["C_PLAYER"])
        t = s.copy(); t.set_alpha(alpha)
        self.screen.blit(t, t.get_rect(center=(W // 2, H - 160)))

    def _mech_lines_locked(self, tab: int) -> List[Tuple[str, str, int]]:
        req = MECH_STAGE_REQ.get(tab)
        out = []
        si = -1
        for text, kind in self._mech_lines_for_tab(tab):
            if kind == "head":
                si += 1
            r = req[si] if (req and 0 <= si < len(req)) else 1
            out.append((text, kind, int(r)))
        return out

    def _mech_visible(self, req: int) -> bool:
        if bool(self.save_data.get("training_done", False)):
            return True
        return int(req) <= int(self.save_data.get("training_unlocked_stage", 1))

    def _mech_lock_text(self, req: int) -> str:
        if int(req) >= MECH_LOCK_RUN:
            return self.S["mech_lock_run"]
        return self.S["mech_lock_stage"].replace("{n}", str(int(req)))

    def _ctrl_row_locked(self, i: int) -> bool:
        reqs = CTRL_STAGE_REQ
        if i >= len(reqs):
            return False
        return not self._mech_visible(reqs[i])

    def _draw_padlock(self, x: float, y: float, s: float, col, alpha: float) -> None:
        try:
            w = max(4.0, float(s))
            lw = max(1, int(round(w * 0.11)))
            sh = w * 0.46
            pygame.draw.arc(self.screen, col,
                            (x + w * 0.22, y, w * 0.56, sh * 2.0), 0, math.pi, lw)
            bh = w * 0.54
            bx = x
            by = y + sh
            pygame.draw.rect(self.screen, col, (bx, by, w, bh), lw)
            hw = max(1, int(round(w * 0.10)))
            pygame.draw.line(self.screen, col,
                             (bx + w * 0.5, by + bh * 0.30),
                             (bx + w * 0.5, by + bh * 0.78), hw)
        except Exception:
            pass

    def _mech_lines_for_tab(self, tab: int) -> List[Tuple[str, str]]:
        if tab == 1:
            return []
        dash_cost = CONFIG["DASH_COST"]
        dash_cost_str = str(int(dash_cost)) if float(dash_cost).is_integer() else f"{dash_cost:g}"
        lives = int(CONFIG["RUN_LIVES"])
        sp_wave = str(int(CONFIG["SPLIT_FROM_WAVE"]))
        sp_spd = str(int(round(float(CONFIG["SPLIT_SPEED_MUL"]) * 100)))
        ev_from = str(int(CONFIG["WAVE_EVENT_FROM"]))
        ev_mul = (str(int(CONFIG["ELITE_SCORE_MUL"]))
                  if float(CONFIG["ELITE_SCORE_MUL"]).is_integer()
                  else f"{CONFIG['ELITE_SCORE_MUL']:g}")

        if not self.use_cjk:
            if tab == 0:
                return [
                    ("Field and Units", "head"),
                    ("The player controls a single circular unit that moves freely inside the field. Two hostile unit types exist: Hunters and Spitters. Hunters spawn from the field edge and pursue the player continuously, predicting their movement. Spitters appear from the third wave onward, remain stationary, and periodically fire bolts toward the player.", "body"),
                    ("", "body"),
                    ("Splitters", "head"),
                    ("Splitters are a third hostile type, appearing from wave " + sp_wave + " onward and drawn as a violet hexagon. They move at " + sp_spd + "% of a Hunter's speed, but killing one splits it: two ordinary Hunters are flung out perpendicular to the line between you and the Splitter, landing beyond the detonation radius and stunned for a moment. Elite waves always field Splitters.", "body"),
                    ("", "body"),
                    ("Core Loop", "head"),
                    ("Dashing consumes one energy unit. When energy is depleted, dashing becomes unavailable. Detonation is the only means of recovering energy: each enemy detonated refunds " + dash_cost_str + " energy unit. The core of this game is therefore not evasion, but deliberately approaching, detonating, and withdrawing.", "body"),
                    ("", "body"),
                    ("Mark and Detonate", "head"),
                    ("Passing through a Hunter during a dash applies a Mark, shown as a white ring. Dashing through a marked target again triggers a Detonation: the target is knocked back and coated in slime, " + dash_cost_str + " energy unit is refunded, and score is awarded.", "body"),
                    ("", "body"),
                    ("Shadow and Swap", "head"),
                    ("Each dash leaves a Shadow at its starting point, shown as a cyan triangle. Pressing Shift teleports the player to the Shadow nearest the cursor. Upon teleporting, both the origin and the destination release a shock that coats nearby enemies in slime.", "body"),
                    ("", "body"),
                    ("Slime", "head"),
                    ("Enemies coated in slime move significantly slower. The player is slowed by the same amount while standing in slime and should avoid being immobilized by the slime they have laid down.", "body"),
                    ("", "body"),
                    ("Lives and Waves", "head"),
                    ("In Run mode the player holds " + str(lives) + " lives. Each failure consumes one life; the player then respawns at the centre of the field with brief invulnerability, and nearby enemies and bolts are cleared. When all lives are spent, the run ends. Difficulty rises with each wave: the enemy cap increases, the spawn interval shortens, and Spitters become more numerous, fire faster, and launch faster bolts.", "body"),
                    ("", "body"),
                    ("Wave Events", "head"),
                    ("From wave " + ev_from + " onward, waves alternate in a fixed cycle. Elite waves raise the enemy cap, shorten the spawn interval, always field Splitters, and award score at x" + ev_mul + ". Safe waves halve the enemy cap, greatly extend the spawn interval, field no Splitters, and leave room to recover. The HUD names the current wave type.", "body"),
                    ("", "body"),
                    ("Milestones", "head"),
                    ("Milestones unlock permanent abilities such as an extra life, a shorter swap cooldown, or a higher chain cap. Each can be toggled on its own in the Milestones panel. The more you enable, the higher your load: enemy count, spawn rate, movement speed and bolt speed all rise slightly, and every ability also sharpens the particular pressure that answers it. Score multiplier grows with load as compensation. Switching everything off returns both difficulty and score to their base values.", "body"),
                    ("", "body"),
                    ("Training Mode", "head"),
                    ("Training mode imposes no life limit. A stage resets immediately upon failure and may be retried at any time. It exists to build each of the operations above one at a time. Clearing a stage inside its target time awards a grade from S down to C; grades only ever improve, and the best one is shown on the training row of the main menu.", "body"),
                ]
            return [
                ("Direct Contact with a Hunter", "head"),
                ("Contact with any Hunter results in failure. The target already passed through during the current dash is excluded. Hunters flung out by a killed Splitter are lethal as well.", "body"),
                ("", "body"),
                ("Struck by a Bolt", "head"),
                ("Being hit by a bolt fired from a Spitter results in failure.", "body"),
                ("", "body"),
                ("All Lives Spent", "head"),
                ("In Run mode, each of the above failures consumes one life. The run ends once all " + str(lives) + " lives have been spent.", "body"),
                ("", "body"),
                ("Training Mode", "head"),
                ("Training mode imposes no life limit. A failure resets the current stage immediately, and the stage may be retried without penalty.", "body"),
            ]
        if tab == 0:
            return [
                ("场地与单位", "head"),
                ("玩家操控一枚可在场地内自由移动的圆形单位。场地内存在两类敌方单位：追猎者与喷浆口。追猎者自场地边缘出现，持续追击玩家，并对其移动位置进行预判。喷浆口自第三波起出现，位置固定，定期向玩家所在方向发射弹丸。", "body"),
                ("", "body"),
                ("分裂者", "head"),
                ("分裂者是第三类敌方单位，自第 " + sp_wave + " 波起出现，外观为紫红色六边形。其移动速度为追猎者的 " + sp_spd + "%，但被击杀后会向外分裂：沿与玩家连线垂直的两侧各弹射出一只普通追猎者，落点必定位于引爆范围之外，并附带一段短暂硬直。精英波中必定出现分裂者。", "body"),
                ("", "body"),
                ("核心循环", "head"),
                ("冲刺消耗一格能量，能量耗尽时无法发动冲刺。引爆是恢复能量的唯一途径：每引爆一名敌人，返还 " + dash_cost_str + " 格能量。因此本作的核心并非规避，而是主动接近、完成引爆、随即撤离。", "body"),
                ("", "body"),
                ("标记与引爆", "head"),
                ("冲刺路径经过追猎者时，将为其附加标记，以白色圆环表示。对已标记的目标再次发动冲刺并穿过其所在位置，即触发引爆：目标被击退并陷入黏液，同时返还 " + dash_cost_str + " 格能量并累计得分。", "body"),
                ("", "body"),
                ("影与换位", "head"),
                ("每次冲刺都会在起点留下一枚「影」，以青色三角表示。按下 Shift 键后，玩家瞬移至距鼠标最近的影所在位置。瞬移时，起点与终点各产生一次范围冲击，使范围内敌人陷入黏液。", "body"),
                ("", "body"),
                ("黏液", "head"),
                ("陷入黏液的敌人移动速度显著下降。玩家自身处于黏液中时同样会被减速，应避免被自身铺设的黏液限制移动。", "body"),
                ("", "body"),
                ("生命与波次", "head"),
                ("实战模式下玩家拥有 " + str(lives) + " 条命。每发生一次失败即消耗一条命，随后玩家于场地中央复活并获得短暂无敌，附近的敌人与弹丸将被清除。生命耗尽时本局结束。难度随波次推进而提升：敌人数量上限提高，生成间隔缩短，喷浆口数量增加，其攻击间隔缩短且弹丸速度提升。", "body"),
                ("", "body"),
                ("波次事件", "head"),
                ("自第 " + ev_from + " 波起，波次按固定循环交替。精英波提高敌人上限、缩短生成间隔、必定出现分裂者，本波得分 ×" + ev_mul + "。休整波将敌人上限减半、大幅延长生成间隔，且不出现分裂者，用于喘息与重整。当前波次类型会标注在 HUD 上。", "body"),
                ("", "body"),
                ("里程碑", "head"),
                ("达成里程碑会解锁一项永久能力，例如额外的生命、更短的换位冷却或更高的连锁上限。每项能力都能在里程碑面板中单独开关。开启的项越多，负重越高：敌人数量、生成频率、移动速度与弹速都会小幅提升，且每项能力还会针对性地强化与之对应的压力方向。作为补偿，分数倍率随负重提高。全部关闭时，难度与得分均回到原始值。", "body"),
                ("", "body"),
                ("训练模式", "head"),
                ("训练模式不设生命限制。发生失败时本关立即重置，可随时重新尝试。训练模式用于逐项掌握上述操作。在目标时间内通关会获得评级，自高到低为 S、A、B、C，只升不降，并显示在主菜单的训练行上。", "body"),
            ]
        return [
            ("与追猎者发生直接接触", "head"),
            ("玩家与任一追猎者发生接触即判定失败。本次冲刺路径中已经穿过的目标除外。分裂者被击杀后弹射出的追猎者同样会致败。", "body"),
            ("", "body"),
            ("被弹丸命中", "head"),
            ("被喷浆口发射的弹丸命中即判定失败。", "body"),
            ("", "body"),
            ("生命耗尽", "head"),
            ("实战模式下，每发生一次上述失败即消耗一条生命。全部 " + str(lives) + " 条生命耗尽时，本局结束。", "body"),
            ("", "body"),
            ("训练模式", "head"),
            ("训练模式不设生命限制。发生失败时本关立即重置，可随时重新尝试。", "body"),
        ]

    def _wrap_text(self, text: str, font: FTFont, max_w: int) -> List[str]:
        if not text: return [""]
        adv = font.advances(text)
        out = []
        cur = ""
        cur_w = 0.0
        i = 0
        for ch in text:
            a = adv[i] if i < len(adv) else font.char_w(ch)
            i += 1
            if cur and cur_w + a > max_w:
                out.append(cur)
                cur = ch
                cur_w = a
            else:
                cur = cur + ch
                cur_w += a
        if cur: out.append(cur)
        return out

    def _draw_esc_panel(self, W: int, H: int) -> None:
        a = max(0.0, min(1.0, self.esc_anim.value))
        if a < 0.001:
            return
        alpha_bg = int(225 * a)
        y_off = int((1.0 - a) * 14)

        self._tint_full((11, 15, 20, alpha_bg))

        self._draw_logo(self.screen, 90, 90 + y_off, scale=0.45, alpha=int(140 * a))

        if self.esc_page == "ROOT":
            t = self.f_big.render(self.S["esc_title"], True, CONFIG["G_80"])
            t.set_alpha(int(255 * a))
            self.screen.blit(t, t.get_rect(center=(W // 2, 140 + y_off)))
            pygame.draw.line(self.screen, CONFIG["G_20"], (W // 2 - 240, 180 + y_off), (W // 2 + 240, 180 + y_off))

            opts = self._esc_root_options()
            rects = self._esc_root_rects()
            for i, ((label, _), r) in enumerate(zip(opts, rects)):
                rr = (r[0], r[1] + y_off, r[2], r[3])
                if i == len(opts) - 1 and len(opts) > 1:
                    ly = rr[1] - CONFIG["ESC_ROOT_EXIT_GAP"] // 2
                    sep = pygame.Surface((rr[2], 1), pygame.SRCALPHA)
                    sep.fill((255, 255, 255, 28))
                    sep.set_alpha(int(255 * a))
                    self.screen.blit(sep, (rr[0], ly))
                selected = (i == self.esc_sel)
                if selected:
                    pygame.draw.rect(self.screen, CONFIG["G_20"], rr)
                    pygame.draw.rect(self.screen, CONFIG["C_PLAYER"], (rr[0], rr[1], 4, rr[3]))
                col = CONFIG["C_PLAYER"] if selected else CONFIG["G_80"]
                s = self.f_med.render(label, True, col)
                s.set_alpha(int(255 * a))
                self.screen.blit(s, s.get_rect(center=(rr[0] + rr[2] // 2, rr[1] + rr[3] // 2)))

            self._hint("↑↓ 选择  ·  ENTER 确认  ·  ESC 关闭" if self.use_cjk
                       else "↑↓ select  ·  ENTER confirm  ·  ESC close",
                       W // 2, H - 40, CONFIG["G_60"], a)

        elif self.esc_page == "MECHANICS":
            tabs = self.S["mech_tabs"]
            tab_rects = self._esc_mech_tab_rects()
            for i, (name, r) in enumerate(zip(tabs, tab_rects)):
                active = (i == self.esc_mech_tab)
                if active:
                    pygame.draw.rect(self.screen, CONFIG["G_20"], r)
                    pygame.draw.rect(self.screen, CONFIG["C_PLAYER"], (r[0], r[1], 3, r[3]))
                col = CONFIG["C_PLAYER"] if active else CONFIG["G_60"]
                s = self.f_head.render(name, True, col)
                s.set_alpha(int(255 * a))
                self.screen.blit(s, (r[0] + 16, r[1] + 8))

            sep_x = 320
            pygame.draw.line(self.screen, CONFIG["G_20"], (sep_x, 140), (sep_x, H - 60))

            cx0 = sep_x + 40
            cy0 = 150
            cw = W - cx0 - 60

            lines = self._mech_lines_locked(self.esc_mech_tab)
            line_h = CONFIG["BODY_LINE_H"]
            para_gap = CONFIG["BODY_PARA_GAP"]

            if self.esc_mech_tab == 1:
                _cx, _cw, _cy0, _rh, _g, _bt = self._mech_ctrl_geom()
                n_rows = len(self.S["ctrl_rows"])
                view_h = _bt - _cy0
                total_h = n_rows * (_rh + _g) - _g
                self.esc_mech_max_scroll = max(0.0, total_h - view_h)
            else:
                total_h = 0
                for text, kind, req in lines:
                    if not text:
                        total_h += para_gap; continue
                    if kind == "head":
                        total_h += line_h + 6
                    else:
                        body = text if self._mech_visible(req) else self._mech_lock_text(req)
                        wrapped = self._wrap_text(body, self.f_body, cw)
                        total_h += line_h * len(wrapped) + 4
                self.esc_mech_max_scroll = max(0.0, total_h - (H - cy0 - 60))
            if self.esc_mech_scroll > self.esc_mech_max_scroll:
                self.esc_mech_scroll = self.esc_mech_max_scroll

            tab_fade = CONFIG["MECH_TAB_FADE"]
            tab_a = 1.0
            if self.esc_mech_fade > 0:
                tab_a = 1.0 - self.esc_mech_fade / tab_fade
                tab_a = max(0.4, min(1.0, tab_a))
            content_y_off = int((1.0 - tab_a) * 8) + y_off
            final_a = a * tab_a

            if self.esc_mech_tab == 1:
                self._draw_mech_controls(cx0, cw, H, final_a, content_y_off)

            y = cy0 - int(self.esc_mech_scroll) + content_y_off
            for text, kind, req in lines:
                if not text:
                    y += para_gap; continue
                vis = self._mech_visible(req)
                if kind == "head":
                    hcol = CONFIG["C_PLAYER"] if vis else CONFIG["G_40"]
                    indent = 0
                    if not vis:
                        lk = max(10.0, line_h * 0.5)
                        self._draw_padlock(cx0, y + (line_h - lk * 1.32) * 0.5,
                                           lk, CONFIG["G_40"], final_a)
                        indent = int(lk * 1.5)
                    s = self.f_head.render(text, True, hcol)
                    s.set_alpha(int(255 * final_a))
                    self.screen.blit(s, (cx0 + indent, y))
                    y += line_h + 6
                    pygame.draw.line(self.screen, CONFIG["G_20"],
                                     (cx0, y - 3), (cx0 + min(cw, s.get_width() + indent + 24), y - 3))
                else:
                    body = text if vis else self._mech_lock_text(req)
                    wrapped = self._wrap_text(body, self.f_body, cw)
                    for wi, w in enumerate(wrapped):
                        if 0 < y < H - 20:
                            s = self.f_body.render(w, True,
                                                   CONFIG["G_80"] if vis else CONFIG["G_40"])
                            s.set_alpha(int(255 * final_a))
                            indent = 0
                            if not vis and wi == 0:
                                lk = max(9.0, CONFIG["BODY_LINE_H"] * 0.46)
                                self._draw_padlock(cx0, y + (line_h - lk * 1.32) * 0.4,
                                                   lk, CONFIG["G_40"], final_a)
                                indent = int(lk * 1.6)
                            self.screen.blit(s, (cx0 + indent, y))
                        y += line_h
                    y += 4

            if self.esc_mech_max_scroll > 0:
                tip = self.f_tiny.render("滚轮滚动" if self.use_cjk else "scroll",
                                         True, CONFIG["G_40"])
                tip.set_alpha(int(255 * a))
                self.screen.blit(tip, (W - tip.get_width() - 30, H - 40))

            if self.esc_mech_tab == 1:
                hint_txt = self.S["ctrl_hint"]
            else:
                hint_txt = ("↑↓ / 点击切换标签   ·   ESC 返回" if self.use_cjk
                            else "↑↓ / click to switch tabs   ·   ESC back")
            self._hint(hint_txt, W // 2, H - 20, CONFIG["G_60"], a)

        elif self.esc_page == "SETTINGS":
            t = self.f_big.render(self.S["settings"], True, CONFIG["G_80"])
            t.set_alpha(int(255 * a))
            self.screen.blit(t, t.get_rect(center=(W // 2, 110 + y_off)))
            pygame.draw.line(self.screen, CONFIG["G_20"], (W // 2 - 240, 148 + y_off), (W // 2 + 240, 148 + y_off))

            rects = self._esc_settings_rects()
            n, _sy, _rh, _gap, _bg = self._esc_settings_geom()
            last = n - 1
            specs = self._settings_specs()
            clear_idx = len(specs) if self._esc_has_clear() else -1

            hover = getattr(self, "esc_set_arrow_hover", None)

            pad = int(CONFIG["SET_PAD"])
            sel_i = int(getattr(self, "esc_sub_sel", -1))
            if 0 <= sel_i < len(rects):
                sset = self._esc_settings_rects(True)
                sr = sset[sel_i] if sel_i < len(sset) else rects[sel_i]
                self._hi_track(((self._set_hi_y, float(sr[1] + y_off)),
                                (self._set_hi_h, float(sr[3]))),
                               int(getattr(self, "_set_hi_idx", -1)) >= 0
                               and sel_i != int(getattr(self, "_set_hi_idx", -1)))
            self._set_hi_idx = sel_i
            if 0 <= sel_i < len(rects):
                _sh = float(self._set_hi_h.value)
                if _sh > 1.0:
                    _ds2 = float(self.rscale) or 1.0
                    hl = pygame.Surface((max(1, int(sr[2] * _ds2)),
                                         max(1, int(_sh * _ds2))), pygame.SRCALPHA)
                    hl.fill((*CONFIG["G_20"], int(255.0 * float(np.clip(a, 0.0, 1.0)))))
                    self.screen.blit(hl, (int(round(sr[0])),
                                          int(round(self._set_hi_y.value))))
                    bar = pygame.Surface((max(1, int(4 * _ds2)),
                                          max(1, int(_sh * _ds2))), pygame.SRCALPHA)
                    bar.fill((*CONFIG["C_PLAYER"], int(255.0 * float(np.clip(a, 0.0, 1.0)))))
                    self.screen.blit(bar, (int(round(sr[0])),
                                           int(round(self._set_hi_y.value))))
            for i, r0 in enumerate(rects):
                rr = (r0[0], r0[1] + y_off, r0[2], r0[3])
                selected = (self.esc_sub_sel == i)
                if i == last:
                    lbl = self.f_med.render(self.S["back"], True,
                                            CONFIG["C_PLAYER"] if selected else CONFIG["G_80"])
                    lbl.set_alpha(int(255 * a))
                    self.screen.blit(lbl, lbl.get_rect(center=(rr[0] + rr[2] // 2, rr[1] + rr[3] // 2)))
                    continue
                if i == clear_idx:
                    lcol = CONFIG["C_THREAT"] if selected else CONFIG["G_60"]
                    ls = self.f_med.render(self.S["clear_gray"], True, lcol)
                    ls.set_alpha(int(255 * a))
                    self.screen.blit(ls, (rr[0] + pad, rr[1] + (rr[3] - ls.get_height()) // 2))
                    bar_w = rr[2] - 48
                    bar_x = rr[0] + 24
                    bar_y = rr[1] + rr[3] - 8
                    pygame.draw.rect(self.screen, CONFIG["G_20"], (bar_x, bar_y, bar_w, 3))
                    if selected and self.c_hold_frames > 0:
                        frac = min(1.0, self.c_hold_frames / CONFIG["CLEAR_HOLD_FRAMES"])
                        pygame.draw.rect(self.screen, CONFIG["C_THREAT"],
                                         (bar_x, bar_y, int(bar_w * frac), 3))
                    continue

                title, val, cur, count, adjustable = specs[i]
                vcol = CONFIG["C_PLAYER"] if selected else CONFIG["G_80"]
                if adjustable:
                    _bx, _by, _bw, _bh, aw, ag, vw = self._esc_settings_geom_row(i)
                    cluster_x = self._esc_settings_cluster_x(i, aw, ag, vw)
                    lb, rb = self._esc_settings_arrows(i)
                    vx = cluster_x + aw + ag
                    for side, ar in ((0, lb), (1, rb)):
                        if ar is None:
                            continue
                        can = (cur > 0) if side == 0 else (cur < count - 1)
                        hov = (hover is not None and hover[0] == i and hover[1] == side)
                        self._draw_step_arrow(ar, -1 if side == 0 else 1,
                                              can, hov and can, a, y_off)
                    vs = self._fit_font_render(val, vcol, float(vw)).copy()
                    vs.set_alpha(int(255 * a))
                    self.screen.blit(vs, (vx + (vw - vs.get_width()) // 2,
                                          rr[1] + (rr[3] - vs.get_height()) // 2))
                    max_lbl = max(40.0, cluster_x - rr[0] - pad - 18)
                else:
                    vs = self._fit_font_render(val, vcol, max(60.0, rr[2] * 0.62)).copy()
                    vs.set_alpha(int(255 * a))
                    self.screen.blit(vs, (rr[0] + rr[2] - pad - vs.get_width(),
                                          rr[1] + (rr[3] - vs.get_height()) // 2))
                    max_lbl = max(40.0, rr[2] - pad * 2 - vs.get_width() - 18)
                ls = self._fit_font_render(title, vcol, float(max_lbl)).copy()
                ls.set_alpha(int(255 * a))
                self.screen.blit(ls, (rr[0] + pad, rr[1] + (rr[3] - ls.get_height()) // 2))
                exv = self._set_exp(i)
                if exv > 0.01:
                    tal = int(255.0 * a * float(np.clip(exv, 0.0, 1.0)))
                    ty = rr[1] + rr[3] + 2
                    for ln in self._esc_set_tip_lines(i):
                        ts = self.f_tiny.render(ln, True, CONFIG["G_60"])
                        if tal < 255:
                            ts = ts.copy()
                            ts.set_alpha(tal)
                        self.screen.blit(ts, (rr[0] + pad, ty))
                        ty += int(CONFIG["SET_TIP_LH"])

            keys = pygame.key.get_pressed()
            if clear_idx >= 0 and self.esc_sub_sel == clear_idx and keys[pygame.K_c]:
                self.c_hold_frames += 1
                if self.c_hold_frames >= CONFIG["CLEAR_HOLD_FRAMES"]:
                    self.esc_page = "CLEAR_CONFIRM"
                    self.c_hold_frames = 0
                    self.c_hold2_frames = 0
            else:
                self.c_hold_frames = 0

            self._hint("↑↓ 选择  ·  ←→ 调整  ·  ENTER 确认  ·  ESC 返回"
                       if self.use_cjk else
                       "↑↓ select  ·  ←→ adjust  ·  ENTER confirm  ·  ESC back",
                       W // 2, H - 30, CONFIG["G_60"], a)

        elif self.esc_page == "CLEAR_CONFIRM":
            t = self.f_big.render(self.S["clear_page_title"], True, CONFIG["C_THREAT"])
            t.set_alpha(int(255 * a))
            self.screen.blit(t, t.get_rect(center=(W // 2, 90 + y_off)))
            pygame.draw.line(self.screen, CONFIG["G_20"], (W // 2 - 300, 130 + y_off), (W // 2 + 300, 130 + y_off))

            sd = self.save_data
            rows = [
                (self.S["best_score"], f"{int(sd['best_score'])}"),
                (self.S["best_chain"], f"{int(sd['best_chain'])}"),
                (self.S["best_wave"], f"{int(sd['best_wave'])}"),
                (self.S["stage"], f"STAGE {int(sd['training_unlocked_stage'])} / 5"),
                (self.S["detonate_count"], f"{int(sd['total_detonate'])}"),
                (self.S["perfect_count"], f"{int(sd['total_perfect'])}"),
                ("击杀" if self.use_cjk else "Total kills", f"{int(sd['total_kill'])}"),
                ("总局数" if self.use_cjk else "Total runs", f"{int(sd['total_runs'])}"),
            ]
            y0 = 160 + y_off
            for i, (lb, vv) in enumerate(rows):
                ls = self.f_body.render(lb, True, CONFIG["G_60"]); ls.set_alpha(int(255 * a))
                vs = self.f_body.render(vv, True, CONFIG["G_80"]); vs.set_alpha(int(255 * a))
                self.screen.blit(ls, (W // 2 - 260, y0 + i * 30))
                self.screen.blit(vs, (W // 2 + 260 - vs.get_width(), y0 + i * 30))

            bar_w = 400
            bar_x = W // 2 - bar_w // 2
            bar_y = H - 130
            lbl2 = self.f_body.render(self.S["clear_desc_2"], True, CONFIG["C_THREAT"])
            lbl2.set_alpha(int(255 * a))
            self.screen.blit(lbl2, lbl2.get_rect(center=(W // 2, bar_y - 28)))
            pygame.draw.rect(self.screen, CONFIG["G_20"], (bar_x, bar_y, bar_w, 5))
            keys = pygame.key.get_pressed()
            if keys[pygame.K_c]:
                self.c_hold2_frames += 1
                frac = min(1.0, self.c_hold2_frames / CONFIG["CLEAR_HOLD_FRAMES2"])
                pygame.draw.rect(self.screen, CONFIG["C_THREAT"],
                                 (bar_x, bar_y, int(bar_w * frac), 5))
                if self.c_hold2_frames >= CONFIG["CLEAR_HOLD_FRAMES2"]:
                    self._clear_save()
                    self.esc_page = "SETTINGS"
                    self._set_sel(0)
                    self.c_hold2_frames = 0
            else:
                self.c_hold2_frames = 0

            self._hint("ESC 取消" if self.use_cjk else "ESC cancel",
                       W // 2, H - 40, CONFIG["G_60"], a)

    def _pause_controls(self) -> List[Tuple[str, str]]:
        return [
            (self.S["k_move"], self.S["k_move_d"]),
            (self.S["k_lmb"],  self.S["k_lmb_d"]),
            ("SPACE",          self.S["k_space_d"]),
            ("SHIFT",          self.S["k_shift_d"]),
            ("R",              self.S["k_r_d"]),
            ("ESC / P",        self.S["k_esc_d"]),
            ("TAB",            self.S["k_tab_d"]),
            ("F11",            self.S["k_f11_d"]),
        ]

    def _draw_pause_panel(self, W: int, H: int) -> None:
        self._tint_full((11, 15, 20, 218))

        ttl = self.f_big.render(self.S["paused"], True, CONFIG["G_80"])
        self.screen.blit(ttl, ttl.get_rect(center=(W // 2, 70)))

        panel_top = 110
        options = [
            self.S["continue"],
            self.S["restart_run"] if self.mode == "RUN" else self.S["restart_stage"],
            self.S["exit_run"],
        ]
        rects = self._pause_options_rects()
        last_opt_bottom = max(r[1] + r[3] for r in rects)
        panel_bot = last_opt_bottom + 10

        if self.mode == "TRAINING":
            mid_x = W // 2
            lx = mid_x - 470
            ly = panel_top
            hdr = self.f_small.render(self.S["goal_col"], True, CONFIG["G_60"])
            self.screen.blit(hdr, (lx, ly)); ly += 26
            st = self.stage
            name = CONFIG["STAGE_NAMES"][st-1] if self.use_cjk else STAGE_NAMES_EN[st-1]
            s_surf = self.f_med.render(f"STAGE {st} · {name}", True, CONFIG["C_PLAYER"])
            self.screen.blit(s_surf, (lx, ly)); ly += 34
            goal_desc = CONFIG["STAGE_DESCS"][st-1] if self.use_cjk else STAGE_DESCS_EN[st-1]
            g_surf = self.f_small.render(f"{self.S['progress']}: {goal_desc}", True, CONFIG["G_80"])
            self.screen.blit(g_surf, (lx, ly)); ly += 28
            hdr2 = self.f_small.render(self.S["how_to"], True, CONFIG["G_60"])
            self.screen.blit(hdr2, (lx, ly)); ly += 22
            hint_src = CONFIG["STAGE_HINTS"][st-1] if self.use_cjk else STAGE_HINTS_EN[st-1]
            for p in hint_src.split("·"):
                p = p.strip()
                if not p: continue
                h_surf = self.f_tiny.render("· " + p, True, CONFIG["G_80"])
                self.screen.blit(h_surf, (lx, ly)); ly += 18

            pygame.draw.line(self.screen, CONFIG["G_20"],
                             (mid_x, panel_top - 10), (mid_x, panel_bot))
            rx = mid_x + 40
        else:
            rx = W // 2 - 170

        ry = panel_top
        hdr = self.f_small.render(self.S["controls"], True, CONFIG["G_60"])
        self.screen.blit(hdr, (rx, ry)); ry += 28
        for key, desc in self._pause_controls():
            k_surf = self.f_small.render(key, True, CONFIG["C_PLAYER"])
            self.screen.blit(k_surf, (rx, ry))
            d_surf = self.f_tiny.render(desc, True, CONFIG["G_80"])
            self.screen.blit(d_surf, (rx + 130, ry + 3))
            ry += 22

        for i, (label, r) in enumerate(zip(options, rects)):
            rx2, ry2, rw, rh = r
            selected = (i == self.pause_sel)
            if selected:
                pygame.draw.rect(self.screen, CONFIG["G_20"], (rx2, ry2, rw, rh))
                pygame.draw.rect(self.screen, CONFIG["C_PLAYER"], (rx2, ry2, 4, rh))
            col = CONFIG["C_PLAYER"] if selected else CONFIG["G_80"]
            srf = self.f_med.render(label, True, col)
            self.screen.blit(srf, srf.get_rect(center=(rx2 + rw // 2, ry2 + rh // 2)))

        self._hint("P / ESC 关闭  ·  ↑↓ / 1·2·3 选择" if self.use_cjk
                   else "P / ESC close  ·  ↑↓ / 1·2·3 select",
                   W // 2, H - 30, CONFIG["G_60"])

    def _fit_font_render(self, text: str, color, max_w: float, prefer=None):
        order = [prefer or self.f_med, self.f_small, self.f_tiny]
        for f in order:
            s = f.render(text, True, color)
            if s.get_width() <= max_w:
                return s
        return self.f_tiny.render(
            self._fit_text(self.f_tiny, text, max_w), True, color)

    def _fit_text(self, font: FTFont, text: str, max_w: float) -> str:
        if max_w <= 0:
            return ""
        if font.render(text, True, (255, 255, 255)).get_width() <= max_w:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.render(text[:mid] + "…", True, (255, 255, 255)).get_width() <= max_w:
                lo = mid
            else:
                hi = mid - 1
        return (text[:lo] + "…") if lo > 0 else ""

    def _appear_rows(self) -> int:
        return len(CONFIG["FX_NAMES"]) + 1

    def _appear_options(self, i: int) -> List[str]:
        if i == 1:
            return list(CONFIG["TRAIL_STYLES"] if self.use_cjk
                        else CONFIG["TRAIL_STYLES_EN"])
        return [self.S["on"], self.S["off"]]

    def _appear_adjustable(self, i: int) -> bool:
        if i == 0 or i >= self._appear_rows() - 1:
            return False
        if i == 6:
            return bool(self._skin_unlocked(self._ink_index()))
        return True

    def _appear_arrows(self, i: int) -> Tuple[Tuple[int, int, int, int],
                                              Tuple[int, int, int, int], int, int]:
        r = self._appear_rects()[i]
        aw = max(14, min(int(CONFIG["APPR_ARROW_W"]), r[3] - 8))
        ag = int(CONFIG["APPR_ARROW_GAP"])
        vw = int(max(52, max(self._measure_w(self.f_med, v)
                             for v in self._appear_options(i)) + 8))
        total = aw * 2 + ag * 2 + vw
        cx = int(round(r[0] + r[2] - int(CONFIG["APPR_ARROW_PAD"]) - total))
        cy = r[1] + (r[3] - aw) // 2
        return ((cx, cy, aw, aw), (cx + aw + ag + vw + ag, cy, aw, aw),
                cx + aw + ag, vw)

    def _appear_arrow_at(self, pos) -> Tuple[int, int]:
        n = self._appear_rows()
        for i in range(n):
            if not self._appear_adjustable(i):
                continue
            l, rr, _vx, _vw = self._appear_arrows(i)
            pad = int(CONFIG["APPR_ARROW_HIT_PAD"])
            for side, rect in ((0, l), (1, rr)):
                x, y, w, h = rect
                if (x - pad <= pos[0] <= x + w + pad
                        and y - pad <= pos[1] <= y + h + pad):
                    return i, side
        return -1, -1

    def _appear_rects(self) -> List[Tuple[int, int, int, int]]:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        rh = 46
        n = self._appear_rows()
        y0 = H // 2 - (n * (rh + 10)) // 2 + 20
        return [(int(W // 2 - 300), int(y0 + i * (rh + 10)), 600, rh)
                for i in range(n)]

    def _appear_value(self, i: int) -> str:
        if i == 0:
            return self._skin_label(self.skin)
        if i == 1:
            return (CONFIG["TRAIL_STYLES"] if self.use_cjk
                    else CONFIG["TRAIL_STYLES_EN"])[self.fx_trail]
        if i == 2:
            return self.S["on"] if self.fx_afterimage else self.S["off"]
        if i == 3:
            return self.S["on"] if self.fx_energy_glow else self.S["off"]
        if i == 4:
            return self.S["on"] if self.fx_detonate_self else self.S["off"]
        if i == 5:
            return self.S["on"] if self.fx_swap_ghost else self.S["off"]
        if i == 6:
            if not self._skin_unlocked(self._ink_index()):
                return self.S["skin_locked"]
            return self.S["on"] if self.fx_poem else self.S["off"]
        return self.S["back"]

    def _appear_step(self, i: int, d: int) -> None:
        if i == 0:
            self.skin = self._skin_cycle(d)
            self.save_data["skin"] = self.skin
        elif i == 1:
            self.fx_trail = (self.fx_trail + d) % len(CONFIG["TRAIL_STYLES"])
            self.save_data["fx_trail"] = self.fx_trail
        elif i == 2:
            self.fx_afterimage = not self.fx_afterimage
            self.save_data["fx_afterimage"] = self.fx_afterimage
        elif i == 3:
            self.fx_energy_glow = not self.fx_energy_glow
            self.save_data["fx_energy_glow"] = self.fx_energy_glow
        elif i == 4:
            self.fx_detonate_self = not self.fx_detonate_self
            self.save_data["fx_detonate_self"] = self.fx_detonate_self
        elif i == 5:
            self.fx_swap_ghost = not self.fx_swap_ghost
            self.save_data["fx_swap_ghost"] = self.fx_swap_ghost
        elif i == 6:
            if not self._skin_unlocked(self._ink_index()):
                return
            self.fx_poem = not self.fx_poem
            self.save_data["fx_poem"] = self.fx_poem
        if 0 <= i <= 6:
            save_now(CONFIG["SAVE_PATH"], self.save_data)

    def _on_appear_key(self, e) -> None:
        n = self._appear_rows()
        if e.key == pygame.K_UP:
            self.appear_sel = (self.appear_sel - 1) % n
        elif e.key == pygame.K_DOWN:
            self.appear_sel = (self.appear_sel + 1) % n
        elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            d = -1 if e.key == pygame.K_LEFT else 1
            if self.appear_sel < n - 1:
                self._appear_step(self.appear_sel, d)
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.appear_sel == n - 1:
                self.appear_open = False
            elif self.appear_sel == 0:
                self.gallery_open = True
                self.gallery_sel = self.skin
            else:
                self._appear_step(self.appear_sel, 1)
        elif e.key == pygame.K_ESCAPE:
            self.appear_open = False

    def _on_appear_click(self, mx: float, my: float) -> None:
        n = self._appear_rows()
        rects = self._appear_rects()
        ai, aside = self._appear_arrow_at((mx, my))
        if ai >= 0:
            self.appear_sel = ai
            self._appear_step(ai, -1 if aside == 0 else 1)
            return
        for i, r in enumerate(rects):
            if r[0] <= mx <= r[0] + r[2] and r[1] <= my <= r[1] + r[3]:
                if i == n - 1:
                    self.appear_open = False
                    return
                self.appear_sel = i
                if i == 0:
                    self.gallery_open = True
                    self.gallery_sel = self.skin
                else:
                    self._appear_step(i, 1)
                return

    def _draw_appear(self, W: int, H: int) -> None:
        self._tint_full((11, 15, 20, 205))

        self._head2(W, self.S["appearance"], self.S["appr_sub"], 100, 126)

        rects = self._appear_rects()
        n = self._appear_rows()
        for i, r in enumerate(rects):
            sel = (i == self.appear_sel)
            _ds = float(self.rscale)
            bg = pygame.Surface((int(r[2] * _ds), int(r[3] * _ds)),
                                pygame.SRCALPHA)
            bg.fill((*CONFIG["G_20"], 235))
            self.screen.blit(bg, (r[0], r[1]))
            if sel:
                pygame.draw.rect(self.screen, CONFIG["C_PLAYER"],
                                 (r[0], r[1] + 6, 4, r[3] - 12))
            if i == n - 1:
                lb = self.f_med.render(self.S["back"], True,
                                       CONFIG["C_PLAYER"] if sel else CONFIG["G_80"])
                self.screen.blit(lb, lb.get_rect(center=(r[0] + r[2] // 2,
                                                         r[1] + r[3] // 2)))
                continue
            name = self._fx_label(i)
            lc = (self._skin_text_color(self.skin, CONFIG["G_80"])
                  if i == 0 else (CONFIG["C_PLAYER"] if sel else CONFIG["G_80"]))
            lb = self.f_med.render(name, True, lc)
            self.screen.blit(lb, (r[0] + 24, r[1] + (r[3] - lb.get_height()) // 2))

            val = self._appear_value(i)
            plock = (i == 6 and not self._skin_unlocked(self._ink_index()))
            if i == 0:
                vc = self._skin_text_color(self.skin, CONFIG["G_80"])
            elif plock:
                vc = CONFIG["G_60"]
            else:
                vc = CONFIG["G_80"] if sel else CONFIG["G_60"]
            vs = self.f_med.render(val, True, vc)
            vx = r[0] + r[2] - 24
            pad = 20
            if i == 0:
                cw = 18
                cvx = vx - cw
                self._draw_chevron((cvx, r[1] + (r[3] - 18) // 2, cw, 18),
                                   1.0 if sel else 0.8)
                vx -= cw + pad // 2
                vx -= vs.get_width()
                self.screen.blit(vs, (vx, r[1] + (r[3] - vs.get_height()) // 2))
            elif plock:
                vx -= vs.get_width()
                self.screen.blit(vs, (vx, r[1] + (r[3] - vs.get_height()) // 2))
                self._draw_padlock(r[0] + 24 + lb.get_width() + 14,
                                   r[1] + r[3] / 2.0 - 8, 16, CONFIG["G_60"], 1.0)
            else:
                al_rect, ar_rect, vv_x, vv_w = self._appear_arrows(i)
                self.screen.blit(
                    vs, (vv_x + (vv_w - vs.get_width()) // 2,
                         r[1] + (r[3] - vs.get_height()) // 2))
                a_a = 1.0 if sel else 0.78
                self._draw_step_arrow(al_rect, -1, True, False, a_a, 0)
                self._draw_step_arrow(ar_rect, 1, True, False, a_a, 0)

            if i == 0:
                dr = 7
                dot = self._skin_glyph(self.skin, dr, self.anim_t)
                self.screen.blit(dot, (r[0] + 24 + lb.get_width() + 14,
                                       r[1] + (r[3] - dr * 2) // 2))

        self._hint(self.S["appr_hint"], W // 2, H - 30, CONFIG["G_40"])

    def _skin_preview(self, i: int, rad: float, dyn: bool) -> pygame.Surface:
        s = max(0.001, float(self.rscale))
        k = max(0.5, rad / 12.0)
        s2 = s * k
        wl = float(CONFIG["PV_W"])
        hl = float(CONFIG["PV_H"])
        surf = pygame.Surface((max(6, int(wl * s2)), max(6, int(hl * s2))),
                              pygame.SRCALPHA)
        old_g = _SCALE_GETTER
        old_off = _view_offset()
        old_skin = self.skin
        old_fx = self.fx
        cx = float(CONFIG["PV_CX"])
        cy = hl * 0.5
        _set_view_offset(0.0, 0.0)
        _set_scale_getter(lambda: s2)
        self.skin = i
        self.fx = surf
        old_t = self.anim_t
        if not dyn:
            self.anim_t = float(CONFIG["PV_FREEZE_T"])
        try:
            if dyn:
                pts = []
                for q in range(54):
                    u = q / 53.0
                    pts.append((cx - u * float(CONFIG["PV_TRAIL"]),
                                cy + math.sin(u * 5.0 + self.anim_t * 1.05)
                                * 4.2 * (0.30 + 0.70 * u)))
                skp = CONFIG["SKINS"][i]
                self._trail_ink(pts, float(skp["talpha"]),
                                float(skp["tfade"]),
                                float(skp["twidth"])
                                * float(CONFIG["PV_TRAIL_W"]))
            self._draw_player_body(cx, cy)
            if dyn:
                self._pv_glyph_step(self.anim_t)
                for g in self.pv_gly:
                    lt = g["life"] / g["maxlife"]
                    ga = int(float(CONFIG["PV_GLYPH_A"])
                             * min(1.0, (1.0 - lt) * 6.5) * (lt ** 0.85))
                    if ga < 4:
                        continue
                    try:
                        gs, gw, gh = self._poem_glyph(g["ch"])
                    except Exception:
                        continue
                    prog = 1.0 - lt
                    gs2 = float(CONFIG["PV_GLYPH_SCALE"])
                    ck = (g["ch"], round(gs2, 2))
                    img = self._pv_gly_cache.get(ck)
                    if img is None:
                        if len(self._pv_gly_cache) > 64:
                            self._pv_gly_cache.clear()
                        img = pygame.transform.smoothscale(
                            gs, (max(2, int(round(gw * gs2))),
                                 max(2, int(round(gh * gs2)))))
                        self._pv_gly_cache[ck] = img
                    gx = (g["x"] + math.sin(prog * 6.0 + g["seed"] * 6.283) * 2.0) * s2
                    gy = (g["y"] - prog * float(CONFIG["PV_GLYPH_RISE"])) * s2
                    gg = img.copy()
                    gg.set_alpha(ga)
                    surf.blit(gg, (gx - img.get_width() * 0.5,
                                   gy - img.get_height() * 0.5))
        finally:
            self.fx = old_fx
            self.skin = old_skin
            self.anim_t = old_t
            _set_scale_getter(old_g)
            _set_view_offset(old_off[0], old_off[1])
        return surf

    def _pv_glyph_step(self, tnow: float) -> None:
        tnow = float(tnow)
        if self.pv_gly_t < 0.0:
            self.pv_gly_t = tnow
            self.pv_gly = []
            self.pv_gly_cd = 0.0
            return
        dt = tnow - self.pv_gly_t
        self.pv_gly_t = tnow
        if dt <= 0.0:
            return
        if dt > 0.05:
            dt = 0.05
        out = []
        for g in self.pv_gly:
            g["life"] -= dt
            if g["life"] > 0.0:
                out.append(g)
        self.pv_gly = out
        self.pv_gly_cd -= dt
        if self.pv_gly_cd > 0.0:
            return
        gl = CONFIG.get("INK_PREVIEW_GLYPHS") or ["墨", "极"]
        if not gl:
            self.pv_gly_cd = 1.0
            return
        ch = gl[self.pv_gly_i % len(gl)]
        if any(g["ch"] == ch for g in self.pv_gly):
            self.pv_gly_cd = 0.30
            return
        self.pv_gly_i += 1
        life = float(CONFIG["PV_GLYPH_LIFE"])
        self.pv_gly_cd = (float(CONFIG["PV_GLYPH_CD"])
                          * (0.82 + 0.36 * self._hval(float(self.pv_gly_i), 5.5)))
        self.pv_gly.append({
            "ch": ch,
            "x": float(CONFIG["PV_CX"]) + float(CONFIG["PV_GLYPH"]),
            "y": float(CONFIG["PV_H"]) * 0.5 + 2.0,
            "seed": float(self.pv_gly_i % 7) / 7.0,
            "life": life,
            "maxlife": life})
        if len(self.pv_gly) > 4:
            self.pv_gly = self.pv_gly[-4:]

    def _gallery_rows(self) -> int:
        return len(CONFIG["SKINS"]) + 1

    def _gallery_rects(self) -> List[Tuple[int, int, int, int]]:
        W = CONFIG["WIDTH"]
        rh = 76
        n = self._gallery_rows()
        y0 = 132
        return [(W // 2 - 330, y0 + i * (rh + 10), 660, rh) for i in range(n)]

    def _on_gallery_key(self, e) -> None:
        n = self._gallery_rows()
        if e.key == pygame.K_UP:
            self.gallery_sel = (self.gallery_sel - 1) % n
        elif e.key == pygame.K_DOWN:
            self.gallery_sel = (self.gallery_sel + 1) % n
        elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            d = -1 if e.key == pygame.K_LEFT else 1
            self.gallery_sel = max(0, min(n - 2, self.gallery_sel + d))
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.gallery_sel == n - 1:
                self.gallery_open = False
            elif self._skin_unlocked(self.gallery_sel):
                self.skin = self.gallery_sel
                self.save_data["skin"] = self.skin
                save_now(CONFIG["SAVE_PATH"], self.save_data)
        elif e.key == pygame.K_ESCAPE:
            self.gallery_open = False

    def _on_gallery_click(self, mx: float, my: float) -> None:
        n = self._gallery_rows()
        for i, r in enumerate(self._gallery_rects()):
            if r[0] <= mx <= r[0] + r[2] and r[1] <= my <= r[1] + r[3]:
                if i == n - 1:
                    self.gallery_open = False
                    return
                self.gallery_sel = i
                if self._skin_unlocked(i):
                    self.skin = i
                    self.save_data["skin"] = self.skin
                    save_now(CONFIG["SAVE_PATH"], self.save_data)
                return

    def _draw_gallery(self, W: int, H: int) -> None:
        self._tint_full((11, 15, 20, 212))

        self._head2(W, self.S["skin_gallery"], self.S["skin_gallery_sub"],
                    72, 100)

        rects = self._gallery_rects()
        n = self._gallery_rows()
        rad = 16.0
        for i, r in enumerate(rects):
            _ds = float(self.rscale)
            bg = pygame.Surface((int(r[2] * _ds), int(r[3] * _ds)),
                                pygame.SRCALPHA)
            bg.fill((*CONFIG["G_20"], 235))
            self.screen.blit(bg, (r[0], r[1]))
            sel = (i == self.gallery_sel)
            unlocked = self._skin_unlocked(i)
            if not unlocked:
                dk = pygame.Surface((int(r[2] * _ds),
                                     int(r[3] * _ds)), pygame.SRCALPHA)
                dk.fill((6, 8, 12, 120))
                self.screen.blit(dk, (r[0], r[1]))
            if i == n - 1:
                lb = self.f_med.render(self.S["back"], True,
                                       CONFIG["C_PLAYER"] if sel else CONFIG["G_80"])
                self.screen.blit(lb, lb.get_rect(center=(r[0] + r[2] // 2,
                                                         r[1] + r[3] // 2)))
                continue
            top = bool(CONFIG["SKINS"][i].get("top"))
            if sel:
                pygame.draw.rect(self.screen, CONFIG["C_PLAYER"],
                                 (r[0], r[1] + 6, 4, r[3] - 12))
            pv = self._skin_preview(i, rad, top and unlocked)
            if not unlocked:
                pv.set_alpha(78)
            hl = float(CONFIG["PV_H"]) * max(0.5, rad / 12.0)
            self.screen.blit(pv, (r[0] + 18, r[1] + (r[3] - hl) / 2.0))
            nc = self._skin_text_color(i, CONFIG["G_80"]) if unlocked else CONFIG["G_60"]
            lb = self.f_med.render(self._skin_label(i), True, nc)
            self.screen.blit(lb, (r[0] + 112, r[1] + 18))
            if not unlocked:
                st = self.f_small.render(self._skin_req_text(i), True, CONFIG["G_60"])
                self.screen.blit(st, (r[0] + 112, r[1] + 46))
                self._draw_padlock(r[0] + r[2] - 46, r[1] + r[3] / 2.0 - 11,
                                   22, CONFIG["G_60"], 1.0)
            elif i == self.skin:
                st = self.f_small.render(self.S["skin_in_use"], True, nc)
                self.screen.blit(st, (r[0] + 112, r[1] + 46))
                mk = self.f_small.render("●", True, nc)
                self.screen.blit(mk, (r[0] + r[2] - 46,
                                      r[1] + r[3] / 2.0 - mk.get_height() / 2.0))
            else:
                st = self.f_small.render(self._skin_req_text(i), True, CONFIG["G_60"])
                self.screen.blit(st, (r[0] + 112, r[1] + 46))

        self._hint(self.S["skin_gallery_hint"], W // 2, H - 26, CONFIG["G_40"])

    def _draw_menu(self) -> None:
        W, H = CONFIG["WIDTH"], CONFIG["HEIGHT"]
        S = self.S
        breath = breath_wave(self.anim_t * CONFIG["ANIM_MENU_BREATH_HZ"],
                             CONFIG["ANIM_DWELL"],
                             CONFIG["ANIM_WAVE"]) * CONFIG["ANIM_MENU_BREATH_AMP"]

        off = self._menu_block_offset()
        self._draw_logo(self.screen, W // 2, CONFIG["MENU_LOGO_Y"] + off,
                        scale=CONFIG["MENU_LOGO_SCALE"], alpha=255)

        sc = float(self.rscale) or 1.0
        title_line = self._menu_title_line()
        title_y = CONFIG["MENU_TITLE_Y"] + off + breath
        self._blit_shifted(self.screen, title_line,
                           W / 2 - (title_line[0].get_width() / sc) / 2, title_y)

        tag_line = self._menu_tagline_line()
        tag_y = CONFIG["MENU_TAG_Y"] + off + breath * 0.6
        self._blit_shifted(self.screen, tag_line,
                           W / 2 - (tag_line[0].get_width() / sc) / 2, tag_y)

        div_w = int(min(400, W * 0.34))
        pygame.draw.line(self.screen, CONFIG["G_20"],
                         (W // 2 - div_w // 2, int(CONFIG["MENU_DIV_Y"] + off)),
                         (W // 2 + div_w // 2, int(CONFIG["MENU_DIV_Y"] + off)))

        rects = self._menu_options_rects()

        sel_y = self.menu_sel_y.value
        sel_h = float(rects[0][3])
        sel_x = float(rects[0][0])
        sel_w = float(rects[0][2])
        _ds = float(self.rscale)
        hi = pygame.Surface((int(sel_w * _ds), int(sel_h * _ds)), pygame.SRCALPHA)
        hi.fill((*CONFIG["G_20"], 255))
        self.screen.blit(hi, (int(round(sel_x)), int(round(sel_y))))
        bar_x = sel_x
        bar_h = sel_h - 12
        pygame.draw.rect(self.screen, CONFIG["C_PLAYER"],
                         (int(round(bar_x)), int(round(sel_y + 6)), 4, int(bar_h)))

        period = 1.0 / max(0.01, CONFIG["ANIM_MENU_SWEEP_HZ"])
        phase = (self.anim_t % period) / period
        sweep_x = phase * (sel_w + 200) - 100
        if 0 < sweep_x < sel_w:
            pygame.draw.line(self.screen, CONFIG["C_PLAYER"],
                             (int(round(sel_x + sweep_x)), int(round(sel_y + 6))),
                             (int(round(sel_x + sweep_x)), int(round(sel_y + sel_h - 6))), 1)

        r = rects[0]
        unlocked = int(self.save_data["training_unlocked_stage"])
        sub_txt = (CONFIG["STAGE_NAMES"][self.menu_stage - 1] if self.use_cjk
                   else STAGE_NAMES_EN[self.menu_stage - 1]) if self.menu_stage <= unlocked else S["locked"]
        col = CONFIG["C_PLAYER"] if self.menu_sel == 0 else CONFIG["G_80"]
        lbl = self.f_menu.render(S["training"], True, col)
        lbl_y = r[1] + (r[3] - lbl.get_height()) // 2
        self.screen.blit(lbl, (r[0] + 24, lbl_y))
        sc = CONFIG["G_80"] if self.menu_sel == 0 else CONFIG["G_60"]

        _rk = None
        try:
            _rk = (self.save_data.get("stage_rank") or [None] * 5)[self.menu_stage - 1]
        except Exception:
            _rk = None
        stage_surf = self.f_med.render(
            f"{S['stage']} {self.menu_stage}/5" + (f"  ·  {_rk}" if _rk else ""),
            True, CONFIG["G_80"])
        al_rect, ar_rect, vx, vw = self._menu_arrows()
        mid_y = lambda sf: r[1] + (r[3] - sf.get_height()) // 2
        self.screen.blit(stage_surf,
                         (vx + (vw - stage_surf.get_width()) // 2, mid_y(stage_surf)))
        a_step = 1.0 if self.menu_sel == 0 else 0.72
        _hv = getattr(self, "menu_arrow_hover", None)
        self._draw_step_arrow(al_rect, -1, self.menu_stage > 1,
                              _hv == 0, a_step, 0)
        self._draw_step_arrow(ar_rect, 1, self.menu_stage < unlocked,
                              _hv == 1, a_step, 0)

        s2_x = r[0] + 24 + lbl.get_width() + 14
        max_w = al_rect[0] - s2_x - 12
        if max_w > 24:
            s2 = self.f_tiny.render(self._fit_text(self.f_tiny, sub_txt, max_w), True, sc)
            self.screen.blit(s2, (s2_x, r[1] + (r[3] - s2.get_height()) // 2))

        r = rects[1]
        run_ok = bool(self.save_data.get("training_done", False))
        if run_ok:
            col = CONFIG["C_PLAYER"] if self.menu_sel == 1 else CONFIG["G_80"]
            lbl = self.f_menu.render(S["run"], True, col)
            lbl_y = r[1] + (r[3] - lbl.get_height()) // 2
            self.screen.blit(lbl, (r[0] + 24, lbl_y))
            sc = CONFIG["G_80"] if self.menu_sel == 1 else CONFIG["G_60"]
            s2_x = r[0] + 24 + lbl.get_width() + 14
            max_w = (r[0] + r[2] - 20) - s2_x - 12
            s2 = self.f_tiny.render(self._fit_text(self.f_tiny, S["run_hint"], max_w), True, sc)
            self.screen.blit(s2, (s2_x, r[1] + (r[3] - s2.get_height()) // 2))
        else:
            lbl = self.f_menu.render(S["run_locked"], True, CONFIG["G_40"])
            lbl_y = r[1] + (r[3] - lbl.get_height()) // 2
            self.screen.blit(lbl, (r[0] + 24, lbl_y))
            s2_x = r[0] + 24 + lbl.get_width() + 14
            max_w = (r[0] + r[2] - 20) - s2_x - 12
            s2 = self.f_tiny.render(self._fit_text(self.f_tiny, S["unlock_hint"], max_w),
                                    True, CONFIG["G_40"])
            self.screen.blit(s2, (s2_x, r[1] + (r[3] - s2.get_height()) // 2))

        r = rects[2]
        col = CONFIG["C_PLAYER"] if self.menu_sel == 2 else CONFIG["G_80"]
        lbl = self.f_menu.render(S["milestones"], True, col)
        lbl_y = r[1] + (r[3] - lbl.get_height()) // 2
        self.screen.blit(lbl, (r[0] + 24, lbl_y))
        _dn, _dt = self._ms_done_count()
        cv = self.f_med.render(f"{_dn}/{_dt}", True,
                               CONFIG["C_PLAYER"] if _dn else
                               (CONFIG["G_80"] if self.menu_sel == 2 else CONFIG["G_60"]))
        self.screen.blit(cv, (r[0] + r[2] - 24 - cv.get_width(),
                              r[1] + (r[3] - cv.get_height()) // 2))
        _bx = r[0] + 24 + lbl.get_width() + 14
        _bwmax = (r[0] + r[2] - 24 - cv.get_width() - 16) - _bx - 12
        if _bwmax > 24:
            s2 = self.f_tiny.render(
                self._fit_text(self.f_tiny, S["ms_sub"], _bwmax), True,
                CONFIG["G_80"] if self.menu_sel == 2 else CONFIG["G_60"])
            self.screen.blit(s2, (_bx, r[1] + (r[3] - s2.get_height()) // 2))

        r = rects[3]
        col = CONFIG["C_PLAYER"] if self.menu_sel == 3 else CONFIG["G_80"]
        lbl = self.f_menu.render(S["appearance"], True, col)
        lbl_y = r[1] + (r[3] - lbl.get_height()) // 2
        self.screen.blit(lbl, (r[0] + 24, lbl_y))
        sc2 = CONFIG["G_80"] if self.menu_sel == 2 else CONFIG["G_60"]
        s2_x = r[0] + 24 + lbl.get_width() + 14
        dot_r = 7
        dot = self._skin_glyph(self.skin, dot_r, self.anim_t)
        max_w = (r[0] + r[2] - 20) - s2_x - 12 - (dot_r * 2 + 10)
        nm = self._skin_label(self.skin)
        nc = self._skin_text_color(self.skin, sc2)
        s3 = self.f_small.render(self._fit_text(self.f_small, nm, max_w), True, nc)
        self.screen.blit(s3, (s2_x, r[1] + (r[3] - s3.get_height()) // 2))
        self.screen.blit(dot, (s2_x + s3.get_width() + 10,
                               r[1] + (r[3] - dot_r * 2) // 2))

        sd = self.save_data
        bests = [
            (S["best_score"], f"{int(sd['best_score'])}"),
            (S["best_chain"], f"{int(sd['best_chain'])}"),
            (S["best_wave"],  f"{int(sd['best_wave'])}"),
        ]
        sy = rects[3][1] + rects[3][3]
        stat_y = min(sy + 58, H - 138)
        bw = int(min(200, W * 0.20)); bx0 = W // 2 - (bw * len(bests)) // 2
        for i, (lb, vv) in enumerate(bests):
            cx = bx0 + i * bw + bw // 2
            l_s = self.f_tiny.render(lb, True, CONFIG["G_40"])
            v_s = self.f_med.render(vv, True, CONFIG["G_80"])
            self.screen.blit(l_s, l_s.get_rect(center=(cx, stat_y)))
            self.screen.blit(v_s, v_s.get_rect(center=(cx, stat_y + 26)))

        self._hint(S["menu_hint"], W // 2, H - 24, CONFIG["G_40"])

    def _draw_training_hint(self, W: int, H: int) -> None:
        stage = self.stage
        if stage < 1 or stage > 5: return
        name = CONFIG["STAGE_NAMES"][stage - 1] if self.use_cjk else STAGE_NAMES_EN[stage - 1]
        hint = CONFIG["STAGE_HINTS"][stage - 1] if self.use_cjk else STAGE_HINTS_EN[stage - 1]
        a = min(1.0, self.hint_timer / 0.5) if self.hint_timer < 0.5 else 1.0
        alpha = int(230 * a)
        b1 = self.f_med.render(f"STAGE {stage} · {name}", True, CONFIG["C_PLAYER"])
        b2 = self.f_small.render(hint, True, CONFIG["G_80"])
        t1 = b1.copy(); t1.set_alpha(alpha)
        t2 = b2.copy(); t2.set_alpha(alpha)
        self.screen.blit(t1, t1.get_rect(center=(W // 2, 150)))
        self.screen.blit(t2, t2.get_rect(center=(W // 2, 182)))

    def _draw_wave_banner(self, W: int, H: int) -> None:
        t = self.wave_flash
        a = min(1.0, t / 0.25) if t < 0.25 else 1.0
        a = min(a, min(1.0, (1.4 - t) / 0.4) if t > 1.0 else 1.0)
        alpha = int(230 * max(0.0, min(1.0, a)))
        if alpha <= 2: return
        dy = int((1.0 - min(1.0, t / 0.25)) * -14)
        t1 = self.f_big.render(f"WAVE {self.wave:02d}", True, CONFIG["C_THREAT"])
        t2 = self.f_small.render(self._wave_intro_line(), True, CONFIG["G_80"])
        s1 = t1.copy(); s1.set_alpha(alpha)
        s2 = t2.copy(); s2.set_alpha(alpha)
        self.screen.blit(s1, s1.get_rect(center=(W // 2, 190 + dy)))
        self.screen.blit(s2, s2.get_rect(center=(W // 2, 236 + dy)))

    def _draw_hud(self, W: int, H: int) -> None:
        if self.mode == "TRAINING":
            st = self.stage
            goal = CONFIG["STAGE_GOALS"][st - 1]
            if st == 1:
                prog = f"{self.stage_progress:.1f} / {goal:.0f} {self.S['seconds']}"
            else:
                prog = f"{int(self.stage_progress)} / {int(goal)}"
            h1 = self.f_small.render(f"STAGE {st}", True, CONFIG["C_PLAYER"])
            h2 = self.f_med.render(prog, True, CONFIG["G_80"])
            self.screen.blit(h1, (32, 20))
            self.screen.blit(h2, (32, 40))
        else:
            total = self.score_detonate + self.score_perfect + self.score_kill
            score_surf = self.f_big.render(f"{total}", True, CONFIG["G_80"])
            self.screen.blit(score_surf, (32, 20))
            sub = self.f_tiny.render(f"{self.t:5.1f}{self.S['seconds']}", True, CONFIG["G_60"])
            self.screen.blit(sub, (36, 84))
            if self._has_ms("kill_hud"):
                kc = self.f_tiny.render(
                    f"{self.S['ms_kills']} {int(self.kill_count)}", True, CONFIG["G_60"])
                self.screen.blit(kc, (36, 100))

        if self._marks_on() and self.chain_count > 0 and self.chain_timer > 0:
            idx = min(self.chain_count - 1, len(self._chain_mults()) - 1)
            mult = self._chain_mults()[idx]
            cs = self.f_chain.render(f"CHAIN  x{self.chain_count}   ×{mult}", True, (255, 255, 255))
            self.screen.blit(cs, cs.get_rect(center=(W // 2, 110)))
            bw = 240; bx = W // 2 - bw // 2
            frac = self.chain_bar_tween.value
            pygame.draw.rect(self.screen, CONFIG["G_20"], (bx, 138, bw, 2))
            pygame.draw.rect(self.screen, (255, 255, 255), (bx, 138, int(bw * frac), 2))
        elif self.chain_break_flash > 0:
            alpha = int(255 * (self.chain_break_flash / 18))
            base = self.f_chain.render("CHAIN  BREAK", True, CONFIG["C_THREAT"])
            surf = base.copy(); surf.set_alpha(alpha)
            self.screen.blit(surf, surf.get_rect(center=(W // 2, 110)))

        n_threat = len(self.ai_positions) + len(self.pending_spawns) + len(self.projectiles)
        cnt = self.f_med.render(f"{n_threat:02d}", True, CONFIG["C_THREAT"])
        self.screen.blit(cnt, (W - cnt.get_width() - 32, 22))
        tl = self.f_tiny.render("THREATS", True, CONFIG["G_60"])
        self.screen.blit(tl, (W - tl.get_width() - 32, 52))

        bx = 32
        GAP = 6
        e_val = self.energy_tween.value
        empty = e_val < CONFIG["DASH_COST"] - 1e-6
        blink = 0.5 + 0.5 * math.sin(self.anim_t * 2.0 * math.pi * 1.6)

        y = H - 44
        ey = y

        swap_y = None
        if self._shadows_on():
            swap_y = y - GAP - 11
            y = swap_y - GAP

        lives_y = None
        if self.mode == "RUN":
            lives_y = y - 9
            y = lives_y - GAP

        warn_y = y - 11

        sw, sh, sg = 26, 5, 4
        for i in range(int(CONFIG["MAX_ENERGY"])):
            sx = bx + i * (sw + sg)
            pygame.draw.rect(self.screen, CONFIG["G_20"], (sx, ey, sw, sh))
            fill = min(1.0, max(0.0, e_val - i))
            if fill > 0:
                col = CONFIG["C_PLAYER"]
                if empty:
                    col = tuple(int(round(a + (b - a) * blink))
                                for a, b in zip(CONFIG["C_PLAYER"], CONFIG["C_THREAT"]))
                pygame.draw.rect(self.screen, col,
                                 (sx, ey, int(round(sw * fill)), sh))

        if swap_y is not None:
            lbl = self.f_tiny.render("SWAP", True, CONFIG["G_60"])
            self.screen.blit(lbl, (bx, swap_y))
            cw = 120
            bar_x = bx + 42
            bar_y = swap_y + (11 - 3) // 2
            pygame.draw.rect(self.screen, CONFIG["G_20"], (bar_x, bar_y, cw, 3))
            cf = max(0.0, min(1.0, self.swap_cd_tween.value))
            pygame.draw.rect(self.screen, CONFIG["C_PLAYER"] if cf >= 0.999 else CONFIG["G_60"],
                             (bar_x, bar_y, int(round(cw * cf)), 3))

        if lives_y is not None:
            n = int(CONFIG["RUN_LIVES"])
            for i in range(n):
                sx = bx + i * 14
                alive_i = i < self.lives
                col = CONFIG["C_PLAYER"] if alive_i else CONFIG["G_20"]
                pygame.draw.rect(self.screen, col, (sx, lives_y, 9, 9))
                if alive_i:
                    pygame.draw.rect(self.screen, CONFIG["G_20"], (sx, lives_y, 9, 9), 1)
            lbl = self.f_tiny.render("命" if self.use_cjk else "LIVES", True, CONFIG["G_60"])
            self.screen.blit(lbl, (bx + n * 14 + 6, lives_y - 1))

        if empty:
            warn = self.f_tiny.render("无能量" if self.use_cjk else "NO ENERGY",
                                      True, CONFIG["C_THREAT"])
            warn.set_alpha(int(140 + 115 * blink))
            self.screen.blit(warn, (bx, warn_y))

    def _draw_practice_panel(self, W: int, H: int) -> None:
        ft = self.f_tiny.render(
            f"FRAME {self.frame:6d}   STATE {self.player_state:8s} F{self.state_frame:02d}",
            True, CONFIG["G_80"])
        self.screen.blit(ft, (W // 2 - ft.get_width() // 2, H - 60))

        if self.player_state == "BACKSWING":
            frac = self.state_frame / max(1, CONFIG["CANCEL_WINDOW_FRAMES"])
            bw = 300; bx = W // 2 - bw // 2; by = H - 42
            pygame.draw.rect(self.screen, CONFIG["G_20"], (bx, by, bw, 8))
            pygame.draw.rect(self.screen, CONFIG["C_PLAYER"], (bx, by, int(bw * (1 - frac)), 8))

        cw = 260; bx = W - cw - 32; by = 90
        pygame.draw.rect(self.screen, CONFIG["G_20"], (bx, by, cw, 3))
        if self.chain_timer > 0:
            frac = self.chain_bar_tween.value
            pygame.draw.rect(self.screen, (255, 255, 255), (bx, by, int(cw * frac), 3))

    def run(self) -> None:
        while True:
            raw_dt = self.clock.tick(CONFIG["FPS"]) / 1000.0
            self.anim_t += raw_dt
            dt = min(raw_dt, 1.0 / 24.0)

            self.handle_events()
            self._consume_resize()
            self._frame_t0 = time.perf_counter()

            self.menu_sel_y.update(raw_dt)
            self.esc_anim.update(raw_dt)
            self._tick_ui_exp(raw_dt)
            self.energy_tween.set_target(self.energy, CONFIG["UI_TWEEN_NORMAL"], ease_out_cubic)
            self.energy_tween.update(raw_dt)
            if self.swap_cd_frames > 0:
                target = 1.0 - self.swap_cd_frames / max(
                    1, int(getattr(self, "swap_cd_max", CONFIG["SWAP_CD_FRAMES"])))
            else:
                target = 1.0
            self.swap_cd_tween.set_target(target, CONFIG["UI_TWEEN_NORMAL"], ease_out_cubic)
            self.swap_cd_tween.update(raw_dt)
            if self.chain_timer > 0:
                chain_frac = self.chain_timer / CONFIG["CHAIN_WINDOW_FRAMES"]
            else:
                chain_frac = 0.0
            self.chain_bar_tween.set_target(chain_frac, CONFIG["UI_TWEEN_FAST"], ease_out_cubic)
            self.chain_bar_tween.update(raw_dt)
            self.gameover_anim.update(raw_dt)
            self.gameover_sel_x.update(raw_dt)
            self.stage_complete_anim.update(raw_dt)

            if self.esc_open and self.esc_anim.target < 0.5 and self.esc_anim.value < 0.005:
                self.esc_open = False
                self.esc_anim.snap(0.0)

            if self.esc_open:
                self.frame += 1
                self._tick_fade(raw_dt)
                if self.esc_mech_fade > 0:
                    self.esc_mech_fade = max(0.0, self.esc_mech_fade - raw_dt)
                self._update_esc_hover()
                if self.toast_timer > 0:
                    self.toast_timer = max(0.0, self.toast_timer - raw_dt)
                self.draw()
                continue

            if self.paused:
                self._tick_fade(raw_dt)
                self.draw()
                continue

            if self.mode == "MENU":
                self.frame += 1
                self._tick_fade(raw_dt)
                if self.toast_timer > 0:
                    self.toast_timer = max(0.0, self.toast_timer - raw_dt)
                self.draw()
                continue

            if not self.game_over:
                self.update(dt)
            else:
                self._update_gameover(dt)

            self.draw()


if __name__ == "__main__":
    Game().run()
