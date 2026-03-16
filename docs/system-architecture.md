# System Architecture

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  API Layer (Routers)                       │ │
│  │  /extract  /jobs  /schemas  /health  + Gradio UI         │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │                                        │
│  ┌────────────────────▼─────────────────────────────────────┐ │
│  │              Services Layer                              │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │ │
│  │  │ Job Service  │ │Router Service│ │Confidence Scorer │ │ │
│  │  │(Persistence) │ │ (Selection)  │ │  (Aggregation)   │ │ │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘ │ │
│  │                                                          │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │      Extraction Worker (Async Queue)             │  │ │
│  │  │  • Dequeue job • Select provider • Score result  │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                       │                                      │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │         Extraction Pipelines (Providers)              │  │
│  │                                                       │  │
│  │  ┌──────────────────┐    ┌──────────────────────┐  │  │
│  │  │  Cloud Pipeline  │    │   Local Pipeline     │  │  │
│  │  │                  │    │                      │  │  │
│  │  │ • Gemini API     │    │ • Ollama/vLLM VLM    │  │  │
│  │  │ • Mistral API    │    │ • PaddleOCR Fallback │  │  │
│  │  └──────────────────┘    └──────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │   Data Access Layer                                  │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │  SQLite Database (jobs, schemas, results)    │   │  │
│  │  │  File Storage (uploaded images)              │   │  │
│  │  │  Schema Store (templates + validation)       │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### API Layer (`src/routers/`)
- **extract.py** — POST /extract (file + schema) → job creation, validation
- **jobs.py** — GET /jobs, /jobs/{id}, poll status & retrieve results
- **schemas.py** — CRUD operations for schema templates
- **health.py** — GET /health liveness/readiness check

### Services Layer (`src/services/`)
- **job-service.py** — Job CRUD, persistence, status transitions
- **router-service.py** — Provider selection logic (local vs cloud)
- **extraction-worker.py** — Async worker pool, job dequeue, result scoring
- **confidence-scorer.py** — Aggregate confidence metrics

### Schema Engine (`src/schemas/`)
- **schema-models.py** — Data structures (SchemaField, ExtractionSchema, ExtractionResult)
- **schema-validator.py** — Field validation, type checking
- **schema-converter.py** — JSON/CSV parsing and normalization
- **schema-store.py** — Template persistence and seeding

### Extraction Pipelines (`src/pipelines/`)
- **base-provider.py** — Abstract interface (extract, is_available, get_cost_info)
- **cloud/** — Gemini & Mistral API integrations with cost tracking
- **local/** — Ollama/vLLM/llama.cpp VLM + PaddleOCR fallback

### Models (`src/models/`)
- **api-models.py** — Pydantic request/response schemas (ExtractionRequest, JobResponse, etc.)
- **job.py** — Job ORM model for SQLite persistence

### UI (`src/ui/`)
- **gradio-app.py** — Web interface for interactive extraction
- **ui-helpers.py** — Form builders and UI utilities

## Data Flow: Single Extraction Request

```
1. Client sends multipart form (image + mode + schema) to POST /extract
2. validate_or_raise() checks schema syntax
3. Job created in SQLite with status="pending"
4. Job ID returned (202 Accepted)
5. Client polls GET /jobs/{job_id}

Background Processing:
6. extraction-worker dequeues job
7. router-service selects provider:
   - mode="local_only" → LocalProvider
   - mode="cloud" → CloudProvider (default Gemini)
   - mode="auto" → Try local first, fallback to cloud on low confidence
8. selected_provider.extract(image, schema) → PipelineResult
9. confidence-scorer aggregates field-level confidence scores
10. Job marked complete with result + cost + confidence
11. Client polls and receives full result

Result stored schema:
{
  label_name: str,
  value: str | [str],
  confidence: float (0-1),
  extracted_by: "local" | "cloud"
}
```

## Database Schema

### `jobs` table
```sql
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
  mode TEXT,
  cloud_provider TEXT,
  input_file TEXT,
  schema_fields TEXT,  -- JSON array
  result TEXT,  -- JSON array of ExtractionResult
  confidence REAL,
  cost_input_tokens INTEGER,
  cost_output_tokens INTEGER,
  cost_usd REAL,
  error TEXT,
  created_at TEXT,
  completed_at TEXT
);
```

### `schemas` table
```sql
CREATE TABLE schemas (
  id TEXT PRIMARY KEY,
  name TEXT,
  fields TEXT,  -- JSON array of SchemaField
  is_template BOOLEAN,
  created_at TEXT
);
```

## Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| **Web Framework** | FastAPI 0.115+ | REST API server |
| **Async Runtime** | asyncio | Job queue, concurrent workers |
| **Database** | SQLite + aiosqlite | Lightweight persistence |
| **Cloud VLM** | google-genai (Gemini), mistralai (Mistral) | Structured extraction with cost tracking |
| **Local VLM** | Ollama/vLLM/llama.cpp | Privacy-preserving inference |
| **OCR Fallback** | PaddleOCR | Text extraction when VLM unavailable |
| **Web UI** | Gradio 5.0+ | Interactive extraction interface |
| **Config** | pydantic-settings | Environment-driven settings |

## Module Dependencies

```
main.py
  ├── routers/ (extract, jobs, schemas, health)
  │   ├── services/ (job-service, router-service, extraction-worker)
  │   │   ├── pipelines/ (base, cloud, local)
  │   │   │   └── models/ (api-models, job)
  │   │   └── schemas/ (schema-models, validator, converter, store)
  │   └── schemas/
  ├── database.py (SQLite connection & init)
  ├── config.py (Settings)
  └── ui/gradio-app.py (optional UI mount)
```

## Provider Selection Strategy

### Auto Mode (Default)
1. Check if local VLM is available (health endpoint)
2. If available: run local extraction
3. If confidence >= threshold (0.85): return result
4. Else: run cloud extraction, compare confidence, return best
5. If cloud unavailable: return local result with warning

### Fallback Chain
- Local → Cloud (Gemini) → Cloud (Mistral) → PaddleOCR (text-only)

## Cost Tracking

Each provider returns:
```python
CostInfo(
  input_tokens: int,
  output_tokens: int,
  estimated_cost_usd: float
)
```

Cloud providers calculate estimates based on public pricing; local inference has $0 cost.

## Scalability Considerations

- **Async I/O** — All database and network calls non-blocking
- **Worker Pool** — Configurable concurrent workers (default 3)
- **Job Queue** — In-memory asyncio.Queue (production: upgrade to Redis/Celery)
- **File Storage** — Uploads stored on filesystem (production: use S3)
- **Database** — SQLite suitable for <10K jobs/day; upgrade to PostgreSQL for higher load
