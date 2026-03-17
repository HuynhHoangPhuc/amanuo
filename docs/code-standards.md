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
  - **middleware/** — Auth middleware (API key, JWT validation)
  - **engine/** — Pipeline executor, step registry, config parser
  - **routers/** — FastAPI route handlers (extract, jobs, batches, pipelines, webhooks, auth, workspaces)
  - **services/** — Business logic (job, batch, workspace, auth, webhook, folder-watcher)
  - **pipelines/** — Extraction providers (base, cloud, local)
  - **schemas/** — Schema engine (validation, versioning, migration, conversion)
  - **models/** — Pydantic & ORM models (job, batch, pipeline, webhook, workspace, api-models)
  - **ui/** — Gradio interface (optional)
- **frontend/** — React/TanStack application
  - **routes/** — File-based TanStack Router pages
  - **components/** — Reusable React components (header, sidebar, modals, forms)
  - **lib/** — API client, query keys, type definitions
  - **public/** — Static assets

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
    # Database
    database_url: str = "sqlite+aiosqlite:///./amanuo.db"

    # Authentication
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 15
    jwt_refresh_expiration_days: int = 7
    bcrypt_rounds: int = 12

    # VLM & Cloud
    gemini_api_key: str = ""
    vlm_backend: Literal["ollama", "vllm", "llamacpp"] = "ollama"
    vlm_model: str = "qwen3-vl:4b"
    vlm_base_url: str = "http://localhost:11434"

    # Processing
    max_workers: int = 3
    max_file_size_mb: int = 20
    batch_window_seconds: int = 60
    default_mode: Literal["local_only", "cloud", "auto"] = "auto"

    # Webhooks
    webhook_retry_backoff: list[int] = [60, 300, 1800, 7200]

settings = Settings()  # Load from .env

# Usage:
from src.config import settings
db_url = settings.database_url
```

## Authentication Patterns

### API Key Authentication
```python
# src/services/auth-service.py
from hashlib import sha256

def hash_api_key(raw_key: str) -> str:
    """Hash API key with SHA256 for storage."""
    return sha256(raw_key.encode()).hexdigest()

# Middleware validation (src/middleware/auth-middleware.py)
async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Extract and validate X-API-Key header, return workspace_id."""
    # Query database for key hash, check workspace_id
    # Never log raw key
    pass
```

### JWT Token Generation
```python
# src/services/auth-service.py
from bcrypt import hashpw, gensalt, checkpw
from jwt import encode, decode

def hash_password(password: str) -> str:
    """Hash with bcrypt, 12 rounds for slow brute-force."""
    return hashpw(password.encode(), gensalt(rounds=12)).decode()

def create_jwt_token(user_id: str, workspace_id: str, expires_in_minutes: int) -> str:
    """Create HS256 JWT token."""
    payload = {
        "sub": user_id,
        "workspace_id": workspace_id,
        "exp": datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    }
    return encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
```

## Pipeline Configuration Standards

### YAML Config Format
```yaml
# Pipeline stored in database, name: invoice-extraction
name: invoice-extraction
description: Extract structured data from invoices
steps:
  - name: preprocess
    type: preprocess
    config:
      auto_rotate: true
      enhance_contrast: true

  - name: extract
    type: extract
    config:
      schema_id: invoice-v2
      mode: auto

  - name: validate
    type: validate
    config:
      required_fields: [invoice_id, total_amount]

  - name: export
    type: export
    config:
      format: json
      include_confidence: true
```

### Pipeline Executor Pattern
```python
# src/engine/pipeline-executor.py
async def execute_pipeline(config: PipelineConfig, image: bytes) -> PipelineResult:
    """Execute steps sequentially, pass context through."""
    context = StepContext(image=image, schema=config.schema)

    for step in config.steps:
        step_executor = step_registry.get(step.type)
        context = await step_executor.execute(context, step.config)

        # Record timing, handle errors
        if context.error:
            return context.to_result()  # Stop on first error

    return context.to_result()
```

## Webhook Standards

### HMAC-SHA256 Signing
```python
# src/services/webhook-service.py
import hmac
from hashlib import sha256

def sign_payload(payload: dict, secret: str) -> str:
    """Sign webhook payload with HMAC-SHA256."""
    payload_str = json.dumps(payload, sort_keys=True)
    return hmac.new(
        secret.encode(),
        payload_str.encode(),
        sha256
    ).hexdigest()

# Include in webhook header:
# X-Amanuo-Signature: sha256={signature}
```

### Event Types
```python
# Supported events:
# - job.completed: Single extraction complete
# - job.failed: Single extraction failed
# - batch.completed: All batch items processed
# - batch.failed: Batch encountered critical error
# - batch.partial: Some items failed, some succeeded

# Retry backoff: [60s, 5m, 30m, 2h] (exponential)
```

## Frontend Standards (TanStack React + shadcn/ui)

### Component Naming
- **Pages:** PascalCase, match route file name
- **shadcn/ui Components:** PascalCase in `src/components/ui/` (e.g., `Badge`, `Button`, `Card`)
- **Custom Components:** PascalCase, domain-specific (e.g., `StatusBadge`, `LoadingSkeleton`)
- **Hooks:** camelCase (e.g., `useJobStatus`, `useBatchProgress`)
- **Utilities:** camelCase (e.g., `formatDate`, `parseResponse`)

### shadcn/ui Integration
- **Setup:** 10 pre-installed components (badge, button, card, input, select, sheet, skeleton, table, textarea, tooltip)
- **Config:** `components.json` defines style (New York), baseColor (zinc), and tsx output
- **Usage:** Import from `@/components/ui/` alias (configured in tsconfig)
- **Styling:** CVA (class-variance-authority) for component variants + clsx + tailwind-merge for class merging. All components use flat, compact styling (rounded-md borders, 13px text sizes, 36px table rows)
- **Refactored Components:** StatusBadge and RoleBadge use shadcn Badge, LoadingSkeleton uses shadcn Skeleton
- **ThemeToggle:** Icon-only button (Sun/Moon/Monitor from lucide-react) with dark/light/auto mode cycling
- **Sidebar Navigation:** Collapsible left sidebar with grouped nav sections + keyboard hints (kbd tags for ⌘K, ⌘1, etc.)
- **Command Palette:** CommandPalette component triggered by ⌘K (macOS) or Ctrl+K (Windows/Linux) for quick navigation and actions
- **Mobile Sidebar:** Uses shadcn Sheet for responsive hamburger on <768px breakpoint

### Tailwind & Theme Token Conventions
- **CSS Framework:** Tailwind CSS v4 with @tailwindcss/vite plugin
- **Theme Tokens:** Linear-inspired zinc + indigo palette with oklch-based token system (--background, --foreground, --primary, --muted, --accent, --destructive, --border, --input, --ring)
- **Typography:** Inter (sans-serif) for UI, JetBrains Mono (monospace) for code/technical content
- **Styling:** Flat, compact design (rounded-md, 13px text, 36px table rows) following Linear aesthetics
- **Dark Mode:** Applied via `[class="dark"]` selector on `<html>` element
- **Token Application:** Tailwind classes automatically use token values (e.g., `bg-background`, `text-muted-foreground`)
- **Navigation:** Collapsible sidebar with grouped sections + keyboard hints (kbd tags), command palette (⌘K)

### TanStack Router Setup
```typescript
// frontend/src/routes/__root.tsx
export const Route = createRootRoute({
  component: RootComponent,
  // Nested routes auto-discovered from directory structure
})

// Nested route example: frontend/src/routes/jobs/$jobId.tsx
export const Route = createFileRoute('/jobs/$jobId')({
  component: JobDetailPage,
})
```

### Theme Token System (Linear-Inspired Zinc + Indigo)
The Linear-inspired design uses oklch-based CSS tokens with monochrome zinc + indigo accents for color consistency across all 19 routes + 24 components:

```css
/* Global theme tokens in styles.css */
:root {
  --background: oklch(...);      /* Light background (zinc-50) */
  --foreground: oklch(...);      /* Dark text (zinc-950) */
  --primary: oklch(...);         /* Primary brand color (indigo-600) */
  --primary-foreground: oklch(...);
  --secondary: oklch(...);
  --secondary-foreground: oklch(...);
  --muted: oklch(...);           /* Muted text/backgrounds (zinc-500) */
  --muted-foreground: oklch(...);
  --accent: oklch(...);          /* Accent color (indigo-500) */
  --accent-foreground: oklch(...);
  --destructive: oklch(...);     /* Error/delete actions (red) */
  --destructive-foreground: oklch(...);
  --border: oklch(...);          /* Subtle borders (zinc-200) */
  --input: oklch(...);
  --ring: oklch(...);            /* Focus ring color (indigo) */
}

