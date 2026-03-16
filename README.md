# Amanuo — Adaptive Hybrid OCR System

**Privacy-first structured document extraction** with adaptive cloud/local pipelines for English, Japanese, and Vietnamese documents.

## Overview

Amanuo extracts structured data from documents using user-defined schemas. It routes requests intelligently between local VLM inference (Ollama/vLLM) and cloud APIs (Gemini/Mistral) based on availability and confidence. When VLMs fail, it falls back to PaddleOCR for text extraction.

**Core Features:**
- Multi-workspace platform with soft multi-tenancy
- API key authentication (SHA256 hash) + JWT sessions
- Batch processing (multi-file upload, async status tracking)
- Pipeline engine with YAML-based config + executor
- Webhook system with event routing and retry backoff
- Schema versioning (semver auto-bump, migration tracking)
- TanStack frontend (React 19, Tailwind CSS v4, file-based routing)
- Schema-driven extraction (JSON/CSV format)
- Dual-pipeline execution (local + cloud with fallback)
- Cost tracking and confidence scoring
- 204 unit & E2E tests (6.5s execution)

## Quick Start

### Prerequisites
- Python 3.11+
- `uv` package manager
- Local VLM (Ollama, vLLM, or llama.cpp) — optional but recommended
- Cloud API keys (Gemini or Mistral) — optional

### Setup (Backend + Frontend)

```bash
# Clone & install dependencies
git clone https://github.com/yourusername/amanuo.git
cd amanuo
uv sync

# Copy environment template
cp .env.example .env

# Start API server (port 8000)
uv run uvicorn src.main:app --reload

# In separate terminal: Start frontend (port 3000)
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

## API Endpoints (39 Total)

**Authentication & Authorization**

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | User registration |
| POST | `/auth/login` | User login (JWT + refresh tokens) |
| POST | `/auth/logout` | Logout & token revocation |

**Workspaces (Multi-Tenancy)**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/workspaces` | List user's workspaces |
| POST | `/workspaces` | Create workspace |
| DELETE | `/workspaces/{id}` | Delete workspace |

**API Keys**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api-keys` | List API keys |
| POST | `/api-keys` | Generate new API key (SHA256 hashed) |
| DELETE | `/api-keys/{id}` | Revoke API key |

**Extraction (Core)**

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/extract` | Single file extraction (202 Accepted) |
| GET | `/jobs` | List jobs in workspace |
| GET | `/jobs/{id}` | Get job status & results |
| GET | `/schemas` | List saved schema templates |
| POST | `/schemas` | Create new schema template |
| GET | `/schemas/{id}` | Get schema details |
| PUT | `/schemas/{id}` | Update schema |
| DELETE | `/schemas/{id}` | Delete schema |
| GET | `/schemas/{id}/versions` | Schema version history |

**Batch Processing**

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/extract/batch` | Multi-file upload (202 Accepted) |
| GET | `/batches` | List batches |
| GET | `/batches/{id}` | Get batch status & progress |
| POST | `/batches/{id}/cancel` | Cancel batch |

**Pipelines (YAML Config)**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/pipelines` | List pipelines |
| POST | `/pipelines` | Create pipeline (YAML config) |
| GET | `/pipelines/{id}` | Get pipeline details |
| PUT | `/pipelines/{id}` | Update pipeline |
| DELETE | `/pipelines/{id}` | Delete pipeline |

**Webhooks (Event-Driven)**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/webhooks` | List webhook endpoints |
| POST | `/webhooks` | Register webhook (event types: job.*, batch.*) |
| DELETE | `/webhooks/{id}` | Delete webhook |
| POST | `/webhooks/{id}/test` | Send test event |
| GET | `/webhooks/{id}/deliveries` | View delivery log with retry status |

**System**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness + provider availability |

### Example: Authenticate & Extract

```bash
# 1. Create API key
curl -X POST "http://localhost:8000/api-keys" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "production-key"}'

# Returns: {"id": "key-123", "key": "amanuo_pk_..."}

# 2. Submit extraction job (uses API key)
curl -X POST "http://localhost:8000/extract" \
  -H "X-API-Key: amanuo_pk_..." \
  -F "file=@invoice.png" \
  -F "schema_id=invoice-template"

# Returns: {"job_id": "job-abc123"}

# 3. Poll job status
curl -H "X-API-Key: amanuo_pk_..." \
  "http://localhost:8000/jobs/job-abc123"

