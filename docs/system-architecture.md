# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Deployment Layer                       │
├──────────────────────┬──────────────────────┬─────────────────┬────────────┤
│  Frontend (nginx)    │  Backend (FastAPI)   │  Redis (ARQ)    │  PostgreSQL │
│  Port 80 (prod)      │  Port 8000           │  Port 6379      │  Port 5432 │
│  Port 3000 (dev)     │                      │                 │            │
└──────────────────────┴──────────────────────┴─────────────────┴────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend + React Frontend                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Frontend (React 19, TanStack Router/Query, Tailwind CSS v4)                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Pages: Dashboard │ Schemas │ Jobs │ Batches │ Pipelines │ Webhooks   │ │
│  │  Components: Headers, Sidebars, Forms, Result Viewers, Modals        │ │
│  │  API Client: X-API-Key auth, TanStack Query caching                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                            ↓ HTTP/REST (port 3000→8000)                     │
│                                                                              │
│  API Layer (50+ Endpoints)                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Auth: /auth/register /auth/login /auth/logout                        │ │
│  │  Keys: /api-keys (CRUD, SHA256 hash)                                  │ │
│  │  Workspaces: /workspaces (CRUD, soft multi-tenancy)                  │ │
│  │  Extraction: /extract /jobs /jobs/{id}/document /schemas/*           │ │
│  │  Batch: /extract/batch /batches /batches/{id}/cancel                 │ │
│  │  Pipelines: /pipelines (YAML CRUD)                                   │ │
│  │  Reviews: /reviews/{job_id}, GET /reviews (HITL corrections)         │ │
│  │  Accuracy: /accuracy/{schema_id} (metrics + compute)                 │ │
│  │  Analytics: /analytics/usage /costs /providers /overview; POST /refresh │ │
│  │  Templates: /templates /templates/{id}/import /schemas/suggest       │ │
│  │  Users: /users, /users/me, /users/{id}/roles (RBAC management)       │ │
│  │  Approval: /approval-policies/* (CRUD), /review-queue, /review-*     │ │
│  │  WebSocket: /ws/events (Redis pub/sub, 30s heartbeat)                │ │
│  │  Webhooks: /webhooks /webhooks/{id}/deliveries (retry backoff)       │ │
│  │  Health: /health (liveness + provider availability)                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                  ↓                                           │
│  Middleware Layer                                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Auth Middleware: Validate X-API-Key (SHA256) → workspace scoping     │ │
│  │  JWT Middleware: Validate HS256 token (HS256, 15min / 7d refresh)     │ │
│  │  Error Handler: Structured error responses, exception logging         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                  ↓                                           │
│  Services Layer (Business Logic)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Auth Service: Register, login, JWT/API key generation, validation  │   │
│  │  Workspace Service: CRUD, isolation, default workspace mgmt         │   │
│  │  Job Service: Status tracking, result persistence, cost agg         │   │
│  │  Batch Service: Multi-file upload, status derivation, cancellation  │   │
│  │  Pipeline Service: YAML parsing, executor delegation, step registry │   │
│  │  Webhook Service: Event registry, HMAC-SHA256 signing, delivery     │   │
│  │  Webhook Delivery: Async queue, retry backoff [60s, 5m, 30m, 2h]   │   │
│  │  Schema Service: Versioning, migration tracking, diff analysis      │   │
│  │  Review Service: CRUD, correction diff, auto-review gating          │   │
│  │  Accuracy Service: Compute metrics, cache, per-field breakdown      │   │
│  │  Analytics Service: Daily usage/cost queries, materialized views    │   │
│  │  Prompt Hint Builder: Aggregate corrections → hint generation       │   │
│  │  Schema Suggest: VLM field suggestion, graceful degradation         │   │
│  │  Template Service: Template CRUD, seeding, marketplace              │   │
│  │  Redis Pool: ARQ connection pool singleton                          │   │
│  │  ARQ Worker: Background job processor, async handlers, cron (5m)    │   │
│  │  Event Broadcaster: Redis pub/sub for WebSocket events              │   │
│  │  Router Service: Provider selection (local → cloud fallback)        │   │
│  │  Extraction Worker: ARQ job enqueue, provider delegation, scoring   │   │
│  │  Folder Watcher: watchfiles-based batch aggregation (60s window)    │   │
│  │  Confidence Scorer: Field-level aggregation                         │   │
│  │  Role Service: RBAC role assignment/removal, user listing           │   │
│  │  Approval Policy Service: Policy CRUD, validation                   │   │
│  │  Approval Engine: Workflow orchestration, conflict detection        │   │
│  │  Review Assignment Service: Auto-assign reviewers, track status     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                  ↓                                           │
│  Pipeline Engine Layer (Step-Based)                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Pipeline Executor: Sequential step execution with timing/errors    │   │
│  │  Step Registry: preprocess, extract, validate, export               │   │
│  │  StepContext: Data carrier between steps, error propagation         │   │
│  │  Config Parser: YAML → PipelineConfig (stored in DB)               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                  ↓                                           │
│  Extraction Pipelines (Provider Interface)                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Cloud Providers: Gemini API, Mistral API (cost tracking)           │   │
│  │  Local Provider: Ollama, vLLM, llama.cpp (multi-backend fallback)   │   │
│  │  Fallback: PaddleOCR for text-only extraction                       │   │
│  │  Base Provider: Abstract interface (extract, is_available, cost)    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                  ↓                                           │
│  Data Layer                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Database: SQLAlchemy ORM + SQLite/PostgreSQL (15 tables)           │   │
│  │    Tables: users, workspaces, api_keys, jobs, schemas,              │   │
│  │             schema_versions, pipelines, batches, batch_items,       │   │
│  │             webhooks, webhook_deliveries, schema_templates,         │   │
│  │             extraction_reviews, accuracy_metrics                    │   │
│  │  Views (PG only): mv_daily_workspace_stats, mv_daily_provider_stats,│   │
│  │                   mv_monthly_cost_summary (5min refresh)            │   │
│  │  Queue: ARQ (Redis-backed job queue, in-memory fallback)            │   │
│  │  Pub/Sub: Redis for WebSocket event broadcast                       │   │
│  │  File Storage: Uploaded documents, batch items, extracted docs     │   │
│  │  Cache: In-memory schema templates, prompt hints, provider avail.  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Middleware (`src/middleware/`)
- **auth-middleware.py** — API key (SHA256 hash) validation, JWT token verification, workspace scoping, role-based access control (RBAC)

### API Layer (`src/routers/`)
- **auth.py** — POST /auth/register, /login, /logout (JWT, refresh tokens)
- **extract.py** — POST /extract (single file), validation, job creation
- **jobs.py** — GET /jobs, /jobs/{id}, status polling, result retrieval
- **batch.py** — POST /extract/batch (multi-file), GET /batches, cancel operations
- **pipelines.py** — CRUD for YAML-based pipelines, config validation
- **schemas.py** — CRUD for schema templates, version history endpoint
- **analytics.py** — GET /analytics/usage, /costs, /providers, /overview; POST /analytics/refresh
- **webhooks.py** — Register webhooks, test delivery, view delivery logs
- **workspaces.py** — Workspace CRUD, user isolation
- **users.py** — User list, role assignment/removal, current user profile
- **approval-policies.py** — Approval policy CRUD (GET, POST, PUT, DELETE) for admin
- **review-workflow.py** — Review queue, job assignment, review submission, escalation, audit
- **health.py** — Liveness check + provider availability

### Services Layer (`src/services/`)
- **auth-service.py** — User registration/login, password hashing (bcrypt), JWT generation
- **workspace-service.py** — Workspace CRUD, soft multi-tenancy enforcement
- **job-service.py** — Job CRUD, persistence, status transitions
- **batch-service.py** — Batch creation, atomic counter updates, status derivation
- **pipeline-service.py** — Pipeline CRUD, executor delegation
- **webhook-service.py** — Event registration, HMAC-SHA256 signing
- **webhook-delivery.py** — Async delivery queue, retry backoff scheduler
- **router-service.py** — Provider selection logic (local vs cloud)
- **extraction-worker.py** — Async worker pool, job dequeue, result scoring
- **confidence-scorer.py** — Field-level confidence aggregation
- **analytics-service.py** — Daily usage/cost/provider stats (SQLite queries + PG materialized view fallback)
- **folder-watcher.py** — watchfiles-based batch aggregation (configurable window)
- **role-service.py** — Role assignment/removal, user listing per workspace
- **approval-policy-service.py** — Policy CRUD, config validation
- **approval-engine.py** — Workflow orchestration, conflict detection, escalation
- **review-assignment-service.py** — Auto-assign reviewers, track round status

### Pipeline Engine (`src/engine/`)
- **pipeline-executor.py** — Sequential step execution, timing, error handling
- **pipeline-config.py** — YAML parser, config validation
- **step-registry.py** — Step type registry (preprocess, extract, validate, export)
- **step-interface.py** — Abstract StepContext, step execution protocol

### Schema Engine (`src/schemas/`)
- **schema-models.py** — Pydantic models (SchemaField, ExtractionSchema, ExtractionResult)
- **schema-validator.py** — Field validation, type checking, occurrence rules
- **schema-converter.py** — JSON/CSV parsing and normalization
- **schema-store.py** — Template persistence, in-memory caching
- **schema-versioning.py** — Semver auto-bump, compatibility checks, field diff analysis
- **schema-migration.py** — Version migration tracking, backward compatibility

### Extraction Pipelines (`src/pipelines/`)
- **base-provider.py** — Abstract interface (extract, is_available, get_cost_info)
- **cloud/gemini-provider.py** — Gemini API integration with cost tracking
- **cloud/mistral-provider.py** — Mistral API integration with cost tracking
- **cloud/cloud-utils.py** — Token counting, prompt optimization
- **local/local-provider.py** — VLM orchestrator, multi-backend fallback
- **local/ollama-backend.py** — Ollama API calls
- **local/vllm-backend.py** — vLLM API calls
- **local/llamacpp-backend.py** — llama.cpp API calls
- **local/vlm-prompt-builder.py** — Schema → VLM prompt conversion
- **local/paddleocr-fallback.py** — Text-only extraction fallback

### Models (`src/models/`)
- **api-models.py** — Pydantic request/response schemas
- **job.py** — Job ORM model for SQLite
- **batch.py** — Batch ORM model, item tracking
- **pipeline.py** — Pipeline ORM model, YAML config storage
- **webhook.py** — Webhook ORM model, event types
- **workspace.py** — Workspace ORM model, user association

### Frontend (`frontend/src/`)
- **routes/**.tsx — Page components (file-based TanStack Router)
- **components/** — Reusable UI components (Header, Sidebar, Forms, Modals)
- **lib/api-client.ts** — HTTP client with X-API-Key authentication
- **lib/query-keys.ts** — TanStack Query key factories
- **lib/types.ts** — TypeScript type definitions

### UI (`src/ui/`)
- **gradio-app.py** — Optional web interface for interactive extraction
- **ui-helpers.py** — Form builders and UI utilities

## Data Flows

### Single Extraction Request
```
1. Client calls POST /extract with X-API-Key header
2. Auth middleware extracts workspace_id from API key hash
3. API validates schema syntax, file size
4. Job created in DB with status="pending", workspace_id set
5. Job ID returned (202 Accepted)
6. Client polls GET /jobs/{job_id}

Background (extraction-worker):
7. Dequeue job (workspace-scoped)
8. Router selects provider:
   - mode="local_only" → LocalProvider
   - mode="cloud" → CloudProvider (Gemini or Mistral)
   - mode="auto" → Try local first, fallback to cloud on low confidence
9. Provider executes extraction
10. Confidence scorer aggregates field-level scores
11. Job marked complete with result + cost + workspace_id
12. Client polls and receives full result

Result format:
{
  label_name: str,
  value: str | [str],
  confidence: float (0-1),
  extracted_by: "local" | "cloud"
}
```

### Batch Processing Flow
```
1. Client calls POST /extract/batch with multiple files, X-API-Key
2. Auth middleware: workspace_id extracted
3. Batch created in DB with status="pending", total_items count
4. Batch ID returned (202 Accepted)
5. Folder watcher (watchfiles) monitors upload directory
6. After batch_window_seconds (default 60s), trigger batch processing
7. For each file:
   - Create job in DB (batch_id FK)
   - extraction-worker dequeues
   - Extract → score → store result
   - Increment processed_items counter atomically
8. Status derivation:
   - All succeeded → "completed"
   - Some failed → "partial"
   - All failed → "failed"
9. Webhook event triggered (batch.completed or batch.failed)
10. Client polls GET /batches/{id} to see progress
```

### Pipeline Execution Flow
```
1. User creates pipeline: POST /pipelines
   - YAML config stored in DB
   - Name, steps (preprocess, extract, validate, export)
2. User submits extraction: POST /extract with pipeline_id
3. Pipeline executor retrieved from registry
4. For each step:
   - Step executor retrieved from registry
   - StepContext passed through (image, schema, errors)
   - If error: stop pipeline, return error
   - Record timing per step
5. Final result stored in job
```

### Webhook Event Flow
```
1. Job/batch completes
2. Webhook service queries active webhooks for workspace
3. For each webhook:
   - Filter by event_type (job.completed, batch.failed, etc.)
   - Create payload JSON
   - Sign with HMAC-SHA256 (secret + payload)
   - Create webhook_delivery record (pending)
4. Async delivery worker:
   - Send HTTP POST to webhook.url
   - Include X-Amanuo-Signature header
   - If 2xx: mark delivered
   - If error: schedule retry at next backoff interval [60s, 5m, 30m, 2h]
5. Webhook subscription receiver verifies signature, processes event
```

### Authentication Flow (API Key)
```
1. User calls POST /api-keys with JWT token
2. Auth service generates raw key: "amanuo_pk_{random}"
3. Hash with SHA256 (raw key NEVER stored)
4. Store key_hash in DB, workspace_id FK
5. Return key to user (once only)
6. Client uses X-API-Key header for subsequent requests
7. Auth middleware:
   - Extract X-API-Key value
   - Query DB for key_hash = SHA256(X-API-Key)
   - If found: extract workspace_id, inject into request context
   - If not found: 401 Unauthorized
8. All queries automatically filtered by workspace_id
```

### Schema Versioning Flow
```
1. User creates schema v1.0.0
2. User updates schema (e.g., new field, type change)
3. Schema versioning service detects changes:
   - Removed field or type change → major version bump (2.0.0)
   - New field added → minor version bump (1.1.0)
   - Prompt/config change only → patch version bump (1.0.1)
4. New schema_version record created in DB
5. Backward compatibility check:
   - Can old jobs still use new schema? Yes if only fields added
6. User can rollback to previous version or use specific version for jobs
7. Version history accessible via GET /schemas/{id}/versions
```

## Job Queue (ARQ + Redis)

### Architecture
- **Queue Backend**: Redis (7-alpine in docker-compose.yml, AOF persistence)
- **Worker Settings**: `arq-worker-settings.py` defines WorkerSettings, job handlers
- **Redis Pool**: Singleton ARQ Redis pool in `redis-pool.py`
- **Job Handlers**: `process_extraction_job()`, `deliver_webhook_task()` in WorkerSettings

### Job Processing Flow
```
1. extraction-worker.py calls enqueue_job()
2. Job enqueued to ARQ queue (or asyncio.Queue fallback if Redis unavailable)
3. Worker process (via `uv run arq src.services.arq-worker-settings.WorkerSettings`):
   - Dequeues job
   - Executes handler (extraction logic)
   - Publishes job.completed / job.failed event
4. Event broadcaster notifies WebSocket subscribers
```

### Running Standalone Worker
```bash
uv run arq src.services.arq-worker-settings.WorkerSettings
```

## WebSocket Event Stream (Redis Pub/Sub)

### Architecture
- **Broadcaster**: Redis pub/sub via `broadcaster[redis]` package
- **Singleton**: `event-broadcaster.py` creates module-level broadcaster instance
- **Events Published**: `job.completed`, `job.failed`, `batch.progress`, `batch.completed`, `batch.failed`
- **Client Subscription**: `GET /ws/events?api_key=X` (TanStack Start)

### WebSocket Protocol
```
GET /ws/events?api_key={api_key}
Response: 30s heartbeat, real-time JSON events

Event format:
{
  "event_type": "job.completed" | "job.failed" | "batch.progress" | ...,
  "workspace_id": "...",
  "data": { "job_id": "...", "status": "...", "result": {...} },
  "timestamp": "2026-03-16T..."
}
```

### Client-Side Handling
- `frontend/src/lib/websocket-client.ts` — exponential backoff reconnect
- `frontend/src/hooks/use-realtime-events.ts` — TanStack Query cache invalidation
- Auto-refresh job/batch status on event receipt

## Template Marketplace & Schema Suggest

### Schema Templates
- **Storage**: `schema_templates` table (ORM model: `SchemaTemplate`)
- **Curated Templates**: 4 built-in templates in `src/data/curated-templates.yaml`:
  - Invoice (EN), Invoice (JP), Receipt, ID Card
- **Endpoints**: GET /templates, POST /templates/{id}/import

### Schema Auto-Suggest
- **Service**: `schema-suggest-service.py` uses VLM to suggest fields
- **Endpoint**: `POST /schemas/suggest` (payload: document file + initial schema)
- **VLM Call**: Query extraction VLM, extract field names + types
- **Graceful Degradation**: Falls back to empty suggestion if VLM unavailable
- **Frontend**: `schema-suggest-form.tsx`, `suggested-fields-editor.tsx`

## Role-Based Access Control (RBAC)

### Role Hierarchy
```
Amanuo defines 5 roles per workspace:
- viewer: Read-only access to schemas and completed jobs
- member: Can submit extractions, view own results
- reviewer: Can review jobs and submit corrections
- approver: Can approve/reject review rounds, escalate conflicts
- admin: Full access including policy management, role assignment
```

### Role Assignment
- Stored in `role_assignments` table (user_id, workspace_id, role, granted_by, created_at)
- Each user has 1-N roles per workspace
- Role grants via admin endpoints: POST /users/{user_id}/roles
- Role removal via admin endpoints: DELETE /users/{user_id}/roles/{role}
- Cannot remove own admin role (lockout prevention)

### Middleware Integration
- Middleware enriches JWT token with roles from role_assignments table
- `@require_role("admin")` decorator gates endpoints to specific roles
- All endpoints check user["roles"] for authorization

## Multi-Reviewer Approval Chains (Approval Engine)

### Approval Flow
```
1. Job extracted and marked pending_review if schema requires_review=true
2. Approval policy matched (e.g., "chain_3_levels" or "quorum_2of3")
3. First review round created with assigned reviewers
4. Reviewers submit decisions: approved, corrected, rejected
5. Depending on policy:
   - Chain: Move to next round on approval, escalate on rejection
   - Quorum: Tally votes, escalate if no consensus (M votes vs N)
6. On escalation: Route to approver_id for final decision
7. Audit log tracks all decisions, conflicts, escalations
8. Job marked reviewed on final approval
```

### Policy Types
- **Sequential Chain** — N rounds with configurable approvers per round
  - Example: "chain_3_levels" = 3 sequential review rounds
  - If any round rejects: escalate to approver level
  - If all approve: mark completed

- **M-of-N Quorum** — Parallel voting by N reviewers, require M approvals
  - Example: "quorum_2of3" = 3 reviewers, need 2 approvals to pass
  - Voting window: configurable deadline_hours
  - Tie-breaker: auto-escalate to approver on tie/rejection

### Workflow Tables
- **approval_policies** — Policy config (name, type, config JSON, deadline)
- **review_rounds** — Round instance (job_id, round_number, type, deadline_at)
- **review_assignments** — Assigned reviewers (user_id, round_id, status)
- **review_audit_log** — Decision audit (assignment_id, action, result, timestamp)

### API Endpoints
- `GET /approval-policies` — List all policies in workspace
- `POST /approval-policies` — Create policy (admin only)
- `GET /approval-policies/{id}` — Get policy details
- `PUT /approval-policies/{id}` — Update policy (admin only)
- `DELETE /approval-policies/{id}` — Delete policy (admin only)

- `GET /review-queue` — Get pending assignments for current user (reviewer/approver)
- `GET /jobs/{id}/review-status` — Get job approval progress
- `POST /jobs/{id}/assign-reviewers` — Auto-assign reviewers to review round
- `POST /jobs/{id}/review` — Submit review decision (approved/rejected/corrected)
- `GET /jobs/{id}/audit-log` — Get full approval audit trail

## Database Schema (20 Tables)

### Authentication & Workspaces
```sql
-- Users
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  workspace_id TEXT FOREIGN KEY,
  email TEXT UNIQUE,
  password_hash TEXT,
  created_at TEXT,
  INDEX(workspace_id)
);

-- Workspaces
CREATE TABLE workspaces (
  id TEXT PRIMARY KEY,
  name TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TEXT
);

-- API Keys
CREATE TABLE api_keys (
  id TEXT PRIMARY KEY,
  workspace_id TEXT FOREIGN KEY,
  key_hash TEXT UNIQUE,  -- SHA256 hash
  name TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TEXT,
  INDEX(workspace_id),
  INDEX(key_hash)
);
```

### Extraction & Jobs
```sql
-- Jobs
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  workspace_id TEXT FOREIGN KEY,
  status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed', 'pending_review', 'reviewed')),
  mode TEXT,
  pipeline_id TEXT,
  input_file TEXT,
  schema_id TEXT,
  result TEXT,  -- JSON array
  confidence REAL,
  cost_input_tokens INTEGER,
  cost_output_tokens INTEGER,
  cost_usd REAL,
  error TEXT,
  created_at TEXT,
  completed_at TEXT,
  INDEX(workspace_id),
  INDEX(status),
  INDEX(created_at)
);

-- Schemas
CREATE TABLE schemas (
  id TEXT PRIMARY KEY,
  workspace_id TEXT FOREIGN KEY,
  name TEXT,
  fields TEXT,  -- JSON array
  is_template BOOLEAN,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TEXT,
  INDEX(workspace_id),
  INDEX(is_template)
);

-- Schema Versions
CREATE TABLE schema_versions (
  id TEXT PRIMARY KEY,
  schema_id TEXT FOREIGN KEY,
  version TEXT,  -- Semver: major.minor.patch
  fields TEXT,  -- JSON array
  change_type TEXT,  -- major, minor, patch
  breaking_changes TEXT,  -- JSON
  created_at TEXT,
  INDEX(schema_id),
  INDEX(version)
);
```

### Batch Processing
```sql
-- Batches
CREATE TABLE batches (
  id TEXT PRIMARY KEY,
  workspace_id TEXT FOREIGN KEY,
  status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'partial', 'failed')),
  pipeline_id TEXT,
  total_items INTEGER,
  processed_items INTEGER,
  failed_items INTEGER,
  created_at TEXT,
  completed_at TEXT,
  INDEX(workspace_id),
  INDEX(status)
);

-- Batch Items
CREATE TABLE batch_items (
  id TEXT PRIMARY KEY,
  batch_id TEXT FOREIGN KEY,
  job_id TEXT FOREIGN KEY,
  file_path TEXT,
  status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
  INDEX(batch_id),
  INDEX(job_id)
);
```

### Pipelines, Webhooks & Templates
```sql
-- Pipelines
CREATE TABLE pipelines (
  id TEXT PRIMARY KEY,
  workspace_id TEXT FOREIGN KEY,
  name TEXT,
  config TEXT,  -- YAML as JSON
  is_active BOOLEAN DEFAULT TRUE,
  created_at TEXT,
  INDEX(workspace_id)
);

-- Webhooks
CREATE TABLE webhooks (
  id TEXT PRIMARY KEY,
  workspace_id TEXT FOREIGN KEY,
  url TEXT,
  event_types TEXT,  -- JSON array
  secret TEXT,  -- For HMAC-SHA256 signing
  is_active BOOLEAN DEFAULT TRUE,
  created_at TEXT,
  INDEX(workspace_id)
);

-- Webhook Deliveries
CREATE TABLE webhook_deliveries (
  id TEXT PRIMARY KEY,
  webhook_id TEXT FOREIGN KEY,
  event_type TEXT,
  payload TEXT,  -- JSON
  status TEXT CHECK(status IN ('pending', 'delivered', 'failed')),
  attempt INTEGER DEFAULT 0,
  next_retry_at TEXT,
  response_status INTEGER,
  response_body TEXT,
  created_at TEXT,
  INDEX(webhook_id),
  INDEX(status),
  INDEX(next_retry_at)
);

-- Schema Templates (Template Marketplace)
CREATE TABLE schema_templates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  category TEXT,  -- "invoice", "receipt", "id_card", etc.
  schema_fields TEXT,  -- JSON array
  curated BOOLEAN DEFAULT FALSE,
  created_at TEXT,
  INDEX(category),
  INDEX(curated)
);

-- Extraction Reviews (HITL Review System)
CREATE TABLE extraction_reviews (
  id TEXT PRIMARY KEY,
  job_id TEXT FOREIGN KEY UNIQUE,
  workspace_id TEXT FOREIGN KEY,
  status TEXT CHECK(status IN ('approved', 'corrected')),
  original_result TEXT,  -- JSON: original extraction
  corrected_result TEXT,  -- JSON: corrected fields (nullable)
  corrections TEXT,  -- JSON: [{field, original, corrected}]
  reviewer_id TEXT FOREIGN KEY,  -- User who reviewed (nullable)
  review_time_ms INTEGER,  -- Time spent reviewing
  created_at TEXT,
  INDEX(workspace_id),
  INDEX(job_id),
  INDEX(status)
);

-- Accuracy Metrics (Dashboard & Learning)
CREATE TABLE accuracy_metrics (
  id TEXT PRIMARY KEY,
  schema_id TEXT FOREIGN KEY,
  workspace_id TEXT FOREIGN KEY,
  period_start TEXT,  -- ISO date
  period_end TEXT,  -- ISO date
  total_reviews INTEGER,
  approved_count INTEGER,  -- No corrections needed
  corrected_count INTEGER,  -- Corrections submitted
  accuracy_pct REAL,  -- approved / total * 100
  field_accuracy TEXT,  -- JSON: {field: {correct, total, pct}}
  created_at TEXT,
  INDEX(workspace_id),
  INDEX(schema_id),
  INDEX(period_start)
);

-- RBAC & Approval (Phase 8)
CREATE TABLE role_assignments (
  id TEXT PRIMARY KEY,
  user_id TEXT FOREIGN KEY,
  workspace_id TEXT FOREIGN KEY,
  role TEXT,  -- "viewer", "member", "reviewer", "approver", "admin"
  granted_by TEXT FOREIGN KEY,  -- user_id who granted role
  created_at TEXT,
  INDEX(workspace_id),
  INDEX(user_id),
  INDEX(role)
);

-- Approval Policies
CREATE TABLE approval_policies (
  id TEXT PRIMARY KEY,
  workspace_id TEXT FOREIGN KEY,
  name TEXT NOT NULL,
  policy_type TEXT,  -- "chain" | "quorum"
  config TEXT,  -- JSON: {rounds: [{approvers: [id]}, ...]} or {m: 2, n: 3}
  deadline_hours INTEGER,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TEXT,
  INDEX(workspace_id),
  INDEX(policy_type)
);

-- Review Rounds (instances of policy application)
CREATE TABLE review_rounds (
  id TEXT PRIMARY KEY,
  job_id TEXT FOREIGN KEY,
  policy_id TEXT FOREIGN KEY,
  round_number INTEGER,  -- 1, 2, 3, ...
  round_type TEXT,  -- "chain" | "quorum"
  deadline_at TEXT,  -- ISO timestamp
  status TEXT CHECK(status IN ('pending', 'in_progress', 'approved', 'rejected', 'escalated')),
  created_at TEXT,
  INDEX(job_id),
  INDEX(policy_id),
  INDEX(status)
);

-- Review Assignments (per-reviewer within round)
CREATE TABLE review_assignments (
  id TEXT PRIMARY KEY,
  round_id TEXT FOREIGN KEY,
  user_id TEXT FOREIGN KEY,
  status TEXT CHECK(status IN ('pending', 'in_progress', 'approved', 'rejected', 'skipped')),
  decision TEXT,  -- "approved" | "rejected" | "corrected"
  corrected_result TEXT,  -- JSON if decision="corrected"
  submitted_at TEXT,
  created_at TEXT,
  INDEX(round_id),
  INDEX(user_id),
  INDEX(status)
);

-- Approval Audit Log
CREATE TABLE review_audit_log (
  id TEXT PRIMARY KEY,
  assignment_id TEXT FOREIGN KEY,
  job_id TEXT FOREIGN KEY,
  round_id TEXT FOREIGN KEY,
  user_id TEXT FOREIGN KEY,
  action TEXT,  -- "submitted", "escalated", "auto_approved"
  result TEXT,  -- JSON: {decision, reason, conflicts}
  metadata TEXT,  -- JSON: extra context
  created_at TEXT,
  INDEX(job_id),
  INDEX(user_id),
  INDEX(action)
);
```

## Deployment Architecture

### Production (`docker-compose.yml`)
```
┌──────────────────────┐
│  nginx (port 80)     │  ← Single entry point for clients
│  - Serves dist/      │    (production-built React SPA)
│  - Proxies /api/*    │
│  - Proxies /ws/*     │
│  - SPA fallback      │
└──────────────┬───────┘
               ↓
         ┌─────────────┐
         │ app:8000    │
         │ (FastAPI)   │
         └─────┬───────┘
               ↓
      ┌────────────────┐
      │  redis:6379    │
      │  postgres:5432 │
      └────────────────┘
```

**Stack:**
- **Frontend Service** — `frontend/Dockerfile` (multi-stage: node build → nginx serve)
  - Build stage: `node:22-alpine`, installs deps, runs `npm run build` → `dist/`
  - Runtime stage: `nginx:alpine` serves `dist/` at port 80
  - nginx config routes `/api/*`, `/schemas/*`, `/jobs/*`, etc. to backend app:8000
  - SPA fallback: `try_files $uri $uri/ /index.html`
  - WebSocket support: `Upgrade` header forwarding for `/ws/*`
- **Backend Service** — `Dockerfile` (multi-stage: Python build → slim runtime)
  - Build stage: Python 3.11-slim, installs dependencies via uv
  - Runtime stage: Copies .venv, runs uvicorn on port 8000
- **Redis** — `redis:7-alpine` with AOF persistence (port 6379, queue + event broadcast)
- **PostgreSQL** — `postgres:16-alpine` (port 5432, persistent data + materialized views)

### Development (`docker-compose.dev.yml`)
```
┌─────────────────────────────────────┐
│  Vite dev server (port 3000)        │  ← Frontend with HMR
│  VITE_API_URL=http://app:8000      │
│  (node:22-alpine)                   │
└────────────────┬────────────────────┘
                 ↓
         ┌──────────────────┐
         │  app (port 8000) │
         │  --reload        │  ← Hot reload on code changes
         │  (FastAPI)       │
         └────────┬─────────┘
                  ↓
      ┌────────────────┐
      │  redis:6379    │
      │  postgres:5432 │
      └────────────────┘
```

**Stack:**
- **Frontend** — `node:22-alpine` with Vite dev server (`npm run dev -- --host 0.0.0.0`)
  - `VITE_API_URL=http://app:8000` (service name for Docker network)
  - vite.config.ts uses env var: `const apiTarget = process.env.VITE_API_URL || 'http://localhost:8000'`
  - Hot Module Replacement (HMR) for code changes
  - node_modules isolated via named volume
- **Backend** — Same `Dockerfile` but with `--reload` flag in docker-compose.dev.yml
- **Redis**, **PostgreSQL** — Same as production

## Technology Stack

### Backend
| Component | Technology | Purpose |
|---|---|---|
| **Web Framework** | FastAPI 0.115+ | REST API server, async middleware |
| **ORM** | SQLAlchemy 2.0+ | Async ORM, migration (alembic) |
| **Database** | SQLite / PostgreSQL | Persistence; SQLAlchemy supports both |
| **Database Driver** | aiosqlite, asyncpg | Async database access |
| **Authentication** | PyJWT, bcrypt | JWT tokens (HS256), password hashing (rounds=12) |
| **Job Queue** | ARQ 0.27+, Redis 5.3+ | Async background job processing |
| **Pub/Sub** | broadcaster[redis] 0.3+ | WebSocket event broadcast |
| **Config** | pydantic-settings | Environment-driven settings |
| **YAML** | PyYAML | Pipeline configuration parsing |
| **File Watcher** | watchfiles | Batch aggregation (folder monitoring) |
| **Cloud VLM** | google-genai, mistralai | Structured extraction + cost tracking |
| **Local VLM** | Ollama, vLLM, llama.cpp | Privacy-preserving inference |
| **OCR Fallback** | PaddleOCR | Text extraction fallback |
| **HTTP Client** | httpx | Async HTTP requests (webhooks, providers) |
| **Container** | Docker | Multi-stage builds for frontend & backend |

### Frontend
| Component | Technology | Purpose |
|---|---|---|
| **Framework** | React 19.0+ | UI library |
| **Router** | TanStack Router | File-based, type-safe routing |
| **State Mgmt** | TanStack Query | Async state, caching, refetching |
| **Styling** | Tailwind CSS 4.0+ | Utility-first CSS framework |
| **Build Tool** | Vite 7.0+ | Fast dev server, optimized builds |
| **Language** | TypeScript 5.0+ | Type safety |
| **HTTP Client** | Fetch API + wrapper | X-API-Key authentication |
| **Web Server** | nginx-alpine | Reverse proxy, SPA routing, WebSocket upgrade |

## Module Dependencies

```
main.py
  ├── middleware/
  │   └── auth-middleware.py
  ├── routers/
  │   ├── auth.py
  │   ├── extract.py, batch.py, jobs.py
  │   ├── pipelines.py, schemas.py, webhooks.py
  │   ├── workspaces.py, health.py
  │   └── services/ (job, batch, workspace, pipeline, webhook, auth, extraction-worker, etc.)
  │       ├── pipelines/ (base, cloud, local)
  │       ├── schemas/ (models, validator, converter, store, versioning, migration)
  │       └── engine/ (executor, config, registry, step-interface)
  ├── models/ (api-models, job, batch, pipeline, webhook, workspace)
  ├── database.py (SQLite schema + init)
  ├── config.py (Settings)
  └── ui/gradio-app.py (optional)

frontend/
  ├── routes/ (file-based TanStack Router)
  ├── components/ (React components)
  ├── lib/ (api-client.ts, query-keys.ts, types.ts)
  └── main.tsx (React entry point)
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
