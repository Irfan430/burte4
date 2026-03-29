"""modules/system_control.py — Cross-platform OS control tools."""
import logging
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Optional

from config import IS_LINUX, IS_MAC, IS_WINDOWS

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30


def run_command(cmd: str, timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Run a shell command and return stdout/stderr."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return {
            "observation": output or "কমান্ড সম্পন্ন (কোনো আউটপুট নেই)",
            "display": None,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"observation": f"কমান্ড সময়সীমা অতিক্রম ({timeout}s): {cmd}", "display": None, "returncode": -1}
    except OSError as exc:
        return {"observation": f"কমান্ড ত্রুটি: {exc}", "display": None, "returncode": -1}


def screenshot(save_path: Optional[str] = None) -> dict:
    """Take a screenshot and save to file."""
    from config import SCREENSHOTS_DIR

    ts = int(time.time() * 1000)
    out_path = save_path or str(SCREENSHOTS_DIR / f"screenshot_{ts}.png")

    # Primary: mss
    try:
        import mss
        import mss.tools

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            mss.tools.to_png(img.rgb, img.size, output=out_path)
        return {"observation": f"স্ক্রিনশট নেওয়া হয়েছে: {out_path}", "display": out_path}
    except (ImportError, Exception) as exc:
        logger.warning(f"mss ব্যর্থ: {exc}")

    # Fallback: platform specific
    if IS_LINUX:
        result = run_command(f"scrot '{out_path}'", timeout=10)
        if result["returncode"] == 0:
            return {"observation": f"স্ক্রিনশট (scrot): {out_path}", "display": out_path}
    elif IS_MAC:
        result = run_command(f"screencapture '{out_path}'", timeout=10)
        if result["returncode"] == 0:
            return {"observation": f"স্ক্রিনশট (screencapture): {out_path}", "display": out_path}
    elif IS_WINDOWS:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(out_path)
            return {"observation": f"স্ক্রিনশট (PIL): {out_path}", "display": out_path}
        except (ImportError, OSError) as exc:
            pass

    return {"observation": "স্ক্রিনশট নেওয়া সম্ভব হয়নি", "display": None}


def open_app(name: str) -> dict:
    """Open an application by name."""
    if IS_LINUX:
        result = run_command(f"xdg-open '{name}' &", timeout=5)
    elif IS_MAC:
        result = run_command(f"open -a '{name}'", timeout=5)
    elif IS_WINDOWS:
        result = run_command(f"start '' '{name}'", timeout=5)
    else:
        result = run_command(f"xdg-open '{name}' &", timeout=5)

    return {"observation": f"অ্যাপ চালু করা হয়েছে: {name}", "display": None}


def clipboard_get() -> dict:
    """Get clipboard content."""
    try:
        import pyperclip
        content = pyperclip.paste()
        return {"observation": content, "display": None}
    except (ImportError, Exception) as exc:
        pass

    if IS_LINUX:
        result = run_command("xclip -selection clipboard -o 2>/dev/null || xsel --clipboard --output 2>/dev/null")
        return {"observation": result["observation"], "display": None}
    elif IS_MAC:
        result = run_command("pbpaste")
        return {"observation": result["observation"], "display": None}
    elif IS_WINDOWS:
        result = run_command("powershell Get-Clipboard")
        return {"observation": result["observation"], "display": None}
    return {"observation": "ক্লিপবোর্ড পড়া যায়নি", "display": None}