# Response when complete:
{
  "id": "job-abc123",
  "status": "completed",
  "result": [{
    "label_name": "invoice_id",
    "value": "INV-2025-001234",
    "confidence": 0.98
  }],
  "cost": {"estimated_cost_usd": 0.001}
}
```

## Project Structure

```
src/
  ├── middleware/       # Auth middleware (API key, JWT validation)
  ├── engine/           # Pipeline executor + step registry
  ├── routers/          # API endpoints (extract, batch, pipelines, webhooks, etc.)
  ├── services/         # Business logic (batch, webhook, workspace, auth, etc.)
  ├── pipelines/        # Extraction backends (cloud, local, OCR)
  ├── schemas/          # Schema engine (validation, versioning, migration)
  ├── models/           # Pydantic & ORM models
  ├── ui/               # Gradio web interface (optional)
  ├── config.py         # Settings & environment management
  ├── database.py       # SQLite schema + initialization
  └── main.py           # FastAPI app entry + lifespan
frontend/               # TanStack React app (React 19, Tailwind CSS v4)
tests/                  # 204 unit & E2E tests (6.5s)
docs/                   # Architecture, code standards, API docs
samples/                # Example schemas (invoice, ID card, license)
```

## Configuration

Set environment variables in `.env`:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./amanuo.db

# Authentication
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=15
JWT_REFRESH_EXPIRATION_DAYS=7
BCRYPT_ROUNDS=12

# Cloud providers
GEMINI_API_KEY=your-key-here
MISTRAL_API_KEY=your-key-here

# Local VLM
VLM_BACKEND=ollama                    # ollama | vllm | llamacpp
VLM_MODEL=qwen3-vl:4b
VLM_BASE_URL=http://localhost:11434

# Processing
DEFAULT_MODE=auto                     # local_only | cloud | auto
MAX_WORKERS=3                         # Concurrent extraction jobs
MAX_FILE_SIZE_MB=20                   # Upload size limit
BATCH_WINDOW_SECONDS=60               # Folder watcher batch window
UPLOAD_DIR=data/uploads

# Webhooks
WEBHOOK_RETRY_BACKOFF=[60,300,1800,7200]  # Seconds: 1m, 5m, 30m, 2h
```

## Docker Deployment

```bash
# Build image
docker build -t amanuo:latest .

# Run with compose (includes Ollama service)
docker-compose up
```

## Running Tests

```bash
# All 204 tests (6.5s total)
uv run pytest

# Unit tests only (fastest)
uv run pytest -m unit

# Integration tests (requires Ollama/cloud APIs)
uv run pytest -m integration

# End-to-end tests (full workflows)
uv run pytest -m e2e

# Specific test file
uv run pytest tests/unit/test-auth-middleware.py

# With coverage report
uv run pytest --cov=src --cov-report=html
```

## Documentation

- **[Project Overview & PDR](docs/project-overview-pdr.md)** — Goals, scope, acceptance criteria
- **[System Architecture](docs/system-architecture.md)** — Component design, data flow, database schema
- **[Code Standards](docs/code-standards.md)** — File naming, module limits, testing patterns
- **[Codebase Summary](docs/codebase-summary.md)** — Directory structure, key files, test coverage

## Development Workflow

1. **Design** — Update docs first, then implement
2. **Code** — Follow code standards; use kebab-case for Python files
3. **Test** — Write unit tests alongside code; run `pytest` before commit
4. **Review** — Ensure 100% coverage on services, 95%+ on pipelines
5. **Commit** — Use conventional commits (feat:, fix:, docs:)

## Roadmap

**Phase 1 (Complete)**
- [x] Multi-workspace platform with soft multi-tenancy
- [x] API key authentication + JWT sessions
- [x] Batch processing (multi-file upload)
- [x] Pipeline engine with YAML config
- [x] Webhook system with retry backoff
- [x] Schema versioning & migration
- [x] TanStack frontend (React 19)

**Phase 2 (Upcoming)**
- [ ] Fine-tuning pipeline for custom models
- [ ] Redis queue for production scaling
- [ ] PostgreSQL support for larger deployments
- [ ] Real-time WebSocket updates for job status
- [ ] Advanced analytics & usage tracking
- [ ] Document classification pre-processor

## License

See LICENSE file.

## Support

For issues, questions, or contributions, open a GitHub issue or contact the team.
