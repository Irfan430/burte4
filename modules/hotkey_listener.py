"""modules/hotkey_listener.py — Global hotkeys that work anywhere in the OS.

Ctrl+Space  → Activate NOVA (show mini input overlay)
Alt+V       → Voice command mode
Ctrl+Alt+N  → Stop current NOVA task
"""
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Listens for global hotkeys using pynput — works in any app."""

    def __init__(
        self,
        on_activate: Callable[[], None] | None = None,
        on_voice: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
    ):
        self.on_activate = on_activate or (lambda: None)
        self.on_voice = on_voice or (lambda: None)
        self.on_stop = on_stop or (lambda: None)
        self._listener = None

    def start(self):
        try:
            from pynput import keyboard

            hotkeys = {
                "<ctrl>+space": self._safe_call(self.on_activate),
                "<alt>+v": self._safe_call(self.on_voice),
                "<ctrl>+<alt>+n": self._safe_call(self.on_stop),
            }
            self._listener = keyboard.GlobalHotKeys(hotkeys)
            logger.info("গ্লোবাল হটকি সক্রিয়: Ctrl+Space, Alt+V, Ctrl+Alt+N")
            self._listener.run()  # Blocking
        except ImportError:
            logger.warning("pynput পাওয়া যায়নি — হটকি নিষ্ক্রিয়। pip install pynput")
        except Exception as exc:
            logger.error(f"হটকি লিসেনার ত্রুটি: {exc}")

    def stop(self):
        if self._listener:
            self._listener.stop()

    @staticmethod
    def _safe_call(fn: Callable) -> Callable:
        def wrapper():
            try:
                t = threading.Thread(target=fn, daemon=True)
                t.start()
            except Exception as exc:
                logger.error(f"হটকি কলব্যাক ত্রুটি: {exc}")
        return wrapper
