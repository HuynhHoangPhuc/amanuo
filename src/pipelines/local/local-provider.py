"""Main local extraction provider with backend auto-detection and fallback chain."""

import importlib
import json
import logging
import time

from src.config import settings
from src.schemas import ExtractionSchema, normalize_output, to_json_schema

_base = importlib.import_module("src.pipelines.base-provider")
BaseProvider = _base.BaseProvider
CostInfo = _base.CostInfo
PipelineResult = _base.PipelineResult

_ollama = importlib.import_module("src.pipelines.local.ollama-backend")
_vllm = importlib.import_module("src.pipelines.local.vllm-backend")
_llamacpp = importlib.import_module("src.pipelines.local.llamacpp-backend")
_paddle = importlib.import_module("src.pipelines.local.paddleocr-fallback")
_prompt = importlib.import_module("src.pipelines.local.vlm-prompt-builder")

logger = logging.getLogger(__name__)


class LocalProvider(BaseProvider):
    """Local extraction provider with VLM backend detection and PaddleOCR fallback."""

    def __init__(self):
        self._backends = {
            "ollama": _ollama.OllamaBackend(),
            "vllm": _vllm.VLLMBackend(),
            "llamacpp": _llamacpp.LlamaCppBackend(),
        }
        self._active_backend: str | None = None

    def provider_name(self) -> str:
        return f"local:{self._active_backend or 'none'}"

    async def health_check(self) -> bool:
        """Check if any VLM backend or PaddleOCR is available."""
        # Check configured backend first
        preferred = settings.vlm_backend
        if preferred in self._backends:
            if await self._backends[preferred].is_available():
                self._active_backend = preferred
                return True

        # Try others in priority order
        for name in ["ollama", "vllm", "llamacpp"]:
            if name != preferred and await self._backends[name].is_available():
                self._active_backend = name
                return True

        # Check PaddleOCR as last resort
        try:
            _paddle._get_paddleocr()
            self._active_backend = "paddleocr"
            return True
        except Exception:
            pass

        return False

    async def _detect_backend(self) -> str | None:
        """Detect the best available backend."""
        if self._active_backend:
            return self._active_backend
        await self.health_check()
        return self._active_backend

    async def extract(
        self, image: bytes, schema: ExtractionSchema, **kwargs
    ) -> PipelineResult:
        """Extract fields using best available local backend."""
        start = time.monotonic()
        backend_name = await self._detect_backend()

        if not backend_name:
            raise ConnectionError("No local VLM backend or PaddleOCR available")

        lang = kwargs.get("lang", "en")

        # Try VLM backend first
        if backend_name in self._backends:
            try:
                return await self._extract_with_vlm(
                    image, schema, backend_name, start
                )
            except Exception as e:
                logger.warning("VLM backend %s failed: %s, trying PaddleOCR", backend_name, e)

        # Fallback to PaddleOCR
        return await self._extract_with_paddleocr(image, schema, lang, start)

    async def _extract_with_vlm(
        self, image: bytes, schema: ExtractionSchema, backend_name: str, start: float
    ) -> PipelineResult:
        """Extract using a VLM backend."""
        backend = self._backends[backend_name]
        prompt_text = _prompt.build_vlm_extraction_prompt(schema)
        json_schema = to_json_schema(schema)

        response = await backend.generate(image, prompt_text, json_schema)

        # Parse JSON from response
        try:
            raw_output = json.loads(response)
        except json.JSONDecodeError:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                raw_output = json.loads(response[start_idx:end_idx])
            else:
                raise

        latency_ms = int((time.monotonic() - start) * 1000)
        normalized = normalize_output(raw_output, schema)

        return PipelineResult(
            raw_output=raw_output,
            normalized=normalized,
            confidence=0.0,
            cost=CostInfo(),  # No cost for local
            latency_ms=latency_ms,
            provider=f"local:{backend_name}",
        )

    async def _extract_with_paddleocr(
        self, image: bytes, schema: ExtractionSchema, lang: str, start: float
    ) -> PipelineResult:
        """Extract using PaddleOCR + local LLM fallback."""
        # Find any available backend for Stage 2 LLM
        text_backend = None
        for name, backend in self._backends.items():
            if await backend.is_available():
                text_backend = backend
                break

        if text_backend is None:
            raise ConnectionError("PaddleOCR needs a local LLM backend for field extraction")

        raw_output = await _paddle.paddleocr_extract(image, schema, text_backend, lang)
        latency_ms = int((time.monotonic() - start) * 1000)
        normalized = normalize_output(raw_output, schema)

        return PipelineResult(
            raw_output=raw_output,
            normalized=normalized,
            confidence=0.0,
            cost=CostInfo(),
            latency_ms=latency_ms,
            provider="local:paddleocr",
        )
