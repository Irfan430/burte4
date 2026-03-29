"""core/memory.py — JSON-based pattern memory for NOVA."""
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from config import MEMORY_FILE

logger = logging.getLogger(__name__)


class Memory:
    """Persistent pattern memory backed by a JSON file."""

    def __init__(self, path: Path = MEMORY_FILE):
        self.path = path
        self._data: dict[str, Any] = {"patterns": [], "preferences": {}}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(f"মেমোরি লোড ব্যর্থ, নতুন শুরু করছি: {exc}")
                self._data = {"patterns": [], "preferences": {}}
        else:
            self._data = {"patterns": [], "preferences": {}}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.error(f"মেমোরি সংরক্ষণ ব্যর্থ: {exc}")

    # ------------------------------------------------------------------
    # Pattern storage
    # ------------------------------------------------------------------

    def save_pattern(
        self,
        goal: str,
        steps: list[str],
        tools_used: list[str],
        success: bool,
    ) -> None:
        """Save a completed task pattern for future reference."""
        pattern = {
            "goal": goal,
            "steps": steps,
            "tools_used": tools_used,
            "success": success,
            "timestamp": time.time(),
        }
        self._data.setdefault("patterns", []).append(pattern)

        # Update tool preferences
        prefs = self._data.setdefault("preferences", {})
        for tool in tools_used:
            prefs[tool] = prefs.get(tool, 0) + (1 if success else 0)

        self._save()
        logger.debug(f"প্যাটার্ন সংরক্ষিত: {goal[:40]}")

    def find_similar(self, goal: str) -> list[dict]:
        """Find patterns with similar keywords (simple keyword matching)."""
        keywords = set(re.findall(r"\w+", goal.lower()))
        results = []
        for pattern in self._data.get("patterns", []):
            pattern_words = set(re.findall(r"\w+", pattern.get("goal", "").lower()))
            overlap = keywords & pattern_words
            if overlap:
                score = len(overlap) / max(len(keywords), 1)
                results.append({**pattern, "_score": score})

        results.sort(key=lambda x: x["_score"], reverse=True)
        return results[:5]

    def get_preferences(self) -> dict[str, int]:
        """Return tool usage frequency (most used first)."""
        prefs = self._data.get("preferences", {})
        return dict(sorted(prefs.items(), key=lambda kv: kv[1], reverse=True))

    def get_all_patterns(self) -> list[dict]:
        return self._data.get("patterns", [])

    def clear(self) -> None:
        self._data = {"patterns": [], "preferences": {}}
        self._save()
        logger.info("মেমোরি পরিষ্কার করা হয়েছে।")
