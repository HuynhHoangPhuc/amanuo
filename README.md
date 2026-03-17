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
- Human-in-the-loop review & correction system
- Accuracy tracking dashboard with per-field metrics
- Schema auto-suggest & template marketplace
- WebSocket real-time job/batch updates
- Advanced analytics dashboard (cost tracking, usage, provider comparison)
- RBAC with 5 roles (viewer/member/reviewer/approver/admin)
- Multi-reviewer approval chains (sequential + quorum M-of-N voting)
- ~384 test functions across 34 test files, ~13s execution

## Quick Start

### Prerequisites
- Python 3.11+
- `uv` package manager
- **Redis** — required for job queue (ARQ) and WebSocket broadcaster
- **PostgreSQL 16** — required for production; SQLite used for local dev (see below)
- Local VLM (Ollama, vLLM, or llama.cpp) — optional but recommended
- Cloud API keys (Gemini or Mistral) — optional

### Setup — Local Dev (SQLite, no Docker)

```bash
# Clone & install dependencies
git clone https://github.com/yourusername/amanuo.git
cd amanuo
uv sync

# Copy environment template (SQLite is the default DATABASE_URL)
cp .env.example .env

# Start Redis (required for job queue)
redis-server &

# Start API server (port 8000)
uv run uvicorn src.main:app --reload

# In separate terminal: Start frontend (port 3000)
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

### Setup — Docker Compose

**Production (Multi-stage builds, nginx reverse proxy):**
```bash
# Starts: app (FastAPI:8000), frontend (nginx:80), redis, postgres
docker-compose up

# App auto-creates tables and seeds default workspace/API key on first start
# Frontend accessible at http://localhost
# Backend API at http://localhost/api or http://localhost:8000 directly
```

**Development (Vite hot-reload, uvicorn reload):**
```bash
# Starts: app (hot reload:8000), frontend (Vite dev:3000), redis, postgres
docker-compose -f docker-compose.dev.yml up

# Frontend at http://localhost:3000
# Backend at http://localhost:8000
```

## API Endpoints (65+)

**Authentication & Authorization**

| POST | `/auth/register`, `/login`, `/logout` | User registration, login, logout |
| GET | `/api-keys` | List API keys |
| POST | `/api-keys` | Generate new API key (SHA256 hashed) |
| DELETE | `/api-keys/{id}` | Revoke API key |
| GET | `/users` | List workspace users with roles (admin) |
| GET | `/users/me` | Current user profile + roles |
| POST | `/users/{id}/roles` | Assign role to user (admin) |
| DELETE | `/users/{id}/roles/{role}` | Remove role from user (admin) |

**Workspaces & Extraction**

| GET | `/workspaces` | List workspaces |
| POST | `/extract` | Single file extraction (202 Accepted) |
| POST | `/extract/batch` | Multi-file upload (202 Accepted) |
| GET | `/jobs` | List jobs |
| GET | `/jobs/{id}` | Job status & results |
| GET | `/jobs/{id}/document` | Serve extracted document (path traversal protected) |
| GET | `/batches` | List batches |
| GET | `/batches/{id}` | Batch status & progress |
| POST | `/batches/{id}/cancel` | Cancel batch |

**Schemas & Versioning**

| GET | `/schemas` | List schemas |
| POST | `/schemas` | Create schema |
| GET | `/schemas/{id}` | Get schema details |
| PUT | `/schemas/{id}` | Update schema |
| DELETE | `/schemas/{id}` | Delete schema |
| GET | `/schemas/{id}/versions` | Schema version history |
| POST | `/schemas/suggest` | Auto-suggest schema fields from document |

**Templates & Marketplace**

| GET | `/templates` | List curated templates (4 built-in) |
| POST | `/templates/{id}/import` | Import template as new schema |

**Reviews & Accuracy**

| GET | `/reviews` | List reviews in workspace |
| POST | `/reviews/{job_id}` | Submit review corrections |
| GET | `/reviews/{job_id}` | Get review details |
| GET | `/accuracy/{schema_id}` | Get accuracy metrics per schema |
| POST | `/accuracy/{schema_id}/compute` | Compute accuracy metrics |

**Approval Workflows**

| GET | `/approval-policies` | List approval policies |
| POST | `/approval-policies` | Create policy — chain or quorum (admin) |
| GET | `/approval-policies/{id}` | Get policy detail |
| PUT | `/approval-policies/{id}` | Update policy (admin) |
| DELETE | `/approval-policies/{id}` | Soft-delete policy (admin) |
| GET | `/review-queue` | My pending review assignments (reviewer+) |
| GET | `/jobs/{id}/review-status` | Current round, assignments, conflicts |
| POST | `/jobs/{id}/assign` | Assign reviewers to current round (admin) |
| POST | `/jobs/{id}/review` | Submit review for assignment (reviewer+) |
| GET | `/jobs/{id}/audit-log` | Review action history (admin) |

**Pipelines & Webhooks**

| GET | `/pipelines` | List pipelines |
| POST | `/pipelines` | Create pipeline (YAML config) |
| PUT | `/pipelines/{id}` | Update pipeline |
| DELETE | `/pipelines/{id}` | Delete pipeline |
| GET | `/webhooks` | List webhook endpoints |
| POST | `/webhooks` | Register webhook |
| DELETE | `/webhooks/{id}` | Delete webhook |
| POST | `/webhooks/{id}/test` | Send test event |
| GET | `/webhooks/{id}/deliveries` | View delivery log with retry status |

**Analytics**

| GET | `/analytics/overview` | Aggregated totals (jobs, cost, confidence, schemas) — `?period=7d\|30d\|90d` |
| GET | `/analytics/usage` | Daily job volume by status |
| GET | `/analytics/costs` | Daily cost breakdown by provider |
| GET | `/analytics/providers` | Per-provider comparison (jobs, success rate, cost) |
| POST | `/analytics/refresh` | Force-refresh PostgreSQL materialized views |

**System & Real-Time**

| GET | `/health` | Liveness + provider availability |
| GET | `/ws/events` | WebSocket stream (real-time job/batch updates, 30s heartbeat) |

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
  ├── database.py       # SQLite/PostgreSQL schema + initialization
  └── main.py           # FastAPI app entry + lifespan
frontend/               # TanStack React app (React 19, Tailwind CSS v4, Recharts)
tests/                  # 384 unit & E2E tests (~13s)
docs/                   # Architecture, code standards, API docs
samples/                # Example schemas (invoice, ID card, license)
```

