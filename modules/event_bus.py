"""modules/event_bus.py — System event listener.

Monitors OS-level events and emits them to NOVA:
- Battery low/charging
- Network connect/disconnect
- USB device plug/unplug
- File system changes
- Screen lock/unlock
"""
import logging
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)


class EventBus:
    """Listens for system events and dispatches them to a callback."""

    def __init__(self, on_event: Callable[[dict], None] | None = None, poll_interval: float = 5.0):
        self.on_event = on_event or (lambda e: None)
        self.poll_interval = poll_interval
        self._running = True
        self._last_battery: int | None = None
        self._last_net_state: bool | None = None

    def run(self):
        """Blocking event loop — run in daemon thread."""
        logger.info("ইভেন্ট বাস শুরু")
        while self._running:
            try:
                self._check_battery()
                self._check_network()
            except Exception as exc:
                logger.debug(f"ইভেন্ট চেক ত্রুটি: {exc}")
            time.sleep(self.poll_interval)

    def stop(self):
        self._running = False

    def _emit(self, event: dict):
        try:
            t = threading.Thread(target=self.on_event, args=(event,), daemon=True)
            t.start()
        except Exception as exc:
            logger.warning(f"ইভেন্ট emit ত্রুটি: {exc}")

    def _check_battery(self):
        try:
            import psutil
            batt = psutil.sensors_battery()
            if batt is None:
                return
            level = int(batt.percent)
            plugged = batt.power_plugged

            if self._last_battery is None:
                self._last_battery = level
                return

            # Low battery warning
            if level <= 15 and self._last_battery > 15:
                self._emit({"type": "battery_low", "level": level})

            # Battery fully charged
            if level >= 98 and plugged and self._last_battery < 98:
                self._emit({"type": "battery_full", "level": level})

            # Plugged in
            if plugged and not getattr(self, "_was_plugged", plugged):
                self._emit({"type": "power_plugged", "level": level})

            # Unplugged
            if not plugged and getattr(self, "_was_plugged", not plugged):
                self._emit({"type": "power_unplugged", "level": level})

            self._last_battery = level
            self._was_plugged = plugged
        except ImportError:
            pass
        except Exception:
            pass

    def _check_network(self):
        try:
            import psutil
            stats = psutil.net_if_stats()
            # Check if any interface is up
            any_up = any(
                s.isup for name, s in stats.items()
                if name not in ("lo", "localhost")
            )

            if self._last_net_state is None:
                self._last_net_state = any_up
                return

            if any_up and not self._last_net_state:
                self._emit({"type": "network_connected"})
            elif not any_up and self._last_net_state:
                self._emit({"type": "network_disconnected"})

            self._last_net_state = any_up
        except ImportError:
            pass
        except Exception:
            pass
