"""core/brain.py — Multi-LLM brain via OpenRouter with model routing and compression."""
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from config import MODELS, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PROMPTS_DIR

logger = logging.getLogger(__name__)

# Approximate cost per 1M tokens (USD)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "qwen/qwen2.5-coder-32b-instruct": {"input": 0.07, "output": 0.07},
    "google/gemini-flash-1.5": {"input": 0.075, "output": 0.30},
    "deepseek/deepseek-r1": {"input": 0.55, "output": 2.19},
    "qwen/qwen2.5-vl-7b-instruct": {"input": 0.10, "output": 0.10},
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
}


def _load_prompt(name: str) -> str:
    """Load a prompt from the prompts directory."""
    path = PROMPTS_DIR / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.warning(f"প্রম্পট ফাইল পাওয়া যায়নি: {path}")
    return ""


def _route_model(task_hint: str) -> str:
    """Route to the best model based on task_hint keywords."""
    hint = task_hint.lower()
    if any(k in hint for k in ("code", "script", "program", "function", "debug")):
        return MODELS["code"]
    if any(k in hint for k in ("browse", "web", "url", "internet", "search")):
        return MODELS["browse"]
    if any(k in hint for k in ("analyze", "plan", "complex", "reason", "think", "research")):
        return MODELS["analyze"]
    if any(k in hint for k in ("vision", "screen", "image", "screenshot", "visual")):
        return MODELS["vision"]
    return MODELS["default"]


class Brain:
    """Multi-LLM interface with routing, compression, and cost tracking."""

    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.base_url = OPENROUTER_BASE_URL
        self.total_cost: float = 0.0
        self.usage_log: list[dict[str, Any]] = []
        self._system_prompt = _load_prompt("system")

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/nova-agent",
            "X-Title": "NOVA v9 Autonomous OS Agent",
        }

    def _post(self, payload: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
        """Synchronous HTTP POST to OpenRouter."""
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Cost tracking
    # ------------------------------------------------------------------

    def _track_usage(self, model: str, response: dict[str, Any]) -> None:
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        pricing = MODEL_PRICING.get(model, {"input": 0.5, "output": 1.5})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        self.total_cost += cost
        entry = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
        }
        self.usage_log.append(entry)
        logger.debug(f"ব্যবহার রেকর্ড: {entry}")

    def get_cost_summary(self) -> dict[str, Any]:
        return {
            "total_cost_usd": round(self.total_cost, 6),
            "calls": len(self.usage_log),
            "breakdown": self.usage_log,
        }

    # ------------------------------------------------------------------
    # Context compression
    # ------------------------------------------------------------------

    def _compress_messages(self, messages: list[dict]) -> list[dict]:
        """Summarise older messages when history grows too long."""
        if len(messages) <= 20:
            return messages

        compress_prompt = _load_prompt("compress")
        old_messages = messages[:-10]
        recent_messages = messages[-10:]

        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in old_messages
        )
        summary_payload = {
            "model": MODELS["default"],
            "messages": [
                {"role": "system", "content": compress_prompt or "নিচের কথোপকথনের সারাংশ বাংলায় লেখো।"},
                {"role": "user", "content": f"এই কথোপকথনের সারাংশ করো:\n\n{history_text}"},
            ],
            "max_tokens": 512,
        }
        try:
            resp = self._post(summary_payload, timeout=60.0)
            summary = resp["choices"][0]["message"]["content"]
            self._track_usage(MODELS["default"], resp)
            compressed = [
                {"role": "system", "content": self._system_prompt},
                {"role": "assistant", "content": f"[আগের কথোপকথনের সারাংশ]: {summary}"},
            ] + recent_messages
            logger.info(f"বার্তা সংকোচন সম্পন্ন: {len(old_messages)} → ২ বার্তা")
            return compressed
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning(f"সংকোচন ব্যর্থ, পুরানো বার্তা রাখা হলো: {exc}")
            return messages

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def call(self, messages: list[dict], task_hint: str = "default") -> str:
        """Call the appropriate LLM and return the response text."""
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY সেট করা নেই। .env ফাইল চেক করুন।")

        model = _route_model(task_hint)
        compressed = self._compress_messages(messages)

        # Ensure system prompt is present
        if not compressed or compressed[0].get("role") != "system":
            compressed = [{"role": "system", "content": self._system_prompt}] + compressed

        payload = {
            "model": model,
            "messages": compressed,
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        logger.info(f"LLM কল → মডেল: {model}, বার্তা: {len(compressed)}")
        try:
            resp = self._post(payload)
            self._track_usage(model, resp)
            content = resp["choices"][0]["message"]["content"]
            return content
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP ত্রুটি: {exc.response.status_code} — {exc.response.text}")
            raise
        except (KeyError, IndexError) as exc:
            logger.error(f"প্রতিক্রিয়া পার্স ত্রুটি: {exc}")
            raise

    def decompose(self, goal: str) -> list[str]:
        """Decompose a complex goal into a list of atomic steps."""
        decompose_prompt = _load_prompt("decompose")
        messages = [
            {
                "role": "system",
                "content": decompose_prompt or (
                    "তুমি একটি টাস্ক ডিকম্পোজার। দেওয়া লক্ষ্যকে ছোট ছোট ধাপে ভাগ করো। "
                    "প্রতিটি ধাপ এক লাইনে লেখো। JSON অ্যারে ফরম্যাটে উত্তর দাও।"
                ),
            },
            {"role": "user", "content": f"এই লক্ষ্য ভাগ করো: {goal}"},
        ]
        try:
            raw = self.call(messages, task_hint="analyze")
            # Try to extract JSON array
            raw = raw.strip()
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                steps = json.loads(raw[start : end + 1])
                if isinstance(steps, list) and steps:
                    return [str(s) for s in steps]
        except (json.JSONDecodeError, httpx.HTTPError, KeyError, IndexError) as exc:
            logger.warning(f"ডিকম্পোজিশন পার্স ব্যর্থ: {exc}")

        # Fallback: treat whole goal as one step
        return [goal]

    def replan(self, goal: str, failed_steps: list[str], error: str) -> list[str]:
        """Replan after failure — generate alternative approach."""
        replan_prompt = _load_prompt("replan")
        context = (
            f"মূল লক্ষ্য: {goal}\n"
            f"ব্যর্থ ধাপ: {', '.join(failed_steps)}\n"
            f"ত্রুটি: {error}"
        )
        messages = [
            {
                "role": "system",
                "content": replan_prompt or (
                    "তুমি একটি টাস্ক রিপ্ল্যানার। পূর্বের ব্যর্থতা বিশ্লেষণ করে নতুন পদ্ধতি সুপারিশ করো।"
                ),
            },
            {"role": "user", "content": context},
        ]
        try:
            raw = self.call(messages, task_hint="analyze plan complex")
            raw = raw.strip()
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                steps = json.loads(raw[start : end + 1])
                if isinstance(steps, list) and steps:
                    return [str(s) for s in steps]
        except (json.JSONDecodeError, httpx.HTTPError, KeyError, IndexError) as exc:
            logger.warning(f"রিপ্ল্যান পার্স ব্যর্থ: {exc}")
        return [goal]
