"""modules/os_controller.py — True OS-level control via xdotool, wmctrl, AT-SPI.

This is deeper than system_control.py — it controls the OS at the input-injection level:
- Type text into ANY app without focus tricks
- Click ANY element in ANY window
- Manage windows: minimize, maximize, move, resize, focus
- Read UI elements via accessibility tree (AT-SPI)
"""
import logging
import subprocess
import time
from typing import Any

from config import IS_LINUX, IS_MAC, IS_WINDOWS

logger = logging.getLogger(__name__)


def _run(cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip() or r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "টাইমআউট"
    except FileNotFoundError:
        return False, f"কমান্ড পাওয়া যায়নি: {cmd[0]}"
    except OSError as e:
        return False, str(e)


# ── Mouse & Keyboard (xdotool on Linux) ──────────────────────────────────────

def xdo_click(x: int, y: int, button: int = 1) -> dict:
    """Click at absolute screen coordinates."""
    if IS_LINUX:
        ok, out = _run(["xdotool", "mousemove", str(x), str(y), "click", str(button)])
        return {"observation": f"ক্লিক ({x},{y})" if ok else f"ত্রুটি: {out}", "display": None}
    elif IS_MAC:
        ok, out = _run(["cliclick", f"c:{x},{y}"])
        return {"observation": f"ক্লিক ({x},{y})" if ok else f"ত্রুটি: {out}", "display": None}
    return {"observation": "অসমর্থিত প্ল্যাটফর্ম", "display": None}


def xdo_type(text: str, delay_ms: int = 12) -> dict:
    """Type text into the currently focused window."""
    if IS_LINUX:
        ok, out = _run(["xdotool", "type", "--delay", str(delay_ms), "--", text])
        return {"observation": f"টাইপ করা হয়েছে" if ok else f"ত্রুটি: {out}", "display": None}
    elif IS_MAC:
        script = f'tell application "System Events" to keystroke "{text}"'
        ok, out = _run(["osascript", "-e", script])
        return {"observation": "টাইপ সম্পন্ন" if ok else f"ত্রুটি: {out}", "display": None}
    elif IS_WINDOWS:
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=0.05)
            return {"observation": "টাইপ সম্পন্ন", "display": None}
        except ImportError:
            return {"observation": "pyautogui পাওয়া যায়নি", "display": None}
    return {"observation": "অসমর্থিত প্ল্যাটফর্ম", "display": None}


def xdo_key(key: str) -> dict:
    """Press a key combination (e.g. 'ctrl+c', 'Return', 'alt+F4')."""
    if IS_LINUX:
        ok, out = _run(["xdotool", "key", key])
        return {"observation": f"কী চাপা হয়েছে: {key}" if ok else f"ত্রুটি: {out}", "display": None}
    elif IS_MAC:
        # Convert xdotool key names to AppleScript
        script = f'tell application "System Events" to keystroke "{key}"'
        ok, out = _run(["osascript", "-e", script])
        return {"observation": f"কী: {key}" if ok else f"ত্রুটি: {out}", "display": None}
    return {"observation": "অসমর্থিত", "display": None}


# ── Window Management (wmctrl on Linux) ──────────────────────────────────────

def list_windows() -> dict:
    """List all open windows."""
    if IS_LINUX:
        ok, out = _run(["wmctrl", "-l"])
        if ok:
            windows = []
            for line in out.split("\n"):
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    windows.append({"id": parts[0], "desktop": parts[1], "title": parts[3]})
            return {"observation": f"{len(windows)}টি উইন্ডো\n" + "\n".join(w["title"] for w in windows), "display": None, "windows": windows}
    return {"observation": "wmctrl পাওয়া যায়নি", "display": None, "windows": []}


def focus_window(title_pattern: str) -> dict:
    """Focus a window by title pattern."""
    if IS_LINUX:
        ok, out = _run(["wmctrl", "-a", title_pattern])
        return {"observation": f"উইন্ডো ফোকাস: {title_pattern}" if ok else f"ত্রুটি: {out}", "display": None}
    elif IS_MAC:
        script = f'tell application "{title_pattern}" to activate'
        ok, out = _run(["osascript", "-e", script])
        return {"observation": "উইন্ডো ফোকাস" if ok else f"ত্রুটি: {out}", "display": None}
    return {"observation": "অসমর্থিত", "display": None}


def close_window(title_pattern: str) -> dict:
    """Close a window by title pattern."""
    if IS_LINUX:
        ok, out = _run(["wmctrl", "-c", title_pattern])
        return {"observation": "উইন্ডো বন্ধ" if ok else f"ত্রুটি: {out}", "display": None}
    return {"observation": "অসমর্থিত", "display": None}


def maximize_window(title_pattern: str = "") -> dict:
    """Maximize current or named window."""
    if IS_LINUX:
        if title_pattern:
            _run(["wmctrl", "-a", title_pattern])
        ok, out = _run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"])
        return {"observation": "ম্যাক্সিমাইজ" if ok else f"ত্রুটি: {out}", "display": None}
    return {"observation": "অসমর্থিত", "display": None}


def minimize_window(title_pattern: str = "") -> dict:
    """Minimize current or named window."""
    if IS_LINUX:
        target = title_pattern if title_pattern else ":ACTIVE:"
        ok, out = _run(["xdotool", "getactivewindow", "windowminimize"] if not title_pattern
                       else ["wmctrl", "-r", title_pattern, "-b", "add,hidden"])
        return {"observation": "মিনিমাইজ" if ok else f"ত্রুটি: {out}", "display": None}
    return {"observation": "অসমর্থিত", "display": None}


