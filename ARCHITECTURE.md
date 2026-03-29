# NOVA v9 — OS Daemon Architecture

## ধারণা
NOVA একটি app না — এটি OS-এর অংশ।
Boot হলে চালু হয়, সবসময় background-এ চলে।
ব্যবহারকারী শুধু বলে/টাইপ করে — NOVA বাকি সব করে।

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT LAYER                         │
├──────────────┬───────────────┬───────────────┬─────────────┤
│  Hotkey      │   Wake Word   │  System Tray  │  Terminal   │
│  Ctrl+Space  │   "নোভা"      │  Right-click  │  nova "..."  │
│  Alt+V       │   (Whisper)   │               │             │
└──────┬───────┴───────┬───────┴───────┬───────┴──────┬──────┘
       │               │               │              │
       └───────────────┴───────────────┴──────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Mini UI Overlay   │
                    │  (Floating input)   │
                    └──────────┬──────────┘
                               │ IPC (Unix Socket)
                    ┌──────────▼──────────┐
                    │   NOVA DAEMON       │
                    │  nova_daemon.py     │
                    │  (24/7 background)  │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
  ┌────────▼───────┐  ┌────────▼───────┐  ┌────────▼───────┐
  │  Brain (LLM)   │  │   OODA Loop    │  │ Context Engine │
  │  OpenRouter    │  │  Self-correct  │  │ Active window  │
  │  Model routing │  │  Screenshot    │  │ Clipboard      │
  │  Cost tracking │  │  compare       │  │ Running apps   │
  └────────┬───────┘  └────────┬───────┘  └────────────────┘
           │                   │
           └─────────┬─────────┘
                     │
          ┌──────────▼──────────┐
          │     EXECUTOR        │
          │  55+ tools          │
          └──────────┬──────────┘
                     │
    ┌────────────────┼────────────────────────┐
    │                │                        │
┌───▼────┐   ┌───────▼──────┐   ┌────────────▼───────┐
│OS Tools│   │ Browser Tools│   │  System Tools       │
│xdotool │   │ Playwright   │   │  Files, Git         │
│wmctrl  │   │ browser_use  │   │  Process, Network   │
│xrandr  │   │ CDP intercept│   │  Voice, Vision      │
└────────┘   └──────────────┘   └────────────────────┘
```

## Startup Sequence

```
1. OS Boot
2. XDG Autostart / systemd → nova_daemon.py
3. Daemon loads: Brain, Executor, Memory
4. Subsystems start (parallel threads):
   ├── HotkeyListener  (pynput global hotkeys)
   ├── SystemTray      (pystray taskbar icon)
   ├── ScreenWatcher   (screenshot every 3s)
   ├── ContextEngine   (active window monitor)
   ├── EventBus        (battery, network events)
   ├── VoiceListener   (wake word "নোভা")
   └── APIServer       (FastAPI localhost:8765)
5. IPC Unix socket open → ready
```

## Input Flow

```
User says "নোভা, ব্রাউজারে youtube খোলো"
         ↓
VoiceListener (Whisper STT, Bengali)
         ↓
nova_daemon._on_voice_command(text)
         ↓
nova_daemon.run_goal("ব্রাউজারে youtube খোলো")
         ↓
NOVALoop.run(goal)
         ↓
Brain.decompose(goal) → ["playwright দিয়ে browser খোলো", "youtube.com navigate করো"]
         ↓
For each step:
  Brain.call(history) → {"tool": "playwright_navigate", "args": {"url": "youtube.com"}}
         ↓
Executor.run("playwright_navigate", {"url": "youtube.com"})
         ↓
[Screenshot before] → [Execute] → [Screenshot after]
         ↓
Vision.compare_screens(before, after) → "YouTube homepage দেখা যাচ্ছে"
         ↓
Goal complete → notify("NOVA ✓", "YouTube খোলা হয়েছে")
             → TTS: "YouTube খোলা হয়েছে"
```

## File Structure

```
burte4/
├── nova_daemon.py          ← 24/7 OS daemon (MAIN)
├── nova_ipc.py             ← CLI client to daemon
├── nova.py                 ← Manual run / Full UI
├── config.py               ← All config from .env
├── install.sh              ← One-command install
├── nova.service            ← systemd service
│
├── core/
│   ├── brain.py            ← Multi-LLM, routing, cost
│   ├── executor.py         ← 55+ tool dispatcher
│   ├── nova_loop.py        ← OODA self-correction
│   ├── memory.py           ← Pattern memory (JSON)
│   ├── task_queue.py       ← Priority queue, cron
│   └── undo_manager.py     ← Rollback/backup
│
├── modules/
│   ├── hotkey_listener.py  ← Global hotkeys (pynput)
│   ├── system_tray.py      ← Taskbar icon (pystray)
│   ├── mini_ui.py          ← Floating input overlay
│   ├── screen_watcher.py   ← Real-time screen monitor
│   ├── context_engine.py   ← OS context awareness
│   ├── os_controller.py    ← xdotool, wmctrl, xrandr
│   ├── event_bus.py        ← Battery, network events
│   ├── system_control.py   ← Cross-platform OS ops
│   ├── web_agent.py        ← browser_use + CDP
│   ├── playwright_agent.py ← Playwright automation
│   ├── vision.py           ← Qwen-VL screen analysis
│   ├── voice_stt.py        ← Whisper STT Bengali
│   ├── voice_tts.py        ← edge-tts Bengali TTS
│   ├── cost_display.py     ← Session cost tracker
│   ├── safety.py           ← Dangerous cmd filter
│   ├── api_server.py       ← FastAPI remote control
│   └── github_agent.py     ← Git operations
│
├── utils/
│   └── retry.py            ← Exponential backoff
│
├── ui_modern.py            ← Full Tkinter UI
├── prompts/                ← Bengali LLM prompts
└── plugins/                ← Auto-loaded tools
```

## কমান্ড রেফারেন্স

```bash
# ইনস্টল করো
./install.sh

# Daemon চালু করো
python3 nova_daemon.py

# যেকোনো টার্মিনাল থেকে কমান্ড দাও
nova "স্ক্রিনশট নাও"
nova "ব্রাউজারে google.com খোলো"
nova "সব উইন্ডো দেখাও"
nova --status
nova --stop

# হটকি (যেকোনো অ্যাপ থেকে)
Ctrl+Space   → মিনি ইনপুট বার
Alt+V        → ভয়েস মোড
Ctrl+Alt+N   → বর্তমান কাজ বন্ধ

# systemd (optional)
systemctl --user start nova
systemctl --user status nova
journalctl --user -u nova -f
```
