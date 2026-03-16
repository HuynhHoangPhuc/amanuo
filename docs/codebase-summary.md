# Codebase Summary

## Directory Structure

```
amanuo/
├── src/                              # Main application code (~3,200 LOC)
│   ├── __init__.py                  # Package marker
│   ├── main.py                      # FastAPI app, lifespan, router mounting
│   ├── config.py                    # Settings (pydantic-settings, auth, webhooks)
│   ├── database.py                  # SQLite schema (11 tables), initialization
│   │
│   ├── middleware/
│   │   └── auth-middleware.py       # API key (SHA256), JWT (HS256) validation, workspace scoping
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── api-models.py            # Pydantic request/response schemas
│   │   ├── job.py                   # Job ORM model
│   │   ├── batch.py                 # Batch ORM model, atomic counters
│   │   ├── pipeline.py              # Pipeline ORM model (YAML config storage)
│   │   ├── webhook.py               # Webhook ORM model (event types, secret)
│   │   └── workspace.py             # Workspace ORM model, user isolation
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                  # POST /auth/register, /login, /logout
│   │   ├── extract.py               # POST /extract (single file)
│   │   ├── jobs.py                  # GET /jobs, /jobs/{id}
│   │   ├── batch.py                 # POST /extract/batch, GET /batches, cancel
│   │   ├── pipelines.py             # CRUD /pipelines (YAML config)
│   │   ├── schemas.py               # CRUD /schemas, version history
│   │   ├── templates.py             # GET /templates, POST /import, schema suggest
│   │   ├── webhooks.py              # Register, test, delivery logs
│   │   ├── websocket-events.py      # GET /ws/events (real-time event stream)
│   │   ├── workspaces.py            # CRUD /workspaces
│   │   └── health.py                # GET /health
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth-service.py          # User auth, JWT, password hashing (bcrypt)
│   │   ├── workspace-service.py     # Workspace CRUD, multi-tenancy enforcement
│   │   ├── job-service.py           # Job CRUD, persistence, status transitions
│   │   ├── batch-service.py         # Batch creation, item tracking, status derivation
│   │   ├── pipeline-service.py      # Pipeline CRUD, executor delegation
│   │   ├── webhook-service.py       # Event registration, HMAC-SHA256 signing
│   │   ├── webhook-delivery.py      # Async delivery queue, retry backoff
│   │   ├── extraction-worker.py     # ARQ job enqueue, provider selection, scoring
│   │   ├── redis-pool.py            # ARQ Redis connection pool singleton
│   │   ├── arq-worker-settings.py   # ARQ worker config, job handlers
│   │   ├── event-broadcaster.py     # Redis pub/sub for WebSocket events
│   │   ├── router-service.py        # Provider selection (local→cloud fallback)
│   │   ├── confidence-scorer.py     # Field-level aggregation
│   │   ├── schema-suggest-service.py # VLM field suggestion for schema design
│   │   ├── template-service.py      # Schema template CRUD + seeding
│   │   ├── folder-watcher.py        # watchfiles batch aggregation (60s window)
│   │   └── __init__.py
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── pipeline-executor.py     # Sequential step execution, timing, error handling
│   │   ├── pipeline-config.py       # YAML parser, config validation
│   │   ├── step-registry.py         # Step type registry (preprocess, extract, validate, export)
│   │   ├── step-interface.py        # Abstract StepContext, execution protocol
│   │   └── steps/
│   │       ├── __init__.py
│   │       ├── preprocess-step.py   # Image preprocessing (rotation, contrast)
│   │       ├── extract-step.py      # Delegation to extraction providers
│   │       ├── validate-step.py     # Field validation against schema
│   │       └── export-step.py       # Result formatting (JSON, CSV)
│   │
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── base-provider.py         # Abstract interface (extract, is_available, cost)
│   │   ├── cloud/
│   │   │   ├── __init__.py
│   │   │   ├── gemini-provider.py   # Gemini API integration, cost tracking
│   │   │   ├── mistral-provider.py  # Mistral API integration, cost tracking
│   │   │   └── cloud-utils.py       # Token counting, prompt optimization
│   │   └── local/
│   │       ├── __init__.py
│   │       ├── local-provider.py    # VLM orchestrator, multi-backend fallback
│   │       ├── ollama-backend.py    # Ollama API calls
│   │       ├── vllm-backend.py      # vLLM API calls
│   │       ├── llamacpp-backend.py  # llama.cpp API calls
│   │       ├── vlm-prompt-builder.py # Schema→prompt conversion
│   │       └── paddleocr-fallback.py # Text-only extraction fallback
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── schema-models.py         # Pydantic models (SchemaField, ExtractionSchema)
│   │   ├── schema-validator.py      # Field validation, type checking
│   │   ├── schema-converter.py      # CSV/JSON parsing, normalization
│   │   ├── schema-store.py          # Template persistence, in-memory caching
│   │   ├── schema-versioning.py     # Semver auto-bump, compatibility checks
│   │   ├── schema-migration.py      # Migration tracking, version history
│   │   └── csv-prompt-builder.py    # CSV→schema conversion
│   │
│   ├── data/
│   │   └── curated-templates.yaml   # Built-in 4 templates (Invoice, Receipt, ID Card)
│   │
│   └── ui/
│       ├── __init__.py
│       ├── gradio-app.py            # Gradio web interface (optional)
│       └── ui-helpers.py            # Form builders, utilities
│
├── frontend/                         # React 19 + TanStack (25 files, ~2,300 LOC)
│   ├── src/
│   │   ├── routes/                  # TanStack file-based routing
│   │   │   ├── __root.tsx           # Root layout (header, sidebar)
│   │   │   ├── index.tsx            # Dashboard
│   │   │   ├── jobs.tsx             # Job list
│   │   │   ├── jobs_.$jobId.tsx     # Job detail
│   │   │   ├── schemas.tsx          # Schema management
│   │   │   ├── batches.tsx          # Batch tracking
│   │   │   ├── pipelines.tsx        # Pipeline editor
│   │   │   ├── webhooks.tsx         # Webhook config
│   │   │   └── settings.tsx         # User settings
│   │   ├── components/
│   │   │   ├── Header.tsx           # Top navigation
│   │   │   ├── SidebarNav.tsx       # Left sidebar
│   │   │   ├── PageLayout.tsx       # Common layout wrapper
│   │   │   ├── json-result-viewer.tsx # JSON display component
│   │   │   ├── loading-skeleton.tsx # Loading state
│   │   │   ├── status-badge.tsx     # Status indicator
│   │   │   ├── toast-provider.tsx   # Toast notifications
│   │   │   ├── ThemeToggle.tsx      # Light/dark mode
│   │   │   └── Footer.tsx           # Footer
│   │   ├── lib/
│   │   │   ├── api-client.ts        # HTTP client (X-API-Key auth)
│   │   │   ├── query-keys.ts        # TanStack Query key factories
│   │   │   └── types.ts             # TypeScript type definitions
│   │   ├── main.tsx                 # React entry point
│   │   ├── router.tsx               # TanStack Router setup
│   │   ├── routeTree.gen.ts         # Auto-generated route tree
│   │   └── styles.css               # Global styles
│   ├── public/                       # Static assets (favicon, logos)
│   ├── package.json                 # npm dependencies (React 19, TanStack, Tailwind, Vite)
│   ├── tsconfig.json                # TypeScript config
│   ├── vite.config.ts               # Vite build config (proxy to localhost:8000)
│   └── index.html                   # HTML entry point
│
├── tests/                            # 204 tests (148 unit + 56 E2E), 6.5s execution
│   ├── conftest.py                  # Shared fixtures
│   ├── unit/
│   │   ├── test-auth-middleware.py  # API key, JWT validation
│   │   ├── test-auth-service.py     # Registration, login, password hashing
│   │   ├── test-batch-service.py    # Batch creation, item tracking
│   │   ├── test-confidence-scorer.py # Field aggregation
│   │   ├── test-pipeline-config.py  # YAML parsing, validation
│   │   ├── test-pipeline-executor.py # Step execution, error handling
│   │   ├── test-schema-converter.py # CSV/JSON parsing
│   │   ├── test-schema-models.py    # Pydantic validation
│   │   ├── test-schema-validator.py # Field type checking
│   │   ├── test-schema-versioning.py # Semver bump, compatibility
│   │   ├── test-schema-migration.py # Version migration
│   │   ├── test-router-service.py   # Provider selection
│   │   ├── test-webhook-service.py  # Event registry, HMAC signing
│   │   └── test-csv-prompt-builder.py # CSV→prompt conversion
│   ├── integration/
│   │   └── (external service tests, conditionally skipped)
│   └── e2e/
│       ├── conftest.py              # E2E fixtures
│       ├── test-auth-flow.py        # Register, login, API key generation
│       ├── test-extract-flow.py     # Single extraction workflow
│       ├── test-batch-flow.py       # Multi-file batch processing
│       ├── test-pipeline-flow.py    # Pipeline creation, execution
│       ├── test-webhook-flow.py     # Event registration, delivery
│       ├── test-schema-crud.py      # Schema CRUD operations
│       ├── test-schema-versioning-flow.py # Version management
│       └── test-workspace-isolation.py # Multi-tenant enforcement
│
├── samples/                          # Example schemas (for testing/docs)
│   └── schemas/
│       ├── id-card-generic.json
│       ├── invoice-generic.json
│       └── vehicle-license-vn.json
│
├── data/
│   ├── uploads/                     # Uploaded files (created at runtime)
│   └── amanuo.db                    # SQLite database
│
├── .env.example                     # Configuration template
├── pyproject.toml                   # Project metadata, Python dependencies
├── uv.lock                          # Reproducible dependency lock
├── Dockerfile                       # Container image
├── docker-compose.yml               # Dev environment (Ollama, Postgres option)
├── LICENSE                          # License file
└── README.md                        # Project overview
```