def move_window(title_pattern: str, x: int, y: int, w: int = 0, h: int = 0) -> dict:
    """Move and optionally resize a window."""
    if IS_LINUX:
        gravity = 0
        cmd = ["wmctrl", "-r", title_pattern, "-e", f"{gravity},{x},{y},{w if w else -1},{h if h else -1}"]
        ok, out = _run(cmd)
        return {"observation": "উইন্ডো সরানো হয়েছে" if ok else f"ত্রুটি: {out}", "display": None}
    return {"observation": "অসমর্থিত", "display": None}


# ── Screenshot of specific window ────────────────────────────────────────────

def screenshot_window(title_pattern: str, output_path: str) -> dict:
    """Take a screenshot of a specific window."""
    if IS_LINUX:
        # Get window ID
        ok, out = _run(["xdotool", "search", "--name", title_pattern])
        if ok and out:
            win_id = out.strip().split()[0]
            ok2, out2 = _run(["import", "-window", win_id, output_path])  # ImageMagick
            if ok2:
                return {"observation": f"윈도우 스크린샷: {output_path}", "display": output_path}
    return {"observation": "윈도우 스크린샷 실패", "display": None}


# ── Clipboard (OS-level) ──────────────────────────────────────────────────────

def clipboard_get_os() -> dict:
    """Get clipboard content via OS tools."""
    if IS_LINUX:
        for tool in (["xclip", "-selection", "clipboard", "-o"],
                     ["xsel", "--clipboard", "--output"]):
            ok, out = _run(tool)
            if ok:
                return {"observation": out, "display": None}
    try:
        import pyperclip
        return {"observation": pyperclip.paste() or "", "display": None}
    except ImportError:
        return {"observation": "ক্লিপবোর্ড পড়া যায়নি", "display": None}


def clipboard_set_os(text: str) -> dict:
    """Set clipboard content via OS tools."""
    if IS_LINUX:
        for tool in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
            try:
                r = subprocess.run(tool, input=text, text=True, timeout=5)
                if r.returncode == 0:
                    return {"observation": "ক্লিপবোর্ড সেট হয়েছে", "display": None}
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
    try:
        import pyperclip
        pyperclip.copy(text)
        return {"observation": "ক্লিপবোর্ড সেট হয়েছে", "display": None}
    except ImportError:
        return {"observation": "ক্লিপবোর্ড সেট করা যায়নি", "display": None}


# ── Display Management ────────────────────────────────────────────────────────

def list_displays() -> dict:
    """List connected displays via xrandr."""
    if IS_LINUX:
        ok, out = _run(["xrandr", "--listmonitors"])
        return {"observation": out if ok else "xrandr পাওয়া যায়নি", "display": None}
    return {"observation": "অসমর্থিত", "display": None}


def set_brightness(level: int) -> dict:
    """Set screen brightness (0-100) via xrandr."""
    if IS_LINUX:
        val = max(0.1, min(1.0, level / 100))
        # Get primary display name
        ok, out = _run(["xrandr", "--listmonitors"])
        if ok:
            for line in out.split("\n"):
                if "+" in line:
                    display = line.split()[-1]
                    ok2, _ = _run(["xrandr", "--output", display, "--brightness", str(val)])
                    return {"observation": f"উজ্জ্বলতা {level}%" if ok2 else "ব্যর্থ", "display": None}
    return {"observation": "অসমর্থিত", "display": None}


# ── Autostart Management ──────────────────────────────────────────────────────

def enable_autostart(script_path: str, name: str = "nova") -> dict:
    """Add NOVA to XDG autostart (Linux/freedesktop)."""
    import os
    from pathlib import Path

    if IS_LINUX:
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop_file = autostart_dir / f"{name}.desktop"
        content = f"""[Desktop Entry]
Type=Application
Name=NOVA v9
Comment=NOVA Autonomous OS Agent
Exec=python3 {script_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        desktop_file.write_text(content)
        return {"observation": f"অটোস্টার্ট সক্রিয়: {desktop_file}", "display": None}

    elif IS_MAC:
        # LaunchAgent plist
        launch_agents = Path.home() / "Library" / "LaunchAgents"
        launch_agents.mkdir(exist_ok=True)
        plist = launch_agents / f"com.nova.agent.plist"
        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.nova.agent</string>
    <key>ProgramArguments</key>
    <array><string>python3</string><string>{script_path}</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>"""
        plist.write_text(content)
        os.system(f"launchctl load {plist}")
        return {"observation": f"macOS LaunchAgent যোগ: {plist}", "display": None}

    return {"observation": "অসমর্থিত প্ল্যাটফর্ম", "display": None}


def disable_autostart(name: str = "nova") -> dict:
    """Remove NOVA from XDG autostart."""
    from pathlib import Path

    if IS_LINUX:
        desktop_file = Path.home() / ".config" / "autostart" / f"{name}.desktop"
        if desktop_file.exists():
            desktop_file.unlink()
            return {"observation": "অটোস্টার্ট নিষ্ক্রিয়", "display": None}
        return {"observation": "অটোস্টার্ট ফাইল পাওয়া যায়নি", "display": None}
    return {"observation": "অসমর্থিত", "display": None}
