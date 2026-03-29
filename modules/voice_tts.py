"""modules/voice_tts.py — Bengali text-to-speech via edge-tts."""
import asyncio
import logging
import queue
import threading
import tempfile
import os
from typing import Optional

logger = logging.getLogger(__name__)

VOICE = "bn-BD-NabanitaNeural"
_tts_queue: queue.Queue = queue.Queue()
_worker_thread: Optional[threading.Thread] = None
_running = threading.Event()


async def _synthesize(text: str, out_path: str) -> None:
    """Async TTS synthesis to a file."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(out_path)
    except ImportError:
        raise RuntimeError("edge-tts ইনস্টল নেই। 'pip install edge-tts' চালান।")


def _play_audio(path: str) -> None:
    """Play audio file (cross-platform)."""
    import subprocess
    import shutil
    from config import IS_LINUX, IS_WINDOWS, IS_MAC

    if IS_LINUX:
        for player in ("aplay", "paplay", "mpg123", "ffplay"):
            if shutil.which(player):
                subprocess.run([player, path], capture_output=True, timeout=30)
                return
    elif IS_MAC:
        subprocess.run(["afplay", path], timeout=30)
    elif IS_WINDOWS:
        subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"], timeout=30)


def _tts_worker() -> None:
    """Background worker that processes TTS queue."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while _running.is_set():
        try:
            text = _tts_queue.get(timeout=0.5)
            if text is None:
                break
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                loop.run_until_complete(_synthesize(text, tmp_path))
                _play_audio(tmp_path)
            except Exception as exc:
                logger.error(f"TTS ত্রুটি: {exc}")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            _tts_queue.task_done()
        except queue.Empty:
            continue

    loop.close()


def start_tts() -> None:
    """Start the TTS worker thread."""
    global _worker_thread
    _running.set()
    _worker_thread = threading.Thread(target=_tts_worker, daemon=True)
    _worker_thread.start()
    logger.info("TTS worker শুরু হয়েছে।")


def stop_tts() -> None:
    """Stop the TTS worker."""
    _running.clear()
    _tts_queue.put(None)


def speak(text: str) -> None:
    """Enqueue text for TTS playback (non-blocking)."""
    if not _running.is_set():
        start_tts()
    _tts_queue.put(text)
    logger.debug(f"TTS: {text[:50]}")


def speak_sync(text: str) -> None:
    """Synchronous TTS — blocks until speech is done."""
    asyncio.run(_tts_async_and_play(text))


async def _tts_async_and_play(text: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        await _synthesize(text, tmp_path)
        _play_audio(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