## Key Files & Responsibilities

### Entry Point & Configuration

| File | Lines | Purpose |
|---|---|---|
| `main.py` | ~120 | FastAPI app, lifespan setup, router mounting |
| `config.py` | ~80 | Settings (auth tokens, webhooks, VLM, processing) |
| `database.py` | ~280 | SQLite schema (11 tables), initialization, indexes |

### Authentication & Middleware

| Module | Lines | Purpose |
|---|---|---|
| `middleware/auth-middleware.py` | ~70 | API key (SHA256), JWT (HS256) validation, workspace scoping |
| `services/auth-service.py` | ~120 | User registration/login, bcrypt (12 rounds), JWT generation |

### API Layer (39 Endpoints)

| Router | Endpoints | Purpose |
|---|---|---|
| `routers/auth.py` | /auth/register, /login, /logout | User authentication |
| `routers/extract.py` | POST /extract | Single file extraction |
| `routers/batch.py` | /extract/batch, /batches, /batches/{id}/cancel | Batch processing |
| `routers/jobs.py` | GET /jobs, /jobs/{id} | Job status, results |
| `routers/pipelines.py` | /pipelines (CRUD) | YAML config pipelines |
| `routers/schemas.py` | /schemas, /schemas/{id}/versions | Schema CRUD, versioning |
| `routers/webhooks.py` | /webhooks, /deliveries, /test | Event registration, delivery |
| `routers/workspaces.py` | /workspaces (CRUD) | Multi-tenancy |
| `routers/health.py` | GET /health | Liveness check |

