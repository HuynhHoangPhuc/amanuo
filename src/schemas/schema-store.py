"""SQLite CRUD operations for saved extraction schemas."""

import importlib
import json
import uuid
from datetime import datetime

import aiosqlite

_models = importlib.import_module("src.schemas.schema-models")
ExtractionSchema = _models.ExtractionSchema
SavedSchema = _models.SavedSchema
SchemaField = _models.SchemaField


async def save_schema(
    db: aiosqlite.Connection, name: str, schema: ExtractionSchema,
    workspace_id: str = "default",
) -> SavedSchema:
    """Save a new schema to the database."""
    schema_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    fields_json = json.dumps([f.model_dump() for f in schema.fields])

    await db.execute(
        """INSERT INTO schemas (id, name, fields, created_at, updated_at, workspace_id, current_version)
           VALUES (?, ?, ?, ?, ?, ?, '1.0.0')""",
        (schema_id, name, fields_json, now, now, workspace_id),
    )
    await db.commit()

    return SavedSchema(
        id=schema_id, name=name, fields=schema.fields, created_at=now, updated_at=now
    )


async def get_schema(db: aiosqlite.Connection, schema_id: str) -> SavedSchema | None:
    """Load a schema by ID."""
    cursor = await db.execute("SELECT * FROM schemas WHERE id = ?", (schema_id,))
    row = await cursor.fetchone()
    if not row:
        return None

    fields = [SchemaField(**f) for f in json.loads(row["fields"])]
    return SavedSchema(
        id=row["id"],
        name=row["name"],
        fields=fields,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_schemas(db: aiosqlite.Connection) -> list[SavedSchema]:
    """List all saved schemas."""
    cursor = await db.execute("SELECT * FROM schemas ORDER BY created_at DESC")
    rows = await cursor.fetchall()

    return [
        SavedSchema(
            id=row["id"],
            name=row["name"],
            fields=[SchemaField(**f) for f in json.loads(row["fields"])],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


async def delete_schema(db: aiosqlite.Connection, schema_id: str) -> bool:
    """Delete a schema by ID. Returns True if deleted."""
    cursor = await db.execute("DELETE FROM schemas WHERE id = ?", (schema_id,))
    await db.commit()
    return cursor.rowcount > 0


# Pre-defined schema templates
TEMPLATES: dict[str, list[dict]] = {
    "vehicle-license-vn": [
        {"label_name": "plate_number", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Vehicle registration plate number"},
        {"label_name": "owner_name", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Full name of the vehicle owner"},
        {"label_name": "address", "data_type": "address", "occurrence": "required once", "prompt_for_label": "Registered address of the owner"},
        {"label_name": "brand", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Vehicle brand/manufacturer"},
        {"label_name": "model", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Vehicle model name"},
        {"label_name": "color", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Exterior paint color of the vehicle"},
        {"label_name": "engine_number", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Engine serial number"},
        {"label_name": "chassis_number", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Chassis/frame serial number"},
        {"label_name": "registration_date", "data_type": "datetime", "occurrence": "required once", "prompt_for_label": "Date of registration"},
    ],
    "id-card-generic": [
        {"label_name": "full_name", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Full legal name"},
        {"label_name": "id_number", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "ID card number"},
        {"label_name": "date_of_birth", "data_type": "datetime", "occurrence": "required once", "prompt_for_label": "Date of birth"},
        {"label_name": "gender", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Gender"},
        {"label_name": "nationality", "data_type": "plain text", "occurrence": "optional once", "prompt_for_label": "Nationality"},
        {"label_name": "address", "data_type": "address", "occurrence": "required once", "prompt_for_label": "Permanent address"},
        {"label_name": "issue_date", "data_type": "datetime", "occurrence": "required once", "prompt_for_label": "Date of issue"},
        {"label_name": "expiry_date", "data_type": "datetime", "occurrence": "optional once", "prompt_for_label": "Expiration date"},
    ],
    "invoice-generic": [
        {"label_name": "invoice_number", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Invoice number"},
        {"label_name": "invoice_date", "data_type": "datetime", "occurrence": "required once", "prompt_for_label": "Invoice date"},
        {"label_name": "seller_name", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Seller/vendor company name"},
        {"label_name": "buyer_name", "data_type": "plain text", "occurrence": "required once", "prompt_for_label": "Buyer/customer name"},
        {"label_name": "line_items", "data_type": "plain text", "occurrence": "required multiple", "prompt_for_label": "Line item descriptions"},
        {"label_name": "subtotal", "data_type": "currency", "occurrence": "required once", "prompt_for_label": "Subtotal before tax"},
        {"label_name": "tax", "data_type": "currency", "occurrence": "optional once", "prompt_for_label": "Tax amount"},
        {"label_name": "total", "data_type": "currency", "occurrence": "required once", "prompt_for_label": "Total amount due"},
    ],
}


async def seed_templates(db: aiosqlite.Connection) -> None:
    """Seed default schema templates if they don't exist."""
    for name, fields_data in TEMPLATES.items():
        cursor = await db.execute("SELECT id FROM schemas WHERE name = ?", (name,))
        if await cursor.fetchone():
            continue

        schema = ExtractionSchema(fields=[SchemaField(**f) for f in fields_data])
        await save_schema(db, name, schema)
