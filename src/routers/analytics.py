"""Analytics API endpoints — usage, costs, providers, and view refresh."""

import importlib
from typing import Literal

from fastapi import APIRouter, Depends

_analytics_svc = importlib.import_module("src.services.analytics-service")
_auth = importlib.import_module("src.middleware.auth-middleware")

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/usage")
async def get_usage(
    period: Literal["7d", "30d", "90d"] = "30d",
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Daily job usage breakdown for the workspace."""
    return await _analytics_svc.get_usage_stats(workspace_id, period)


@router.get("/costs")
async def get_costs(
    period: Literal["7d", "30d", "90d"] = "30d",
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Daily cost breakdown with per-provider split."""
    return await _analytics_svc.get_cost_stats(workspace_id, period)


@router.get("/providers")
async def get_providers(
    period: Literal["7d", "30d", "90d"] = "30d",
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Per-provider comparison: job count, success rate, cost."""
    return await _analytics_svc.get_provider_stats(workspace_id, period)


@router.get("/overview")
async def get_overview(
    period: Literal["7d", "30d", "90d"] = "30d",
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Aggregated overview stats for the dashboard header."""
    return await _analytics_svc.get_overview(workspace_id, period)


@router.post("/refresh")
async def refresh_views(
    workspace_id: str = Depends(_auth.get_workspace_id),
):
    """Force-refresh materialized views (PG only; no-op on SQLite)."""
    await _analytics_svc.refresh_views()
    return {"status": "ok"}
