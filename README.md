# Amanuo — Adaptive Hybrid OCR System

**Privacy-first structured document extraction** with adaptive cloud/local pipelines for English, Japanese, and Vietnamese documents.

## Overview

Amanuo extracts structured data from documents using user-defined schemas. It routes requests intelligently between local VLM inference (Ollama/vLLM) and cloud APIs (Gemini/Mistral) based on availability and confidence. When VLMs fail, it falls back to PaddleOCR for text extraction.

**MVP Features:**
- Schema-driven extraction (JSON/CSV format)
- Dual-pipeline execution (local + cloud with fallback)
- Async job queue with SQLite persistence
- Cost tracking and confidence scoring
- Gradio web UI + REST API
- 67+ unit & E2E tests (100% core module coverage)

## Quick Start

### Prerequisites
- Python 3.11+
- `uv` package manager
- Local VLM (Ollama, vLLM, or llama.cpp) — optional but recommended
- Cloud API keys (Gemini or Mistral) — optional

### Setup

```bash
# Clone & install dependencies
git clone https://github.com/yourusername/amanuo.git
cd amanuo
uv sync

# Copy environment template
cp .env.example .env

# Start API server
uv run uvicorn src.main:app --reload

# (Optional) Start Gradio UI in browser
# Visit http://localhost:8000/ui
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| **POST** | `/extract` | Submit extraction job (202 Accepted) |
| **GET** | `/jobs` | List all jobs |
| **GET** | `/jobs/{job_id}` | Get job status & results |
| **GET** | `/schemas` | List saved schema templates |
| **POST** | `/schemas` | Create new schema template |
| **GET** | `/health` | Check server + provider availability |

### Example: Extract Data from Image

```bash
# 1. Create extraction job
curl -X POST "http://localhost:8000/extract" \
  -F "file=@invoice.png" \
  -F "mode=auto" \
  -F "schema_fields=[{\"label_name\": \"invoice_id\", \"data_type\": \"text\", \"occurrence\": \"required once\"}]"

# Returns: {"job_id": "abc123"}

# 2. Poll job status
curl "http://localhost:8000/jobs/abc123"

# Response when complete:
{
  "id": "abc123",
  "status": "completed",
  "result": [
    {
      "label_name": "invoice_id",
      "value": "INV-2025-001234",
      "confidence": 0.98
    }
  ],
  "confidence": 0.98,
  "cost": {"input_tokens": 150, "output_tokens": 25, "estimated_cost_usd": 0.001}
}
```

## Project Structure

```
src/
  ├── routers/          # API endpoints (extract, jobs, schemas, health)
  ├── services/         # Business logic (job processing, routing, scoring)
  ├── pipelines/        # Extraction backends (cloud, local, OCR fallback)
  ├── schemas/          # Schema validation & persistence
  ├── models/           # Pydantic & ORM models
  ├── ui/               # Gradio web interface
  ├── config.py         # Settings management
  ├── database.py       # SQLite setup
  └── main.py           # FastAPI app entry
tests/                  # 67+ unit, integration, E2E tests
docs/                   # Architecture, code standards, API docs
```

## Configuration

Set environment variables in `.env`:

```env
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
DATABASE_URL=sqlite+aiosqlite:///./amanuo.db
UPLOAD_DIR=data/uploads
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
# All tests
uv run pytest

# Unit tests only (fast)
uv run pytest -m unit

# Integration tests (requires Ollama/cloud APIs)
uv run pytest -m integration

# End-to-end tests (full workflow)
uv run pytest -m e2e

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

- [ ] Multi-document batching support
- [ ] Fine-tuning pipeline for custom models
- [ ] Redis queue for production scaling
- [ ] PostgreSQL for larger deployments
- [ ] OAuth authentication
- [ ] Real-time WebSocket updates

## License

See LICENSE file.

## Support

For issues, questions, or contributions, open a GitHub issue or contact the team.
