"""Validation logic for user-submitted extraction schemas."""

import importlib

_models = importlib.import_module("src.schemas.schema-models")
ExtractionSchema = _models.ExtractionSchema

# Maximum nesting depth for field names (e.g., "address.street.number")
MAX_NESTING_DEPTH = 3
MAX_PROMPT_LENGTH = 500


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Schema validation failed: {'; '.join(errors)}")


def validate_schema(schema: ExtractionSchema) -> list[str]:
    """Validate an extraction schema. Returns list of error messages (empty = valid)."""
    errors: list[str] = []

    # Check for duplicate label names
    label_names = [f.label_name for f in schema.fields]
    duplicates = [name for name in set(label_names) if label_names.count(name) > 1]
    if duplicates:
        errors.append(f"Duplicate label names: {', '.join(duplicates)}")

    for field in schema.fields:
        # Check label name characters (alphanumeric, underscore, dot, hyphen, space)
        if not all(c.isalnum() or c in "_-. " for c in field.label_name):
            errors.append(
                f"Invalid characters in label '{field.label_name}': "
                "only alphanumeric, underscore, hyphen, dot, space allowed"
            )

        # Check nesting depth (dots indicate nesting)
        depth = field.label_name.count(".") + 1
        if depth > MAX_NESTING_DEPTH:
            errors.append(
                f"Label '{field.label_name}' nesting depth {depth} exceeds max {MAX_NESTING_DEPTH}"
            )

        # Check prompt length
        if field.prompt_for_label and len(field.prompt_for_label) > MAX_PROMPT_LENGTH:
            errors.append(
                f"Prompt for '{field.label_name}' exceeds {MAX_PROMPT_LENGTH} characters"
            )

    return errors


def validate_or_raise(schema: ExtractionSchema) -> None:
    """Validate schema and raise SchemaValidationError if invalid."""
    errors = validate_schema(schema)
    if errors:
        raise SchemaValidationError(errors)
