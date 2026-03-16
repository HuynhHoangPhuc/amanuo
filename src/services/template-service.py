"""Template marketplace service — CRUD for schema templates.

NOTE: Call `await seed_curated_templates(session)` from main.py lifespan after init_db()
"""

import importlib
import json
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

_template_mod = importlib.import_module("src.models.schema-template")
SchemaTemplate = _template_mod.SchemaTemplate


async def ensure_table(session: AsyncSession) -> None:
    """Create schema_templates table if missing (handles test DBs seeded via raw SQL)."""
    await session.execute(
        __import__("sqlalchemy", fromlist=["text"]).text(
            """CREATE TABLE IF NOT EXISTS schema_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT NOT NULL DEFAULT 'other',
                fields TEXT NOT NULL,
                languages TEXT DEFAULT '["en"]',
                is_curated INTEGER DEFAULT 0,
                workspace_id TEXT,
                usage_count INTEGER DEFAULT 0,
                version TEXT DEFAULT '1.0.0',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
    )
    await session.commit()


async def list_templates(
    session: AsyncSession,
    category: str | None = None,
    lang: str | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """List templates; filter by category, language, or search text."""
    stmt = select(SchemaTemplate).order_by(
        SchemaTemplate.is_curated.desc(), SchemaTemplate.usage_count.desc()
    )

    if category:
        stmt = stmt.where(SchemaTemplate.category == category)
    if search:
        stmt = stmt.where(SchemaTemplate.name.ilike(f"%{search}%"))

    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    templates = []
    for r in rows:
        languages = json.loads(r.languages or '["en"]')
        # Filter by language if requested
        if lang and lang not in languages:
            continue
        templates.append(_to_dict(r, languages))

    return templates


async def get_template(session: AsyncSession, template_id: str) -> dict | None:
    """Get a single template by ID."""
    result = await session.execute(
        select(SchemaTemplate).where(SchemaTemplate.id == template_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        return None
    return _to_dict(row, json.loads(row.languages or '["en"]'))


async def import_template(
    session: AsyncSession, template_id: str, workspace_id: str
) -> dict:
    """Clone a template as a new schema entry. Increments usage_count on source template."""
    template = await get_template(session, template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")

    # Increment usage count
    await session.execute(
        update(SchemaTemplate)
        .where(SchemaTemplate.id == template_id)
        .values(usage_count=SchemaTemplate.usage_count + 1)
    )
    await session.commit()

    return {
        "template_id": template_id,
        "name": template["name"],
        "fields": template["fields"],
        "workspace_id": workspace_id,
        "imported": True,
    }


async def seed_curated_templates(session: AsyncSession) -> int:
    """Idempotent: seed curated templates from YAML. Returns count of newly seeded templates."""
    await ensure_table(session)

    yaml_path = Path(__file__).parent.parent / "data" / "curated-templates.yaml"
    if not yaml_path.exists():
        return 0

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    seeded = 0
    for tmpl in data.get("templates", []):
        # Skip if already seeded (by name + is_curated)
        existing = await session.execute(
            select(SchemaTemplate).where(
                SchemaTemplate.name == tmpl["name"],
                SchemaTemplate.is_curated.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            continue

        now = datetime.utcnow().isoformat()
        languages = tmpl.get("languages", ["en"])
        fields = [
            {
                "label": f["label"],
                "type": f.get("type", "text"),
                "occurrence": f.get("occurrence", "optional once"),
            }
            for f in tmpl.get("fields", [])
        ]

        row = SchemaTemplate(
            id=str(uuid.uuid4()),
            name=tmpl["name"],
            description=tmpl.get("description", ""),
            category=tmpl.get("category", "other"),
            fields=json.dumps(fields),
            languages=json.dumps(languages),
            is_curated=True,
            workspace_id=None,
            usage_count=0,
            version="1.0.0",
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        seeded += 1

    if seeded:
        await session.commit()

    return seeded


def _to_dict(row: SchemaTemplate, languages: list) -> dict:
    """Convert ORM row to response dict."""
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "category": row.category,
        "fields": json.loads(row.fields),
        "languages": languages,
        "is_curated": bool(row.is_curated),
        "workspace_id": row.workspace_id,
        "usage_count": row.usage_count,
        "version": row.version,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
