"""Shared utilities for cloud providers: retry, rate limiting, cost tracking, image encoding."""

import asyncio
import base64
import functools
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# --- Retry with exponential backoff ---

class ProviderUnavailableError(Exception):
    """All retries exhausted or provider unreachable."""


class RateLimitError(Exception):
    """Rate limit exceeded."""

    def __init__(self, retry_after: float = 0):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry after {retry_after}s")


class ExtractionError(Exception):
    """Valid response but extraction failed."""


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Async retry decorator with exponential backoff."""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    delay = e.retry_after if e.retry_after > 0 else base_delay * (2 ** attempt)
                    logger.warning(
                        "Rate limited on attempt %d/%d, retrying in %.1fs",
                        attempt + 1, max_retries, delay,
                    )
                    last_error = e
                    await asyncio.sleep(delay)
                except (TimeoutError, ConnectionError, OSError) as e:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Transient error on attempt %d/%d: %s, retrying in %.1fs",
                        attempt + 1, max_retries, e, delay,
                    )
                    last_error = e
                    await asyncio.sleep(delay)
            raise ProviderUnavailableError(
                f"All {max_retries} retries exhausted"
            ) from last_error

        return wrapper
    return decorator


# --- Rate Limiter (token bucket) ---

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, requests_per_minute: int = 15):
        self.rpm = requests_per_minute
        self.tokens = float(requests_per_minute)
        self.max_tokens = float(requests_per_minute)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request token is available."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, self.tokens + elapsed * (self.rpm / 60.0))
            self.last_refill = now

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / (self.rpm / 60.0)
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


# --- Cost Tracker ---

@dataclass
class CostTracker:
    """Accumulate costs across multiple requests in a session."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    request_count: int = 0
    daily_limit_usd: float = 10.0
    _costs: list[dict] = field(default_factory=list)

    def record(self, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost_usd
        self.request_count += 1
        self._costs.append({
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "timestamp": time.time(),
        })

    @property
    def limit_exceeded(self) -> bool:
        return self.total_cost_usd >= self.daily_limit_usd


# --- Image encoding ---

def encode_image_base64(image: bytes) -> str:
    """Encode raw image bytes to base64 string."""
    return base64.b64encode(image).decode("utf-8")


def detect_mime_type(image: bytes) -> str:
    """Detect image MIME type from magic bytes."""
    if image[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image[:2] == b"\xff\xd8":
        return "image/jpeg"
    if image[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    if image[:5] == b"%PDF-":
        return "application/pdf"
    return "application/octet-stream"
