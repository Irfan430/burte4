# NOVA v9 — CLAUDE.md
## AI Development Guide & Future Roadmap

এই ফাইলটি Claude Code-এর জন্য। NOVA-র codebase বুঝতে এবং future upgrade করতে এটি পড়ো।

---

## Project Identity

**NOVA v9** একটি Autonomous OS Daemon। এটি একটি Python app নয় — এটি OS-এর অংশ।

- **Entry point (daemon):** `nova_daemon.py`
- **Entry point (manual):** `nova.py`
- **IPC client:** `nova_ipc.py`
- **Core loop:** `core/nova_loop.py`
- **All config:** `config.py` (reads from `.env`)
- **All prompts:** `prompts/` (Bengali)

### Critical Rules
1. সব user-facing text **বাংলায়** লেখো
2. API keys কখনো hardcode করো না — `config.py` / `.env` ব্যবহার করো
3. `requests` ব্যবহার করো না — সর্বদা `httpx`
4. Bare `except:` ব্যবহার করো না — specific exceptions ধরো
5. নতুন tool যোগ করলে `core/executor.py`-এর `_register_all()` method-এ যোগ করো
6. প্রতিটি tool `{"observation": str, "display": str | None}` return করবে
7. File modify করার আগে `undo_manager.backup_file(path)` call করো

---

## Current Architecture (v9.0)

```
nova_daemon.py          ← 24/7 daemon, IPC socket server
  └── core/brain.py     ← OpenRouter multi-LLM, model routing
  └── core/executor.py  ← 55+ tool dispatcher
  └── core/nova_loop.py ← OODA loop, self-correction
  └── core/memory.py    ← JSON pattern memory
  └── core/task_queue.py← Priority queue + cron
  └── core/undo_manager.py ← File rollback
  └── modules/*         ← All capabilities
```

### IPC Flow
```
Any Input Source → nova_ipc.py → Unix Socket → nova_daemon.py
                                                  → TaskQueue
                                                  → NOVALoop.run()
                                                  → ~/.nova/status.json
                                                  → ~/.nova/last_response.txt
```

---

## Roadmap — Future Upgrades

### 🔴 PRIORITY 1 — Critical (করতেই হবে)

#### P1-A: Wayland Native Support
**ফাইল:** `modules/hotkey_listener.py`, `modules/mini_ui.py`

বর্তমানে hotkey শুধু X11-এ কাজ করে। Wayland support যোগ করতে হবে:
```python
# hotkey_listener.py-এ যোগ করতে হবে:
# 1. WAYLAND_DISPLAY detect করো
# 2. ydotool ব্যবহার করো (xdotool-এর Wayland বিকল্প)
# 3. libinput-based evdev fallback (input group লাগবে)
# 4. pynput 1.7.6+ automatically handles এটা

# install.sh-এ যোগ করতে হবে:
sudo apt install ydotool
sudo usermod -aG input $USER
```

#### P1-B: Persistent Wake Word (Always-On)
**ফাইল:** `modules/voice_stt.py`

বর্তমানে voice শুধু `FEATURE_VOICE_INPUT=true` হলে চালু। Always-on করতে হবে:
```python
# Two-stage detection:
# Stage 1: Whisper tiny — 1s chunks, শুধু "নোভা" খোঁজো (fast)
# Stage 2: "নোভা" পেলে → 5s record → Whisper base → full command
# এটা CPU কম ব্যবহার করবে
```

#### P1-C: Auto-Restart on Crash (Watchdog hardening)
**ফাইল:** `nova_daemon.py`

বর্তমান watchdog আছে কিন্তু complete না:
```python
# nova_daemon.py-এ যোগ করতে হবে:
# - Task thread timeout: 5 মিনিট পর auto-kill
# - Memory limit: RAM > 1GB হলে restart
# - Log rotation: ~/.nova/logs/ auto-cleanup (max 100MB)
```

---

### 🟡 PRIORITY 2 — High Value (শীঘ্রই করা উচিত)

#### P2-A: Multi-Monitor Support
**ফাইল:** `modules/screen_watcher.py`, `modules/system_control.py`

```python
# screen_watcher.py-এ:
# - সব monitor-এর screenshot নাও আলাদাভাবে
# - Active monitor detect করো (cursor position দিয়ে)
# - xrandr থেকে monitor layout পড়ো

# system_control.py-এ:
# - take_screenshot(monitor=0) — নির্দিষ্ট monitor
# - move_window_to_monitor(title, monitor_id)
```

#### P2-B: Scheduled Tasks (Cron-style)
**ফাইল:** `core/task_queue.py`

```python
# task_queue.py-এ TaskScheduler class যোগ করো:
# - "প্রতিদিন সকাল ৯টায় emails check করো"
# - "প্রতি ঘণ্টায় system backup নাও"
# - crontab-এর মতো syntax: "0 9 * * *"
# - tasks.json-এ persist করো

# নতুন executor tool:
"schedule_task"  →  schedule_task(goal, cron_expr)
"list_scheduled" →  list_scheduled_tasks()
"cancel_schedule" → cancel_scheduled_task(task_id)
```

