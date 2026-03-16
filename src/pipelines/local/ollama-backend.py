"""Ollama VLM backend — HTTP API client for local inference."""

import importlib
import logging

import httpx

from src.config import settings

_utils = importlib.import_module("src.pipelines.cloud.cloud-utils")
encode_image_base64 = _utils.encode_image_base64

logger = logging.getLogger(__name__)


class OllamaBackend:
    """Ollama HTTP API client for vision model inference."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.base_url = (base_url or settings.vlm_base_url).rstrip("/")
        self.model = model or settings.vlm_model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self, image: bytes, prompt: str, json_schema: dict | None = None
    ) -> str:
        """Generate a response from Ollama with an image."""
        b64_image = encode_image_base64(image)

        body: dict = {
            "model": self.model,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
        }

        if json_schema:
            body["format"] = "json"

        resp = await self._client.post(f"{self.base_url}/api/generate", json=body)

        if resp.status_code != 200:
            raise ConnectionError(f"Ollama error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        return data.get("response", "")

    async def generate_text(self, prompt: str, json_schema: dict | None = None) -> str:
        """Generate a text-only response (no image, for PaddleOCR Stage 2)."""
        body: dict = {
            "model": self.model.replace("-vl", "").replace("-VL", ""),  # Use text model variant
            "prompt": prompt,
            "stream": False,
        }

        if json_schema:
            body["format"] = "json"

        resp = await self._client.post(f"{self.base_url}/api/generate", json=body)

        if resp.status_code != 200:
            raise ConnectionError(f"Ollama error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        return data.get("response", "")

    async def is_available(self) -> bool:
        """Check if Ollama server is running and model is loaded."""
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags")
            if resp.status_code != 200:
                return False
            models = resp.json().get("models", [])
            return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in models)
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags")
            if resp.status_code != 200:
                return []
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []
