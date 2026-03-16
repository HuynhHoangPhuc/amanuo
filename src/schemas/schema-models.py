"""Pydantic models for extraction schema input/output."""

from typing import Literal

from pydantic import BaseModel, Field

# Valid data types for schema fields
DataType = Literal["plain text", "number", "address", "datetime", "currency", "checkbox"]

# Valid occurrence types
Occurrence = Literal["optional once", "optional multiple", "required once", "required multiple"]


class SchemaField(BaseModel):
    """Single field definition in an extraction schema."""

    label_name: str = Field(..., min_length=1, max_length=100)
    data_type: DataType
    occurrence: Occurrence = "required once"
    prompt_for_label: str | None = None


class ExtractionSchema(BaseModel):
    """Complete extraction schema with multiple fields."""

    fields: list[SchemaField] = Field(..., min_length=1, max_length=50)
    name: str | None = None


class ExtractionResult(BaseModel):
    """Single extracted field result."""

    label_name: str
    data_type: str
    value: str | list[str] | None = None
    confidence: float | None = None


class SavedSchema(BaseModel):
    """Schema record stored in the database."""

    id: str
    name: str
    fields: list[SchemaField]
    created_at: str
    updated_at: str
