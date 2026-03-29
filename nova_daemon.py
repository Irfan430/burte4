"""nova_daemon.py — NOVA v9 OS Daemon. Runs 24/7 as a background service.

Start: python nova_daemon.py
Stop:  python nova_daemon.py --stop
Status: python nova_daemon.py --status
"""
import argparse
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path

# ── Setup paths ──────────────────────────────────────────────────────────────
HOME = Path.home()
NOVA_DIR = HOME / ".nova"
NOVA_DIR.mkdir(exist_ok=True)
PID_FILE = NOVA_DIR / "nova.pid"
SOCK_FILE = NOVA_DIR / "nova.sock"
LOG_FILE = NOVA_DIR / "daemon.log"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("nova.daemon")


class NOVADaemon:
    """Central daemon process — orchestrates all NOVA subsystems."""

    def __init__(self):
        self._running = threading.Event()
        self._nova_loop = None
        self._brain = None
        self._executor = None
        self._tray = None
        self._hotkey = None
        self._screen_watcher = None
        self._context_engine = None
        self._tts = None
        self._stt = None
        self._ipc_server = None
        self._current_task_thread: threading.Thread | None = None

    # ──────────────────────────────────────────────────────────────────────────
    # Startup
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        logger.info("═══ NOVA v9 Daemon শুরু হচ্ছে ═══")
        self._write_pid()
        self._running.set()

        # Load core components
        try:
            from config import (
                FEATURE_VOICE_INPUT, FEATURE_VOICE_OUTPUT,
                FEATURE_API_SERVER, API_SERVER_PORT,
            )
            from core.brain import Brain
            from core.executor import Executor
            from core.nova_loop import NOVALoop
            from core.memory import Memory

            self._brain = Brain()
            self._executor = Executor()
            self._memory = Memory()
            self._nova_loop = NOVALoop(
                brain=self._brain,
                executor=self._executor,
                memory=self._memory,
            )
            # Wire callbacks
            self._nova_loop.on_thought = self._on_thought
            self._nova_loop.on_tool_call = self._on_tool_call
            self._nova_loop.on_complete = self._on_complete
            self._nova_loop.on_error = self._on_error
            logger.info("কোর মডিউল লোড সম্পন্ন")
        except Exception as exc:
            logger.error(f"কোর লোড ব্যর্থ: {exc}")
            sys.exit(1)

        # Start subsystems in order
        self._start_subsystems()

        logger.info("NOVA Daemon প্রস্তুত। IPC socket শুনছি...")
        self._ipc_loop()  # Blocking: listen for commands

    def _start_subsystems(self):
        threads = [
            ("TTS", self._init_tts),
            ("STT", self._init_stt),
            ("Screen Watcher", self._init_screen_watcher),
            ("Context Engine", self._init_context_engine),
            ("Hotkey Listener", self._init_hotkey),
            ("System Tray", self._init_tray),
            ("API Server", self._init_api_server),
            ("Event Bus", self._init_event_bus),
        ]
        for name, fn in threads:
            try:
                fn()
                logger.info(f"  ✓ {name}")
            except Exception as exc:
                logger.warning(f"  ✗ {name}: {exc}")

    def _init_tts(self):
        try:
            from modules.voice_tts import TTSQueue
            self._tts = TTSQueue()
            self._tts.start()
            if self._nova_loop:
                self._nova_loop.tts = self._tts
        except ImportError:
            pass

    def _init_stt(self):
        try:
            from config import FEATURE_VOICE_INPUT
            if not FEATURE_VOICE_INPUT:
                return
            from modules.voice_stt import VoiceListener
            self._stt = VoiceListener(callback=self._on_voice_command)
            self._stt.start()
        except ImportError:
            pass

    def _init_screen_watcher(self):
        try:
            from modules.screen_watcher import ScreenWatcher
            self._screen_watcher = ScreenWatcher(
                on_change=self._on_screen_change,
                interval=3.0,
            )
            t = threading.Thread(target=self._screen_watcher.run, daemon=True, name="screen-watcher")
            t.start()
        except ImportError:
            pass

    def _init_context_engine(self):
        try:
            from modules.context_engine import ContextEngine
            self._context_engine = ContextEngine()
            if self._nova_loop:
                self._nova_loop.context_engine = self._context_engine
        except ImportError:
            pass

    def _init_hotkey(self):
        try:
            from modules.hotkey_listener import HotkeyListener
            self._hotkey = HotkeyListener(
                on_activate=self._on_hotkey_activate,
                on_voice=self._on_hotkey_voice,
            )
            t = threading.Thread(target=self._hotkey.start, daemon=True, name="hotkey-listener")
            t.start()
        except ImportError:
            pass

    def _init_tray(self):
        try:
            from modules.system_tray import NovaTray
            self._tray = NovaTray(daemon=self)
            t = threading.Thread(target=self._tray.run, daemon=True, name="system-tray")
            t.start()
        except ImportError:
            pass

    def _init_api_server(self):
        try:
            from config import FEATURE_API_SERVER, API_SERVER_PORT
            if not FEATURE_API_SERVER:
                return
            from modules.api_server import NovaAPIServer
            api = NovaAPIServer(nova_loop=self._nova_loop, port=API_SERVER_PORT)
            api.start()
        except ImportError:
            pass

    def _init_event_bus(self):
        try:
            from modules.event_bus import EventBus
            self._event_bus = EventBus(on_event=self._on_system_event)
            t = threading.Thread(target=self._event_bus.run, daemon=True, name="event-bus")
            t.start()
        except ImportError:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # IPC Server (Unix Socket)
    # ──────────────────────────────────────────────────────────────────────────

    def _ipc_loop(self):
        """Listen on Unix socket for commands from hotkey/tray/CLI."""
        if SOCK_FILE.exists():
            SOCK_FILE.unlink()

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(SOCK_FILE))
        server.listen(5)
        server.settimeout(1.0)
        SOCK_FILE.chmod(0o600)

        while self._running.is_set():
            try:
                conn, _ = server.accept()
                t = threading.Thread(
                    target=self._handle_ipc, args=(conn,), daemon=True
                )
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

        server.close()

    def _handle_ipc(self, conn: socket.socket):
        try:
            data = b""
            while chunk := conn.recv(4096):
                data += chunk
                if b"\n" in data:
                    break
            msg = json.loads(data.decode().strip())
            cmd = msg.get("cmd", "")
            payload = msg.get("payload", {})
            response = self._dispatch_ipc(cmd, payload)
            conn.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"IPC ত্রুটি: {exc}")
        finally:
            conn.close()

    def _dispatch_ipc(self, cmd: str, payload: dict) -> dict:
        if cmd == "run_goal":
            goal = payload.get("goal", "")
            if goal:
                self.run_goal(goal)
                return {"ok": True, "msg": f"কাজ শুরু: {goal[:50]}"}
        elif cmd == "stop":
            if self._nova_loop:
                self._nova_loop.stop()
            return {"ok": True, "msg": "বন্ধ হচ্ছে"}
        elif cmd == "status":
            return {"ok": True, "running": bool(self._current_task_thread and self._current_task_thread.is_alive())}
        elif cmd == "open_ui":
            self._open_full_ui()
            return {"ok": True}
        elif cmd == "shutdown":
            self._running.clear()
            return {"ok": True, "msg": "Daemon বন্ধ হচ্ছে"}
        return {"ok": False, "msg": f"অজানা কমান্ড: {cmd}"}

    # ──────────────────────────────────────────────────────────────────────────
    # Goal execution
    # ──────────────────────────────────────────────────────────────────────────

    def run_goal(self, goal: str, dry_run: bool = False):
        """Execute a goal in a background thread."""
        if self._current_task_thread and self._current_task_thread.is_alive():
            logger.warning("আগের কাজ চলছে। প্রথমে বন্ধ করুন।")
            if self._tts:
                self._tts.speak("আগের কাজ এখনো শেষ হয়নি।")
            return

        if self._nova_loop and self._nova_loop._stop_event.is_set():
            self._nova_loop._stop_event.clear()

        def _target():
            try:
                if self._tray:
                    self._tray.set_status("কাজ করছি...")
                self._nova_loop.run(goal, dry_run=dry_run)
            except Exception as exc:
                logger.error(f"Goal execution error: {exc}")
            finally:
                if self._tray:
                    self._tray.set_status("প্রস্তুত")

        self._current_task_thread = threading.Thread(target=_target, daemon=True, name="nova-task")
        self._current_task_thread.start()

    # ──────────────────────────────────────────────────────────────────────────
    # Event callbacks
    # ──────────────────────────────────────────────────────────────────────────

    def _on_voice_command(self, text: str):
        logger.info(f"ভয়েস কমান্ড: {text}")
        self.run_goal(text)

    def _on_hotkey_activate(self):
        """Ctrl+Space pressed anywhere in OS — show mini input."""
        logger.info("হটকি সক্রিয়")
        try:
            from modules.mini_ui import MiniUI
            ui = MiniUI(on_submit=self.run_goal)
            ui.show()
        except ImportError:
            pass

    def _on_hotkey_voice(self):
        """Alt+V pressed — start voice listening."""
        if self._stt:
            self._stt.listen_once(self._on_voice_command)
        elif self._tts:
            self._tts.speak("ভয়েস মডিউল সক্রিয় নেই।")

    def _on_screen_change(self, context: dict):
        """Called when screen changes significantly."""
        logger.debug(f"স্ক্রিন পরিবর্তন: {context.get('window_title', '')}")

    def _on_system_event(self, event: dict):
        """React to OS events (USB, network, battery, etc.)."""
        etype = event.get("type", "")
        if etype == "battery_low":
            if self._tts:
                self._tts.speak(f"ব্যাটারি কম: {event.get('level')}%")
        elif etype == "network_disconnected":
            logger.warning("নেটওয়ার্ক সংযোগ বিচ্ছিন্ন")

    def _on_thought(self, text: str):
        if self._tray:
            self._tray.set_status(text[:40])

    def _on_tool_call(self, name: str, args: dict, result: dict):
        logger.info(f"টুল: {name} → {result.get('observation','')[:80]}")

    def _on_complete(self, summary: str):
        logger.info(f"সম্পন্ন: {summary}")
        # Desktop notification
        try:
            from modules.system_control import notify
            notify("NOVA ✓", summary[:100])
        except Exception:
            pass
        if self._tts:
            self._tts.speak(f"কাজ শেষ। {summary[:80]}")

    def _on_error(self, error: str):
        logger.error(f"ত্রুটি: {error}")

    def _open_full_ui(self):
        """Open the full Tkinter UI window."""
        import subprocess
        import sys
        subprocess.Popen([sys.executable, "nova.py", "--text"], cwd=Path(__file__).parent)

    # ──────────────────────────────────────────────────────────────────────────
    # Shutdown
    # ──────────────────────────────────────────────────────────────────────────

    def stop(self, *_):
        logger.info("Daemon বন্ধ হচ্ছে...")
        self._running.clear()
        if self._nova_loop:
            self._nova_loop.stop()
        if PID_FILE.exists():
            PID_FILE.unlink()
        if SOCK_FILE.exists():
            SOCK_FILE.unlink()
        sys.exit(0)

    def _write_pid(self):
        PID_FILE.write_text(str(os.getpid()))

    # ──────────────────────────────────────────────────────────────────────────
    # Watchdog
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def watchdog():
        """Restart daemon if it crashes."""
        import subprocess
        while True:
            proc = subprocess.run([sys.executable, __file__, "--foreground"])
            if proc.returncode == 0:
                break
            logger.warning(f"Daemon crashed ({proc.returncode}), restarting in 3s...")
            time.sleep(3)


