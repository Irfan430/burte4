"""core/executor.py — Tool dispatcher. Maps tool names to implementations."""
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

ToolResult = dict[str, Any]  # {"observation": str, "display": str | None}


def _make_result(observation: str, display: str | None = None) -> ToolResult:
    return {"observation": observation, "display": display}


def _timeout_wrap(fn, timeout: float = 30.0):
    """Run fn() with a simple thread-based timeout."""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return _make_result(f"ত্রুটি: টুল {timeout}s-এর মধ্যে সম্পন্ন হয়নি।")


class Executor:
    """Dispatches tool calls to their implementations."""

    def __init__(self):
        self._map: dict[str, Any] = {}
        self._register_all()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def _register_all(self):
        """Register all available tools, skipping unavailable ones."""
        # System tools
        try:
            from modules.system_control import (
                take_screenshot, type_text, press_key, mouse_click,
                mouse_move, open_app, run_command, read_file, write_file,
                delete_file, list_dir, clipboard_get, clipboard_set,
                file_search, zip_folder, open_terminal, network_info,
                process_list, kill_process, set_volume, get_battery, notify,
            )
            self._map.update({
                "take_screenshot": take_screenshot,
                "type_text": type_text,
                "press_key": press_key,
                "mouse_click": mouse_click,
                "mouse_move": mouse_move,
                "open_app": open_app,
                "run_command": run_command,
                "read_file": read_file,
                "write_file": write_file,
                "delete_file": delete_file,
                "list_dir": list_dir,
                "clipboard_get": clipboard_get,
                "clipboard_set": clipboard_set,
                "file_search": file_search,
                "zip_folder": zip_folder,
                "open_terminal": open_terminal,
                "network_info": network_info,
                "process_list": process_list,
                "kill_process": kill_process,
                "set_volume": set_volume,
                "get_battery": get_battery,
                "notify": notify,
            })
            logger.info("সিস্টেম কন্ট্রোল টুল লোড সম্পন্ন")
        except ImportError as e:
            logger.warning(f"সিস্টেম কন্ট্রোল লোড ব্যর্থ: {e}")

        # Vision tools
        try:
            from modules.vision import describe_screen, compare_screens
            self._map.update({
                "describe_screen": describe_screen,
                "compare_screens": compare_screens,
            })
            logger.info("ভিশন টুল লোড সম্পন্ন")
        except ImportError as e:
            logger.warning(f"ভিশন লোড ব্যর্থ: {e}")

        # Web / Browser tools
        try:
            from modules.web_agent import (
                web_search, scroll_page, browser_back, browser_forward,
                new_tab, close_tab, get_page_source, execute_js,
                intercept_network, get_network_log, download_file,
                extract_text, reverse_engineer_api,
            )
            self._map.update({
                "web_search": web_search,
                "scroll_page": scroll_page,
                "browser_back": browser_back,
                "browser_forward": browser_forward,
                "new_tab": new_tab,
                "close_tab": close_tab,
                "get_page_source": get_page_source,
                "execute_js": execute_js,
                "intercept_network": intercept_network,
                "get_network_log": get_network_log,
                "download_file": download_file,
                "extract_text": extract_text,
                "reverse_engineer_api": reverse_engineer_api,
            })
            logger.info("ওয়েব এজেন্ট টুল লোড সম্পন্ন")
        except ImportError as e:
            logger.warning(f"ওয়েব এজেন্ট লোড ব্যর্থ: {e}")

        # Playwright tools
        try:
            from modules.playwright_agent import (
                playwright_navigate, playwright_click, playwright_type,
                playwright_screenshot, playwright_close,
            )
            self._map.update({
                "playwright_navigate": playwright_navigate,
                "playwright_click": playwright_click,
                "playwright_type": playwright_type,
                "playwright_screenshot": playwright_screenshot,
                "playwright_close": playwright_close,
            })
            logger.info("প্লেরাইট টুল লোড সম্পন্ন")
        except ImportError as e:
            logger.warning(f"প্লেরাইট লোড ব্যর্থ: {e}")

        # Memory tools
        try:
            from core.memory import Memory
            _mem = Memory()
            self._map.update({
                "save_memory": lambda goal, steps, tools, success=True: _mem.save_pattern(goal, steps, tools, success),
                "recall_memory": lambda goal: _mem.find_similar(goal),
            })
            logger.info("মেমোরি টুল লোড সম্পন্ন")
        except ImportError as e:
            logger.warning(f"মেমোরি লোড ব্যর্থ: {e}")

        # Undo tools
        try:
            from core.undo_manager import UndoManager
            _undo = UndoManager()
            self._map["rollback_last"] = _undo.rollback_last
            logger.info("আনডু ম্যানেজার লোড সম্পন্ন")
        except ImportError as e:
            logger.warning(f"আনডু ম্যানেজার লোড ব্যর্থ: {e}")

        # Task queue tools
        try:
            from core.task_queue import TaskQueue
            _queue = TaskQueue()
            self._map.update({
                "queue_task": _queue.add_task,
                "list_tasks": _queue.list_tasks,
            })
            logger.info("টাস্ক কিউ লোড সম্পন্ন")
        except ImportError as e:
            logger.warning(f"টাস্ক কিউ লোড ব্যর্থ: {e}")

        # GitHub tools
        try:
            from modules.github_agent import (
                git_clone, git_commit, git_push, git_status,
                git_create_branch, git_diff,
            )
            self._map.update({
                "git_clone": git_clone,
                "git_commit": git_commit,
                "git_push": git_push,
                "git_status": git_status,
                "git_create_branch": git_create_branch,
                "git_diff": git_diff,
            })
            logger.info("গিটহাব টুল লোড সম্পন্ন")
        except ImportError as e:
            logger.warning(f"গিটহাব এজেন্ট লোড ব্যর্থ: {e}")

        # Telegram notification
        try:
            from modules.cost_display import send_telegram_notification
            self._map["send_telegram"] = send_telegram_notification
        except ImportError as e:
            logger.warning(f"টেলিগ্রাম নোটিফিকেশন লোড ব্যর্থ: {e}")

        # Load plugins
        self._load_plugins()

    def _load_plugins(self):
        """Auto-load any .py file from plugins/ directory."""
        import importlib.util
        from pathlib import Path
        plugins_dir = Path(__file__).parent.parent / "plugins"
        if not plugins_dir.exists():
            return
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"plugins.{plugin_file.stem}", plugin_file
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    tools = mod.register()
                    self._map.update(tools)
                    logger.info(f"প্লাগইন লোড: {plugin_file.name} ({len(tools)} টুল)")
            except Exception as exc:
                logger.warning(f"প্লাগইন লোড ব্যর্থ {plugin_file.name}: {exc}")

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def list_tools(self) -> list[str]:
        return sorted(self._map.keys())

    def run(self, tool_name: str, args: dict[str, Any] | None = None) -> ToolResult:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._map:
            return _make_result(f"ত্রুটি: টুল '{tool_name}' পাওয়া যায়নি। উপলব্ধ: {self.list_tools()}")

        args = args or {}
        fn = self._map[tool_name]
        browser_tools = {
            "playwright_navigate", "playwright_click", "playwright_type",
            "playwright_screenshot", "web_search", "scroll_page",
            "get_page_source", "execute_js", "reverse_engineer_api",
        }
        timeout = 60.0 if tool_name in browser_tools else 30.0

        start = time.time()
        try:
            result = _timeout_wrap(lambda: fn(**args), timeout=timeout)
            elapsed = time.time() - start
            # Normalize result to ToolResult format
            if isinstance(result, dict) and "observation" in result:
                result["_elapsed_s"] = round(elapsed, 2)
                return result
            # Wrap plain return values
            return _make_result(str(result), display=None)
        except Exception as exc:
            logger.error(f"টুল '{tool_name}' ব্যর্থ: {exc}", exc_info=True)
            return _make_result(f"ত্রুটি '{tool_name}': {exc}")
