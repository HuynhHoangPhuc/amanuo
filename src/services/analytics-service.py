"""Analytics service: usage stats, cost breakdowns, provider comparison.

SQLite fallback: direct queries on jobs table (same response shape as PG path).
PostgreSQL: queries pre-computed materialized views for speed.
"""

import importlib
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import text

from src.database import get_engine, get_session_factory

_analytics_models = importlib.import_module("src.models.analytics-models")
AnalyticsOverview = _analytics_models.AnalyticsOverview
DailyCostStat = _analytics_models.DailyCostStat
DailyUsageStat = _analytics_models.DailyUsageStat
ProviderStat = _analytics_models.ProviderStat


def _is_postgresql() -> bool:
    """Detect if the current engine targets PostgreSQL."""
    engine = get_engine()
    return engine is not None and engine.url.drivername.startswith("postgresql")


def _period_start(period: str) -> str:
    """Convert period string (7d/30d/90d) to ISO start datetime."""
    days = {"7d": 7, "30d": 30, "90d": 90}
    delta = timedelta(days=days.get(period, 30))
    return (datetime.utcnow() - delta).isoformat()


def _get_session():
    return get_session_factory()()


# ---- Usage Stats ----

async def get_usage_stats(workspace_id: str, period: str) -> list[DailyUsageStat]:
    start = _period_start(period)
    if _is_postgresql():
        return await _pg_usage_stats(workspace_id, start)
    return await _sqlite_usage_stats(workspace_id, start)


