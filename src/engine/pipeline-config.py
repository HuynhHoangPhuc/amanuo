"""YAML pipeline configuration parsing and validation."""

import importlib

import yaml
from pydantic import BaseModel

# Default pipeline YAML (matches MVP behavior — direct cloud extraction)
DEFAULT_PIPELINE_YAML = """
name: default
description: Default extraction pipeline (matches MVP behavior)
steps:
  - id: extract
    type: extract
    config:
      mode: auto
      cloud_provider: gemini
  - id: validate
    type: validate
    config:
      min_confidence: 0.0
""".strip()


class StepDefinition(BaseModel):
    """Definition of a single step within a pipeline config."""

    id: str
    type: str
    config: dict = {}


class PipelineConfig(BaseModel):
    """Full pipeline configuration parsed from YAML."""

    name: str
    description: str = ""
    steps: list[StepDefinition]


def parse_pipeline_yaml(yaml_str: str) -> PipelineConfig:
    """Parse YAML string into a PipelineConfig model.

    Args:
        yaml_str: Raw YAML configuration string.

    Returns:
        Validated PipelineConfig instance.

    Raises:
        ValueError: If YAML is malformed or config is invalid.
    """
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Pipeline config must be a YAML mapping")

    return PipelineConfig(**data)


def validate_pipeline(config: PipelineConfig) -> list[str]:
    """Validate step type compatibility within a pipeline.

    Checks that all step types referenced in the config are registered
    in the step registry. Returns a list of warning messages (empty = valid).

    Args:
        config: Parsed PipelineConfig to validate.

    Returns:
        List of warning strings; empty list means no issues found.
    """
    _registry = importlib.import_module("src.engine.step-registry")
    warnings: list[str] = []

    for step_def in config.steps:
        try:
            _registry.get_step_class(step_def.type)
        except ValueError:
            warnings.append(f"Unknown step type '{step_def.type}' in step '{step_def.id}'")

    return warnings
