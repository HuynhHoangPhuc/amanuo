"""Mistral OCR 3 extraction provider."""

import importlib
import json
import logging
import time

import httpx

from src.config import settings
from src.schemas import ExtractionSchema, normalize_output, to_extraction_prompt

_base = importlib.import_module("src.pipelines.base-provider")
BaseProvider = _base.BaseProvider
CostInfo = _base.CostInfo
PipelineResult = _base.PipelineResult

_utils = importlib.import_module("src.pipelines.cloud.cloud-utils")
RateLimiter = _utils.RateLimiter
RateLimitError = _utils.RateLimitError
ExtractionError = _utils.ExtractionError
encode_image_base64 = _utils.encode_image_base64
detect_mime_type = _utils.detect_mime_type
retry_with_backoff = _utils.retry_with_backoff

logger = logging.getLogger(__name__)

# Mistral pricing estimate (per page)
_COST_PER_PAGE = 0.001  # ~$1/1k pages

_MISTRAL_API_BASE = "https://api.mistral.ai/v1"


class MistralProvider(BaseProvider):
    """Mistral OCR 3 extraction via REST API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.mistral_api_key
        self.rate_limiter = RateLimiter(requests_per_minute=30)
        self._client = httpx.AsyncClient(timeout=30.0)

    def provider_name(self) -> str:
        return "mistral"

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            resp = await self._client.get(
                f"{_MISTRAL_API_BASE}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            return resp.status_code == 200
        except Exception:
            return False

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def extract(
        self, image: bytes, schema: ExtractionSchema, **kwargs
    ) -> PipelineResult:
        """Extract structured data from image using Mistral chat + vision."""
        await self.rate_limiter.acquire()
        start = time.monotonic()

        mime_type = detect_mime_type(image)
        b64_image = encode_image_base64(image)
        prompt = to_extraction_prompt(schema)

        # Use Mistral's chat completions with vision
        body = {
            "model": "mistral-large-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_image}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }

        resp = await self._client.post(
            f"{_MISTRAL_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
        )

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("retry-after", "5"))
            raise RateLimitError(retry_after)

        if resp.status_code != 200:
            raise ExtractionError(f"Mistral API error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        latency_ms = int((time.monotonic() - start) * 1000)

        # Parse response
        try:
            text = data["choices"][0]["message"]["content"]
            raw_output = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ExtractionError(f"Failed to parse Mistral response: {e}") from e

        # Token usage
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost_usd = _COST_PER_PAGE  # Rough per-page estimate

        normalized = normalize_output(raw_output, schema)

        return PipelineResult(
            raw_output=raw_output,
            normalized=normalized,
            confidence=0.0,
            cost=CostInfo(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=round(cost_usd, 6),
            ),
            latency_ms=latency_ms,
            provider="mistral",
        )
