
<div align="center">

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗     ██╗   ██╗ █████╗
████╗  ██║██╔═══██╗██║   ██║██╔══██╗    ██║   ██║██╔══██╗
██╔██╗ ██║██║   ██║██║   ██║███████║    ██║   ██║╚██████║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║    ╚██╗ ██╔╝ ╚═══██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║     ╚████╔╝  █████╔╝
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝      ╚═══╝   ╚════╝
```

### **স্বায়ত্তশাসিত OS এজেন্ট — আপনার কম্পিউটার নিজেই কাজ করে**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Multi--LLM-FF6B35?style=for-the-badge&logo=openai&logoColor=white)](https://openrouter.ai)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Mac%20%7C%20Windows-0D1117?style=for-the-badge&logo=linux&logoColor=white)](.)
[![License](https://img.shields.io/badge/License-Personal-E94560?style=for-the-badge)](.)
[![Status](https://img.shields.io/badge/Status-Production-00D4AA?style=for-the-badge)](.)

</div>

---

<div align="center">

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   "শুধু বলুন — NOVA বাকি সব করবে"                              │
│                                                                 │
│   Boot হলেই চালু  •  সবসময় Background-এ  •  Full OS Control  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

</div>

---

## ◈ NOVA কী?

NOVA v9 একটি **Autonomous OS Daemon** — এটি কোনো সাধারণ Python অ্যাপ নয়। এটি আপনার **অপারেটিং সিস্টেমের অংশ** হয়ে যায়।

```
আগে:                              NOVA দিয়ে:
─────────────────────────────────────────────────────
আপনি নিজে app খুলবেন      →    "Firefox-এ YouTube খোলো"
নিজে file organize করবেন  →    "Downloads ফোল্ডার গুছিয়ে দাও"
নিজে code লিখবেন          →    "এই bug fix করো"
নিজে screenshot নেবেন     →    "স্ক্রিনে কী আছে বলো"
নিজে সব করবেন             →    আপনি শুধু বলবেন
```

---

## ◈ System Architecture

```
                    ╔═══════════════════════════════╗
                    ║     আপনি (User / Commander)    ║
                    ╚═══════════╤═══════════════════╝
                                │
          ┌─────────────────────┼──────────────────────┐
          │                     │                      │
   ┌──────▼──────┐    ┌─────────▼────────┐   ┌────────▼──────┐
   │  🎤 ভয়েস   │    │  ⌨  Ctrl+Space   │   │  💻 Terminal  │
   │  "নোভা..."  │    │  Mini UI Overlay │   │  nova "কমান্ড"│
   └──────┬──────┘    └─────────┬────────┘   └────────┬──────┘
          │                     │                      │
          └─────────────────────┼──────────────────────┘
                                │ IPC (Unix Socket)
                    ╔═══════════▼═══════════╗
                    ║    NOVA DAEMON        ║
                    ║  nova_daemon.py       ║
                    ║  (24/7 background)    ║
                    ╚═══════════╤═══════════╝
                                │
         ┌──────────────────────┼─────────────────────┐
         │                      │                     │
  ┌──────▼──────┐    ┌──────────▼───────┐   ┌────────▼──────┐
  │ 🧠 Brain    │    │  🔄 OODA Loop    │   │ 🖥 Context    │
  │ Multi-LLM   │    │  Self-Correct    │   │ Engine        │
  │ Model Route │    │  Screenshot      │   │ Active Window │
  │ Cost Track  │    │  Compare         │   │ Clipboard     │
  └──────┬──────┘    └──────────┬───────┘   └───────────────┘
         │                      │
         └──────────┬───────────┘
                    │
         ╔══════════▼════════════╗
         ║    EXECUTOR (55+ Tools)║
         ╚══════════╤════════════╝
                    │
    ┌───────────────┼───────────────────┐
    │               │                   │