def clipboard_set(text: str) -> dict:
    """Set clipboard content."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return {"observation": "ক্লিপবোর্ডে কপি হয়েছে", "display": None}
    except (ImportError, Exception) as exc:
        pass

    if IS_LINUX:
        run_command(f"echo '{text}' | xclip -selection clipboard 2>/dev/null || echo '{text}' | xsel --clipboard --input 2>/dev/null")
    elif IS_MAC:
        run_command(f"echo '{text}' | pbcopy")
    elif IS_WINDOWS:
        run_command(f"echo {text} | clip")
    return {"observation": "ক্লিপবোর্ডে সেট করা হয়েছে", "display": None}


def notify(title: str, msg: str) -> dict:
    """Send a desktop notification."""
    if IS_LINUX:
        run_command(f"notify-send '{title}' '{msg}'", timeout=5)
    elif IS_MAC:
        run_command(
            f"osascript -e 'display notification \"{msg}\" with title \"{title}\"'",
            timeout=5,
        )
    elif IS_WINDOWS:
        try:
            from plyer import notification
            notification.notify(title=title, message=msg, timeout=5)
        except (ImportError, Exception) as exc:
            logger.warning(f"বিজ্ঞপ্তি ব্যর্থ: {exc}")
    return {"observation": f"বিজ্ঞপ্তি পাঠানো হয়েছে: {title}", "display": None}


def set_volume(level: int) -> dict:
    """Set system volume (0-100)."""
    level = max(0, min(100, level))
    if IS_LINUX:
        run_command(f"amixer sset Master {level}% 2>/dev/null || pactl set-sink-volume @DEFAULT_SINK@ {level}%")
    elif IS_MAC:
        run_command(f"osascript -e 'set volume output volume {level}'")
    elif IS_WINDOWS:
        run_command(f"nircmd.exe setsysvolume {int(level * 655.35)}")
    return {"observation": f"ভলিউম {level}% সেট করা হয়েছে", "display": None}


def open_terminal() -> dict:
    """Open a terminal window."""
    if IS_LINUX:
        for term in ("gnome-terminal", "xterm", "konsole", "xfce4-terminal"):
            result = run_command(f"{term} &", timeout=3)
            if result["returncode"] == 0:
                return {"observation": f"টার্মিনাল খোলা হয়েছে: {term}", "display": None}
    elif IS_MAC:
        run_command("open -a Terminal")
    elif IS_WINDOWS:
        run_command("start cmd.exe")
    return {"observation": "টার্মিনাল খোলা হয়েছে", "display": None}


def network_info() -> dict:
    """Return network interface information."""
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        lines = []
        for iface, addr_list in addrs.items():
            is_up = stats.get(iface, type("", (), {"isup": False})).isup
            for addr in addr_list:
                lines.append(f"{iface} ({'চালু' if is_up else 'বন্ধ'}): {addr.address}")
        return {"observation": "\n".join(lines) or "নেটওয়ার্ক তথ্য পাওয়া যায়নি", "display": None}
    except ImportError as exc:
        return {"observation": f"psutil পাওয়া যায়নি: {exc}", "display": None}


def process_list() -> dict:
    """List running processes."""
    try:
        import psutil
        procs = []
        for proc in psutil.process_iter(["pid", "name", "status"]):
            try:
                procs.append(f"{proc.info['pid']:>6}  {proc.info['status']:<10}  {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {"observation": "\n".join(procs[:50]), "display": None}
    except ImportError as exc:
        return {"observation": f"psutil পাওয়া যায়নি: {exc}", "display": None}


def kill_process(name_or_pid: str) -> dict:
    """Kill a process by name or PID."""
    try:
        import psutil
        killed = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if str(proc.info["pid"]) == str(name_or_pid) or proc.info["name"] == name_or_pid:
                    proc.kill()
                    killed.append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if killed:
            return {"observation": f"প্রসেস বন্ধ করা হয়েছে: {', '.join(killed)}", "display": None}
        return {"observation": f"প্রসেস পাওয়া যায়নি: {name_or_pid}", "display": None}
    except ImportError as exc:
        return {"observation": f"psutil পাওয়া যায়নি: {exc}", "display": None}


def get_battery() -> dict:
    """Get battery status."""
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            return {"observation": "ব্যাটারি তথ্য পাওয়া যায়নি (ডেস্কটপ?)", "display": None}
        plugged = "চার্জ হচ্ছে" if battery.power_plugged else "চার্জ হচ্ছে না"
        return {
            "observation": f"ব্যাটারি: {battery.percent:.0f}% ({plugged})",
            "display": None,
        }
    except ImportError as exc:
        return {"observation": f"psutil পাওয়া যায়নি: {exc}", "display": None}


def read_file(path: str) -> dict:
    """Read a text file."""
    try:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
        return {"observation": content, "display": None}
    except FileNotFoundError:
        return {"observation": f"ফাইল পাওয়া যায়নি: {path}", "display": None}
    except OSError as exc:
        return {"observation": f"ফাইল পড়তে ত্রুটি: {exc}", "display": None}


def write_file(path: str, content: str) -> dict:
    """Write content to a text file."""
    try:
        from modules.safety import backup_before_modify
        backup_before_modify(path)
    except Exception:
        pass

    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"observation": f"ফাইল লেখা হয়েছে: {path}", "display": None}
    except OSError as exc:
        return {"observation": f"ফাইল লেখতে ত্রুটি: {exc}", "display": None}


def delete_file(path: str) -> dict:
    """Delete a file or directory."""
    try:
        from modules.safety import backup_before_modify
        backup_before_modify(path)
    except Exception:
        pass

    try:
        p = Path(path)
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return {"observation": f"মুছে ফেলা হয়েছে: {path}", "display": None}
    except FileNotFoundError:
        return {"observation": f"ফাইল/ডিরেক্টরি পাওয়া যায়নি: {path}", "display": None}
    except OSError as exc:
        return {"observation": f"মুছতে ত্রুটি: {exc}", "display": None}


def list_dir(path: str = ".") -> dict:
    """List directory contents."""
    try:
        entries = os.listdir(path)
        lines = []
        for entry in sorted(entries):
            full = Path(path) / entry
            kind = "ডি" if full.is_dir() else "ফ"
            size = full.stat().st_size if full.is_file() else 0
            lines.append(f"[{kind}] {entry}  ({size} বাইট)")
        return {"observation": "\n".join(lines) or "(খালি ডিরেক্টরি)", "display": None}
    except (FileNotFoundError, NotADirectoryError) as exc:
        return {"observation": f"ডিরেক্টরি পড়তে ত্রুটি: {exc}", "display": None}


def file_search(query: str, directory: str = ".") -> dict:
    """Search files by name or content."""
    results = []
    try:
        for root, dirs, files in os.walk(directory):
            # Skip hidden and system directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if query.lower() in fname.lower():
                    results.append(os.path.join(root, fname))
                    if len(results) >= 50:
                        break
    except OSError as exc:
        return {"observation": f"ফাইল অনুসন্ধানে ত্রুটি: {exc}", "display": None}

    if results:
        return {"observation": "\n".join(results), "display": None}
    return {"observation": f"'{query}' নামে কোনো ফাইল পাওয়া যায়নি", "display": None}


def zip_folder(path: str) -> dict:
    """Create a zip archive of a folder."""
    try:
        src = Path(path)
        output = str(src) + "_archive"
        result = shutil.make_archive(output, "zip", src.parent, src.name)
        return {"observation": f"জিপ তৈরি হয়েছে: {result}", "display": None}
    except (FileNotFoundError, OSError) as exc:
        return {"observation": f"জিপ করতে ত্রুটি: {exc}", "display": None}


def type_text(text: str) -> dict:
    """Type text using pynput or xdotool."""
    try:
        from pynput.keyboard import Controller
        kb = Controller()
        kb.type(text)
        return {"observation": f"টাইপ করা হয়েছে: {text[:50]}", "display": None}
    except (ImportError, Exception) as exc:
        pass

    if IS_LINUX:
        result = run_command(f"xdotool type '{text}'", timeout=10)
        return {"observation": result["observation"], "display": None}
    return {"observation": "টাইপ করা সম্ভব হয়নি", "display": None}


def press_key(key: str) -> dict:
    """Press a keyboard key."""
    try:
        from pynput.keyboard import Controller, Key
        kb = Controller()
        key_map = {
            "enter": Key.enter, "tab": Key.tab, "esc": Key.esc,
            "space": Key.space, "backspace": Key.backspace,
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "ctrl": Key.ctrl, "alt": Key.alt, "shift": Key.shift,
        }
        k = key_map.get(key.lower(), key)
        kb.press(k)
        kb.release(k)
        return {"observation": f"কী চাপা হয়েছে: {key}", "display": None}
    except (ImportError, Exception) as exc:
        pass

    if IS_LINUX:
        result = run_command(f"xdotool key '{key}'", timeout=5)
        return {"observation": result["observation"], "display": None}
    return {"observation": f"কী চাপা সম্ভব হয়নি: {key}", "display": None}


def mouse_click(x: int, y: int, button: str = "left") -> dict:
    """Click mouse at position."""
    try:
        from pynput.mouse import Button, Controller
        mouse = Controller()
        mouse.position = (x, y)
        btn = Button.left if button == "left" else Button.right
        mouse.click(btn)
        return {"observation": f"মাউস ক্লিক: ({x}, {y}) {button}", "display": None}
    except (ImportError, Exception) as exc:
        pass

    if IS_LINUX:
        btn_num = "1" if button == "left" else "3"
        result = run_command(f"xdotool mousemove {x} {y} click {btn_num}", timeout=5)
        return {"observation": result["observation"], "display": None}
    return {"observation": "মাউস ক্লিক সম্ভব হয়নি", "display": None}


def mouse_move(x: int, y: int) -> dict:
    """Move mouse to position."""
    try:
        from pynput.mouse import Controller
        mouse = Controller()
        mouse.position = (x, y)
        return {"observation": f"মাউস সরানো হয়েছে: ({x}, {y})", "display": None}
    except (ImportError, Exception) as exc:
        pass

    if IS_LINUX:
        result = run_command(f"xdotool mousemove {x} {y}", timeout=5)
        return {"observation": result["observation"], "display": None}
    return {"observation": "মাউস সরানো সম্ভব হয়নি", "display": None}
