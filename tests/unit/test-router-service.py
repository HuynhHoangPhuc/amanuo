"""Unit tests for router service."""

import importlib

from src.pipelines.cloud import GeminiProvider, MistralProvider
from src.pipelines.local import LocalProvider

_router = importlib.import_module("src.services.router-service")


class TestRouterService:
    def test_cloud_mode_gemini(self):
        provider = _router.route("cloud", "gemini")
        assert isinstance(provider, GeminiProvider)

    def test_cloud_mode_mistral(self):
        provider = _router.route("cloud", "mistral")
        assert isinstance(provider, MistralProvider)

    def test_local_mode(self):
        provider = _router.route("local_only")
        assert isinstance(provider, LocalProvider)

    def test_auto_mode_defaults_to_cloud(self):
        provider = _router.route("auto", "gemini")
        assert isinstance(provider, GeminiProvider)

    def test_auto_mode_mistral(self):
        provider = _router.route("auto", "mistral")
        assert isinstance(provider, MistralProvider)