┌───▼────┐   ┌──────▼──────┐   ┌───────▼──────┐
│🖱 OS   │   │ 🌐 Browser  │   │ 📁 System    │
│xdotool │   │ Playwright  │   │ Files, Git   │
│wmctrl  │   │ CDP Capture │   │ Process, Net │
│xrandr  │   │ API Reverse │   │ Voice, Vision│
└────────┘   └─────────────┘   └──────────────┘
```

---

## ◈ Features

<div align="center">

| ✦ Feature | বিবরণ |
|-----------|--------|
| 🔄 **OODA Self-Correction** | প্রতি ধাপে screenshot নেয়, compare করে, নিজেই replan করে |
| 🧠 **Smart Model Routing** | Code → Qwen Coder, Browse → Gemini Flash, Think → DeepSeek R1 |
| 🖥 **True OS Control** | xdotool দিয়ে যেকোনো app-এ click/type করে |
| 🌐 **Browser Automation** | Playwright + CDP, network intercept, API reverse engineer |
| 👁 **Vision (Qwen-VL)** | স্ক্রিনে কী আছে বোঝে, before/after compare করে |
| 🎤 **Bengali Voice** | "নোভা" বললেই শোনে, Whisper STT + edge-tts Bengali TTS |
| ⌨ **Global Hotkey** | Ctrl+Space যেকোনো app থেকে — Mini UI overlay আসে |
| 🔔 **System Tray** | Taskbar-এ সবসময় আছে, real-time status দেখায় |
| 🧩 **Plugin System** | `plugins/` folder-এ .py file রাখলেই নতুন tool |
| 💾 **Pattern Memory** | সফল কাজের pattern মনে রাখে, পরে hint দেয় |
| 💰 **Cost Dashboard** | Real-time API cost tracking, model-wise breakdown |
| 🛡 **Safety Layer** | Dangerous command block, file backup before modify |
| 🔌 **Remote API** | FastAPI + WebSocket, Telegram থেকে mobile control |
| ↩ **Rollback/Undo** | যেকোনো file পরিবর্তন undo করা যায় |

</div>

---

## ◈ Quick Start

### ১. ইনস্টল করুন

```bash
git clone https://github.com/Irfan430/burte4 nova
cd nova
./install.sh
```

### ২. API Key সেট করুন

```bash
nano .env
```

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxx

# Optional features
FEATURE_VOICE_INPUT=true
FEATURE_VOICE_OUTPUT=true
FEATURE_API_SERVER=false
NOVA_COST_LIMIT=1.0
```

### ৩. NOVA চালু করুন

```bash
python3 nova_daemon.py
```

**পরের লগইন থেকে স্বয়ংক্রিয়ভাবে চালু হবে।** ✓

---

## ◈ ব্যবহার

### Hotkey দিয়ে (সব জায়গা থেকে)

```
Ctrl+Space    →  Mini input overlay আসবে
Alt+V         →  Voice mode চালু
Ctrl+Alt+N    →  চলমান কাজ বন্ধ
```

### Terminal থেকে

```bash
nova "ব্রাউজারে github.com খোলো"
nova "Downloads ফোল্ডার-এ কী আছে বলো"
nova "এই Python script-এ bug আছে কিনা দেখো"
nova "স্ক্রিনশট নাও এবং কী দেখছ বলো"
nova "ভলিউম ৫০ করো"
nova --status
nova --stop
```

### Voice দিয়ে

```
বলুন: "নোভা, Firefox-এ YouTube খোলো"
বলুন: "নোভা, এই file-টা Desktop-এ নিয়ে যাও"
বলুন: "নোভা, ব্যাটারি কত?"
```

---

## ◈ Project Structure

```
nova/
│
├── 🔧 nova_daemon.py        ← 24/7 OS Daemon (মূল প্রক্রিয়া)
├── 📡 nova_ipc.py           ← IPC Client (daemon-এ কমান্ড পাঠাও)
├── 🖥  nova.py              ← Full UI / Manual mode
├── ⚙  config.py            ← সব configuration (.env থেকে)
├── 📜 nova_service.sh       ← systemd/autostart wrapper
├── 🚀 install.sh            ← One-command setup
│
├── core/
│   ├── 🧠 brain.py          ← Multi-LLM, model routing, cost
│   ├── ⚡ executor.py        ← 55+ tool dispatcher
│   ├── 🔄 nova_loop.py      ← OODA self-correction loop
│   ├── 💾 memory.py         ← Pattern memory (JSON)
│   ├── 📋 task_queue.py     ← Priority queue + cron
│   └── ↩  undo_manager.py  ← Rollback / backup
│
├── modules/
│   ├── ⌨  hotkey_listener.py  ← Global hotkeys (pynput)
│   ├── 🔔 system_tray.py      ← Taskbar icon (pystray)
│   ├── 💬 mini_ui.py          ← Floating input overlay
│   ├── 👁  screen_watcher.py  ← Real-time screen monitor
│   ├── 🗺  context_engine.py  ← OS context awareness
│   ├── 🖱  os_controller.py   ← xdotool, wmctrl, xrandr
│   ├── 📡 event_bus.py        ← Battery, network events
│   ├── 🖥  system_control.py  ← Cross-platform OS tools
│   ├── 🌐 web_agent.py        ← browser_use + CDP
│   ├── 🎭 playwright_agent.py ← Playwright automation
│   ├── 👁  vision.py          ← Qwen-VL screen analysis
│   ├── 🎤 voice_stt.py        ← Whisper Bengali STT
│   ├── 🔊 voice_tts.py        ← edge-tts Bengali TTS
│   ├── 💰 cost_display.py     ← API cost tracker
│   ├── 🛡  safety.py          ← Dangerous command filter
│   ├── 🌍 api_server.py       ← FastAPI remote control
│   └── 📂 github_agent.py     ← Git operations
│
├── utils/
│   └── 🔁 retry.py          ← Exponential backoff
│
├── ui_modern.py             ← Full Tkinter UI (optional)
├── prompts/                 ← Bengali LLM prompts
│   ├── system.txt
│   ├── vision.txt
│   ├── decompose.txt
│   ├── replan.txt
│   ├── compress.txt
│   └── safety.txt
└── plugins/                 ← Auto-loaded custom tools
    └── example_plugin.py
```

