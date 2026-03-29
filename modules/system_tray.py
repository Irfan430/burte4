"""modules/system_tray.py — NOVA system tray icon.

Always visible in the taskbar. Right-click for options.
Click = show mini input overlay.
"""
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Tray icon (16x16 PNG as bytes — purple circle)
_ICON_BYTES = None

def _get_icon():
    global _ICON_BYTES
    if _ICON_BYTES:
        return _ICON_BYTES
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=(233, 69, 96, 255))  # NOVA red
        draw.text((18, 18), "N", fill="white")
        _ICON_BYTES = img
        return img
    except ImportError:
        return None


class NovaTray:
    """System tray icon with context menu."""

    def __init__(self, daemon=None):
        self._daemon = daemon
        self._icon = None
        self._status_item = None

    def set_status(self, text: str):
        """Update tray tooltip/title."""
        if self._icon:
            try:
                self._icon.title = f"NOVA: {text}"
            except Exception:
                pass

    def run(self):
        try:
            import pystray
            from PIL import Image

            icon_img = _get_icon()
            if icon_img is None:
                logger.warning("PIL পাওয়া যায়নি — tray আইকন নেই")
                return

            menu = pystray.Menu(
                pystray.MenuItem("NOVA v9 — প্রস্তুত", lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("⌨  কমান্ড দাও (Ctrl+Space)", self._on_command),
                pystray.MenuItem("🎤 ভয়েস কমান্ড (Alt+V)", self._on_voice),
                pystray.MenuItem("🖥  Full UI খোলো", self._on_open_ui),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("⏹  বর্তমান কাজ বন্ধ করো", self._on_stop_task),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("✕  NOVA বন্ধ করো", self._on_exit),
            )

            self._icon = pystray.Icon(
                "NOVA v9",
                icon=icon_img,
                title="NOVA v9 — প্রস্তুত",
                menu=menu,
            )
            logger.info("System tray আইকন চালু")
            self._icon.run()  # Blocking
        except ImportError:
            logger.warning("pystray পাওয়া যায়নি — tray নিষ্ক্রিয়। pip install pystray pillow")
        except Exception as exc:
            logger.error(f"Tray ত্রুটি: {exc}")

    def _on_command(self):
        if self._daemon:
            self._daemon._on_hotkey_activate()

    def _on_voice(self):
        if self._daemon:
            self._daemon._on_hotkey_voice()

    def _on_open_ui(self):
        if self._daemon:
            self._daemon._open_full_ui()

    def _on_stop_task(self):
        if self._daemon and self._daemon._nova_loop:
            self._daemon._nova_loop.stop()

    def _on_exit(self):
        if self._icon:
            self._icon.stop()
        if self._daemon:
            self._daemon.stop()