### Services Layer (Business Logic)

| Module | Lines | Purpose |
|---|---|---|
| `auth-service.py` | ~120 | User management, token generation, password hashing |
| `workspace-service.py` | ~80 | Workspace CRUD, isolation enforcement |
| `job-service.py` | ~90 | Job CRUD, status transitions, cost tracking |
| `batch-service.py` | ~100 | Batch creation, item tracking, atomic counters |
| `pipeline-service.py` | ~85 | Pipeline CRUD, executor delegation |
| `webhook-service.py` | ~90 | Event registry, HMAC-SHA256 signing |
| `webhook-delivery.py` | ~110 | Async queue, retry backoff [60s, 5m, 30m, 2h] |
| `extraction-worker.py` | ~90 | Job dequeue, provider selection, scoring |
| `router-service.py` | ~65 | Provider selection (local→cloud fallback) |
| `confidence-scorer.py` | ~60 | Field-level confidence aggregation |
| `folder-watcher.py` | ~80 | watchfiles batch aggregation (60s window) |

### Pipeline Engine (Step-Based Execution)

| Module | Lines | Purpose |
|---|---|---|
| `engine/pipeline-executor.py` | ~100 | Sequential step execution, timing, error handling |
| `engine/pipeline-config.py` | ~80 | YAML parser, config validation, DB storage |
| `engine/step-registry.py` | ~50 | Step type registry, factory pattern |
| `engine/step-interface.py` | ~40 | Abstract StepContext, execution protocol |
| `engine/steps/preprocess-step.py` | ~60 | Image preprocessing (rotation, contrast) |
| `engine/steps/extract-step.py` | ~70 | Delegation to extraction providers |
| `engine/steps/validate-step.py` | ~70 | Field validation against schema |
| `engine/steps/export-step.py` | ~60 | Result formatting (JSON, CSV) |

### Schema Engine (Validation, Versioning, Migration)

