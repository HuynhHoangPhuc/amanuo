# Amanuo OCR System — Project Overview & PDR

## Project Vision

Amanuo is an adaptive hybrid OCR system for **structured document extraction** across English, Japanese, and Vietnamese documents. It prioritizes **privacy-first processing** with local-first fallback to cost-effective cloud providers.

## Goals

1. **Accuracy** — Multilingual structured extraction with high confidence scoring
2. **Privacy** — Local processing when possible; cloud offloading only when beneficial
3. **Cost-Efficiency** — Minimize token usage via schema-driven extraction; support multiple cloud providers
4. **Developer Experience** — Clear REST API, batch job processing, persistent schema templates

## Scope (Phases 1, 2, 3, 6 Completed)

### Completed Features
**Multi-Workspace Platform**
- Soft multi-tenancy via workspace_id FK in all tables
- User registration/login with bcrypt (12 rounds) + JWT (HS256, 15min access / 7d refresh)
- API key authentication (SHA256 hash, stateless, X-API-Key header)
- Workspace CRUD with default workspace protection

**Batch Processing**
- Multi-file upload via POST /extract/batch (202 Accepted)
- Atomic counter updates, status derivation (pending→processing→completed/partial/failed)
- Batch cancellation, folder watcher (watchfiles-based, configurable batch window)

**Pipeline Engine**
- YAML-based configuration stored in database
- StepContext dataclass + PipelineStep ABC interface
- Sequential executor with per-step timing & error handling
- Step registry: preprocess, extract, validate, export
- Default pipeline emulates MVP behavior

**Webhook System**
- Event registration (job.completed, job.failed, batch.completed, batch.failed)
- HMAC-SHA256 payload signing
- Async delivery queue with retry backoff: [60s, 5m, 30m, 2h]
- Test delivery endpoint, delivery log viewer

**Schema Versioning**
- Semver auto-bump: breaking changes → major, new fields → minor, prompt changes → patch
- Backward compatibility checks, field diff analysis
- Version history endpoint, schema migration tracking

**SQLAlchemy ORM Migration (Phase 1)**
- `src/database.py` refactored: `create_engine_from_url()`, `get_session()`, async sessions
- `src/models/base.py` created: `Base`, `TimestampMixin`
- All services rewritten to use SQLAlchemy AsyncSession (no raw SQL)
- Dependencies: sqlalchemy[asyncio], asyncpg, alembic

**Redis + ARQ Job Queue (Phase 2)**
- `src/services/redis-pool.py` — ARQ Redis pool singleton
- `src/services/arq-worker-settings.py` — WorkerSettings, job handlers
- `src/services/extraction-worker.py` refactored — ARQ job enqueue
- Standalone worker: `uv run arq src.services.arq-worker-settings.WorkerSettings`
- docker-compose.yml updated: Redis (7-alpine, AOF) + PostgreSQL services

**WebSocket Event Stream (Phase 3)**
- `src/services/event-broadcaster.py` — Redis pub/sub singleton
- `src/routers/websocket-events.py` — `GET /ws/events?api_key=X`, 30s heartbeat
- job.completed/job.failed/batch.progress events published
- Frontend: `websocket-client.ts`, `use-realtime-events.ts` (TanStack Query cache invalidation)

**Schema Auto-Suggest & Template Marketplace (Phase 6)**
- `src/models/schema-template.py` — SchemaTemplate ORM
- `src/services/schema-suggest-service.py` — VLM field suggestion, graceful degradation
- `src/services/template-service.py` — template CRUD + seed
- `src/routers/templates.py` — GET /templates, POST /templates/{id}/import, POST /schemas/suggest
- `src/data/curated-templates.yaml` — 4 curated templates (Invoice EN/JP, Receipt, ID Card)
- Frontend: templates marketplace, suggested-fields-editor

**Frontend (TanStack)**
- React 19 + TanStack Router (file-based) + TanStack Query + Tailwind CSS v4
- Pages: Dashboard, Schemas, Jobs, Pipelines, Batches, Webhooks, Templates, Settings
- API client with X-API-Key auth, toast notifications, WebSocket event handling
- Build: 1831+ modules, 17+ chunks, 0 errors

**Testing**
- 243 tests (increase from 204), 148 unit + 56 E2E + 39 new (ARQ, WebSocket, templates)
- Execution time: ~6.5s
- Coverage: auth, batch, pipeline, webhook, workspace, schema versioning, job queue, events

### Out-of-Scope (Phase 4+)
- Fine-tuning or model training
- OAuth / social authentication
- Advanced analytics & cost breakdowns per workspace
- HITL (human-in-the-loop) correction workflows

