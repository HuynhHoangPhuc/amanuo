# Advanced Implementation Patterns

Detailed patterns for SQLAlchemy, ARQ, WebSocket, HITL Review, Accuracy Metrics, Prompt Hints, and Templates.

## SQLAlchemy ORM Patterns

### Async Session Management
```python
# src/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def get_session() -> AsyncSession:
    """Get async database session."""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

# Usage in routers:
@router.get("/jobs")
async def list_jobs(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Job).filter_by(workspace_id=workspace_id))
    return result.scalars().all()
```

### ORM Model Patterns
```python
# src/models/job.py
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, TimestampMixin

class Job(Base, TimestampMixin):
    """Job ORM model with async-compatible annotations."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, ForeignKey("workspaces.id"))
    status: Mapped[str] = mapped_column(String, default="pending")
    result: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

# TimestampMixin provides created_at, updated_at
```

### Parameterized Queries (Injection Protection)
```python
# ✓ Safe parameterized query
result = await session.execute(
    select(Job).filter(Job.workspace_id == workspace_id, Job.status == "completed")
)

# ✗ Never use string interpolation
result = await session.execute(f"SELECT * FROM jobs WHERE workspace_id = {workspace_id}")
```

## ARQ Job Queue Patterns

### Job Enqueuing
```python
# src/services/extraction-worker.py
from src.services.redis-pool import redis_pool

async def enqueue_extraction_job(job_id: str, workspace_id: str, **kwargs):
    """Enqueue extraction job to ARQ queue."""
    queue = await redis_pool.get_queue()

    # Falls back to asyncio.Queue if Redis unavailable
    await queue.enqueue(
        "src.services.arq_worker_settings.process_extraction_job",
        job_id=job_id,
        workspace_id=workspace_id,
        **kwargs
    )
```

### Worker Handler Definition
```python
# src/services/arq-worker-settings.py
class WorkerSettings:
    """ARQ worker configuration."""
    queue_name = "default"
    max_jobs = 10

    async def startup(ctx):
        """Initialize on worker startup."""
        ctx['db'] = await get_db()

    @staticmethod
    async def process_extraction_job(ctx, job_id: str, **kwargs):
        """Job handler: extract document and store results."""
        job = await ctx['db'].get(Job, job_id)

        # Run extraction pipeline
        result = await extract_provider.extract(image, schema)

        # Publish event
        await event_broadcaster.publish("job.completed", {
            "job_id": job_id,
            "status": "completed",
            "result": result
        })
```

### Standalone Worker Execution
```bash
uv run arq src.services.arq-worker-settings.WorkerSettings
```

## WebSocket Event Patterns

### Event Broadcaster (Redis Pub/Sub)
```python
# src/services/event-broadcaster.py
from broadcaster import Broadcaster

broadcaster = Broadcaster("redis://localhost:6379")

async def publish_event(event_type: str, data: dict):
    """Publish event to WebSocket subscribers."""
    await broadcaster.publish(
        channel=f"workspace:{workspace_id}",
        message=json.dumps({
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
    )

# In extraction-worker after job completes:
await publish_event("job.completed", {"job_id": job_id, "status": "completed"})
```

### WebSocket Endpoint
```python
# src/routers/websocket-events.py
@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket, api_key: str = Query(...)):
    """WebSocket stream with workspace-scoped real-time updates."""
    workspace_id = await validate_api_key(api_key)
    await websocket.accept()

    async with broadcaster.subscribe(f"workspace:{workspace_id}") as subscriber:
        while True:
            message = await subscriber.get()
            await websocket.send_text(message)
            # 30s heartbeat to keep connection alive
            await asyncio.sleep(30)
```

### Frontend Connection
```typescript
// frontend/src/lib/websocket-client.ts
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  async connect(apiKey: string) {
    const url = `ws://localhost:8000/ws/events?api_key=${apiKey}`;
    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Invalidate TanStack Query cache on event
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    };

    this.ws.onerror = () => this.reconnectWithBackoff();
  }

  private reconnectWithBackoff() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      const delay = Math.pow(2, this.reconnectAttempts) * 1000;
      setTimeout(() => this.connect(this.apiKey), delay);
      this.reconnectAttempts++;
    }
  }
}
```

## HITL Review Patterns

### Review Service
```python
# src/services/review-service.py
async def submit_review(
    job_id: str,
    corrected_result: list[dict],
    workspace_id: str
) -> ExtractionReview:
    """Submit review corrections and store field-level diffs."""
    original_job = await session.get(Job, job_id)
    original_result = json.loads(original_job.result)

    # Compute field-level diff
    corrections = []
    for field in original_result:
        corrected_field = next(
            (c for c in corrected_result if c['label_name'] == field['label_name']),
            None
        )
        if corrected_field and corrected_field['value'] != field['value']:
            corrections.append({
                "field": field['label_name'],
                "original": field['value'],
                "corrected": corrected_field['value']
            })

    # Store review
    review = ExtractionReview(
        job_id=job_id,
        workspace_id=workspace_id,
        original_result=json.dumps(original_result),
        corrected_result=json.dumps(corrected_result),
        corrections=json.dumps(corrections),
        status="corrected" if corrections else "approved"
    )
    session.add(review)
    await session.commit()

    return review

