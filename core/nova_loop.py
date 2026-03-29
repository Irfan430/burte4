"""core/nova_loop.py — OODA (Observe-Orient-Decide-Act) self-correction loop."""
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from config import LOGS_DIR, SCREENSHOTS_DIR, NOVA_STATUS_FILE, NOVA_RESPONSE_FILE

logger = logging.getLogger(__name__)


class NOVALoop:
    """Autonomous OODA loop with self-correction, screenshot comparison, and replanning."""

    MAX_RETRIES_PER_STEP = 3
    MAX_TOTAL_STEPS = 50

    def __init__(self, brain, executor, memory=None, tts=None, context_engine=None):
        self.brain = brain
        self.executor = executor
        self.memory = memory
        self.tts = tts
        self.context_engine = context_engine  # OS context awareness

        self._stop_event = threading.Event()
        self._session_log: list[dict] = []
        self._log_file: Path | None = None

        # Callbacks for UI
        self.on_thought: Callable[[str], None] = lambda x: None
        self.on_tool_call: Callable[[str, dict, dict], None] = lambda t, a, r: None
        self.on_observation: Callable[[str], None] = lambda x: None
        self.on_complete: Callable[[str], None] = lambda x: None
        self.on_error: Callable[[str], None] = lambda x: None

    # ------------------------------------------------------------------
    # Session logging
    # ------------------------------------------------------------------

    def _init_log(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file = LOGS_DIR / f"session_{ts}.jsonl"

    def _log(self, event: dict):
        event.setdefault("ts", datetime.now().isoformat())
        self._session_log.append(event)
        if self._log_file:
            try:
                with self._log_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            except OSError as exc:
                logger.warning(f"লগ লেখা ব্যর্থ: {exc}")

    # ------------------------------------------------------------------
    # Screenshot helpers
    # ------------------------------------------------------------------

    def _take_screenshot(self, label: str) -> str | None:
        """Take a screenshot, save to screenshots dir, return path."""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = str(SCREENSHOTS_DIR / f"{label}_{ts}.png")
            result = self.executor.run("take_screenshot", {"path": path})
            if "ত্রুটি" not in result.get("observation", ""):
                return path
        except Exception as exc:
            logger.warning(f"স্ক্রিনশট ব্যর্থ: {exc}")
        return None

    def _compare_screens(self, before: str | None, after: str | None) -> str:
        """Use vision model to compare before/after screenshots."""
        if not before or not after:
            return "স্ক্রিনশট তুলনা সম্ভব হয়নি।"
        try:
            result = self.executor.run("compare_screens", {"before_path": before, "after_path": after})
            return result.get("observation", "পরিবর্তন নির্ধারণ করা যায়নি।")
        except Exception as exc:
            logger.warning(f"স্ক্রিন তুলনা ব্যর্থ: {exc}")
            return "স্ক্রিন তুলনা ব্যর্থ হয়েছে।"

    # ------------------------------------------------------------------
    # Plan parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tool_call(raw: str) -> tuple[str, dict] | None:
        """Extract tool_name and args from LLM response JSON block."""
        try:
            raw = raw.strip()
            # Look for JSON block
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                return None
            blob = json.loads(raw[start:end + 1])
            tool = blob.get("tool") or blob.get("action") or blob.get("name")
            args = blob.get("args") or blob.get("parameters") or blob.get("params") or {}
            if tool:
                return str(tool), dict(args)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _write_status(self, state: str, goal: str = "", step: str = ""):
        """Write daemon status to ~/.nova/status.json for tray/overlay polling."""
        try:
            NOVA_STATUS_FILE.write_text(
                json.dumps({
                    "state": state,
                    "goal": goal[:80],
                    "step": step[:80],
                    "ts": datetime.now().isoformat(),
                }, ensure_ascii=False)
            )
        except OSError:
            pass

    def run(self, goal: str, dry_run: bool = False) -> str:
        """Execute a goal autonomously. Returns final summary."""
        self._init_log()
        self._stop_event.clear()
        self._log({"event": "start", "goal": goal, "dry_run": dry_run})
        self._write_status("thinking", goal=goal, step="লক্ষ্য বিশ্লেষণ")

        # Emit thought
        self.on_thought(f"লক্ষ্য বিশ্লেষণ করছি: {goal}")

        # Gather OS context and inject into goal
        os_context = ""
        if self.context_engine:
            try:
                os_context = self.context_engine.get_context_string()
            except Exception:
                pass

        # Check memory for similar patterns
        hint = ""
        if self.memory:
            similar = self.memory.find_similar(goal)
            if similar:
                hint = f"\n\n[মেমোরি হিন্ট]: এই ধরনের কাজ আগে করা হয়েছিল:\n"
                for s in similar[:2]:
                    hint += f"- লক্ষ্য: {s['goal']}, ধাপ: {', '.join(s['steps'][:3])}\n"

        # Decompose into steps
        self.on_thought("লক্ষ্যকে ধাপে ভাগ করছি...")
        steps = self.brain.decompose(goal + hint)
        self._log({"event": "decompose", "steps": steps})
        self.on_thought(f"{len(steps)}টি ধাপ তৈরি হয়েছে: {steps}")
        self._write_status("working", goal=goal, step=f"{len(steps)}টি ধাপ")

        # Build conversation history — inject OS context into first message
        context_block = f"\n\n[OS Context]\n{os_context}" if os_context else ""
        history = [
            {
                "role": "user",
                "content": (
                    f"লক্ষ্য: {goal}{context_block}\n\n"
                    f"ধাপসমূহ:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)) +
                    f"\n\nউপলব্ধ টুল: {self.executor.list_tools()}\n"
                    "প্রতিটি পদক্ষেপে JSON ফরম্যাটে টুল কল করো: "
                    '{"tool": "tool_name", "args": {...}}'
                    "\nলক্ষ্য সম্পন্ন হলে বলো: DONE: <সারাংশ>"
                ),
            }
        ]

        total_steps = 0
        completed_steps: list[str] = []
        tools_used: list[str] = []
        last_observation = ""
        same_state_count = 0

        while not self._stop_event.is_set() and total_steps < self.MAX_TOTAL_STEPS:
            total_steps += 1

            # Get next action from brain
            self.on_thought(f"পরবর্তী পদক্ষেপ চিন্তা করছি... (ধাপ {total_steps})")
            self._write_status("thinking", goal=goal, step=f"ধাপ {total_steps}")
            raw_response = self.brain.call(history, task_hint=goal)
            self._log({"event": "brain_response", "step": total_steps, "raw": raw_response})

            # Check if done
            if "DONE:" in raw_response or raw_response.strip().startswith("DONE"):
                summary = raw_response.split("DONE:", 1)[-1].strip() if "DONE:" in raw_response else raw_response
                self._write_status("idle", goal=goal, step="সম্পন্ন ✓")
                # Write last response for overlay/tray to read
                try:
                    NOVA_RESPONSE_FILE.write_text(summary, encoding="utf-8")
                except OSError:
                    pass
                self.on_complete(summary)
                self._log({"event": "complete", "summary": summary})
                if self.memory:
                    self.memory.save_pattern(goal, completed_steps, tools_used, success=True)
                if self.tts:
                    self.tts.speak(f"কাজ সম্পন্ন: {summary}")
                return summary

            # Parse tool call
            parsed = self._parse_tool_call(raw_response)
            if not parsed:
                # No valid tool call — add to history and continue
                history.append({"role": "assistant", "content": raw_response})
                history.append({
                    "role": "user",
                    "content": "JSON টুল কল ফরম্যাটে উত্তর দাও অথবা DONE: <সারাংশ> লেখো।",
                })
                continue

            tool_name, tool_args = parsed

            # Take screenshot before action
            screen_before = self._take_screenshot("before")

            # Execute with retries
            observation = ""
            for attempt in range(self.MAX_RETRIES_PER_STEP):
                if self._stop_event.is_set():
                    break
                self.on_thought(f"টুল চালাচ্ছি: {tool_name} (চেষ্টা {attempt+1})")

                if dry_run:
                    result = {"observation": f"[DRY-RUN] {tool_name}({tool_args}) — চালানো হয়নি", "display": None}
                else:
                    result = self.executor.run(tool_name, tool_args)

                observation = result.get("observation", "")
                elapsed = result.get("_elapsed_s", 0)
                self.on_tool_call(tool_name, tool_args, result)
                self._log({
                    "event": "tool_call",
                    "tool": tool_name,
                    "args": tool_args,
                    "observation": observation,
                    "elapsed_s": elapsed,
                    "attempt": attempt + 1,
                })

                if "ত্রুটি" not in observation and "Error" not in observation:
                    break  # Success

                if attempt < self.MAX_RETRIES_PER_STEP - 1:
                    logger.warning(f"টুল ব্যর্থ, পুনরায় চেষ্টা: {observation}")
                    time.sleep(1)

            tools_used.append(tool_name)
            completed_steps.append(f"{tool_name}: {observation[:100]}")

            # Take screenshot after action
            screen_after = self._take_screenshot("after")

            # Compare screens to detect progress
            if screen_before and screen_after:
                screen_diff = self._compare_screens(screen_before, screen_after)
                self._log({"event": "screen_diff", "diff": screen_diff})

                # Detect if stuck in same state
                if "পরিবর্তন নেই" in screen_diff or "পার্থক্য নেই" in screen_diff:
                    same_state_count += 1
                else:
                    same_state_count = 0

                if same_state_count >= 2:
                    self.on_thought("একই অবস্থায় আটকে আছি, নতুন পদ্ধতি চেষ্টা করছি...")
                    new_steps = self.brain.replan(goal, completed_steps, "একই অবস্থায় আটকে আছি")
                    history.append({
                        "role": "user",
                        "content": f"নতুন পদ্ধতি: {new_steps}। ভিন্ন টুল বা পদ্ধতি ব্যবহার করো।",
                    })
                    same_state_count = 0
                    continue

            # Stuck detection — same observation twice
            if observation == last_observation and observation:
                same_state_count += 1
            last_observation = observation

            self.on_observation(observation)

            # Update history
            history.append({"role": "assistant", "content": raw_response})
            history.append({"role": "user", "content": f"পর্যবেক্ষণ: {observation}\n\nপরবর্তী পদক্ষেপ নাও।"})

        # Max steps reached or stopped
        if self._stop_event.is_set():
            msg = "ব্যবহারকারী দ্বারা বন্ধ করা হয়েছে।"
        else:
            msg = f"সর্বোচ্চ {self.MAX_TOTAL_STEPS}টি ধাপ সম্পন্ন হয়েছে।"

        self._write_status("idle", goal=goal, step="বন্ধ")
        self.on_complete(msg)
        if self.memory:
            self.memory.save_pattern(goal, completed_steps, tools_used, success=False)
        return msg

    def stop(self):
        """Gracefully stop the current task."""
        self._stop_event.set()
        self._write_status("idle")
        logger.info("NOVA লুপ বন্ধের অনুরোধ পাওয়া গেছে")