/* Dark mode overrides */
[class="dark"] {
  --background: oklch(...);      /* Dark background (zinc-950) */
  --foreground: oklch(...);      /* Light text (zinc-50) */
  --muted: oklch(...);           /* Muted text/backgrounds (zinc-700) */
  --border: oklch(...);          /* Subtle borders (zinc-800) */
  /* ... other dark overrides */
}
```

**Usage:** Apply via Tailwind classes (e.g., `bg-background`, `text-muted-foreground`, `border-border`). Typography uses Inter (sans) for UI and JetBrains Mono for code blocks.

### API Client with Auth
```typescript
// frontend/src/lib/api-client.ts
const client = new APIClient({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'X-API-Key': getStoredAPIKey() // From localStorage
  }
})
```

### Query Key Structure
```typescript
// frontend/src/lib/query-keys.ts
export const jobKeys = {
  all: () => ['jobs'],
  list: () => [...jobKeys.all(), 'list'],
  detail: (id: string) => [...jobKeys.all(), 'detail', id],
}

// Usage:
useQuery({
  queryKey: jobKeys.detail(jobId),
  queryFn: () => client.getJob(jobId)
})
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

## SQLAlchemy ORM Patterns

**Async Session Management** — Use `AsyncSession` with dependency injection in routers. All queries with `session.execute()` must be awaited. ORM models use `Mapped` type hints with `mapped_column()` for type safety.

