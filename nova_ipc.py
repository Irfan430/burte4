"""nova_ipc.py — IPC client. Send commands to running NOVA daemon.

Usage:
    python nova_ipc.py "স্ক্রিনশট নাও"
    python nova_ipc.py --status
    python nova_ipc.py --stop
    python nova_ipc.py --ui
"""
import argparse
import json
import socket
import sys
from pathlib import Path

SOCK_FILE = Path.home() / ".nova" / "nova.sock"


def send(cmd: str, payload: dict = None) -> dict | None:
    if not SOCK_FILE.exists():
        print("NOVA Daemon চলছে না। চালু করুন: python nova_daemon.py")
        return None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(str(SOCK_FILE))
        msg = json.dumps({"cmd": cmd, "payload": payload or {}}) + "\n"
        s.sendall(msg.encode())
        data = s.recv(4096)
        s.close()
        return json.loads(data.decode().strip())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"IPC ত্রুটি: {exc}")
        return None


def main():
    parser = argparse.ArgumentParser(description="NOVA IPC Client")
    parser.add_argument("goal", nargs="?", help="লক্ষ্য / কমান্ড")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--ui", action="store_true", help="Full UI খোলো")
    args = parser.parse_args()

    if args.status:
        resp = send("status")
        if resp:
            print("কাজ করছে" if resp.get("running") else "প্রস্তুত (idle)")
    elif args.stop:
        resp = send("stop")
        print(resp.get("msg", "") if resp else "")
    elif args.ui:
        send("open_ui")
    elif args.goal:
        resp = send("run_goal", {"goal": args.goal})
        if resp:
            print(resp.get("msg", ""))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
