"""Pipeline executor — runs steps sequentially, tracking per-step timing."""

import importlib
import logging
import time

logger = logging.getLogger(__name__)

_registry = importlib.import_module("src.engine.step-registry")
_config_mod = importlib.import_module("src.engine.pipeline-config")


async def execute_pipeline(pipeline_config, context):
    """Execute pipeline steps sequentially against a shared StepContext.

    Each step's elapsed wall-clock time is stored in
    ``context.metadata["step_{step_id}_ms"]``.

    Execution halts early if any step sets ``context.metadata["abort"] = True``.

    Args:
        pipeline_config: A PipelineConfig instance with a list of StepDefinition.
        context: A StepContext instance carrying input data and accumulating results.

    Returns:
        The final StepContext after all steps (or after abort).
    """
    logger.info(
        "execute_pipeline: starting pipeline '%s' with %d steps",
        pipeline_config.name,
        len(pipeline_config.steps),
    )

    for step_def in pipeline_config.steps:
        step_class = _registry.get_step_class(step_def.type)
        step = step_class(step_id=step_def.id, config=step_def.config)

        logger.debug("execute_pipeline: running step '%s' (type=%s)", step_def.id, step_def.type)

        start = time.monotonic()
        context = await step.execute(context)
        elapsed = time.monotonic() - start

        context.metadata[f"step_{step_def.id}_ms"] = round(elapsed * 1000, 2)

        if context.metadata.get("abort"):
            logger.warning(
                "execute_pipeline: aborted at step '%s' — reason: %s",
                step_def.id,
                context.metadata.get("abort_reason", "unspecified"),
            )
            break

    logger.info("execute_pipeline: pipeline '%s' complete", pipeline_config.name)
    return context
