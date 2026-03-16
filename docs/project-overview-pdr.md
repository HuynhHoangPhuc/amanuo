# Amanuo OCR System — Project Overview & PDR

## Project Vision

Amanuo is an adaptive hybrid OCR system for **structured document extraction** across English, Japanese, and Vietnamese documents. It prioritizes **privacy-first processing** with local-first fallback to cost-effective cloud providers.

## Goals

1. **Accuracy** — Multilingual structured extraction with high confidence scoring
2. **Privacy** — Local processing when possible; cloud offloading only when beneficial
3. **Cost-Efficiency** — Minimize token usage via schema-driven extraction; support multiple cloud providers
4. **Developer Experience** — Clear REST API, batch job processing, persistent schema templates

## Scope (MVP)

### In-Scope
- Single-document extraction with user-provided schemas (JSON/CSV formats)
- Schema validation and template management
- Dual-pipeline extraction: local VLM (Ollama/vLLM/llama.cpp + PaddleOCR) & cloud (Gemini/Mistral)
- Adaptive routing: local-only, cloud-only, or auto-select based on confidence
- Async job queue with SQLite persistence
- Cost tracking and confidence scoring
- Gradio web UI for interactive extraction
- 67 unit + E2E tests with 100% core module coverage

### Out-of-Scope
- Multi-document batching
- Fine-tuning or model training
- Real-time streaming
- OAuth authentication

## Functional Requirements

| Requirement | Detail |
|---|---|
| **Schema Definition** | Accept JSON schema or CSV import; validate field types (text, number, date, currency, checkbox, address) |
| **Image Processing** | Support PNG, JPEG, TIFF, PDF (up to 20MB) |
| **Extraction** | Extract fields per schema with value deduplication & confidence metrics |
| **Job Tracking** | Create jobs (202 Accepted), poll status, retrieve results |
| **Cloud Integration** | Support Gemini & Mistral with cost estimation |
| **Local Inference** | Fallback to PaddleOCR if VLM unavailable |
| **UI** | Gradio interface for upload → schema selection → result review |

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Latency** | Local: <3s; Cloud: <10s (p95) |
| **Throughput** | 3 concurrent workers (configurable) |
| **Accuracy** | >90% confidence on structured fields |
| **Languages** | English, Japanese, Vietnamese |
| **Uptime** | Graceful degradation on cloud failures |
| **Code Quality** | <200 LOC per file; 100% test coverage on core services |

## Technical Architecture

### Core Components
1. **Schema Engine** — Models, validation, CSV/JSON parsing
2. **Extraction Pipelines** — Base provider interface + cloud/local implementations
3. **Job Service** — Async queue, status tracking, SQLite persistence
4. **Router Service** — Intelligent provider selection (local → cloud fallback)
5. **Web Layer** — FastAPI REST API + optional Gradio UI

### Data Flow
```
Upload Image → Validate Schema → Enqueue Job →
Route (Local/Cloud) → Extract → Confidence Score → Store Result → Poll/Retrieve
```

## Acceptance Criteria

- [ ] All 67 tests passing (unit + E2E)
- [ ] REST API functional with documented endpoints
- [ ] Gradio UI operational for manual testing
- [ ] Cost tracking accurate for cloud providers
- [ ] Local fallback works when VLM unavailable
- [ ] Documentation complete (API, architecture, code standards)

## Success Metrics

- **Field Accuracy** — >90% confidence on known test documents
- **Latency** — P95 <10s for cloud, <3s for local
- **Availability** — Graceful handling of provider failures
- **Coverage** — 100% test coverage on services/pipelines
