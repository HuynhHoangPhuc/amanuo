"""Gemini 3 Flash extraction provider."""

import importlib
import json
import logging
import time

import httpx

from src.config import settings
from src.schemas import ExtractionSchema, normalize_output

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

# Gemini pricing (per token)
_INPUT_COST_PER_TOKEN = 0.50 / 1_000_000   # $0.50 per 1M input tokens
_OUTPUT_COST_PER_TOKEN = 3.00 / 1_000_000  # $3.00 per 1M output tokens

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(BaseProvider):
    """Gemini 3 Flash extraction via REST API."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model
        self.rate_limiter = RateLimiter(requests_per_minute=15)
        self._client = httpx.AsyncClient(timeout=30.0)

    def provider_name(self) -> str:
        return "gemini"

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            resp = await self._client.get(
                f"{_GEMINI_API_BASE}/models/{self.model}",
                headers={"x-goog-api-key": self.api_key},
            )
            return resp.status_code == 200
        except Exception:
            return False

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def extract(
        self, image: bytes, schema: ExtractionSchema, **kwargs
    ) -> PipelineResult:
        """Extract structured data from image using Gemini."""
        await self.rate_limiter.acquire()
        start = time.monotonic()

        from src.schemas import to_extraction_prompt, to_gemini_schema

        mime_type = detect_mime_type(image)
        b64_image = encode_image_base64(image)
        prompt = to_extraction_prompt(schema)
        gemini_schema = to_gemini_schema(schema)

        # Build request body
        body = {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": b64_image}},
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": gemini_schema,
                "temperature": 0,
            },
        }

        resp = await self._client.post(
            f"{_GEMINI_API_BASE}/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            json=body,
        )

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("retry-after", "5"))
            raise RateLimitError(retry_after)

        if resp.status_code != 200:
            raise ExtractionError(f"Gemini API error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        latency_ms = int((time.monotonic() - start) * 1000)

        # Parse response
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            raw_output = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ExtractionError(f"Failed to parse Gemini response: {e}") from e

        # Extract token usage
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        cost_usd = (input_tokens * _INPUT_COST_PER_TOKEN) + (
            output_tokens * _OUTPUT_COST_PER_TOKEN
        )

        normalized = normalize_output(raw_output, schema)

        return PipelineResult(
            raw_output=raw_output,
            normalized=normalized,
            confidence=0.0,  # Will be calculated by confidence scorer
            cost=CostInfo(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=round(cost_usd, 6),
            ),
            latency_ms=latency_ms,
            provider="gemini",
        )