# ── CLI entry point ───────────────────────────────────────────────────────────

def send_ipc(cmd: str, payload: dict = None) -> dict | None:
    if not SOCK_FILE.exists():
        return None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(str(SOCK_FILE))
        msg = json.dumps({"cmd": cmd, "payload": payload or {}}) + "\n"
        s.sendall(msg.encode())
        data = s.recv(4096)
        s.close()
        return json.loads(data.decode().strip())
    except (OSError, json.JSONDecodeError):
        return None


def main():
    parser = argparse.ArgumentParser(description="NOVA v9 Daemon")
    parser.add_argument("--stop", action="store_true", help="Daemon বন্ধ করো")
    parser.add_argument("--status", action="store_true", help="স্ট্যাটাস দেখো")
    parser.add_argument("--foreground", action="store_true", help="Foreground-এ চালাও")
    parser.add_argument("--watchdog", action="store_true", help="Watchdog মোড")
    args = parser.parse_args()

    if args.stop:
        resp = send_ipc("shutdown")
        print(resp["msg"] if resp else "Daemon চলছে না।")
        return

    if args.status:
        resp = send_ipc("status")
        if resp:
            state = "কাজ করছে" if resp.get("running") else "প্রস্তুত (idle)"
            print(f"NOVA Daemon: {state}")
        else:
            print("NOVA Daemon চলছে না।")
        return

    if args.watchdog:
        NOVADaemon.watchdog()
        return

    # Check if already running
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            print(f"NOVA ইতিমধ্যে চলছে (PID: {pid})")
            return
        except ProcessLookupError:
            PID_FILE.unlink()

    daemon = NOVADaemon()
    signal.signal(signal.SIGTERM, daemon.stop)
    signal.signal(signal.SIGINT, daemon.stop)
    daemon.start()


if __name__ == "__main__":
    main()
