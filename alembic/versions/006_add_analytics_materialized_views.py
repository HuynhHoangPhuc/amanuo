"""Add PostgreSQL materialized views for analytics aggregation.

Revision ID: 006_add_analytics_materialized_views
Revises: 004_add_schema_templates
Create Date: 2026-03-16

Creates 3 materialized views (PG only — skipped for SQLite):
  mv_daily_workspace_stats  — daily job counts and cost totals per workspace
  mv_daily_provider_stats   — daily per-provider breakdown
  mv_monthly_cost_summary   — monthly cost rollup per workspace

Each view gets a UNIQUE index to enable CONCURRENT refresh (non-blocking).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006_add_analytics_materialized_views"
down_revision: Union[str, Sequence[str], None] = "004_add_schema_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite has no materialized views — skip

    op.execute("""
        CREATE MATERIALIZED VIEW mv_daily_workspace_stats AS
        SELECT
            workspace_id,
            DATE(created_at) AS date,
            COUNT(*) AS job_count,
            COUNT(*) FILTER (WHERE status = 'completed') AS success_count,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed_count,
            COUNT(*) FILTER (WHERE status IN ('pending_review', 'reviewed')) AS review_count,
            AVG(confidence) FILTER (WHERE confidence IS NOT NULL) AS avg_confidence,
            SUM(COALESCE(cost_input_tokens, 0)) AS total_input_tokens,
            SUM(COALESCE(cost_output_tokens, 0)) AS total_output_tokens,
            SUM(COALESCE(cost_estimated_usd, 0)) AS total_cost_usd
        FROM jobs
        GROUP BY workspace_id, DATE(created_at)
    """)
    op.execute(
        "CREATE UNIQUE INDEX ON mv_daily_workspace_stats (workspace_id, date)"
    )

    op.execute("""
        CREATE MATERIALIZED VIEW mv_daily_provider_stats AS
        SELECT
            workspace_id,
            COALESCE(cloud_provider, mode) AS provider,
            DATE(created_at) AS date,
            COUNT(*) AS job_count,
            COUNT(*) FILTER (WHERE status = 'completed') AS success_count,
            AVG(confidence) FILTER (WHERE confidence IS NOT NULL) AS avg_confidence,
            SUM(COALESCE(cost_estimated_usd, 0)) AS total_cost_usd
        FROM jobs
        GROUP BY workspace_id, COALESCE(cloud_provider, mode), DATE(created_at)
    """)
    op.execute(
        "CREATE UNIQUE INDEX ON mv_daily_provider_stats (workspace_id, provider, date)"
    )

    op.execute("""
        CREATE MATERIALIZED VIEW mv_monthly_cost_summary AS
        SELECT
            workspace_id,
            TO_CHAR(DATE(created_at), 'YYYY-MM') AS month,
            SUM(COALESCE(cost_estimated_usd, 0)) AS total_cost_usd,
            COUNT(*) AS total_jobs,
            CASE WHEN COUNT(*) > 0
                THEN SUM(COALESCE(cost_estimated_usd, 0)) / COUNT(*)
                ELSE 0
            END AS cost_per_job_avg
        FROM jobs
        GROUP BY workspace_id, TO_CHAR(DATE(created_at), 'YYYY-MM')
    """)
    op.execute(
        "CREATE UNIQUE INDEX ON mv_monthly_cost_summary (workspace_id, month)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_monthly_cost_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_provider_stats")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_workspace_stats")
