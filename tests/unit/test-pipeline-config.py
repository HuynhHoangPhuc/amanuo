"""Unit tests for pipeline configuration parsing and validation."""

import importlib
import pytest

_config = importlib.import_module("src.engine.pipeline-config")
parse_pipeline_yaml = _config.parse_pipeline_yaml
validate_pipeline = _config.validate_pipeline
PipelineConfig = _config.PipelineConfig
StepDefinition = _config.StepDefinition
DEFAULT_PIPELINE_YAML = _config.DEFAULT_PIPELINE_YAML


class TestPipelineConfigParsing:
    """Test YAML pipeline configuration parsing."""

    @pytest.mark.unit
    def test_parse_default_pipeline(self):
        """Default pipeline YAML parses correctly."""
        config = parse_pipeline_yaml(DEFAULT_PIPELINE_YAML)
        assert config.name == "default"
        assert len(config.steps) >= 1
        assert any(step.type == "extract" for step in config.steps)

    @pytest.mark.unit
    def test_parse_valid_simple_pipeline(self):
        """Valid simple pipeline YAML parses correctly."""
        yaml_str = """
name: test-pipeline
description: A test pipeline
steps:
  - id: step1
    type: extract
    config:
      mode: local
      backend: ollama
  - id: step2
    type: validate
    config:
      min_confidence: 0.8
"""
        config = parse_pipeline_yaml(yaml_str)
        assert config.name == "test-pipeline"
        assert config.description == "A test pipeline"
        assert len(config.steps) == 2
        assert config.steps[0].id == "step1"
        assert config.steps[0].type == "extract"
        assert config.steps[0].config["mode"] == "local"

    @pytest.mark.unit
    def test_parse_pipeline_with_no_config(self):
        """Pipeline step without config defaults to empty dict."""
        yaml_str = """
name: minimal
steps:
  - id: step1
    type: extract
"""
        config = parse_pipeline_yaml(yaml_str)
        assert config.steps[0].config == {}

    @pytest.mark.unit
    def test_parse_invalid_yaml_raises_valueerror(self):
        """Malformed YAML raises ValueError."""
        yaml_str = "{ invalid yaml []["
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_pipeline_yaml(yaml_str)

    @pytest.mark.unit
    def test_parse_non_dict_yaml_raises_valueerror(self):
        """YAML that doesn't parse to dict raises ValueError."""
        yaml_str = "- just a list"
        with pytest.raises(ValueError, match="must be a YAML mapping"):
            parse_pipeline_yaml(yaml_str)

    @pytest.mark.unit
    def test_parse_missing_required_fields_raises_error(self):
        """YAML missing required fields (name, steps) raises error."""
        yaml_str = """
description: missing name and steps
"""
        with pytest.raises((ValueError, KeyError)):
            parse_pipeline_yaml(yaml_str)

    @pytest.mark.unit
    def test_parse_steps_without_type_raises_error(self):
        """Step missing type field raises error."""
        yaml_str = """
name: bad-pipeline
steps:
  - id: step1
"""
        with pytest.raises((ValueError, KeyError)):
            parse_pipeline_yaml(yaml_str)


class TestPipelineValidation:
    """Test pipeline configuration validation."""

    @pytest.mark.unit
    def test_validate_default_pipeline_no_warnings(self):
        """Default pipeline validation returns no warnings."""
        config = parse_pipeline_yaml(DEFAULT_PIPELINE_YAML)
        warnings = validate_pipeline(config)
        assert warnings == []

    @pytest.mark.unit
    def test_validate_known_step_types_no_warnings(self):
        """Pipeline with registered step types returns no warnings."""
        yaml_str = """
name: valid
steps:
  - id: extract
    type: extract
  - id: validate
    type: validate
"""
        config = parse_pipeline_yaml(yaml_str)
        warnings = validate_pipeline(config)
        assert warnings == []

    @pytest.mark.unit
    def test_validate_unknown_step_type_returns_warning(self):
        """Pipeline with unknown step type returns warning."""
        yaml_str = """
name: invalid
steps:
  - id: unknown
    type: unknown_step_type
"""
        config = parse_pipeline_yaml(yaml_str)
        warnings = validate_pipeline(config)
        assert len(warnings) >= 1
        assert "unknown_step_type" in warnings[0]

    @pytest.mark.unit
    def test_validate_multiple_unknown_types(self):
        """Pipeline with multiple unknown types returns multiple warnings."""
        yaml_str = """
name: invalid
steps:
  - id: s1
    type: unknown1
  - id: s2
    type: unknown2
"""
        config = parse_pipeline_yaml(yaml_str)
        warnings = validate_pipeline(config)
        assert len(warnings) >= 2
