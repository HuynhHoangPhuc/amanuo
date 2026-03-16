# Codebase Summary

## Directory Structure

```
amanuo/
├── src/                          # Main application code (1,373 LOC)
│   ├── __init__.py              # Package marker
│   ├── main.py                  # FastAPI app definition, lifespan setup
│   ├── config.py                # Environment settings (pydantic-settings)
│   ├── database.py              # SQLite connection & schema initialization
│   ├── models/
│   │   ├── api-models.py        # Pydantic request/response schemas
│   │   └── job.py               # Job ORM model
│   ├── routers/
│   │   ├── extract.py           # POST /extract endpoint
│   │   ├── jobs.py              # GET /jobs, /jobs/{id} endpoints
│   │   ├── schemas.py           # Schema CRUD endpoints
│   │   └── health.py            # GET /health liveness check
│   ├── services/
│   │   ├── extraction-worker.py # Async job queue & worker pool
│   │   ├── job-service.py       # Job persistence & status management
│   │   ├── router-service.py    # Provider selection logic
│   │   └── confidence-scorer.py # Field-level confidence aggregation
│   ├── pipelines/
│   │   ├── base-provider.py     # Abstract provider interface
│   │   ├── cloud/
│   │   │   ├── gemini-provider.py    # Gemini API integration
│   │   │   ├── mistral-provider.py   # Mistral API integration
│   │   │   └── cloud-utils.py        # Cloud provider utilities
│   │   └── local/
│   │       ├── local-provider.py     # Local VLM orchestrator
│   │       ├── ollama-backend.py     # Ollama VLM backend
│   │       ├── vllm-backend.py       # vLLM backend
│   │       ├── llamacpp-backend.py   # llama.cpp backend
│   │       ├── vlm-prompt-builder.py # Prompt construction
│   │       └── paddleocr-fallback.py # PaddleOCR text extraction
│   ├── schemas/
│   │   ├── schema-models.py     # Data classes (SchemaField, ExtractionSchema)
│   │   ├── schema-validator.py  # Schema validation logic
│   │   ├── schema-converter.py  # CSV/JSON parser
│   │   └── schema-store.py      # Template persistence & seeding
│   └── ui/
│       ├── gradio-app.py        # Gradio web interface
│       └── ui-helpers.py        # UI form builders & utilities
├── tests/                        # Test suite (14 files, 67+ tests)
│   ├── test-*.py                # Unit tests (no I/O)
│   ├── integration/             # Integration tests (external services)
│   └── e2e/                     # End-to-end workflow tests
├── samples/                      # Sample images & documents for testing
├── data/
│   ├── uploads/                 # Uploaded files (created at runtime)
│   └── amanuo.db                # SQLite database
├── .env.example                 # Configuration template
├── pyproject.toml               # Project metadata & dependencies
├── Dockerfile                   # Container image definition
├── docker-compose.yml           # Local dev environment (Ollama, Gemini, etc.)
└── README.md                    # Project overview
```

## Key Files & Responsibilities

### Entry Point & Configuration

| File | Lines | Purpose |
|---|---|---|
| `main.py` | 72 | FastAPI app setup, router mounting, lifespan management |
| `config.py` | 37 | Environment-driven settings (API keys, VLM config) |
| `database.py` | ~50 | SQLite initialization, connection pooling |

### API Layer (45 lines per router)

| Router | Endpoints | Purpose |
|---|---|---|
| `routers/extract.py` | POST /extract | Job submission with schema validation |
| `routers/jobs.py` | GET /jobs, /jobs/{id} | Job status polling & result retrieval |
| `routers/schemas.py` | GET/POST/PUT/DELETE /schemas | Schema template CRUD |
| `routers/health.py` | GET /health | Liveness check + provider availability |

### Services Layer (Core Business Logic)

| Module | Lines | Purpose |
|---|---|---|
| `extraction-worker.py` | 80 | Async job dequeue, extraction delegation, result storage |
| `job-service.py` | 60 | Job CRUD operations, status transitions, SQLite persistence |
| `router-service.py` | 55 | Provider selection (local → cloud fallback) |
| `confidence-scorer.py` | 40 | Field-level confidence aggregation & ranking |

### Schema Engine (Validation & Persistence)

| Module | Lines | Purpose |
|---|---|---|
| `schema-models.py` | 45 | Pydantic models for SchemaField, ExtractionSchema, ExtractionResult |
| `schema-validator.py` | 70 | Type checking, occurrence validation, prompt building |
| `schema-converter.py` | 50 | CSV/JSON parsing, schema normalization |
| `schema-store.py` | 60 | Template seeding, persistence, in-memory caching |

### Extraction Pipelines (Abstract → Concrete)