| Module | Lines | Purpose |
|---|---|---|
| `schema-models.py` | ~70 | Pydantic models (SchemaField, ExtractionSchema, ExtractionResult) |
| `schema-validator.py` | ~90 | Field validation, type checking, occurrence rules |
| `schema-converter.py` | ~70 | CSV/JSON parsing, normalization |
| `schema-store.py` | ~80 | Template persistence, in-memory caching |
| `schema-versioning.py` | ~110 | Semver auto-bump, backward compatibility checks |
| `schema-migration.py` | ~100 | Migration tracking, field diff analysis |
| `csv-prompt-builder.py` | ~60 | CSV→schema conversion for imports |

### Extraction Pipelines (Provider Interface)

| Module | Lines | Purpose |
|---|---|---|
| `base-provider.py` | ~50 | Abstract interface (extract, is_available, get_cost_info) |
| **Cloud:** | | |
| `gemini-provider.py` | ~100 | Gemini API, cost calculation, structured output |
| `mistral-provider.py` | ~100 | Mistral API, cost calculation, structured output |
| `cloud-utils.py` | ~60 | Token counting, prompt optimization |
| **Local:** | | |
| `local-provider.py` | ~90 | VLM orchestrator, multi-backend fallback |
| `ollama-backend.py` | ~70 | Ollama HTTP calls, model management |
| `vllm-backend.py` | ~70 | vLLM HTTP calls, model management |
| `llamacpp-backend.py` | ~70 | llama.cpp HTTP calls |
| `vlm-prompt-builder.py` | ~80 | Schema→VLM prompt conversion, formatting |
| `paddleocr-fallback.py` | ~60 | Text-only extraction fallback |

### Models (Data Layer)

| Module | Purpose |
|---|---|
| `models/base.py` | `Base` ORM declarative, `TimestampMixin` (created_at, updated_at) |
| `models/api-models.py` | Pydantic request/response schemas (ExtractionRequest, JobResponse, etc.) |
| `models/job.py` | Job ORM model, SQLAlchemy mapping |
| `models/batch.py` | Batch ORM model, item tracking |
| `models/pipeline.py` | Pipeline ORM model, YAML config storage |
| `models/webhook.py` | Webhook ORM model, event types, secret |
| `models/workspace.py` | Workspace ORM model, user isolation |
| `models/schema-orm.py` | SchemaORM, SchemaVersionORM models |
| `models/schema-template.py` | SchemaTemplate ORM for template marketplace |

### Frontend (React 19 + TanStack)

| Module | Purpose |
|---|---|
| `routes/__root.tsx` | Root layout (header, sidebar, footer) |
| `routes/index.tsx` | Dashboard page |
| `routes/jobs*.tsx` | Job list, detail pages |
| `routes/schemas.tsx` | Schema management page |
| `routes/batches.tsx` | Batch tracking page |
| `routes/pipelines.tsx` | Pipeline editor page |
| `routes/webhooks.tsx` | Webhook configuration page |
| `components/Header.tsx` | Top navigation, user menu |
| `components/SidebarNav.tsx` | Left sidebar navigation |
| `lib/api-client.ts` | HTTP client with X-API-Key authentication |
| `lib/query-keys.ts` | TanStack Query key factories |
| `lib/types.ts` | TypeScript type definitions |

## Core Abstractions & Patterns

### Provider Interface (Polymorphism)

All extraction backends implement `BaseProvider`:
```python
class BaseProvider(ABC):
    @abstractmethod
    async def extract(image: bytes, schema: ExtractionSchema) -> PipelineResult

    @abstractmethod
    async def is_available() -> bool

    @abstractmethod
    def get_cost_info() -> CostInfo
```

**Implementations:**
- `GeminiProvider` — Cloud VLM + cost tracking
- `MistralProvider` — Cloud VLM + cost tracking
- `LocalProvider` — Multi-backend VLM orchestrator
- `PaddleOCRProvider` — Text-only fallback

### Step Interface (Pipeline Engine)

All pipeline steps implement `PipelineStep`:
```python
class PipelineStep(ABC):
    @abstractmethod
    async def execute(context: StepContext, config: dict) -> StepContext
```

**Implementations:**
- `PreprocessStep` — Image enhancement
- `ExtractStep` — Provider delegation
- `ValidateStep` — Schema validation
- `ExportStep` — Result formatting

### Job & Batch State Machines

**Job states:**
```
pending → processing → completed
                    ↓
                    failed
```

