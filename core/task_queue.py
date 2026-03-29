"""core/task_queue.py — Priority task queue with cron-style scheduling."""
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)
QUEUE_FILE = DATA_DIR / "task_queue.json"


@dataclass
class Task:
    goal: str
    priority: int = 5          # 1 (highest) – 10 (lowest)
    schedule: Optional[str] = None   # ISO datetime string or cron expression
    task_id: str = ""
    created_at: float = field(default_factory=time.time)
    status: str = "pending"    # pending | running | done | failed

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{int(self.created_at * 1000)}"


class TaskQueue:
    """Thread-safe priority task queue with JSON persistence."""

    def __init__(self):
        self._lock = threading.Lock()
        self._tasks: list[Task] = []
        self._load()

    def _load(self) -> None:
        if QUEUE_FILE.exists():
            try:
                with QUEUE_FILE.open("r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                    self._tasks = [Task(**t) for t in raw]
                    # Keep only pending tasks across restarts
                    self._tasks = [t for t in self._tasks if t.status == "pending"]
                logger.info(f"টাস্ক কিউ লোড: {len(self._tasks)} পেন্ডিং টাস্ক")
            except (json.JSONDecodeError, OSError, TypeError) as exc:
                logger.warning(f"টাস্ক কিউ লোড ব্যর্থ: {exc}")
                self._tasks = []

    def _save(self) -> None:
        try:
            QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with QUEUE_FILE.open("w", encoding="utf-8") as fh:
                json.dump([asdict(t) for t in self._tasks], fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.error(f"টাস্ক কিউ সংরক্ষণ ব্যর্থ: {exc}")

    def add_task(self, goal: str, priority: int = 5, schedule: Optional[str] = None) -> Task:
        """Add a new task to the queue."""
        task = Task(goal=goal, priority=priority, schedule=schedule)
        with self._lock:
            self._tasks.append(task)
            self._tasks.sort(key=lambda t: t.priority)
            self._save()
        logger.info(f"নতুন টাস্ক যোগ: [{task.task_id}] {goal[:50]}")
        return task

    def get_next(self) -> Optional[Task]:
        """Pop the highest-priority pending task (respecting schedule)."""
        now = time.time()
        with self._lock:
            for task in self._tasks:
                if task.status != "pending":
                    continue
                if task.schedule:
                    try:
                        scheduled_time = float(task.schedule)
                        if scheduled_time > now:
                            continue
                    except ValueError:
                        pass  # Non-numeric schedule strings are run immediately
                task.status = "running"
                self._save()
                return task
        return None

    def mark_done(self, task_id: str, success: bool = True) -> None:
        with self._lock:
            for task in self._tasks:
                if task.task_id == task_id:
                    task.status = "done" if success else "failed"
                    break
            # Remove completed tasks older than 50 entries
            done = [t for t in self._tasks if t.status in ("done", "failed")]
            if len(done) > 50:
                self._tasks = [t for t in self._tasks if t.status not in ("done", "failed")]
                self._tasks.extend(done[-50:])
            self._save()

    def list_tasks(self) -> list[dict]:
        with self._lock:
            return [asdict(t) for t in self._tasks]

    def clear_done(self) -> None:
        with self._lock:
            self._tasks = [t for t in self._tasks if t.status not in ("done", "failed")]
            self._save()