| Module | Lines | Purpose |
|---|---|---|
| `base-provider.py` | 45 | Abstract interface (extract, is_available, get_cost_info) |
| **Cloud:** | | |
| `gemini-provider.py` | 85 | Gemini API calls, cost calculation, JSON parsing |
| `mistral-provider.py` | 85 | Mistral API calls, cost calculation, JSON parsing |
| `cloud-utils.py` | 40 | Token counting, prompt optimization |
| **Local:** | | |
| `local-provider.py` | 70 | VLM orchestration, multi-backend fallback |
| `ollama-backend.py` | 50 | Ollama API calls via httpx |
| `vllm-backend.py` | 50 | vLLM API calls via httpx |
| `llamacpp-backend.py` | 50 | llama.cpp API calls via httpx |
| `vlm-prompt-builder.py` | 60 | Schema → VLM prompt conversion |
| `paddleocr-fallback.py` | 45 | PaddleOCR text extraction (no structured data) |

### Data Models

| Module | Purpose |
|---|---|
| `models/api-models.py` | Pydantic schemas for HTTP requests/responses |
| `models/job.py` | Job ORM model for SQLite mapping |

### UI

| Module | Purpose |
|---|---|
| `ui/gradio-app.py` | Web interface (file upload, schema selection, result display) |
| `ui/ui-helpers.py` | Form builders, file preview utilities |

## Core Abstractions

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
- `PaddleOCRProvider` — Text-only fallback (no structured extraction)

### Job Model (Async Persistence)

Jobs flow through states:
```
pending → processing → completed
                    ↓
                    failed
```

Each state transition persists to SQLite; clients poll `/jobs/{id}` for status.

### Schema Validation (Type Safety)

Two-layer validation:
1. **Schema Syntax** — Required fields, valid types, occurrence rules
2. **Extraction Output** — Value type matches schema type (e.g., number must be numeric)

## Testing Strategy

### Test Coverage (67+ tests)

| Category | Count | Purpose |
|---|---|---|
| **Unit** | 45+ | Validators, converters, scorers (no I/O) |
| **Integration** | 15+ | Provider APIs (Ollama, Gemini, Mistral) |
| **E2E** | 7+ | Full workflow (upload → extract → retrieve) |

### Test Markers (pytest)
```python
@pytest.mark.unit        # No I/O, mocked deps
@pytest.mark.integration # External services
@pytest.mark.e2e         # Full job lifecycle
```

### Key Test Files
- `test-schema-validator.py` — 15+ validation scenarios
- `test-extraction-worker.py` — Job processing, fallback
- `test-gemini-provider.py` — Cloud API mocking
- `test-local-provider.py` — Multi-backend fallback
- `test-e2e-extraction.py` — Full workflow

## Data Flow Summary

```
Client Request
    ↓
[extract.py] validates schema & file
    ↓
[job-service.py] creates job (pending)
    ↓
[extraction-worker.py] dequeues job
    ↓
[router-service.py] selects provider (local/cloud)
    ↓
[selected provider] runs extraction
    ↓
[confidence-scorer.py] aggregates confidence
    ↓
[job-service.py] updates result (completed)
    ↓
Client polls /jobs/{id} to retrieve result
```

## Performance Profile

| Operation | Latency | Notes |
|---|---|---|
| Local extraction | <3s | Ollama/vLLM inference on GPU |
| Cloud extraction | <10s | Network + API latency |
| PaddleOCR fallback | <2s | Text-only, CPU-based |
| Schema validation | <50ms | In-memory parsing |
| Job status query | <20ms | SQLite lookup |

## Dependencies at a Glance

| Category | Packages |
|---|---|
| **Web** | fastapi, uvicorn, python-multipart |
| **Database** | aiosqlite |
| **Cloud APIs** | google-genai, mistralai |
| **Local VLM** | ollama, vllm, llama-cpp-python |
| **OCR** | paddleocr, paddlepaddle |
| **UI** | gradio |
| **HTTP Client** | httpx |
| **Config** | pydantic-settings |
| **Testing** | pytest, pytest-asyncio |
| **Linting** | ruff |

## Configuration (Environment Variables)

See `.env.example`:
```
GEMINI_API_KEY=          # For Gemini cloud provider
MISTRAL_API_KEY=         # For Mistral cloud provider
VLM_BACKEND=ollama       # Local VLM: ollama | vllm | llamacpp
VLM_MODEL=qwen3-vl:4b    # Model to load
VLM_BASE_URL=http://localhost:11434  # VLM server URL
DATABASE_URL=sqlite+aiosqlite:///./amanuo.db
DEFAULT_MODE=auto        # local_only | cloud | auto
MAX_WORKERS=3            # Concurrent extraction workers
MAX_FILE_SIZE_MB=20      # Upload limit
```

## Summary Statistics

| Metric | Value |
|---|---|
| **Total Lines of Code** | 1,373 |
| **Avg File Size** | 35 lines |
| **Test Files** | 14 |
| **Test Count** | 67+ |
| **Modules** | 24 |
| **Classes** | ~30 |
| **Async Functions** | 25+ |
| **Test Coverage** | 100% (services), 95%+ (pipelines) |
