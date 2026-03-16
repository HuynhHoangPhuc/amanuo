"""Preprocess step — image resize and format conversion before extraction."""

import importlib
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency on Pillow
_pil_available: bool | None = None


def _check_pil() -> bool:
    global _pil_available
    if _pil_available is None:
        try:
            importlib.import_module("PIL.Image")
            _pil_available = True
        except ImportError:
            _pil_available = False
            logger.warning("Pillow not available — preprocess step will pass through unchanged")
    return _pil_available


_iface = importlib.import_module("src.engine.step-interface")
PipelineStep = _iface.PipelineStep
StepContext = _iface.StepContext


class PreprocessStep(PipelineStep):
    """Resize image and optionally convert format using Pillow.

    Config options:
        max_width (int): Maximum image width in pixels. Default 2048.
        format (str): Output image format ("png", "jpeg", etc.). Default "png".
    """

    def __init__(self, step_id: str, config: dict[str, Any] | None = None):
        super().__init__(step_id, config)
        self._max_width: int = int(self.config.get("max_width", 2048))
        self._format: str = str(self.config.get("format", "png")).upper()

    @property
    def step_type(self) -> str:
        return "preprocess"

    @property
    def input_type(self) -> str:
        return "image"

    @property
    def output_type(self) -> str:
        return "image"

    async def execute(self, context: StepContext) -> StepContext:
        """Resize and reformat image bytes. Passes through if Pillow not available."""
        if context.image is None:
            logger.debug("preprocess: no image in context, skipping")
            return context

        if not _check_pil():
            # Pillow not installed — pass through unchanged
            return context

        try:
            PIL_Image = importlib.import_module("PIL.Image")
            img = PIL_Image.open(io.BytesIO(context.image))

            # Resize if wider than max_width while preserving aspect ratio
            if img.width > self._max_width:
                ratio = self._max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self._max_width, new_height), PIL_Image.LANCZOS)
                logger.debug(
                    "preprocess: resized to %dx%d", self._max_width, new_height
                )

            # Convert to target format
            buf = io.BytesIO()
            fmt = self._format if self._format != "JPG" else "JPEG"
            img.save(buf, format=fmt)
            context.image = buf.getvalue()
            logger.debug("preprocess: converted to %s (%d bytes)", fmt, len(context.image))

        except Exception as exc:  # noqa: BLE001
            logger.warning("preprocess: image processing failed (%s), passing through", exc)

        return context
