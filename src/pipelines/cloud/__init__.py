"""Cloud extraction providers."""

import importlib

from src.config import settings

_gemini = importlib.import_module("src.pipelines.cloud.gemini-provider")
_mistral = importlib.import_module("src.pipelines.cloud.mistral-provider")

GeminiProvider = _gemini.GeminiProvider
MistralProvider = _mistral.MistralProvider


def get_cloud_provider(name: str) -> _gemini.GeminiProvider | _mistral.MistralProvider:
    """Factory to get a cloud provider by name."""
    providers = {
        "gemini": lambda: GeminiProvider(api_key=settings.gemini_api_key),
        "mistral": lambda: MistralProvider(api_key=settings.mistral_api_key),
    }
    if name not in providers:
        raise ValueError(f"Unknown cloud provider: {name}. Available: {list(providers.keys())}")
    return providers[name]()
