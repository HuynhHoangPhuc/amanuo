"""llama.cpp backend — HTTP server client for CPU/quantized inference."""

import importlib
import logging

import httpx

_utils = importlib.import_module("src.pipelines.cloud.cloud-utils")
encode_image_base64 = _utils.encode_image_base64

logger = logging.getLogger(__name__)


class LlamaCppBackend:
    """llama.cpp HTTP server client."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=300.0)  # CPU can be slow

    async def generate(
        self, image: bytes, prompt: str, json_schema: dict | None = None
    ) -> str:
        """Generate response with image via llama.cpp /completion endpoint."""
        b64 = encode_image_base64(image)

        body: dict = {
            "prompt": prompt,
            "image_data": [{"data": b64, "id": 0}],
            "n_predict": 2048,
            "temperature": 0,
        }

        if json_schema:
            # llama.cpp uses grammar for JSON constraints
            body["json_schema"] = json_schema

        resp = await self._client.post(f"{self.base_url}/completion", json=body)

        if resp.status_code != 200:
            raise ConnectionError(f"llama.cpp error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        return data.get("content", "")

    async def generate_text(self, prompt: str, json_schema: dict | None = None) -> str:
        """Generate text-only response."""
        body: dict = {"prompt": prompt, "n_predict": 2048, "temperature": 0}
        if json_schema:
            body["json_schema"] = json_schema

        resp = await self._client.post(f"{self.base_url}/completion", json=body)

        if resp.status_code != 200:
            raise ConnectionError(f"llama.cpp error {resp.status_code}: {resp.text[:200]}")

        return resp.json().get("content", "")

    async def is_available(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base_url}/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        # llama.cpp only serves one model at a time
        if await self.is_available():
            return ["loaded-model"]
        return []
