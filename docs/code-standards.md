# Code Standards & Guidelines

## File Naming Conventions

### Python Files
- Use **kebab-case** with descriptive names
- Max 50 characters before `.py` extension
- Avoid `utils.py`, `helpers.py` — be specific
- Use `importlib.import_module()` for dynamic imports of kebab-cased files

**Examples:**
```
✓ extraction-worker.py
✓ vlm-prompt-builder.py
✓ paddleocr-fallback.py
✓ schema-validator.py

✗ extractionworker.py
✗ util.py
✗ helper_functions.py
```

### Directory Structure
- **src/** — Application code
  - **routers/** — FastAPI route handlers
  - **services/** — Business logic (job, routing, scoring)
  - **pipelines/** — Extraction providers (base, cloud, local)
  - **schemas/** — Data modeling & validation
  - **models/** — Pydantic & ORM models
  - **ui/** — Gradio interface

## Module Size Limits

| Type | Max Lines | Purpose |
|---|---|---|
| **Service Class** | 200 | Business logic (job processing, routing) |
| **Router Handler** | 100 | API endpoint definitions |
| **Provider** | 150 | Pipeline implementation |
| **Utility** | 80 | Helper functions, validators |
| **Test File** | 300 | Unit + integration tests |

**Strategy:** When approaching limit, extract cohesive functionality into separate modules.

## Code Organization

### Module Header
Every Python file begins with:
```python
"""One-line description of module purpose."""

# Standard library imports
import asyncio
from pathlib import Path

# Third-party imports
from fastapi import FastAPI
from pydantic import BaseModel

# Local imports
from src.config import settings
from src.models import JobModel
```

### Class & Function Structure
```python
class ExtractionService:
    """Brief docstring explaining purpose."""

    def __init__(self, db_path: str):
        """Initialize with dependencies."""
        self.db_path = db_path

    async def extract_job(self, job_id: str) -> dict:
        """Extract structured data from uploaded image.

        Args:
            job_id: Unique job identifier

        Returns:
            Dictionary with result, confidence, cost

        Raises:
            FileNotFoundError: If job image not found
        """
        # Implementation
        pass
```

## Import Management

### importlib for Dynamic Imports
Use `importlib.import_module()` for files with kebab-case names:
```python
# ✓ Correct way to import kebab-cased modules
_worker = importlib.import_module("src.services.extraction-worker")
_scorer = importlib.import_module("src.services.confidence-scorer")

# Later in code:
result = await _worker.process_job(job_id)
confidence = _scorer.calculate(results)
```

### Standard Import Rules
1. Group: stdlib → third-party → local imports
2. Sort alphabetically within groups
3. Use `from module import name` for clarity
4. Avoid `import *` except in `__init__.py`

## Type Hints

All functions must have type hints:
```python
async def extract(
    image_bytes: bytes,
    schema: ExtractionSchema,
    mode: str = "auto"
) -> PipelineResult:
    """Extract fields from image."""
    pass
```

## Testing Patterns

### Test File Organization
- Naming: `test-{module-name}.py` or `test_{function_name}.py`
- One test class per module
- Use fixtures for shared setup

```python
@pytest.mark.unit
class TestSchemaValidator:
    def test_valid_schema_accepts_required_field(self):
        schema = {"label": "color", "type": "text"}
        assert validate_or_raise([schema]) is None

    def test_invalid_type_raises_error(self):
        schema = {"label": "color", "type": "invalid"}
        with pytest.raises(SchemaValidationError):
            validate_or_raise([schema])

@pytest.mark.integration
async def test_extraction_with_real_image():
    result = await extract_provider.extract(image_bytes, schema)
    assert result.confidence > 0.0
```

### Test Categories
- **@pytest.mark.unit** — No I/O, mocked dependencies
- **@pytest.mark.integration** — External services (Ollama, Gemini)
- **@pytest.mark.e2e** — Full workflow (upload → extract → retrieve)

### Coverage Targets
- Services layer: 100%
- Pipeline providers: 95%+
- Routers: 80%+
- Utilities: 90%+

## Error Handling

### Exception Hierarchy
```python
class ExtractionError(Exception):
    """Base exception for all extraction-related errors."""
    pass

class SchemaValidationError(ExtractionError):
    """Raised when schema is invalid."""
    pass

class ProviderUnavailableError(ExtractionError):
    """Raised when all providers fail."""
    pass
```

### Async Error Patterns
```python
async def safe_extract(job_id: str) -> PipelineResult:
    """Extract with fallback error handling."""
    try:
        result = await provider.extract(image, schema)
        return result
    except ProviderUnavailableError:
        logger.warning(f"Provider unavailable for {job_id}, trying fallback")
        return await fallback_provider.extract(image, schema)
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise
```

## Logging

Use standard library `logging`:
```python
import logging

logger = logging.getLogger(__name__)

# Log levels:
logger.debug("Detailed extraction metrics")
logger.info("Job completed successfully")
logger.warning("Low confidence score, attempting retry")
logger.error("Provider API timeout", exc_info=True)
```

## Configuration Management

All environment-specific values go to `src/config.py`:
```python
# src/config.py
class Settings(BaseSettings):
    gemini_api_key: str = ""
    vlm_backend: Literal["ollama", "vllm", "llamacpp"] = "ollama"
    max_workers: int = 3

settings = Settings()  # Load from .env

# Usage:
from src.config import settings
db_url = settings.database_url
```

## Code Quality Standards

### Line Length
- Target: 100 characters max
- Breaking long lines: use implicit line continuation

```python
# ✓ Good
result = await provider.extract(
    image_bytes=image,
    schema=schema,
    confidence_threshold=0.85
)

# ✗ Avoid
result = await provider.extract(image_bytes=image, schema=schema, confidence_threshold=0.85)
```

### Naming Conventions
| Scope | Style | Example |
|---|---|---|
| **Variables** | snake_case | `job_id`, `image_bytes` |
| **Classes** | PascalCase | `ExtractionService`, `SchemaValidator` |
| **Constants** | UPPER_SNAKE_CASE | `MAX_FILE_SIZE`, `TIMEOUT_SECONDS` |
| **Private methods** | _leading_underscore | `_validate_schema()` |
| **Async functions** | verb_noun | `process_job()`, `extract_image()` |

### Docstring Format
Use Google-style docstrings:
```python
def validate_schema(fields: list[dict]) -> None:
    """Validate extraction schema fields.

    Args:
        fields: List of field dictionaries with label, type, occurrence

    Raises:
        SchemaValidationError: If any field is invalid

    Example:
        >>> validate_schema([{"label": "color", "type": "text", "occurrence": "required once"}])
    """
```

## Performance Considerations

### Async First
- All I/O operations must be async (database, network, file)
- Use `asyncio.gather()` for concurrent operations
- Never block event loop with sync I/O

### Database Queries
- Use parameterized queries (protection against injection)
- Batch operations where possible
- Add indexes on frequently queried columns (job_id, status, created_at)

### Caching
- Schema templates cached in-memory after first load
- Provider availability checked once per worker startup
- Cost calculations cached per provider

## Pre-Commit Checklist

Before committing Python code:
1. Run linter: `ruff check src/ tests/`
2. Format code: `ruff format src/ tests/`
3. Run tests: `pytest` (all must pass)
4. Check line length: `ruff check --select E501`
5. Verify type hints: manual inspection

## Dependencies & Versioning

### Core Dependencies
- **FastAPI** >= 0.115.0 (async web framework)
- **Pydantic** >= 2.5 (validation)
- **aiosqlite** >= 0.20.0 (async SQLite)
- **httpx** >= 0.27.0 (async HTTP client)

### Optional Dependencies
- **Cloud:** google-genai, mistralai (install via `pip install amanuo[cloud]`)
- **Local:** paddleocr, paddlepaddle (install via `pip install amanuo[local]`)
- **UI:** gradio >= 5.0 (install via `pip install amanuo[ui]`)

Keep dependencies minimal; don't add packages for convenience if they're not core to extraction logic.
