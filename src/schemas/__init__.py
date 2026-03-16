"""Schema engine — parse, validate, convert extraction schemas."""

import importlib

# Re-export from kebab-case modules using importlib
schema_models = importlib.import_module("src.schemas.schema-models")
schema_validator = importlib.import_module("src.schemas.schema-validator")
schema_converter = importlib.import_module("src.schemas.schema-converter")
csv_prompt_builder = importlib.import_module("src.schemas.csv-prompt-builder")
schema_store = importlib.import_module("src.schemas.schema-store")

# Convenience re-exports
SchemaField = schema_models.SchemaField
ExtractionSchema = schema_models.ExtractionSchema
ExtractionResult = schema_models.ExtractionResult
SavedSchema = schema_models.SavedSchema

validate_schema = schema_validator.validate_schema
validate_or_raise = schema_validator.validate_or_raise
SchemaValidationError = schema_validator.SchemaValidationError

to_json_schema = schema_converter.to_json_schema
to_gemini_schema = schema_converter.to_gemini_schema
to_extraction_prompt = schema_converter.to_extraction_prompt
normalize_output = schema_converter.normalize_output

to_csv_prompt = csv_prompt_builder.to_csv_prompt

save_schema = schema_store.save_schema
get_schema = schema_store.get_schema
list_schemas = schema_store.list_schemas
delete_schema = schema_store.delete_schema
seed_templates = schema_store.seed_templates