**Batch states (with atomic counter updates):**
```
pending → processing → completed (if all succeeded)
                    ├→ partial (if some failed)
                    └→ failed (if all failed)
```

### Authentication Patterns

**API Key (Stateless):**
- Raw key: `amanuo_pk_{random}`
- Storage: SHA256(raw_key)
- Header: `X-API-Key: amanuo_pk_{value}`
- Validation: Hash & lookup, extract workspace_id

**JWT Token (Session-Based):**
- Algorithm: HS256
- Payload: sub (user_id), workspace_id, exp
- Expiration: 15min (access), 7d (refresh)
- Generation: bcrypt(12 rounds) password hash during registration

### Webhook Delivery with Retry Backoff

**Retry schedule:** [60s, 5m, 30m, 2h]
**Signature:** `X-Amanuo-Signature: sha256={HMAC-SHA256(secret, payload)}`
**Status tracking:** pending → delivered | failed (max 4 attempts)

### Schema Versioning (Semver)

**Auto-bump rules:**
- Removed field or type change → major (breaking)
- New field added → minor (backward-compatible)
- Prompt/config change only → patch

**Backward compatibility check:** Can old jobs use new schema?

### Multi-Tenancy (Soft Deletion)

- All tables have `workspace_id` FK
- Auth middleware injects workspace_id into context
- All queries filtered by workspace_id
- Soft deletion: `is_active` flag (never hard delete)

## Testing Strategy

### Test Coverage (204 tests, 6.5s execution)

| Category | Count | Purpose |
|---|---|---|
| **Unit** | 148 | Validators, services, providers (no I/O, mocked) |
| **Integration** | 0 | (Skipped in CI; require live services) |
| **E2E** | 56 | Full workflows: auth, extraction, batch, pipeline, webhook, workspace |

### Test Markers (pytest)
```python
@pytest.mark.unit        # No I/O, mocked dependencies
@pytest.mark.integration # External services (Ollama, Gemini) — skipped in CI
@pytest.mark.e2e         # Full job/workflow lifecycle
```

### Test Files Breakdown

**Unit Tests (148):**
- `test-auth-middleware.py` — API key, JWT validation
- `test-auth-service.py` — Registration, login, password hashing
- `test-batch-service.py` — Batch creation, status derivation
- `test-confidence-scorer.py` — Field aggregation
- `test-pipeline-config.py` — YAML parsing, validation
- `test-pipeline-executor.py` — Step execution, error handling
- `test-schema-converter.py` — CSV/JSON parsing
- `test-schema-models.py` — Pydantic validation
- `test-schema-validator.py` — Field type checking (15+ scenarios)
- `test-schema-versioning.py` — Semver bump, compatibility
- `test-schema-migration.py` — Version history, field diffs
- `test-router-service.py` — Provider selection logic
- `test-webhook-service.py` — Event registry, HMAC signing
- `test-csv-prompt-builder.py` — CSV→prompt conversion

**E2E Tests (56):**
- `test-auth-flow.py` — Register, login, API key generation
- `test-extract-flow.py` — Single extraction workflow
- `test-batch-flow.py` — Multi-file batch processing
- `test-pipeline-flow.py` — Pipeline creation, execution, steps
- `test-webhook-flow.py` — Event registration, delivery, retry
- `test-schema-crud.py` — Create, read, update, delete schemas
- `test-schema-versioning-flow.py` — Version management, migration
- `test-workspace-isolation.py` — Multi-tenant enforcement

## Data Flow Summary

### Single Extraction
```
Client: POST /extract (X-API-Key, file, schema_id)
    ↓
[auth-middleware] validates key → workspace_id
    ↓
[extract.py] validates schema & file
    ↓
[job-service.py] creates job (status=pending)
    ↓
[extraction-worker.py] dequeues job
    ↓
[router-service.py] selects provider (local/cloud)
    ↓
[selected provider] runs extraction
    ↓
[confidence-scorer.py] aggregates field-level scores
    ↓
[job-service.py] updates result (status=completed)
    ↓
[webhook-service] triggers job.completed event
    ↓
[webhook-delivery] signs & delivers to subscribers
    ↓
Client: GET /jobs/{id} receives full result
```

### Batch Processing
```
Client: POST /extract/batch (X-API-Key, multiple files, pipeline_id)
    ↓
[auth-middleware] workspace_id
    ↓
[batch-service.py] creates batch (status=pending)
    ↓
[folder-watcher] monitors upload dir for batch_window_seconds
    ↓
After window: triggers batch processing
    ↓
For each file: enqueue job (batch_id FK)
    ↓
[extraction-worker] processes jobs, updates atomic counters
    ↓
[batch-service] derives status (completed/partial/failed)
    ↓
[webhook-service] triggers batch.completed | batch.failed
    ↓
Client: GET /batches/{id} sees progress
```

