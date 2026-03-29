"""Retry decorator with exponential backoff"""
import functools
import time
import logging

logger = logging.getLogger(__name__)


def retry(max_attempts: int = 3, backoff_base: int = 2, exceptions: tuple = (Exception,)):
    """Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        backoff_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait = backoff_base ** attempt
                    logger.warning(
                        f"পুনরায় চেষ্টা {attempt + 1}/{max_attempts} "
                        f"{wait} সেকেন্ড পরে: {e}"
                    )
                    time.sleep(wait)
        return wrapper
    return decorator


def async_retry(max_attempts: int = 3, backoff_base: int = 2, exceptions: tuple = (Exception,)):
    """Async retry decorator with exponential backoff."""
    import asyncio

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait = backoff_base ** attempt
                    logger.warning(
                        f"অ্যাসিঙ্ক পুনরায় চেষ্টা {attempt + 1}/{max_attempts} "
                        f"{wait} সেকেন্ড পরে: {e}"
                    )
                    await asyncio.sleep(wait)
        return wrapper
    return decorator
