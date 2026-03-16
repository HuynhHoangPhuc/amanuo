"""vLLM backend — OpenAI-compatible API client for local GPU inference."""

import importlib
import logging

import httpx

_utils = importlib.import_module("src.pipelines.cloud.cloud-utils")
encode_image_base64 = _utils.encode_image_base64
detect_mime_type = _utils.detect_mime_type

logger = logging.getLogger(__name__)


class VLLMBackend:
    """vLLM OpenAI-compatible API client."""

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        model: str = "Qwen/Qwen3-VL-4B-Instruct",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self, image: bytes, prompt: str, json_schema: dict | None = None
    ) -> str:
        """Generate response with image via OpenAI-compatible chat API."""
        mime = detect_mime_type(image)
        b64 = encode_image_base64(image)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        body: dict = {"model": self.model, "messages": messages, "temperature": 0}

        if json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}

        resp = await self._client.post(f"{self.base_url}/v1/chat/completions", json=body)

        if resp.status_code != 200:
            raise ConnectionError(f"vLLM error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def generate_text(self, prompt: str, json_schema: dict | None = None) -> str:
        """Generate text-only response (no image)."""
        body: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        if json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}

        resp = await self._client.post(f"{self.base_url}/v1/chat/completions", json=body)

        if resp.status_code != 200:
            raise ConnectionError(f"vLLM error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base_url}/v1/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            resp = await self._client.get(f"{self.base_url}/v1/models")
            if resp.status_code != 200:
                return []
            return [m["id"] for m in resp.json().get("data", [])]
        except Exception:
            return []
