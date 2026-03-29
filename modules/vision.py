"""modules/vision.py — Screen vision using Qwen-VL via OpenRouter."""
import base64
import logging
import time
from pathlib import Path
from typing import Optional

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODELS, PROMPTS_DIR, SCREENSHOTS_DIR

logger = logging.getLogger(__name__)


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _encode_image(path: str) -> str:
    """Base64-encode an image file."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_vision(image_path: str, prompt: str) -> str:
    """Call Qwen-VL via OpenRouter with an image and prompt."""
    if not OPENROUTER_API_KEY:
        return "OPENROUTER_API_KEY সেট করা নেই"

    try:
        image_b64 = _encode_image(image_path)
    except (FileNotFoundError, OSError) as exc:
        return f"ছবি পড়তে ব্যর্থ: {exc}"

    # Detect MIME type
    suffix = Path(image_path).suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"

    payload = {
        "model": MODELS["vision"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": 1024,
    }

    for attempt in range(3):
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://nova-agent.local",
                        "X-Title": "NOVA v9",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, httpx.TimeoutException, KeyError, IndexError) as exc:
            logger.warning(f"ভিশন কল চেষ্টা {attempt + 1}/3 ব্যর্থ: {exc}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    return "ভিশন মডেল থেকে সাড়া পাওয়া যায়নি"


def take_screenshot(save_path: Optional[str] = None) -> str:
    """Take a screenshot and return the file path."""
    ts = int(time.time() * 1000)
    out_path = save_path or str(SCREENSHOTS_DIR / f"vision_{ts}.png")

    try:
        import mss
        import mss.tools
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            mss.tools.to_png(img.rgb, img.size, output=out_path)
        return out_path
    except (ImportError, Exception) as exc:
        logger.warning(f"mss স্ক্রিনশট ব্যর্থ: {exc}")

    from modules.system_control import screenshot
    result = screenshot(out_path)
    return result.get("display") or out_path


def describe_screen(image_path: Optional[str] = None) -> str:
    """Describe what is currently on screen.

    Takes a screenshot if no image path provided.
    Returns Bengali description.
    """
    if image_path is None:
        image_path = take_screenshot()

    vision_prompt = _load_prompt("vision") or (
        "এই স্ক্রিনশটে কী দেখা যাচ্ছে বাংলায় বিস্তারিত বর্ণনা করো। "
        "উইন্ডো, বোতাম, টেক্সট, এবং সব উপাদান উল্লেখ করো।"
    )

    description = _call_vision(image_path, vision_prompt)
    logger.info(f"স্ক্রিন বিবরণ: {description[:100]}...")
    return description


def compare_screens(before_path: str, after_path: str) -> str:
    """Compare two screenshots and describe the differences."""
    try:
        before_b64 = _encode_image(before_path)
        after_b64 = _encode_image(after_path)
    except (FileNotFoundError, OSError) as exc:
        return f"স্ক্রিনশট পড়তে ব্যর্থ: {exc}"

    if not OPENROUTER_API_KEY:
        return "OPENROUTER_API_KEY সেট করা নেই"

    payload = {
        "model": MODELS["vision"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{before_b64}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{after_b64}"}},
                    {
                        "type": "text",
                        "text": (
                            "এই দুটি স্ক্রিনশটের মধ্যে পার্থক্য কী? "
                            "প্রথমটি 'আগে' এবং দ্বিতীয়টি 'পরে'। "
                            "বাংলায় পরিবর্তনগুলি বর্ণনা করো।"
                        ),
                    },
                ],
            }
        ],
        "max_tokens": 512,
    }

    for attempt in range(3):
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://nova-agent.local",
                        "X-Title": "NOVA v9",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, httpx.TimeoutException, KeyError, IndexError) as exc:
            logger.warning(f"স্ক্রিন তুলনা চেষ্টা {attempt + 1}/3 ব্যর্থ: {exc}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    return "স্ক্রিন তুলনা সম্ভব হয়নি"
