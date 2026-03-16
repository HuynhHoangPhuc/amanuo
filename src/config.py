"""Application configuration via environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "amanuo"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./amanuo.db"

    # Cloud API keys
    gemini_api_key: str = ""
    mistral_api_key: str = ""

    # Local VLM config
    vlm_backend: Literal["ollama", "vllm", "llamacpp"] = "ollama"
    vlm_model: str = "qwen3-vl:4b"
    vlm_base_url: str = "http://localhost:11434"

    # Processing
    default_mode: Literal["local_only", "cloud", "auto"] = "auto"
    max_file_size_mb: int = 20
    max_workers: int = 3

    # Redis (optional, for future Celery queue)
    redis_url: str = "redis://localhost:6379/0"

    # Upload storage
    upload_dir: str = "data/uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