**ORM Model Best Practices:**
- Inherit from `Base` and `TimestampMixin` for `created_at`/`updated_at`
- Use parameterized queries (prevent SQL injection)
- All table operations via ORM (no raw SQL except migrations)

See `/docs/advanced-patterns.md` for detailed SQLAlchemy, ARQ, WebSocket, review, accuracy, template, RBAC, and approval engine patterns.

## Role-Based Access Control (RBAC) Patterns

### Role Definition
```python
# Roles (in workspace context):
ROLES = ["viewer", "member", "reviewer", "approver", "admin"]

# Role hierarchy:
viewer < member < reviewer < approver < admin
```

### Middleware Integration
```python
# src/middleware/auth-middleware.py
async def require_role(*allowed_roles: str):
    """Decorator to gate endpoint by role."""
    async def check_role(user: dict = Depends(get_current_user)):
        if not any(role in user["roles"] for role in allowed_roles):
            raise HTTPException(403, "Insufficient permissions")
        return user
    return check_role

# Usage in routers:
@router.post("/approve")
async def approve_job(
    user: dict = Depends(require_role("approver", "admin"))
):
    """Only approvers and admins can approve."""
    pass
```

### Role Assignment Service
```python
# src/services/role-service.py
async def assign_role(user_id: str, workspace_id: str, role: str, granted_by: str):
    """Assign role to user in workspace (admin only)."""
    # Validate role in ROLES
    # Create role_assignment record
    # Log via audit
    pass

async def remove_role(user_id: str, workspace_id: str, role: str):
    """Remove role from user (prevent self-removal of admin)."""
    # Prevent admin from removing own admin role
    # Delete role_assignment
    # Log via audit
    pass
```

## Approval Engine Patterns

### Policy Configuration
```python
# Chain policy example:
{
  "policy_type": "chain",
  "config": {
    "rounds": [
      {"round_number": 1, "approvers": ["reviewer_1"]},
      {"round_number": 2, "approvers": ["reviewer_2", "reviewer_3"]},
      {"round_number": 3, "approvers": ["approver_1"]}
    ],
    "escalate_on_rejection": True
  }
}

# Quorum policy example:
{
  "policy_type": "quorum",
  "config": {
    "m": 2,  # Approvals needed
    "n": 3,  # Total reviewers
    "approvers": ["reviewer_1", "reviewer_2", "reviewer_3"]
  }
}
```

### Approval Engine Service
```python
# src/services/approval-engine.py
async def orchestrate_review_workflow(job_id: str, policy_id: str):
    """Orchestrate multi-round approval workflow."""
    policy = await get_policy(policy_id)

    if policy.type == "chain":
        # Sequential rounds: Each round must approve to move to next
        for round_config in policy.config["rounds"]:
            round_orm = await create_round(job_id, round_config)
            await assign_reviewers(round_orm.id, round_config["approvers"])

            # Wait for round decision
            result = await wait_for_round_completion(round_orm.id)
            if result == "rejected":
                await escalate_to_approver(job_id)
                return

    elif policy.type == "quorum":
        # Parallel voting: Tally votes, need M of N approvals
        round_orm = await create_quorum_round(job_id, policy.config)
        await assign_reviewers(round_orm.id, policy.config["approvers"])

        decisions = await wait_for_quorum_completion(round_orm.id)
        approvals = sum(1 for d in decisions if d == "approved")

        if approvals >= policy.config["m"]:
            await mark_job_approved(job_id)
        else:
            await escalate_to_approver(job_id)
```

### Review Workflow Endpoints
```python
# Reviewer workflow:
GET /review-queue  # Get pending assignments
POST /jobs/{id}/review  # Submit decision (approved/rejected/corrected)
GET /jobs/{id}/review-status  # Check workflow progress

# Admin workflow:
GET /approval-policies  # List policies
POST /approval-policies  # Create policy
PUT /approval-policies/{id}  # Update policy
DELETE /approval-policies/{id}  # Delete policy
POST /jobs/{id}/assign-reviewers  # Auto-assign round reviewers
GET /jobs/{id}/audit-log  # Approval audit trail
```

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
- **PyYAML** (pipeline config parsing)
- **PyJWT** (JWT token generation)
- **bcrypt** (password hashing)
- **watchfiles** (folder watcher for batch processing)

### Optional Dependencies
- **Cloud:** google-genai, mistralai
- **Local:** paddleocr, paddlepaddle
- **UI:** gradio >= 5.0

### Frontend Dependencies
- **React** >= 19.0 (UI framework)
- **TanStack Router** (file-based routing)
- **TanStack Query** (async state management)
- **Tailwind CSS** >= 4.0 (utility-first styling)
- **Vite** >= 7.0 (build tool)
- **TypeScript** >= 5.0 (type safety)

Keep dependencies minimal; don't add packages for convenience if they're not core to extraction logic.
