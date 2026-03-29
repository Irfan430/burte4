"""modules/context_engine.py — OS context awareness for NOVA.

Provides real-time context about what's happening on the screen:
- Active window/app
- Focused text field content
- Clipboard
- Screen text (via AT-SPI or OCR)
- Running apps list
"""
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class ContextEngine:
    """Gathers OS context to inject into NOVA's prompts."""

    def get_context(self) -> dict[str, Any]:
        """Return current OS context as a dict."""
        return {
            "active_window": self.active_window(),
            "active_app": self.active_app(),
            "clipboard": self.clipboard_peek(),
            "running_apps": self.running_apps()[:10],
        }

    def get_context_string(self) -> str:
        """Return context as a Bengali string for injection into prompts."""
        ctx = self.get_context()
        parts = []
        if ctx["active_window"]:
            parts.append(f"সক্রিয় উইন্ডো: {ctx['active_window']}")
        if ctx["active_app"]:
            parts.append(f"সক্রিয় অ্যাপ: {ctx['active_app']}")
        if ctx["clipboard"]:
            parts.append(f"ক্লিপবোর্ড: {ctx['clipboard'][:100]}")
        return " | ".join(parts) if parts else ""

    @staticmethod
    def active_window() -> str:
        try:
            from config import IS_LINUX, IS_MAC, IS_WINDOWS
            if IS_LINUX:
                r = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=2,
                )
                return r.stdout.strip() if r.returncode == 0 else ""
            elif IS_MAC:
                r = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to get name of first window of first process whose frontmost is true'],
                    capture_output=True, text=True, timeout=2,
                )
                return r.stdout.strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def active_app() -> str:
        try:
            from config import IS_LINUX, IS_MAC
            if IS_LINUX:
                r = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowpid"],
                    capture_output=True, text=True, timeout=2,
                )
                if r.returncode == 0:
                    pid = r.stdout.strip()
                    c = subprocess.run(["cat", f"/proc/{pid}/comm"],
                                       capture_output=True, text=True, timeout=1)
                    return c.stdout.strip()
            elif IS_MAC:
                r = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to get name of first process whose frontmost is true'],
                    capture_output=True, text=True, timeout=2,
                )
                return r.stdout.strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def clipboard_peek() -> str:
        try:
            import pyperclip
            content = pyperclip.paste()
            return content[:200] if content else ""
        except Exception:
            return ""

    @staticmethod
    def running_apps() -> list[str]:
        try:
            from config import IS_LINUX, IS_MAC, IS_WINDOWS
            if IS_LINUX:
                r = subprocess.run(
                    ["wmctrl", "-l"], capture_output=True, text=True, timeout=3,
                )
                if r.returncode == 0:
                    lines = r.stdout.strip().split("\n")
                    return [" ".join(l.split()[3:]) for l in lines if l.strip()]
            elif IS_WINDOWS:
                import psutil
                return [p.name() for p in psutil.process_iter(["name"]) if p.info["name"]][:20]
        except Exception:
            pass
        return []

    @staticmethod
    def screen_text_at_cursor() -> str:
        """Try to read text at cursor position using AT-SPI (Linux)."""
        try:
            import subprocess
            from config import IS_LINUX
            if not IS_LINUX:
                return ""
            # AT-SPI via atspi-dump or python-atspi
            r = subprocess.run(
                ["python3", "-c",
                 "import pyatspi; d=pyatspi.Registry.getDesktop(0); "
                 "print(d[0].name if d else '')"],
                capture_output=True, text=True, timeout=2,
            )
            return r.stdout.strip()
        except Exception:
            return ""
