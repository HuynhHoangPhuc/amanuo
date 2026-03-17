"""Unit tests for analytics service — SQLite fallback path."""

import importlib
import pytest

_analytics_svc = importlib.import_module("src.services.analytics-service")


@pytest.mark.unit
async def test_get_usage_stats_returns_daily_breakdown(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    result = await _analytics_svc.get_usage_stats(workspace_id, "30d")
    assert isinstance(result, list)
    if result:
        stat = result[0]
        assert hasattr(stat, "date")
        assert hasattr(stat, "job_count")
        assert hasattr(stat, "success_count")
        assert hasattr(stat, "failed_count")
        assert hasattr(stat, "review_count")
        assert stat.job_count >= 0


@pytest.mark.unit
async def test_get_usage_stats_filters_by_workspace(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    result_mine = await _analytics_svc.get_usage_stats(workspace_id, "30d")
    result_other = await _analytics_svc.get_usage_stats("non-existent-ws", "30d")
    assert len(result_other) == 0
    assert len(result_mine) > 0


@pytest.mark.unit
async def test_get_usage_stats_respects_period_7d(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    result_7d = await _analytics_svc.get_usage_stats(workspace_id, "7d")
    result_90d = await _analytics_svc.get_usage_stats(workspace_id, "90d")
    # 90d window should return >= 7d window
    total_7d = sum(s.job_count for s in result_7d)
    total_90d = sum(s.job_count for s in result_90d)
    assert total_90d >= total_7d


@pytest.mark.unit
async def test_get_cost_stats_returns_daily_list(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    result = await _analytics_svc.get_cost_stats(workspace_id, "30d")
    assert isinstance(result, list)
    if result:
        stat = result[0]
        assert hasattr(stat, "total_cost_usd")
        assert hasattr(stat, "provider_breakdown")
        assert stat.total_cost_usd >= 0


@pytest.mark.unit
async def test_get_cost_stats_returns_provider_breakdown(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    result = await _analytics_svc.get_cost_stats(workspace_id, "30d")
    # At least one day should have provider breakdown
    has_breakdown = any(len(s.provider_breakdown) > 0 for s in result)
    assert has_breakdown


@pytest.mark.unit
async def test_get_cost_stats_zero_cost_jobs_handled(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    # Should not raise even if some jobs have cost=0.0
    result = await _analytics_svc.get_cost_stats(workspace_id, "30d")
    for stat in result:
        assert stat.total_cost_usd >= 0


@pytest.mark.unit
async def test_get_provider_stats_groups_by_provider(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    result = await _analytics_svc.get_provider_stats(workspace_id, "30d")
    assert isinstance(result, list)
    providers = {s.provider for s in result}
    # Fixture uses gemini, mistral, local_only — at least 2 providers
    assert len(providers) >= 2


@pytest.mark.unit
async def test_get_provider_stats_success_rate_valid(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    result = await _analytics_svc.get_provider_stats(workspace_id, "30d")
    for stat in result:
        assert 0.0 <= stat.success_rate <= 100.0
        assert stat.job_count > 0
        assert stat.total_cost_usd >= 0


@pytest.mark.unit
async def test_get_provider_stats_empty_workspace_returns_empty():
    result = await _analytics_svc.get_provider_stats("no-such-workspace", "30d")
    assert result == []


@pytest.mark.unit
async def test_get_overview_returns_aggregated_summary(db_with_analytics_jobs):
    workspace_id, _ = db_with_analytics_jobs
    result = await _analytics_svc.get_overview(workspace_id, "30d")
    assert result.total_jobs > 0
    assert result.total_cost_usd >= 0
    assert result.period == "30d"
    assert result.active_schemas >= 0


@pytest.mark.unit
async def test_get_overview_empty_workspace():
    result = await _analytics_svc.get_overview("empty-workspace-xyz", "7d")
    assert result.total_jobs == 0
    assert result.total_cost_usd == 0.0
    assert result.avg_confidence is None


@pytest.mark.unit
async def test_refresh_views_noop_on_sqlite():
    # Should complete without error on SQLite (no-op)
    await _analytics_svc.refresh_views()


@pytest.mark.unit
async def test_is_postgresql_returns_false_for_sqlite():
    # Tests always run on SQLite
    assert _analytics_svc._is_postgresql() is False


@pytest.mark.unit
async def test_period_start_7d():
    from datetime import datetime, timedelta, timezone
    start = _analytics_svc._period_start("7d")
    expected = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    # Allow 1-second tolerance
    assert start[:16] == expected[:16]


@pytest.mark.unit
async def test_empty_workspace_usage_returns_empty():
    result = await _analytics_svc.get_usage_stats("totally-empty-ws", "30d")
    assert result == []