## Configuration

Set environment variables in `.env`:

```env
# Database — SQLite (local dev) or PostgreSQL (docker/production)
DATABASE_URL=sqlite+aiosqlite:///./amanuo.db
# DATABASE_URL=postgresql+asyncpg://amanuo:amanuo@localhost:5432/amanuo

# Redis (required for job queue + WebSocket broadcaster)
REDIS_URL=redis://localhost:6379/0

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

## Docker Architecture

**Production (`docker-compose.yml`):**
- **app** — FastAPI (uvicorn, port 8000, multi-stage Python build)
- **frontend** — nginx (port 80, serves built React SPA from dist/, proxies /api/* to app:8000, WebSocket upgrade support)
- **redis** — Redis 7-alpine (for job queue + event broadcast)
- **postgres** — PostgreSQL 16-alpine (persistent data)

**Development (`docker-compose.dev.yml`):**
- **app** — FastAPI with `--reload` for code changes
- **frontend** — Node.js 22-alpine running Vite dev server (http://app:8000 as VITE_API_URL)
- **redis**, **postgres** — same as production

**Environment Variables (docker-compose):**
```env
DATABASE_URL=postgresql+asyncpg://amanuo:amanuo@postgres:5432/amanuo
REDIS_URL=redis://redis:6379/0
BROADCASTER_URL=redis://redis:6379/0
```

**Frontend Build:**
- Multi-stage: `node:22-alpine` build → `nginx:alpine` serve
- nginx config: API routes (/api/*, /schemas/*, /jobs/*, etc.) proxied to backend
- SPA fallback: `try_files $uri $uri/ /index.html`
- WebSocket: `proxy_http_version 1.1`, `Upgrade` header forwarding

## Running Tests

```bash
# All tests (~384 test functions, ~13s total)
uv run pytest

# Unit tests only (fastest)
uv run pytest -m unit

# Integration tests (requires Ollama/cloud APIs, skipped in CI)
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

**Completed Phases (1–8)**
- [x] Phase 1: Core OCR extraction + multi-workspace platform
- [x] Phase 2: SQLAlchemy ORM migration + Redis/ARQ job queue
- [x] Phase 3: WebSocket real-time events + template marketplace
- [x] Phase 4: Human-in-the-loop review & correction UI
- [x] Phase 5: Accuracy tracking + prompt hint generation
- [x] Phase 6: Full TanStack React frontend + schema auto-suggest
- [x] Phase 7: Advanced analytics — cost tracking, usage dashboards, provider comparison (PostgreSQL materialized views + Recharts)
- [x] Phase 8: Multi-reviewer approval chains — RBAC, sequential chain + quorum workflows, conflict escalation, policy management UI

**Future Work**
- [ ] Fine-tuning pipeline for custom models
- [ ] Document classification pre-processor
- [ ] OAuth / social authentication

## License

See LICENSE file.

## Support

For issues, questions, or contributions, open a GitHub issue or contact the team.
