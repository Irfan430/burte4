"""modules/web_agent.py — Browser automation via browser_use + OpenRouter."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def web_agent(goal: str, url: Optional[str] = None) -> dict:
    """Execute a browser task using browser_use with OpenRouter.

    Args:
        goal: Natural language goal for the browser agent.
        url: Optional starting URL.

    Returns:
        {"observation": str, "display": None}
    """
    try:
        from browser_use import Agent as BrowserAgent
        from openai import OpenAI
        from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODELS
    except ImportError as exc:
        return {"observation": f"browser_use বা openai লাইব্রেরি পাওয়া যায়নি: {exc}", "display": None}

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    full_goal = goal
    if url:
        full_goal = f"প্রথমে {url} এ যাও। তারপর: {goal}"

    try:
        import asyncio

        async def _run():
            agent = BrowserAgent(
                task=full_goal,
                llm=client,
                llm_model=MODELS["browse"],
            )
            result = await agent.run()
            return result

        result = asyncio.run(_run())
        return {"observation": str(result), "display": None}
    except Exception as exc:
        logger.error(f"browser_use ত্রুটি: {exc}")
        return {"observation": f"ব্রাউজার এজেন্ট ত্রুটি: {exc}", "display": None}


def web_search(query: str) -> dict:
    """Perform a web search and return results."""
    try:
        import httpx
        from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODELS

        # Use DuckDuckGo instant answer API (no key required)
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
            )
            resp.raise_for_status()
            data = resp.json()

        abstract = data.get("AbstractText", "")
        related = [r.get("Text", "") for r in data.get("RelatedTopics", [])[:5]]
        results = abstract or "\n".join(related) or "কোনো ফলাফল পাওয়া যায়নি"
        return {"observation": results, "display": None}
    except Exception as exc:
        logger.error(f"ওয়েব সার্চ ত্রুটি: {exc}")
        return {"observation": f"ওয়েব সার্চ ব্যর্থ: {exc}", "display": None}
