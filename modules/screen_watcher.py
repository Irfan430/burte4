"""modules/screen_watcher.py — Real-time screen monitor.

Takes a screenshot every N seconds. Detects:
- Active window title & app name
- Popups, dialogs, error messages
- Significant visual changes
Feeds context to NOVA's brain automatically.
"""
import hashlib
import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)


class ScreenWatcher:
    """Continuously monitors the screen and emits context updates."""

    def __init__(self, on_change: Callable[[dict], None] | None = None, interval: float = 3.0):
        self.on_change = on_change or (lambda ctx: None)
        self.interval = interval
        self._last_hash = ""
        self._running = True
        self._last_context: dict = {}

    def run(self):
        """Blocking loop — run in a daemon thread."""
        logger.info(f"স্ক্রিন ওয়াচার শুরু (প্রতি {self.interval}s)")
        while self._running:
            try:
                ctx = self._capture_context()
                # Only emit if something changed
                h = self._hash_context(ctx)
                if h != self._last_hash:
                    self._last_hash = h
                    self._last_context = ctx
                    self.on_change(ctx)
            except Exception as exc:
                logger.debug(f"স্ক্রিন ক্যাপচার ত্রুটি: {exc}")
            time.sleep(self.interval)

    def stop(self):
        self._running = False

    def get_current_context(self) -> dict:
        return self._last_context.copy()

    def _capture_context(self) -> dict:
        ctx = {
            "window_title": self._get_active_window_title(),
            "app_name": self._get_active_app(),
            "screen_hash": "",
        }
        # Take screenshot and compute hash to detect changes
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                # Use center region for hash (faster)
                w, h = img.width, img.height
                region_data = bytes(img.raw)[w * (h // 4) * 4: w * (3 * h // 4) * 4: 8]
                ctx["screen_hash"] = hashlib.md5(region_data).hexdigest()
        except ImportError:
            pass
        except Exception as exc:
            logger.debug(f"স্ক্রিনশট হ্যাশ ত্রুটি: {exc}")
        return ctx

    @staticmethod
    def _get_active_window_title() -> str:
        """Get the title of the currently focused window."""
        try:
            import subprocess
            from config import IS_LINUX, IS_MAC, IS_WINDOWS
            if IS_LINUX:
                # xdotool
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=2,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                # Fallback: xprop
                win = subprocess.run(
                    ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                    capture_output=True, text=True, timeout=2,
                )
                if "0x" in win.stdout:
                    win_id = win.stdout.split()[-1]
                    name = subprocess.run(
                        ["xprop", "-id", win_id, "WM_NAME"],
                        capture_output=True, text=True, timeout=2,
                    )
                    if "=" in name.stdout:
                        return name.stdout.split("=", 1)[-1].strip().strip('"')
            elif IS_MAC:
                result = subprocess.run(
                    ["osascript", "-e", 'tell application "System Events" to get name of first window of first process whose frontmost is true'],
                    capture_output=True, text=True, timeout=2,
                )
                return result.stdout.strip()
            elif IS_WINDOWS:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value
        except Exception:
            pass
        return ""

    @staticmethod
    def _get_active_app() -> str:
        """Get the name of the currently active application."""
        try:
            import subprocess
            from config import IS_LINUX, IS_MAC, IS_WINDOWS
            if IS_LINUX:
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowpid"],
                    capture_output=True, text=True, timeout=2,
                )
                if result.returncode == 0:
                    pid = result.stdout.strip()
                    comm = subprocess.run(
                        ["cat", f"/proc/{pid}/comm"],
                        capture_output=True, text=True, timeout=2,
                    )
                    return comm.stdout.strip()
            elif IS_MAC:
                result = subprocess.run(
                    ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
                    capture_output=True, text=True, timeout=2,
                )
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def _hash_context(ctx: dict) -> str:
        return ctx.get("screen_hash", "") + ctx.get("window_title", "")