#### P2-C: Screen Recording / Replay
**ফাইল:** নতুন `modules/screen_recorder.py`

```python
# screen_recorder.py তৈরি করো:
# - ffmpeg দিয়ে screen record
# - NOVA-র সব action record করো (audit trail)
# - Replay: NOVA কী করেছিল দেখানো
# - Gif export for sharing

def start_recording(output_path: str) -> dict: ...
def stop_recording() -> dict: ...
def replay_session(session_file: str) -> dict: ...
```

#### P2-D: Telegram Full Integration
**ফাইল:** `modules/api_server.py`

```python
# Telegram bot দিয়ে mobile থেকে NOVA control:
# - /start — NOVA চালু confirm
# - /goal <text> — goal পাঠাও
# - /status — current status
# - /stop — বর্তমান কাজ বন্ধ
# - /screenshot — live screenshot পাঠাও
# - /cost — আজকের API cost

# .env-এ: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
# Polling mode (webhook নয় — server লাগবে না)
```

#### P2-E: OCR Screen Reading
**ফাইল:** `modules/vision.py`

```python
# AT-SPI না থাকলে OCR fallback:
# - tesseract বা easyocr দিয়ে screen-এর text পড়ো
# - Vision model-এর আগে OCR চেষ্টা করো (সস্তা)
# - Screen-এ error message detect করো

# executor-এ tool:
"read_screen_text"  →  OCR current screen, return text
"find_text_on_screen" → find text position, return coordinates
```

---

### 🟢 PRIORITY 3 — Enhancement (ভবিষ্যতে)

#### P3-A: Multi-Agent Collaboration
**ফাইল:** নতুন `core/agent_pool.py`

```python
# Parallel sub-tasks:
# Main NOVA complex task পেলে sub-agents spawn করে:
# - "Researcher" agent: web search করে
# - "Coder" agent: code লেখে
# - "Tester" agent: test করে
# Main agent results aggregate করে

class AgentPool:
    def spawn(self, role: str, goal: str) -> SubAgent: ...
    def gather_results(self) -> list[dict]: ...
```

#### P3-B: Learning & Adaptation
**ফাইল:** `core/memory.py`

```python
# বর্তমান: simple keyword matching
# Upgrade to:
# - TF-IDF based similarity (no ML library needed)
# - User preference learning: কোন tools বেশি ব্যবহার করে
# - Error pattern learning: কোন approach fail করে
# - Auto-adjust retry strategy based on past failures
# - "এই ধরনের কাজে তুমি আগে X করেছিলে" hint দেওয়া
```

#### P3-C: Natural Language Cron
**ফাইল:** `core/task_queue.py`, `core/brain.py`

```python
# Bengali cron parsing:
# "প্রতিদিন রাত ১০টায় X করো"
# "প্রতি শুক্রবার সকালে Y করো"
# "৩০ মিনিট পর Z করো"
# Brain.parse_schedule(text) → cron expression
```

#### P3-D: Docker Sandbox for Dangerous Commands
**ফাইল:** নতুন `modules/sandbox.py`

```python
# Risky command গুলো sandbox-এ চালাও:
# - rm, format ছাড়া অন্য destructive commands
# - Unknown scripts
# - pip install (security risk)

def run_sandboxed(command: str, image: str = "ubuntu:22.04") -> dict:
    # docker run --rm -v /tmp:/workspace ubuntu:22.04 bash -c command
    ...
```

#### P3-E: Voice Personality Customization
**ফাইল:** `modules/voice_tts.py`

```python
# Multiple voice options:
VOICES = {
    "নাবানিতা": "bn-BD-NabanitaNeural",  # বর্তমান (female)
    "প্রদীপ": "bn-IN-BashkarNeural",      # male
    "রিয়া": "bn-IN-TanishaaNeural",       # female Indian Bengali
}

# Speed, pitch control:
def speak(text: str, voice: str = None, rate: str = "+0%", pitch: str = "+0Hz")
```

#### P3-F: Knowledge Base Integration
**ফাইল:** নতুন `modules/knowledge_base.py`

```python
# User-specific knowledge:
# - User-এর projects, files, preferences সম্পর্কে জানে
# - "আমার Python project কোথায়?" → memory থেকে বলে
# - Manual "মনে রাখো: আমার office password হলো..." — encrypted store
# Simple JSON + encryption (cryptography library)
```

---

### 🔵 PRIORITY 4 — Advanced (দীর্ঘমেয়াদী)

#### P4-A: Web Dashboard
```
নতুন: web_dashboard/
├── app.py          ← Flask/FastAPI
├── templates/
│   └── index.html  ← Real-time dashboard
└── static/

Features:
- Browser থেকে NOVA control করো
- Live task feed (WebSocket)
- Cost charts
- Memory viewer
- Screenshot live feed
- Task history
```