## Functional Requirements

| Requirement | Detail |
|---|---|
| **Authentication** | User registration/login (JWT), API key generation (SHA256 hash), X-API-Key header validation |
| **Multi-Tenancy** | Workspace isolation, all queries filtered by workspace_id, soft deletion for data |
| **Batch Processing** | Multi-file upload, atomic status tracking, batch cancellation, folder watching |
| **Pipelines** | YAML config parsing, step-based executor, default pipeline for MVP behavior |
| **Webhooks** | Event subscription (job.*, batch.*), HMAC-SHA256 signing, retry backoff [60s, 5m, 30m, 2h] |
| **Schema Versioning** | Auto-bump semver, backward compatibility checks, field diff analysis, migration tracking |
| **Extraction** | Extract fields per schema with value deduplication & confidence metrics |
| **Job Tracking** | Create jobs (202 Accepted), poll status, retrieve results with cost tracking |
| **Cloud Integration** | Support Gemini & Mistral with cost estimation |
| **Local Inference** | Fallback to PaddleOCR if VLM unavailable |
| **Frontend** | React UI with TanStack Router/Query, schema management, job monitoring, batch operations |

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Latency** | Local: <3s; Cloud: <10s (p95); Webhook delivery: <5s (first attempt) |
| **Throughput** | 3 concurrent workers, batch window 60s, webhook async queue |
| **Accuracy** | >90% confidence on structured fields |
| **Languages** | English, Japanese, Vietnamese |
| **Uptime** | Graceful degradation on cloud failures, webhook retry backoff |
| **Code Quality** | <200 LOC per file; 100% test coverage on services; 95%+ on pipelines |
| **Test Coverage** | 204 tests, 6.5s execution, all critical paths covered |
| **API Response** | 202 Accepted for async operations (batch, extraction) |
| **Database** | SQLite for dev/small deployments, PostgreSQL-compatible schema |
| **Security** | SHA256 API key hash, JWT HS256, HMAC-SHA256 webhook signing, bcrypt 12 rounds |

## Technical Architecture

### Core Components
1. **Auth Middleware** — API key (SHA256) & JWT (HS256) validation, workspace scoping
2. **Workspace Service** — Multi-tenant isolation, default workspace management
3. **Pipeline Engine** — YAML config parser, step executor, registry pattern
4. **Batch Service** — Multi-file upload, atomic counters, status derivation
5. **Webhook Service** — Event registry, HMAC-SHA256 signing, async delivery queue
6. **Schema Engine** — Versioning, migration, backward compatibility checks
7. **Extraction Pipelines** — Base provider interface + cloud/local implementations
8. **Job Service** — Async queue, status tracking, cost aggregation
9. **Frontend (React)** — TanStack Router, Query caching, API integration

### Data Flow
```
Auth (API Key/JWT) → Workspace Scoping →
  Single: Enqueue Job → Extract → Score → Store
  Batch: Upload Files → Create Batch → Enqueue → Process Each → Aggregate Status
  Webhooks: Trigger Event → Sign HMAC → Async Deliver → Retry on Failure
  Pipelines: Parse YAML → Step Registry → Execute Sequential → Store Result
```

## Acceptance Criteria

- [x] All 204 tests passing (148 unit + 56 E2E), 6.5s execution
- [x] REST API (39 endpoints) functional with documented requests/responses
- [x] Authentication: API key + JWT working, workspace isolation enforced
- [x] Batch processing: multi-file upload, atomic status tracking, cancellation
- [x] Pipeline engine: YAML parsing, executor, step registry, default pipeline
- [x] Webhook system: event subscription, HMAC signing, retry backoff
- [x] Schema versioning: semver auto-bump, compatibility checks, migration tracking
- [x] Frontend: TanStack React app, all major workflows (jobs, batches, pipelines, webhooks)
- [x] Cost tracking accurate for cloud providers
- [x] Local fallback works when VLM unavailable
- [x] Documentation complete (API, architecture, code standards, codebase summary)

## Success Metrics

| Metric | Target | Status |
|---|---|---|
| **Field Accuracy** | >90% confidence on test documents | Pass |
| **Latency (Cloud)** | P95 <10s | Pass |
| **Latency (Local)** | P95 <3s | Pass |
| **Test Coverage** | 100% services, 95%+ pipelines | Pass |
| **API Endpoints** | 39 documented routes | Complete |
| **Database Tables** | 11 (up from 3) | Complete |
| **Test Execution** | <7s total | 6.5s |
| **Workspace Isolation** | All queries filtered by workspace_id | Enforced |
