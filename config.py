import os
from pathlib import Path
from dotenv import load_dotenv
import platform

load_dotenv()

# Platform detection
IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

# API Keys from .env
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Model routing
MODELS = {
    "code": "qwen/qwen2.5-coder-32b-instruct",
    "browse": "google/gemini-flash-1.5",
    "analyze": "deepseek/deepseek-r1",
    "vision": "qwen/qwen2.5-vl-7b-instruct",
    "default": "deepseek/deepseek-chat",
}

# Features (from .env)
FEATURE_VOICE_INPUT = os.getenv("FEATURE_VOICE_INPUT", "false").lower() == "true"
FEATURE_VOICE_OUTPUT = os.getenv("FEATURE_VOICE_OUTPUT", "false").lower() == "true"
FEATURE_SAFETY = os.getenv("FEATURE_SAFETY", "true").lower() == "true"
NOVA_YOLO = os.getenv("NOVA_YOLO", "false").lower() == "true"  # Skip safety confirms
NOVA_COST_LIMIT = float(os.getenv("NOVA_COST_LIMIT", "1.0"))
FEATURE_API_SERVER = os.getenv("FEATURE_API_SERVER", "false").lower() == "true"
API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", "8765"))

# Project paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
BACKUPS_DIR = DATA_DIR / "backups"
MEMORY_FILE = DATA_DIR / "memory.json"
PROMPTS_DIR = BASE_DIR / "prompts"

# Daemon runtime paths (~/.nova/)
NOVA_RUNTIME_DIR = Path.home() / ".nova"
NOVA_SOCK_PATH   = NOVA_RUNTIME_DIR / "nova.sock"
NOVA_PID_FILE    = NOVA_RUNTIME_DIR / "nova.pid"
NOVA_STATUS_FILE = NOVA_RUNTIME_DIR / "status.json"
NOVA_LOG_FILE    = NOVA_RUNTIME_DIR / "logs" / "nova.log"
NOVA_RESPONSE_FILE = NOVA_RUNTIME_DIR / "last_response.txt"

# Create directories
for d in [DATA_DIR, LOGS_DIR, SCREENSHOTS_DIR, BACKUPS_DIR,
          NOVA_RUNTIME_DIR, NOVA_RUNTIME_DIR / "logs"]:
    d.mkdir(parents=True, exist_ok=True)

# OpenRouter base URL
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