#### P4-B: VS Code Extension
```
নতুন: vscode-nova/
- Command palette: "NOVA: Run Goal"
- Right-click: "Fix with NOVA", "Explain with NOVA"
- Terminal integration
- Inline code suggestions from NOVA
```

#### P4-C: Android App (Companion)
```
React Native / Flutter app:
- Voice commands from phone
- NOVA status push notifications
- Screenshot view
- Quick commands
Connects via: FastAPI + ngrok / Tailscale
```

#### P4-D: Self-Improvement
```python
# NOVA নিজেই নিজাকে upgrade করতে পারবে:
# 1. GitHub থেকে latest version pull করে
# 2. Tests run করে
# 3. যদি pass করে → restart করে নতুন version-এ
# 4. যদি fail করে → rollback করে

# nova.py-এ:
"self_update"  →  git pull + test + restart
"check_update" →  GitHub-এ নতুন version আছে কিনা
```

---

## Known Limitations (v9.0)

| সমস্যা | কারণ | সমাধান (Roadmap) |
|--------|------|-----------------|
| Wayland hotkey | pynput X11 only | P1-A: ydotool |
| Wake word always-on নেই | Feature flag | P1-B: two-stage |
| AT-SPI সব app-এ কাজ করে না | App support | P2-E: OCR fallback |
| Single task at a time | Design | P3-A: AgentPool |
| No mobile control | Not built | P2-D: Telegram bot |

---

## Testing Commands

```bash
# Module imports check
python -c "import config; print('config OK')"
python -c "from core.brain import Brain; print('brain OK')"
python -c "from core.executor import Executor; e=Executor(); print(f'executor OK — {len(e.list_tools())} tools')"
python -c "from core.nova_loop import NOVALoop; print('loop OK')"
python -c "from modules.system_control import take_screenshot; print('system OK')"
python -c "from modules.vision import describe_screen; print('vision OK')"
python -c "from modules.hotkey_listener import HotkeyListener; print('hotkey OK')"
python -c "from modules.system_tray import NovaTray; print('tray OK')"
python -c "from modules.mini_ui import MiniUI; print('mini_ui OK')"
python -c "from modules.os_controller import xdo_click; print('os_ctrl OK')"
python -c "from ui_modern import ModernUI; print('ui OK')"

# Full test
python nova.py --text --goal "স্ক্রিনশট নাও এবং কী দেখছ বলো" --dry-run

# Daemon test
python nova_daemon.py &
sleep 2
python nova_ipc.py --status
python nova_ipc.py "হ্যালো NOVA"
python nova_daemon.py --stop
```

---

## Adding a New Tool — Checklist

1. **Function লেখো** (যেকোনো module-এ):
```python
def my_new_tool(param1: str, param2: int = 0) -> dict:
    try:
        # কাজ করো
        return {"observation": "ফলাফল বাংলায়", "display": None}
    except SpecificException as e:
        return {"observation": f"ত্রুটি: {e}", "display": None}
```

2. **executor.py-এ register করো:**
```python
# _register_all() method-এ যোগ করো:
from modules.my_module import my_new_tool
self._map["my_new_tool"] = my_new_tool
```

3. **prompts/system.txt-এ document করো:**
```
- my_new_tool: বর্ণনা (args: param1, param2?)
```

4. **Test করো:**
```bash
python -c "from core.executor import Executor; e=Executor(); print(e.run('my_new_tool', {'param1': 'test'}))"
```

---

## File Modification Guide

| পরিবর্তন করতে চাইলে | কোন ফাইল |
|---------------------|----------|
| LLM model পরিবর্তন | `config.py` → `MODELS` dict |
| নতুন hotkey | `modules/hotkey_listener.py` |
| Tray menu item যোগ | `modules/system_tray.py` |
| Prompt পরিবর্তন | `prompts/*.txt` |
| নতুন OS tool | `modules/os_controller.py` + `executor.py` |
| Boot behavior | `nova_service.sh` + `nova.service` |
| Cost limit | `.env` → `NOVA_COST_LIMIT` |
| Voice language | `modules/voice_stt.py` + `modules/voice_tts.py` |

---

## Environment Variables Reference

```env
# Required
OPENROUTER_API_KEY=sk-or-...

# Voice
FEATURE_VOICE_INPUT=false     # Whisper STT
FEATURE_VOICE_OUTPUT=false    # edge-tts Bengali

# Safety
FEATURE_SAFETY=true           # Dangerous command filter
NOVA_YOLO=false               # true = skip all confirmations

# Cost
NOVA_COST_LIMIT=1.0           # USD per session warning

# Remote
FEATURE_API_SERVER=false      # FastAPI on localhost
API_SERVER_PORT=8765

# Notifications
TELEGRAM_TOKEN=               # Optional mobile notifications
TELEGRAM_CHAT_ID=
```

---

*এই ফাইলটি Claude Code automatically পড়বে। NOVA-র সব context এখানে আছে।*