async def auto_gate_review(job_id: str, schema_id: str) -> bool:
    """Auto-approve jobs with confidence >0.95, gate others for review."""
    job = await session.get(Job, job_id)
    schema = await session.get(Schema, schema_id)

    if schema.require_review or job.confidence < 0.95:
        job.status = "pending_review"
    else:
        job.status = "reviewed"  # Auto-approved

    await session.commit()
    return job.status == "reviewed"
```

## Accuracy Metrics Patterns

### Accuracy Service
```python
# src/services/accuracy-service.py
async def compute_accuracy_metrics(
    schema_id: str,
    workspace_id: str,
    period_days: int = 7
) -> AccuracyMetric:
    """Compute per-schema accuracy from reviews."""
    cutoff_date = datetime.utcnow() - timedelta(days=period_days)

    # Query reviews within period
    reviews = await session.execute(
        select(ExtractionReview)
        .filter(
            ExtractionReview.schema_id == schema_id,
            ExtractionReview.workspace_id == workspace_id,
            ExtractionReview.created_at >= cutoff_date
        )
    )
    reviews = reviews.scalars().all()

    # Count approved vs corrected
    approved_count = sum(1 for r in reviews if r.status == "approved")
    corrected_count = sum(1 for r in reviews if r.status == "corrected")
    total = len(reviews)

    # Per-field breakdown
    field_accuracy = {}
    for review in reviews:
        corrections = json.loads(review.corrections)
        for correction in corrections:
            field = correction['field']
            if field not in field_accuracy:
                field_accuracy[field] = {"correct": 0, "total": 0}
            field_accuracy[field]["total"] += 1
            if review.status == "approved":
                field_accuracy[field]["correct"] += 1

    # Store metrics
    metric = AccuracyMetric(
        schema_id=schema_id,
        workspace_id=workspace_id,
        total_reviews=total,
        approved_count=approved_count,
        corrected_count=corrected_count,
        accuracy_pct=(approved_count / total * 100) if total > 0 else 0,
        field_accuracy=json.dumps(field_accuracy),
        period_start=cutoff_date.date(),
        period_end=datetime.utcnow().date()
    )
    session.add(metric)
    await session.commit()

    return metric
```

## Prompt Hint Builder Patterns

### Hint Generation from Corrections
```python
# src/services/prompt-hint-builder.py
from functools import lru_cache

@lru_cache(maxsize=100)
async def build_hints_for_schema(schema_id: str, workspace_id: str) -> dict:
    """Generate VLM prompt hints from correction patterns."""
    # Query recent reviews for schema
    reviews = await session.execute(
        select(ExtractionReview)
        .filter(ExtractionReview.schema_id == schema_id)
        .order_by(ExtractionReview.created_at.desc())
        .limit(100)
    )

    field_hints = {}
    for review in reviews.scalars():
        corrections = json.loads(review.corrections)
        for correction in corrections:
            field = correction['field']
            if field not in field_hints:
                field_hints[field] = []
            # Aggregate common mistakes
            field_hints[field].append({
                "mistake": correction['original'],
                "correct": correction['corrected']
            })

    # Summarize patterns
    hints = {}
    for field, examples in field_hints.items():
        # Find most common corrections
        from collections import Counter
        common = Counter([f"{e['mistake']} → {e['correct']}" for e in examples])
        hints[field] = f"Watch for: {common.most_common(1)[0][0]}"

    return hints

async def inject_hints_into_prompt(schema: ExtractionSchema, workspace_id: str) -> str:
    """Inject field hints into VLM prompt."""
    hints = await build_hints_for_schema(schema.id, workspace_id)

    prompt = f"Extract fields from document:\n"
    for field in schema.fields:
        prompt += f"- {field['label']}: {field['description']}\n"
        if field['label'] in hints:
            prompt += f"  Hint: {hints[field['label']]}\n"

    return prompt
```

## Template Marketplace Patterns

### Schema Template Service
```python
# src/services/template-service.py
async def seed_curated_templates():
    """Load 4 built-in templates from YAML on startup."""
    with open("src/data/curated-templates.yaml") as f:
        templates = yaml.safe_load(f)

    for template in templates:
        existing = await session.execute(
            select(SchemaTemplate).filter(SchemaTemplate.name == template['name'])
        )
        if not existing.scalars().first():
            new_template = SchemaTemplate(
                name=template['name'],
                description=template['description'],
                category=template['category'],
                schema_fields=json.dumps(template['fields']),
                curated=True
            )
            session.add(new_template)

    await session.commit()

async def import_template(template_id: str, workspace_id: str, custom_name: str) -> Schema:
    """Import curated template as new schema in workspace."""
    template = await session.get(SchemaTemplate, template_id)

    new_schema = Schema(
        id=f"schema_{uuid4().hex[:8]}",
        workspace_id=workspace_id,
        name=custom_name,
        fields=template.schema_fields,  # Copy fields
        is_template=False,
        is_active=True
    )
    session.add(new_schema)
    await session.commit()

    return new_schema
```

## Key Principles

1. **Async-First** — All I/O operations must be awaited; never block the event loop
2. **Workspace Scoping** — All queries filtered by workspace_id for multi-tenancy
3. **Graceful Fallback** — Use asyncio.Queue if Redis unavailable, PaddleOCR if VLM fails
4. **Error Handling** — Publish failure events, log with exc_info=True, return structured errors
5. **Caching** — Use @lru_cache for frequently computed values (hints, templates, availability)
6. **Testing** — Unit test with mocked DB/API, E2E test with real fixtures
