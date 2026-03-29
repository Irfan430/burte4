#!/usr/bin/env bash
# nova_service.sh — Environment wrapper for NOVA v9 daemon
# Used by systemd service and XDG autostart.
#
# Usage:
#   ./nova_service.sh                → start normally
#   ./nova_service.sh --gui-session  → check if daemon running, connect display

set -euo pipefail

NOVA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NOVA_LOG_DIR="$HOME/.nova/logs"
NOVA_SOCK="$HOME/.nova/nova.sock"
PYTHON="${PYTHON:-python3}"

mkdir -p "$NOVA_LOG_DIR" "$HOME/.nova"

# ── Load .env ─────────────────────────────────────────────────────────────────
if [[ -f "$NOVA_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source <(grep -v '^#' "$NOVA_DIR/.env" | grep '=')
    set +a
fi

# ── Discover DISPLAY if not set ───────────────────────────────────────────────
if [[ -z "${DISPLAY:-}" ]]; then
    # Try to find display from running X sessions
    _DISP=$(w -hs 2>/dev/null | awk '$8 ~ /^:[0-9]/ {print $8; exit}' || true)
    [[ -n "$_DISP" ]] && export DISPLAY="$_DISP"
fi

# ── Discover D-Bus session bus ────────────────────────────────────────────────
if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
    for _PID in $(pgrep -u "$USER" -f "gnome-session|kwin_wayland|plasmashell|xfce4-session" 2>/dev/null || true); do
        _DBUS=$(tr '\0' '\n' < "/proc/$_PID/environ" 2>/dev/null | grep DBUS_SESSION_BUS_ADDRESS | cut -d= -f2- || true)
        if [[ -n "$_DBUS" ]]; then
            export DBUS_SESSION_BUS_ADDRESS="$_DBUS"
            break
        fi
    done
fi

# ── XDG_RUNTIME_DIR ───────────────────────────────────────────────────────────
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# ── GUI session mode: connect display to running daemon ───────────────────────
if [[ "${1:-}" == "--gui-session" ]]; then
    if [[ -S "$NOVA_SOCK" ]]; then
        # Daemon already running — notify it about the new display
        echo '{"cmd":"gui_session","payload":{}}' | \
            python3 -c "
import socket, sys, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    s.connect('$NOVA_SOCK')
    s.sendall(sys.stdin.buffer.read() + b'\n')
    print(s.recv(256).decode().strip())
except Exception as e:
    print(f'connect failed: {e}')
" 2>/dev/null || true
        exit 0
    fi
    # Daemon not running — fall through and start it
fi

# ── Start daemon ──────────────────────────────────────────────────────────────
cd "$NOVA_DIR"
exec "$PYTHON" nova_daemon.py --foreground "$@"
