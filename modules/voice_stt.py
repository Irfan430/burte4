"""modules/voice_stt.py — Whisper-based speech-to-text with Bengali support."""
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

WAKE_WORD = "নোভা"
_listening = False
_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _listen_loop(callback: Callable[[str], None]) -> None:
    """Background listening loop."""
    try:
        import whisper
        import sounddevice as sd
        import numpy as np

        model = whisper.load_model("tiny")
        sample_rate = 16000
        chunk_duration = 5  # seconds per chunk

        logger.info("Whisper মডেল লোড হয়েছে, শুনছি...")

        while not _stop_event.is_set():
            try:
                audio = sd.rec(
                    int(chunk_duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()
                audio_flat = audio.flatten()

                result = model.transcribe(
                    audio_flat,
                    language="bn",
                    fp16=False,
                )
                text = result.get("text", "").strip()

                if text:
                    logger.debug(f"STT: {text}")
                    if WAKE_WORD in text:
                        # Remove wake word prefix
                        command = text.replace(WAKE_WORD, "").strip()
                        if command:
                            callback(command)
                        else:
                            callback(text)

            except (OSError, ValueError) as exc:
                logger.warning(f"STT চক্র ত্রুটি: {exc}")

    except ImportError as exc:
        logger.warning(
            f"Whisper বা sounddevice পাওয়া যায়নি, STT নিষ্ক্রিয়: {exc}"
        )
    except Exception as exc:
        logger.error(f"STT লুপ অপ্রত্যাশিত ত্রুটি: {exc}")


def start_listening(callback: Callable[[str], None]) -> None:
    """Start background listening thread.

    Args:
        callback: Called with transcribed text when wake word detected
    """
    global _listening, _thread, _stop_event

    if _listening:
        logger.warning("ইতিমধ্যে শুনছি")
        return

    _stop_event.clear()
    _listening = True
    _thread = threading.Thread(
        target=_listen_loop,
        args=(callback,),
        daemon=True,
        name="nova-stt",
    )
    _thread.start()
    logger.info("STT শুরু হয়েছে")


def stop_listening() -> None:
    """Stop the background listening thread."""
    global _listening, _thread

    _stop_event.set()
    _listening = False
    if _thread and _thread.is_alive():
        _thread.join(timeout=3.0)
    _thread = None
    logger.info("STT বন্ধ হয়েছে")


def is_listening() -> bool:
    return _listening