### Pipeline Execution
```
User: POST /pipelines (YAML config)
    ↓
[pipeline-service] parses YAML, validates, stores in DB
    ↓
User: POST /extract (pipeline_id)
    ↓
[pipeline-executor] loads pipeline config from DB
    ↓
For each step in config:
  [step-registry] retrieves step executor
  [step executor] executes with StepContext
  If error: stop pipeline, return error
    ↓
[job-service] stores final result
```

## Performance Profile

| Operation | Latency | Notes |
|---|---|---|
| Local extraction | <3s (p95) | Ollama/vLLM GPU inference |
| Cloud extraction | <10s (p95) | Network + API latency |
| PaddleOCR fallback | <2s | Text-only, CPU-based |
| Schema validation | <50ms | In-memory parsing |
| Job status query | <20ms | SQLite lookup, workspace-filtered |
| Batch status aggregation | <100ms | Atomic counter reads |
| Webhook delivery | <5s (first attempt) | HTTP POST + signature |
| Webhook retry backoff | [60s, 5m, 30m, 2h] | Exponential backoff |

## Backend Dependencies at a Glance

| Category | Packages |
|---|---|
| **Web** | fastapi 0.115+, uvicorn, python-multipart |
| **Database** | sqlalchemy[asyncio], asyncpg, aiosqlite, alembic |
| **Authentication** | PyJWT, bcrypt |
| **Job Queue** | arq 0.27+, redis 5.3+, fakeredis 2.34+ |
| **Real-time** | broadcaster[redis] (WebSocket event pub/sub) |
| **Config** | pyyaml (pipeline configs), pydantic-settings |
| **Concurrency** | watchfiles (batch aggregation) |
| **Cloud APIs** | google-genai, mistralai |
| **Local VLM** | ollama, vllm, llama-cpp-python |
| **OCR** | paddleocr, paddlepaddle |
| **HTTP Client** | httpx (webhooks, providers) |
| **Testing** | pytest, pytest-asyncio |
| **Linting** | ruff |

## Frontend Dependencies

| Category | Packages |
|---|---|
| **Framework** | react 19.0+, react-dom |
| **Router** | @tanstack/react-router |
| **State** | @tanstack/react-query |
| **Styling** | tailwindcss 4.0+, postcss |
| **Build** | vite 7.0+, typescript 5.0+ |
| **UI** | shadcn/ui (optional components) |

## Configuration (Environment Variables)

See `.env.example`:
```
# Database
DATABASE_URL=sqlite+aiosqlite:///./amanuo.db

# Authentication
JWT_SECRET={your-secret}
JWT_EXPIRATION_MINUTES=15
BCRYPT_ROUNDS=12

# Job Queue (ARQ + Redis)
REDIS_URL=redis://localhost:6379
ARQ_BACKGROUND_JOBS_ENABLED=true

# Cloud providers
GEMINI_API_KEY=
MISTRAL_API_KEY=

# Local VLM
VLM_BACKEND=ollama
VLM_MODEL=qwen3-vl:4b
VLM_BASE_URL=http://localhost:11434

# Processing
MAX_WORKERS=3
MAX_FILE_SIZE_MB=20
BATCH_WINDOW_SECONDS=60
DEFAULT_MODE=auto

# Webhooks
WEBHOOK_RETRY_BACKOFF=[60,300,1800,7200]

# WebSocket Events (Redis pub/sub)
EVENT_BROADCASTER_ENABLED=true
EVENT_HEARTBEAT_INTERVAL=30
```

## Summary Statistics

| Metric | Value |
|---|---|
| **Backend Code** | ~3,200 LOC (src/) |
| **Frontend Code** | ~2,300 LOC (frontend/) |
| **Test Code** | ~2,000 LOC (tests/) |
| **Total LOC** | ~7,500 |
| **Database Tables** | 11 |
| **API Endpoints** | 39 |
| **Test Files** | 20+ |
| **Test Count** | 204 (148 unit + 56 E2E) |
| **Test Execution** | 6.5 seconds |
| **Modules** | ~50 |
| **Classes** | ~70 |
| **Async Functions** | ~80 |
| **Test Coverage** | 100% (services), 95%+ (pipelines) |
