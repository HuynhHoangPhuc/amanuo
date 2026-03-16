"""Unit tests for pipeline executor."""

import importlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

_executor = importlib.import_module("src.engine.pipeline-executor")
_config = importlib.import_module("src.engine.pipeline-config")

execute_pipeline = _executor.execute_pipeline
PipelineConfig = _config.PipelineConfig
StepDefinition = _config.StepDefinition


class MockStepContext:
    """Mock StepContext for testing."""

    def __init__(self):
        self.metadata = {}
        self.data = {}


class MockStep:
    """Mock pipeline step."""

    def __init__(self, step_id: str, config: dict):
        self.step_id = step_id
        self.config = config
        self.execute_called = False

    async def execute(self, context):
        """Mock execute method."""
        self.execute_called = True
        return context


class TestPipelineExecutor:
    """Test pipeline executor."""

    @pytest.mark.unit
    async def test_execute_empty_pipeline(self):
        """Executing empty pipeline returns unchanged context."""
        config = PipelineConfig(name="empty", steps=[])
        context = MockStepContext()

        result = await execute_pipeline(config, context)
        assert result is context
        assert result.metadata == {}

    @pytest.mark.unit
    async def test_execute_single_step_pipeline(self):
        """Executing single step pipeline tracks timing."""
        config = PipelineConfig(
            name="single",
            steps=[StepDefinition(id="step1", type="extract", config={})],
        )
        context = MockStepContext()

        # Import the module that contains _registry
        import importlib
        exec_mod = importlib.import_module("src.engine.pipeline-executor")

        with patch.object(exec_mod._registry, "get_step_class") as mock_get_class:
            mock_get_class.return_value = MagicMock(return_value=MockStep("step1", {}))

            result = await execute_pipeline(config, context)

            assert result is context
            assert "step_step1_ms" in result.metadata
            assert result.metadata["step_step1_ms"] >= 0

    @pytest.mark.unit
    async def test_execute_multiple_steps_sequentially(self):
        """Multiple steps execute in order."""
        config = PipelineConfig(
            name="multi",
            steps=[
                StepDefinition(id="step1", type="extract"),
                StepDefinition(id="step2", type="validate"),
            ],
        )
        context = MockStepContext()

        import importlib
        exec_mod = importlib.import_module("src.engine.pipeline-executor")

        with patch.object(exec_mod._registry, "get_step_class") as mock_get_class:
            mock_get_class.return_value = MagicMock(return_value=MockStep("s", {}))

            result = await execute_pipeline(config, context)

            assert "step_step1_ms" in result.metadata
            assert "step_step2_ms" in result.metadata

    @pytest.mark.unit
    async def test_execute_aborts_on_abort_flag(self):
        """Pipeline halts early when abort flag is set."""
        config = PipelineConfig(
            name="abort",
            steps=[
                StepDefinition(id="step1", type="extract"),
                StepDefinition(id="step2", type="validate"),
            ],
        )
        context = MockStepContext()

        class AbortingStep:
            def __init__(self, step_id, config):
                self.step_id = step_id
                self.config = config

            async def execute(self, ctx):
                ctx.metadata["abort"] = True
                ctx.metadata["abort_reason"] = "test abort"
                return ctx

        import importlib
        exec_mod = importlib.import_module("src.engine.pipeline-executor")

        with patch.object(exec_mod._registry, "get_step_class") as mock_get_class:
            mock_get_class.return_value = MagicMock(return_value=AbortingStep("s", {}))

            result = await execute_pipeline(config, context)

            assert result.metadata["abort"] is True
            # Only step1 timing should be recorded
            assert "step_step1_ms" in result.metadata
            # step2 should not execute
            assert "step_step2_ms" not in result.metadata

    @pytest.mark.unit
    async def test_execute_step_timing_recorded(self):
        """Each step's execution time is recorded in metadata."""
        config = PipelineConfig(
            name="timing",
            steps=[StepDefinition(id="timed", type="extract")],
        )
        context = MockStepContext()

        import importlib
        exec_mod = importlib.import_module("src.engine.pipeline-executor")

        with patch.object(exec_mod._registry, "get_step_class") as mock_get_class:
            mock_get_class.return_value = MagicMock(return_value=MockStep("timed", {}))

            result = await execute_pipeline(config, context)

            assert "step_timed_ms" in result.metadata
            # Should be a number
            assert isinstance(result.metadata["step_timed_ms"], (int, float))
            assert result.metadata["step_timed_ms"] >= 0
