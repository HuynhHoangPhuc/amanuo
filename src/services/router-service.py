"""Pipeline routing logic — dispatch to correct provider based on user choice."""


from src.pipelines import BaseProvider
from src.pipelines.cloud import get_cloud_provider
from src.pipelines.local import LocalProvider

_local_instance: LocalProvider | None = None


def _get_local_provider() -> LocalProvider:
    """Singleton local provider."""
    global _local_instance
    if _local_instance is None:
        _local_instance = LocalProvider()
    return _local_instance


def route(mode: str, cloud_provider: str = "gemini") -> BaseProvider:
    """Select the extraction provider based on user mode choice.

    Args:
        mode: "local_only" | "cloud" | "auto"
        cloud_provider: "gemini" | "mistral" (used when mode is cloud/auto)

    Returns:
        The appropriate BaseProvider instance.
    """
    if mode == "local_only":
        return _get_local_provider()
    elif mode == "cloud":
        return get_cloud_provider(cloud_provider)
    else:  # auto — MVP default: use cloud
        return get_cloud_provider(cloud_provider)
