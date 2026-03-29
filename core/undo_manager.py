"""core/undo_manager.py — File backup and rollback system."""
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from config import BACKUPS_DIR

logger = logging.getLogger(__name__)


class UndoManager:
    """Manages file backups and provides rollback capability."""

    def __init__(self):
        self.backups_dir = BACKUPS_DIR
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        # Session changelog: list of (original_path, backup_path)
        self.changelog: list[tuple[str, str]] = []

    def backup_file(self, path: str) -> Optional[str]:
        """Copy a file to BACKUPS_DIR with a timestamp suffix.

        Returns the backup path, or None if the source does not exist.
        """
        src = Path(path)
        if not src.exists():
            logger.warning(f"ব্যাকআপ করার জন্য ফাইল পাওয়া যায়নি: {path}")
            return None

        timestamp = int(time.time() * 1000)
        safe_name = src.name.replace("/", "_").replace("\\", "_")
        backup_path = self.backups_dir / f"{safe_name}.{timestamp}.bak"

        try:
            shutil.copy2(src, backup_path)
            self.changelog.append((str(src), str(backup_path)))
            logger.info(f"ব্যাকআপ তৈরি: {backup_path}")
            return str(backup_path)
        except OSError as exc:
            logger.error(f"ব্যাকআপ ব্যর্থ: {exc}")
            return None

    def rollback_last(self) -> str:
        """Restore the most recently backed-up file.

        Returns a status message in Bengali.
        """
        if not self.changelog:
            return "রোলব্যাক করার মতো কোনো ব্যাকআপ নেই।"

        original_path, backup_path = self.changelog[-1]
        src = Path(backup_path)
        dst = Path(original_path)

        if not src.exists():
            return f"ব্যাকআপ ফাইল পাওয়া যায়নি: {backup_path}"

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            self.changelog.pop()
            logger.info(f"রোলব্যাক সম্পন্ন: {original_path}")
            return f"রোলব্যাক সম্পন্ন: {original_path}"
        except OSError as exc:
            logger.error(f"রোলব্যাক ব্যর্থ: {exc}")
            return f"রোলব্যাক ব্যর্থ: {exc}"

    def rollback_all(self) -> str:
        """Restore all backups in reverse chronological order."""
        if not self.changelog:
            return "রোলব্যাক করার মতো কোনো ব্যাকআপ নেই।"

        results = []
        while self.changelog:
            results.append(self.rollback_last())
        return "\n".join(results)

    def get_changelog(self) -> list[dict[str, str]]:
        return [{"original": o, "backup": b} for o, b in self.changelog]