---

## ◈ Available Tools (55+)

<details>
<summary><b>🖥 System Control (20 tools)</b></summary>

```
take_screenshot   type_text         press_key
mouse_click       mouse_move        open_app
run_command       read_file         write_file
delete_file       list_dir          clipboard_get
clipboard_set     file_search       zip_folder
open_terminal     network_info      process_list
kill_process      set_volume        get_battery
notify
```
</details>

<details>
<summary><b>🖱 OS Controller (15 tools)</b></summary>

```
xdo_click         xdo_type          xdo_key
list_windows      focus_window      close_window
maximize_window   minimize_window   move_window
clipboard_get_os  clipboard_set_os  list_displays
set_brightness    enable_autostart  disable_autostart
```
</details>

<details>
<summary><b>🌐 Browser Tools (13 tools)</b></summary>

```
web_search         scroll_page        browser_back
browser_forward    new_tab            close_tab
get_page_source    execute_js         intercept_network
get_network_log    download_file      extract_text
reverse_engineer_api
```
</details>

<details>
<summary><b>👁 Vision & AI (3 tools)</b></summary>

```
describe_screen    compare_screens    take_screenshot
```
</details>

<details>
<summary><b>📂 Git / GitHub (6 tools)</b></summary>

```
git_clone    git_commit    git_push
git_status   git_create_branch   git_diff
```
</details>

<details>
<summary><b>🧩 System & Memory (8 tools)</b></summary>

```
save_memory    recall_memory    rollback_last
queue_task     list_tasks       send_telegram
hello_world    get_date
```
</details>

---

## ◈ LLM Model Routing

```
কাজের ধরন            →  মডেল                              কারণ
────────────────────────────────────────────────────────────
code/script/debug    →  qwen/qwen2.5-coder-32b-instruct   সেরা code মডেল
browse/web/url       →  google/gemini-flash-1.5            দ্রুত, সস্তা
analyze/plan/think   →  deepseek/deepseek-r1               গভীর reasoning
vision/screen/image  →  qwen/qwen2.5-vl-7b-instruct        vision specialist
default              →  deepseek/deepseek-chat             সস্তা + দ্রুত
```

---

## ◈ Daemon Status

NOVA নিজের status `~/.nova/status.json`-এ লেখে:

```json
{
  "state": "working",
  "goal": "ব্রাউজারে YouTube খুলছি",
  "step": "playwright_navigate চালাচ্ছি",
  "ts": "2025-03-29T14:23:07"
}
```

System tray এবং Mini UI এটা poll করে real-time আপডেট দেখায়।

---

## ◈ Plugin তৈরি করুন

```python
# plugins/my_tool.py

def my_custom_tool(text: str) -> dict:
    return {"observation": f"কাজ হয়েছে: {text}", "display": None}

def register() -> dict:
    return {"my_tool": my_custom_tool}
```

`plugins/` folder-এ রাখলে NOVA restart ছাড়াই লোড হবে। ✓

---

## ◈ Requirements

```
Python 3.11+
Linux (primary) / macOS / Windows

System packages (Linux):
  xdotool  wmctrl  xclip  scrot  notify-send
  at-spi2-core  portaudio19-dev

Python packages:
  httpx  python-dotenv  mss  Pillow  psutil
  pynput  pystray  playwright  fastapi  uvicorn
  edge-tts  openai-whisper  pyperclip  rich
```

---

<div align="center">

```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   NOVA v9 — আপনার OS এখন আপনার Assistant               ║
║                                                          ║
║   Boot → Daemon → Hotkey → Command → Done               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

**Built with ❤ for full autonomy**

</div>