async def _sqlite_usage_stats(workspace_id: str, start: str) -> list[DailyUsageStat]:
    async with _get_session() as session:
        result = await session.execute(text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as job_count,
                COUNT(CASE WHEN status='completed' THEN 1 END) as success_count,
                COUNT(CASE WHEN status='failed' THEN 1 END) as failed_count,
                COUNT(CASE WHEN status IN ('pending_review','reviewed') THEN 1 END) as review_count,
                AVG(CASE WHEN confidence IS NOT NULL THEN confidence END) as avg_confidence
            FROM jobs
            WHERE workspace_id = :ws AND created_at >= :start
            GROUP BY DATE(created_at)
            ORDER BY date
        """), {"ws": workspace_id, "start": start})
        rows = result.mappings().all()
    return [
        DailyUsageStat(
            date=str(r["date"]),
            job_count=int(r["job_count"]),
            success_count=int(r["success_count"] or 0),
            failed_count=int(r["failed_count"] or 0),
            review_count=int(r["review_count"] or 0),
            avg_confidence=float(r["avg_confidence"]) if r["avg_confidence"] is not None else None,
        )
        for r in rows
    ]


async def _pg_usage_stats(workspace_id: str, start: str) -> list[DailyUsageStat]:
    async with _get_session() as session:
        result = await session.execute(text("""
            SELECT date::text, job_count, success_count, failed_count, review_count, avg_confidence
            FROM mv_daily_workspace_stats
            WHERE workspace_id = :ws AND date >= :start::date
            ORDER BY date
        """), {"ws": workspace_id, "start": start})
        rows = result.mappings().all()
    return [
        DailyUsageStat(
            date=str(r["date"]),
            job_count=int(r["job_count"]),
            success_count=int(r["success_count"] or 0),
            failed_count=int(r["failed_count"] or 0),
            review_count=int(r["review_count"] or 0),
            avg_confidence=float(r["avg_confidence"]) if r["avg_confidence"] is not None else None,
        )
        for r in rows
    ]


# ---- Cost Stats ----

async def get_cost_stats(workspace_id: str, period: str) -> list[DailyCostStat]:
    start = _period_start(period)
    if _is_postgresql():
        return await _pg_cost_stats(workspace_id, start)
    return await _sqlite_cost_stats(workspace_id, start)


async def _sqlite_cost_stats(workspace_id: str, start: str) -> list[DailyCostStat]:
    async with _get_session() as session:
        result = await session.execute(text("""
            SELECT
                DATE(created_at) as date,
                COALESCE(cloud_provider, mode) as provider,
                COALESCE(cost_estimated_usd, 0) as cost_usd,
                COALESCE(cost_input_tokens, 0) as input_tokens,
                COALESCE(cost_output_tokens, 0) as output_tokens
            FROM jobs
            WHERE workspace_id = :ws AND created_at >= :start
            ORDER BY date
        """), {"ws": workspace_id, "start": start})
        rows = result.mappings().all()

    # Aggregate by date in Python (avoids complex SQLite pivot)
    daily: dict[str, dict] = {}
    for r in rows:
        date_str = str(r["date"])
        if date_str not in daily:
            daily[date_str] = {
                "total_cost_usd": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "provider_breakdown": defaultdict(float),
            }
        provider = str(r["provider"] or "unknown")
        daily[date_str]["total_cost_usd"] += float(r["cost_usd"] or 0)
        daily[date_str]["total_input_tokens"] += int(r["input_tokens"] or 0)
        daily[date_str]["total_output_tokens"] += int(r["output_tokens"] or 0)
        daily[date_str]["provider_breakdown"][provider] += float(r["cost_usd"] or 0)
    return [
        DailyCostStat(
            date=date_str,
            total_cost_usd=round(d["total_cost_usd"], 6),
            total_input_tokens=d["total_input_tokens"],
            total_output_tokens=d["total_output_tokens"],
            provider_breakdown=dict(d["provider_breakdown"]),
        )
        for date_str, d in sorted(daily.items())
    ]


async def _pg_cost_stats(workspace_id: str, start: str) -> list[DailyCostStat]:
    async with _get_session() as session:
        ws_result = await session.execute(text("""
            SELECT date::text, total_cost_usd, total_input_tokens, total_output_tokens
            FROM mv_daily_workspace_stats
            WHERE workspace_id = :ws AND date >= :start::date
            ORDER BY date
        """), {"ws": workspace_id, "start": start})
        ws_rows = ws_result.mappings().all()

        prov_result = await session.execute(text("""
            SELECT date::text as date, provider, total_cost_usd
            FROM mv_daily_provider_stats
            WHERE workspace_id = :ws AND date >= :start::date
        """), {"ws": workspace_id, "start": start})
        prov_rows = prov_result.mappings().all()

    daily_provider: dict[str, dict[str, float]] = defaultdict(dict)
    for r in prov_rows:
        daily_provider[str(r["date"])][str(r["provider"])] = float(r["total_cost_usd"] or 0)
    return [
        DailyCostStat(
            date=str(r["date"]),
            total_cost_usd=float(r["total_cost_usd"] or 0),
            total_input_tokens=int(r["total_input_tokens"] or 0),
            total_output_tokens=int(r["total_output_tokens"] or 0),
            provider_breakdown=daily_provider.get(str(r["date"]), {}),
        )
        for r in ws_rows
    ]


# ---- Provider Stats ----

async def get_provider_stats(workspace_id: str, period: str) -> list[ProviderStat]:
    start = _period_start(period)
    if _is_postgresql():
        return await _pg_provider_stats(workspace_id, start)
    return await _sqlite_provider_stats(workspace_id, start)


async def _sqlite_provider_stats(workspace_id: str, start: str) -> list[ProviderStat]:
    async with _get_session() as session:
        result = await session.execute(text("""
            SELECT
                COALESCE(cloud_provider, mode) as provider,
                COUNT(*) as job_count,
                COUNT(CASE WHEN status='completed' THEN 1 END) as success_count,
                AVG(CASE WHEN confidence IS NOT NULL THEN confidence END) as avg_confidence,
                AVG(CASE WHEN completed_at IS NOT NULL
                    THEN (julianday(completed_at) - julianday(created_at)) * 86400000
                    END) as avg_latency_ms,
                SUM(COALESCE(cost_estimated_usd, 0)) as total_cost_usd
            FROM jobs
            WHERE workspace_id = :ws AND created_at >= :start
            GROUP BY COALESCE(cloud_provider, mode)
        """), {"ws": workspace_id, "start": start})
        rows = result.mappings().all()
    return [
        ProviderStat(
            provider=str(r["provider"] or "unknown"),
            job_count=int(r["job_count"]),
            success_rate=round(float(r["success_count"] or 0) / max(int(r["job_count"]), 1) * 100, 2),
            avg_confidence=float(r["avg_confidence"]) if r["avg_confidence"] is not None else None,
            avg_latency_ms=float(r["avg_latency_ms"]) if r["avg_latency_ms"] is not None else None,
            total_cost_usd=float(r["total_cost_usd"] or 0),
        )
        for r in rows
    ]


async def _pg_provider_stats(workspace_id: str, start: str) -> list[ProviderStat]:
    async with _get_session() as session:
        result = await session.execute(text("""
            SELECT
                provider,
                SUM(job_count) as job_count,
                SUM(success_count) as success_count,
                AVG(avg_confidence) as avg_confidence,
                SUM(total_cost_usd) as total_cost_usd
            FROM mv_daily_provider_stats
            WHERE workspace_id = :ws AND date >= :start::date
            GROUP BY provider
        """), {"ws": workspace_id, "start": start})
        rows = result.mappings().all()
    return [
        ProviderStat(
            provider=str(r["provider"]),
            job_count=int(r["job_count"]),
            success_rate=round(float(r["success_count"] or 0) / max(int(r["job_count"]), 1) * 100, 2),
            avg_confidence=float(r["avg_confidence"]) if r["avg_confidence"] is not None else None,
            avg_latency_ms=None,  # Not tracked in materialized view
            total_cost_usd=float(r["total_cost_usd"] or 0),
        )
        for r in rows
    ]


# ---- Overview ----

async def get_overview(workspace_id: str, period: str) -> AnalyticsOverview:
    start = _period_start(period)
    async with _get_session() as session:
        result = await session.execute(text("""
            SELECT
                COUNT(*) as total_jobs,
                SUM(COALESCE(cost_estimated_usd, 0)) as total_cost_usd,
                AVG(CASE WHEN confidence IS NOT NULL THEN confidence END) as avg_confidence,
                COUNT(DISTINCT schema_id) as active_schemas
            FROM jobs
            WHERE workspace_id = :ws AND created_at >= :start
        """), {"ws": workspace_id, "start": start})
        row = result.mappings().one()
    return AnalyticsOverview(
        total_jobs=int(row["total_jobs"] or 0),
        total_cost_usd=float(row["total_cost_usd"] or 0),
        avg_confidence=float(row["avg_confidence"]) if row["avg_confidence"] is not None else None,
        active_schemas=int(row["active_schemas"] or 0),
        period=period,
    )


# ---- Refresh Views ----

async def refresh_views() -> None:
    """Refresh materialized views (PG only). No-op on SQLite."""
    if not _is_postgresql():
        return
    async with _get_session() as session:
        await session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_workspace_stats"))
        await session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_provider_stats"))
        await session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_cost_summary"))
        await session.commit()
