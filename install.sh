#!/usr/bin/env bash
# NOVA v9 — Installation Script
# Usage: ./install.sh [--systemd] [--autostart] [--deps]
set -e

NOVA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
USER_HOME="$HOME"

echo "╔══════════════════════════════════════╗"
echo "║   NOVA v9 — ইনস্টলেশন শুরু হচ্ছে    ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Parse args ───────────────────────────────────────────────────────────────
DO_DEPS=false
DO_SYSTEMD=false
DO_AUTOSTART=false
DO_ALL=true

for arg in "$@"; do
  case $arg in
    --deps)       DO_DEPS=true;       DO_ALL=false ;;
    --systemd)    DO_SYSTEMD=true;    DO_ALL=false ;;
    --autostart)  DO_AUTOSTART=true;  DO_ALL=false ;;
    --all)        DO_ALL=true ;;
  esac
done

if $DO_ALL; then
  DO_DEPS=true
  DO_SYSTEMD=false   # systemd needs sudo — only on request
  DO_AUTOSTART=true
fi

# ── 1. Python dependencies ────────────────────────────────────────────────────
if $DO_DEPS; then
  echo "📦 Python প্যাকেজ ইনস্টল করছি..."
  $PYTHON -m pip install -q --upgrade pip

  # Core
  $PYTHON -m pip install -q \
    httpx python-dotenv mss Pillow psutil plyer \
    rich openai tiktoken pyperclip \
    pynput pystray \
    fastapi uvicorn websockets \
    edge-tts \
    requests

  # Playwright
  $PYTHON -m pip install -q playwright 2>/dev/null || true
  $PYTHON -m playwright install chromium 2>/dev/null || true

  # Optional voice
  $PYTHON -m pip install -q openai-whisper 2>/dev/null || true

  echo "  ✓ Python প্যাকেজ সম্পন্ন"

  # Linux system packages
  if [[ "$(uname)" == "Linux" ]]; then
    echo "🐧 Linux সিস্টেম প্যাকেজ পরীক্ষা করছি..."
    declare -a PKGS=()

    command -v xdotool >/dev/null 2>&1 || PKGS+=("xdotool")
    command -v wmctrl  >/dev/null 2>&1 || PKGS+=("wmctrl")
    command -v xclip   >/dev/null 2>&1 || PKGS+=("xclip")
    command -v scrot   >/dev/null 2>&1 || PKGS+=("scrot")
    command -v notify-send >/dev/null 2>&1 || PKGS+=("libnotify-bin")
    command -v ffplay  >/dev/null 2>&1 || PKGS+=("ffmpeg")

    if [[ ${#PKGS[@]} -gt 0 ]]; then
      echo "  ইনস্টল করছি: ${PKGS[*]}"
      sudo apt-get install -y -q "${PKGS[@]}" 2>/dev/null || \
      sudo pacman -S --noconfirm "${PKGS[@]}" 2>/dev/null || \
      sudo dnf install -y "${PKGS[@]}" 2>/dev/null || \
      echo "  ⚠ ম্যানুয়ালি ইনস্টল করুন: ${PKGS[*]}"
    else
      echo "  ✓ সব সিস্টেম প্যাকেজ আছে"
    fi
  fi
fi

# ── 2. Create .env if not exists ──────────────────────────────────────────────
if [[ ! -f "$NOVA_DIR/.env" ]]; then
  echo ""
  echo "⚙  .env ফাইল তৈরি করছি..."
  cp "$NOVA_DIR/.env.example" "$NOVA_DIR/.env"
  echo "  ✓ $NOVA_DIR/.env তৈরি হয়েছে"
  echo "  ⚠ OPENROUTER_API_KEY সেট করুন: nano $NOVA_DIR/.env"
fi

# ── 3. Create ~/.nova directory ───────────────────────────────────────────────
mkdir -p "$USER_HOME/.nova/logs"
echo "  ✓ ~/.nova ডিরেক্টরি তৈরি"

# ── 4. XDG Autostart (no sudo needed) ────────────────────────────────────────
if $DO_AUTOSTART; then
  echo ""
  echo "🚀 XDG অটোস্টার্ট সেটআপ..."
  AUTOSTART_DIR="$USER_HOME/.config/autostart"
  mkdir -p "$AUTOSTART_DIR"
  cat > "$AUTOSTART_DIR/nova-v9.desktop" << EOF
[Desktop Entry]
Type=Application
Name=NOVA v9
Comment=NOVA Autonomous OS Agent — always running
Exec=$PYTHON $NOVA_DIR/nova_daemon.py --foreground
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
Terminal=false
EOF
  echo "  ✓ অটোস্টার্ট সক্রিয়: $AUTOSTART_DIR/nova-v9.desktop"
  echo "  → পরবর্তী লগইনে NOVA স্বয়ংক্রিয়ভাবে শুরু হবে"
fi

# ── 5. Systemd user service (optional) ───────────────────────────────────────
if $DO_SYSTEMD; then
  echo ""
  echo "🔧 systemd service ইনস্টল করছি..."
  SYSTEMD_USER_DIR="$USER_HOME/.config/systemd/user"
  mkdir -p "$SYSTEMD_USER_DIR"

  sed "s|%h|$USER_HOME|g; s|%U|$(id -u)|g; s|%i|$(whoami)|g" \
    "$NOVA_DIR/nova.service" > "$SYSTEMD_USER_DIR/nova.service"

  systemctl --user daemon-reload
  systemctl --user enable nova
  systemctl --user start nova
  echo "  ✓ systemd service সক্রিয় ও চালু"
  echo "  → স্ট্যাটাস: systemctl --user status nova"
fi

# ── 6. Create nova CLI shortcut ───────────────────────────────────────────────
echo ""
echo "⌨  CLI শর্টকাট তৈরি করছি..."
NOVA_BIN="$USER_HOME/.local/bin/nova"
mkdir -p "$USER_HOME/.local/bin"
cat > "$NOVA_BIN" << EOF
#!/usr/bin/env bash
$PYTHON $NOVA_DIR/nova_ipc.py "\$@"
EOF
chmod +x "$NOVA_BIN"
echo "  ✓ 'nova' কমান্ড তৈরি: $NOVA_BIN"

# ── 7. Final instructions ─────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║           ✅ NOVA v9 ইনস্টল সম্পন্ন!          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "পরবর্তী পদক্ষেপ:"
echo ""
echo "  1. API কী সেট করুন:"
echo "     nano $NOVA_DIR/.env"
echo "     (OPENROUTER_API_KEY=sk-or-...)"
echo ""
echo "  2. NOVA চালু করুন:"
echo "     python3 $NOVA_DIR/nova_daemon.py"
echo ""
echo "  3. কমান্ড দিন (যেকোনো টার্মিনাল থেকে):"
echo "     nova 'ব্রাউজারে youtube.com খোলো'"
echo "     nova --status"
echo "     nova --stop"
echo ""
echo "  4. হটকি (যেকোনো অ্যাপ থেকে):"
echo "     Ctrl+Space  → মিনি ইনপুট বার"
echo "     Alt+V       → ভয়েস কমান্ড"
echo "     Ctrl+Alt+N  → বর্তমান কাজ বন্ধ"
echo ""
echo "  5. পরের লগইনে স্বয়ংক্রিয় শুরু:"
echo "     XDG Autostart সক্রিয় আছে ✓"
echo ""
