"""Step registry — maps step type strings to step classes via lazy import."""

import importlib


def get_step_class(step_type: str):
    """Get step class by type name.

    Uses lazy import to avoid circular imports at module load time.

    Args:
        step_type: One of "preprocess", "extract", "validate", "export".

    Returns:
        The step class corresponding to step_type.

    Raises:
        ValueError: If step_type is not registered.
    """
    _steps = importlib.import_module("src.engine.steps")
    registry = {
        "preprocess": _steps.PreprocessStep,
        "extract": _steps.ExtractStep,
        "validate": _steps.ValidateStep,
        "export": _steps.ExportStep,
    }
    cls = registry.get(step_type)
    if not cls:
        raise ValueError(f"Unknown step type: {step_type}")
    return cls
