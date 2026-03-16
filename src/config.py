"""Application configuration via environment variables."""

from typing import Literal

from pydantic import Field
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

    # Auth
    jwt_secret: str = ""  # Set in .env for production; auto-generated if empty

    # Redis / ARQ job queue
    redis_url: str = "redis://localhost:6379/0"
    broadcaster_url: str = Field(default="redis://localhost:6379/0")
    arq_max_jobs: int = Field(default=3)
    arq_job_timeout: int = Field(default=300)
    arq_max_retries: int = Field(default=3)
    arq_retry_delay: int = Field(default=60)

    # Upload storage
    upload_dir: str = "data/uploads"

    # Folder watcher (batch processing)
    watch_dir: str = ""  # empty = disabled
    watch_schema_id: str = ""
    watch_pipeline_id: str = ""
    watch_batch_window_seconds: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> "Settings":
    """Return the global settings instance."""
    return settings


settings = Settings()
