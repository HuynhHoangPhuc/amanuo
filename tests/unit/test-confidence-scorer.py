"""Unit tests for confidence scorer."""

import importlib

from src.pipelines import CostInfo, PipelineResult
from src.schemas import ExtractionResult, ExtractionSchema, SchemaField

_scorer = importlib.import_module("src.services.confidence-scorer")


def _make_schema(fields_data: list[dict]) -> ExtractionSchema:
    return ExtractionSchema(fields=[SchemaField(**f) for f in fields_data])


def _make_result(normalized: list[ExtractionResult], confidence: float = 0.0) -> PipelineResult:
    return PipelineResult(
        raw_output={},
        normalized=normalized,
        confidence=confidence,
        cost=CostInfo(),
        latency_ms=100,
        provider="test",
    )


class TestConfidenceScorer:
    def test_all_required_filled(self):
        schema = _make_schema([
            {"label_name": "a", "data_type": "plain text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "plain text", "occurrence": "required once"},
        ])
        result = _make_result([
            ExtractionResult(label_name="a", data_type="plain text", value="x"),
            ExtractionResult(label_name="b", data_type="plain text", value="y"),
        ])
        score = _scorer.score(result, schema)
        # completeness=1.0, provider_conf=0.5 (default) -> 0.7*1 + 0.3*0.5 = 0.85
        assert score == 0.85

    def test_half_required_filled(self):
        schema = _make_schema([
            {"label_name": "a", "data_type": "plain text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "plain text", "occurrence": "required once"},
        ])
        result = _make_result([
            ExtractionResult(label_name="a", data_type="plain text", value="x"),
            ExtractionResult(label_name="b", data_type="plain text", value=None),
        ])
        score = _scorer.score(result, schema)
        # completeness=0.5, provider_conf=0.5 -> 0.7*0.5 + 0.3*0.5 = 0.5
        assert score == 0.5

    def test_no_required_fields(self):
        schema = _make_schema([
            {"label_name": "opt", "data_type": "plain text", "occurrence": "optional once"},
        ])
        result = _make_result([
            ExtractionResult(label_name="opt", data_type="plain text", value=None),
        ])
        score = _scorer.score(result, schema)
        # completeness=1.0 (no required fields), provider_conf=0.5
        assert score == 0.85

    def test_with_provider_confidence(self):
        schema = _make_schema([
            {"label_name": "a", "data_type": "plain text", "occurrence": "required once"},
        ])
        result = _make_result([
            ExtractionResult(label_name="a", data_type="plain text", value="x", confidence=0.9),
        ])
        score = _scorer.score(result, schema)
        # completeness=1.0, provider_conf=0.9 -> 0.7*1 + 0.3*0.9 = 0.97
        assert score == 0.97

    def test_empty_result(self):
        schema = _make_schema([
            {"label_name": "a", "data_type": "plain text", "occurrence": "required once"},
        ])
        result = _make_result([
            ExtractionResult(label_name="a", data_type="plain text", value=None),
        ])
        score = _scorer.score(result, schema)
        # completeness=0.0, provider_conf=0.5 -> 0.0 + 0.15 = 0.15
        assert score == 0.15
