"""modules/playwright_agent.py — CDP-based browser automation via Playwright."""
import asyncio
import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Module-level browser state (managed in a dedicated thread with its own event loop)
_browser_loop: Optional[asyncio.AbstractEventLoop] = None
_browser_thread: Optional[threading.Thread] = None
_page: Any = None
_browser: Any = None
_playwright: Any = None
_network_log: list[dict] = []
_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    """Get or create the dedicated browser event loop."""
    global _browser_loop, _browser_thread

    if _browser_loop is None or not _browser_loop.is_running():
        _browser_loop = asyncio.new_event_loop()

        def _run_loop():
            asyncio.set_event_loop(_browser_loop)
            _browser_loop.run_forever()

        _browser_thread = threading.Thread(target=_run_loop, daemon=True, name="playwright-loop")
        _browser_thread.start()

    return _browser_loop


def _run_async(coro) -> Any:
    """Submit a coroutine to the browser event loop and wait for result."""
    loop = _get_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=60)


async def _ensure_browser() -> None:
    """Launch Playwright browser if not already running."""
    global _playwright, _browser, _page

    if _page is not None:
        try:
            await _page.title()  # Check if still alive
            return
        except Exception:
            pass

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError("Playwright ইনস্টল নেই। 'pip install playwright && playwright install chromium' চালান।")

    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=False, args=["--no-sandbox"])
    context = await _browser.new_context()

    # CDP network interception
    await context.route("**/*", lambda route, request: asyncio.ensure_future(
        _handle_route(route, request)
    ))

    _page = await context.new_page()
    logger.info("Playwright ব্রাউজার চালু হয়েছে।")


async def _handle_route(route, request) -> None:
    """Intercept and log all network requests."""
    with _lock:
        _network_log.append({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
        })
        if len(_network_log) > 500:
            _network_log.pop(0)
    await route.continue_()


# ---------------------------------------------------------------------------
# Public browser control functions
# ---------------------------------------------------------------------------

def navigate(url: str) -> dict:
    async def _go():
        await _ensure_browser()
        await _page.goto(url, timeout=30000)
        return await _page.title()

    try:
        title = _run_async(_go())
        return {"observation": f"নেভিগেট: {url} — শিরোনাম: {title}", "display": None}
    except Exception as exc:
        return {"observation": f"নেভিগেশন ব্যর্থ: {exc}", "display": None}


def get_page_source() -> dict:
    async def _get():
        await _ensure_browser()
        return await _page.content()

    try:
        html = _run_async(_get())
        return {"observation": html[:5000], "display": None}
    except Exception as exc:
        return {"observation": f"পেজ সোর্স পাওয়া যায়নি: {exc}", "display": None}


def execute_js(script: str) -> dict:
    async def _exec():
        await _ensure_browser()
        return await _page.evaluate(script)

    try:
        result = _run_async(_exec())
        return {"observation": str(result), "display": None}
    except Exception as exc:
        return {"observation": f"JS এক্সিকিউশন ব্যর্থ: {exc}", "display": None}


def extract_text() -> dict:
    async def _extract():
        await _ensure_browser()
        return await _page.evaluate("() => document.body.innerText")

    try:
        text = _run_async(_extract())
        return {"observation": text[:5000], "display": None}
    except Exception as exc:
        return {"observation": f"টেক্সট এক্সট্র্যাকশন ব্যর্থ: {exc}", "display": None}


def scroll_page(direction: str = "down", amount: int = 500) -> dict:
    dy = amount if direction == "down" else -amount

    async def _scroll():
        await _ensure_browser()
        await _page.evaluate(f"window.scrollBy(0, {dy})")

    try:
        _run_async(_scroll())
        return {"observation": f"স্ক্রল করা হয়েছে ({direction})", "display": None}
    except Exception as exc:
        return {"observation": f"স্ক্রল ব্যর্থ: {exc}", "display": None}


def browser_back() -> dict:
    async def _back():
        await _ensure_browser()
        await _page.go_back(timeout=10000)

    try:
        _run_async(_back())
        return {"observation": "পেছনে গেছে", "display": None}
    except Exception as exc:
        return {"observation": f"ব্যাক ব্যর্থ: {exc}", "display": None}


def browser_forward() -> dict:
    async def _forward():
        await _ensure_browser()
        await _page.go_forward(timeout=10000)

    try:
        _run_async(_forward())
        return {"observation": "সামনে গেছে", "display": None}
    except Exception as exc:
        return {"observation": f"ফরোয়ার্ড ব্যর্থ: {exc}", "display": None}


def new_tab(url: str = "about:blank") -> dict:
    global _page

    async def _new():
        global _page
        await _ensure_browser()
        context = _browser.contexts[0]
        _page = await context.new_page()
        if url != "about:blank":
            await _page.goto(url, timeout=30000)

    try:
        _run_async(_new())
        return {"observation": f"নতুন ট্যাব খোলা হয়েছে: {url}", "display": None}
    except Exception as exc:
        return {"observation": f"নতুন ট্যাব ব্যর্থ: {exc}", "display": None}


def close_tab() -> dict:
    async def _close():
        await _ensure_browser()
        await _page.close()

    try:
        _run_async(_close())
        return {"observation": "ট্যাব বন্ধ করা হয়েছে", "display": None}
    except Exception as exc:
        return {"observation": f"ট্যাব বন্ধ ব্যর্থ: {exc}", "display": None}


def get_network_log() -> dict:
    with _lock:
        entries = list(_network_log[-50:])
    lines = [f"{e['method']} {e['url']}" for e in entries]
    return {"observation": "\n".join(lines) or "কোনো নেটওয়ার্ক লগ নেই", "display": None}


def intercept_network() -> dict:
    with _lock:
        _network_log.clear()
    return {"observation": "নেটওয়ার্ক ইন্টারসেপশন শুরু হয়েছে", "display": None}


def click_element(selector: str) -> dict:
    async def _click():
        await _ensure_browser()
        await _page.click(selector, timeout=10000)

    try:
        _run_async(_click())
        return {"observation": f"ক্লিক করা হয়েছে: {selector}", "display": None}
    except Exception as exc:
        return {"observation": f"ক্লিক ব্যর্থ: {exc}", "display": None}


def type_in_element(selector: str, text: str) -> dict:
    async def _type():
        await _ensure_browser()
        await _page.fill(selector, text)

    try:
        _run_async(_type())
        return {"observation": f"টেক্সট লেখা হয়েছে: {selector}", "display": None}
    except Exception as exc:
        return {"observation": f"টাইপ ব্যর্থ: {exc}", "display": None}


# Convenience alias used in executor
agent = navigate
