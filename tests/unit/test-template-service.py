"""Unit tests for template marketplace service — list, get, import, seed."""

import importlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_svc = importlib.import_module("src.services.template-service")
_template_mod = importlib.import_module("src.models.schema-template")
SchemaTemplate = _template_mod.SchemaTemplate

list_templates = _svc.list_templates
get_template = _svc.get_template
import_template = _svc.import_template
seed_curated_templates = _svc.seed_curated_templates
_to_dict = _svc._to_dict


def _make_template(**kwargs) -> SchemaTemplate:
    """Create a minimal SchemaTemplate ORM row for testing."""
    now = datetime.utcnow().isoformat()
    defaults = dict(
        id=str(uuid.uuid4()),
        name="Test Template",
        description="A test template",
        category="invoice",
        fields=json.dumps([{"label": "invoice_number", "type": "text", "occurrence": "required once"}]),
        languages='["en"]',
        is_curated=True,
        workspace_id=None,
        usage_count=0,
        version="1.0.0",
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    row = SchemaTemplate()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


class TestToDict:
    """Tests for _to_dict helper."""

    @pytest.mark.unit
    def test_converts_row_to_dict(self):
        row = _make_template(name="Invoice EN", category="invoice")
        languages = ["en"]
        result = _to_dict(row, languages)
        assert result["name"] == "Invoice EN"
        assert result["category"] == "invoice"
        assert result["is_curated"] is True
        assert result["languages"] == ["en"]
        assert isinstance(result["fields"], list)

    @pytest.mark.unit
    def test_fields_deserialized_from_json(self):
        fields = [{"label": "total", "type": "number", "occurrence": "required once"}]
        row = _make_template(fields=json.dumps(fields))
        result = _to_dict(row, ["en"])
        assert result["fields"] == fields

    @pytest.mark.unit
    def test_is_curated_coerced_to_bool(self):
        row = _make_template(is_curated=1)
        result = _to_dict(row, ["en"])
        assert result["is_curated"] is True

        row2 = _make_template(is_curated=0)
        result2 = _to_dict(row2, ["en"])
        assert result2["is_curated"] is False


class TestGetTemplate:
    """Tests for get_template — single lookup."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await get_template(session, "nonexistent-id")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_dict_when_found(self):
        row = _make_template(name="Invoice EN")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row
        session.execute = AsyncMock(return_value=mock_result)

        result = await get_template(session, row.id)
        assert result is not None
        assert result["name"] == "Invoice EN"


class TestImportTemplate:
    """Tests for import_template."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_value_error_when_not_found(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await import_template(session, "bad-id", "ws-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_import_result_with_fields(self):
        row = _make_template(name="Receipt")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        result = await import_template(session, row.id, "workspace-abc")
        assert result["template_id"] == row.id
        assert result["name"] == "Receipt"
        assert result["workspace_id"] == "workspace-abc"
        assert result["imported"] is True
        assert isinstance(result["fields"], list)


class TestSeedCuratedTemplates:
    """Tests for seed_curated_templates — idempotent YAML seeding."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_seeds_templates_from_yaml(self, tmp_path):
        """Seeds from real YAML file and returns count > 0."""
        yaml_path = Path(__file__).parent.parent.parent / "src" / "data" / "curated-templates.yaml"
        if not yaml_path.exists():
            pytest.skip("curated-templates.yaml not found")

        session = AsyncMock()
        # Simulate ensure_table and no existing templates
        mock_empty = MagicMock()
        mock_empty.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_empty)
        session.commit = AsyncMock()
        session.add = MagicMock()

        count = await seed_curated_templates(session)
        assert count >= 4  # At least 4 curated templates

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_existing_templates(self, tmp_path):
        """If template already exists, does not seed again."""
        yaml_path = Path(__file__).parent.parent.parent / "src" / "data" / "curated-templates.yaml"
        if not yaml_path.exists():
            pytest.skip("curated-templates.yaml not found")

        session = AsyncMock()
        # Simulate all templates already exist
        existing_row = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_row
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()
        session.add = MagicMock()

        count = await seed_curated_templates(session)
        assert count == 0
        session.add.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_zero_when_yaml_missing(self, tmp_path):
        """Returns 0 without error if YAML file does not exist."""
        session = AsyncMock()
        mock_empty = MagicMock()
        mock_empty.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_empty)
        session.commit = AsyncMock()

        with patch.object(Path, "exists", return_value=False):
            count = await seed_curated_templates(session)
        assert count == 0
