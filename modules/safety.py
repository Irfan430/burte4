"""modules/safety.py — Command safety checker and guardrails."""
import logging
import re
from pathlib import Path

from config import NOVA_YOLO, FEATURE_SAFETY

logger = logging.getLogger(__name__)

# Patterns that are always blocked regardless of NOVA_YOLO
BLACKLIST_PATTERNS: list[str] = [
    r"rm\s+-[rRf]+\s*/\b",
    r"mkfs\.",
    r"dd\s+if=.*of=/dev/(sd|nvme|hd)",
    r":\(\)\s*\{.*\}\s*;",          # Fork bomb
    r"chmod\s+-R\s+777\s+/",
    r">\s*/dev/sda",
    r"format\s+[Cc]:",              # Windows format C:
    r"deltree\s+/[Yy]\s+[Cc]:\\",
]

# Patterns that require confirmation unless NOVA_YOLO=True
CONFIRM_PATTERNS: list[str] = [
    r"\brm\b.*-[rRf]",
    r"\bsudo\b",
    r"\bdrop\s+table\b",
    r"\btruncate\b",
    r"\bkill\s+-9\b",
    r"\bpoweroff\b",
    r"\breboot\b",
    r"\bshutdown\b",
    r"\bchown\s+-R\b",
]


def check_command(cmd: str) -> tuple[bool, str]:
    """Check if a shell command is safe to execute.

    Returns:
        (is_safe, reason) — is_safe=False means blocked.
    """
    if not FEATURE_SAFETY:
        return True, "নিরাপত্তা পরীক্ষা নিষ্ক্রিয়"

    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            reason = f"বিপজ্জনক কমান্ড ব্লক করা হয়েছে: {pattern}"
            logger.warning(f"সেফটি ব্লক: {cmd!r} — {reason}")
            return False, reason

    return True, "নিরাপদ"


def needs_confirm(cmd: str) -> bool:
    """Return True if the command needs user confirmation."""
    if not FEATURE_SAFETY or NOVA_YOLO:
        return False
    for pattern in CONFIRM_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True
    return False


def require_confirm(action: str) -> bool:
    """Prompt user for confirmation of a potentially destructive action.

    In CLI context prints a prompt; in GUI context this should be overridden.
    Returns True if confirmed or NOVA_YOLO is set.
    """
    if NOVA_YOLO or not FEATURE_SAFETY:
        return True

    print(f"\n⚠️  সতর্কতা: এই কাজটি করতে চান? → {action}")
    answer = input("নিশ্চিত করতে 'হ্যাঁ' টাইপ করুন: ").strip().lower()
    confirmed = answer in ("হ্যাঁ", "yes", "y", "ha", "han")
    if not confirmed:
        logger.info(f"ব্যবহারকারী অস্বীকার করেছেন: {action}")
    return confirmed


def backup_before_modify(path: str) -> None:
    """Trigger UndoManager backup before a file is modified or deleted."""
    try:
        from core.undo_manager import UndoManager
        undo = UndoManager()
        undo.backup_file(path)
    except Exception as exc:
        logger.warning(f"ব্যাকআপ নেওয়া যায়নি: {exc}")
