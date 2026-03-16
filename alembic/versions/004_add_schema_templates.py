"""add schema_templates table

Revision ID: 004_add_schema_templates
Revises: 095842ce1f0b
Create Date: 2026-03-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_add_schema_templates"
down_revision: Union[str, Sequence[str], None] = "095842ce1f0b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create schema_templates table."""
    op.create_table(
        "schema_templates",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("category", sa.String, nullable=False, server_default="other"),
        sa.Column("fields", sa.Text, nullable=False),
        sa.Column("languages", sa.Text, nullable=False, server_default='["en"]'),
        sa.Column("is_curated", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("workspace_id", sa.String, nullable=True),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("version", sa.String, nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.String, nullable=False),
        sa.Column("updated_at", sa.String, nullable=False),
    )
    op.create_index("idx_schema_templates_category", "schema_templates", ["category"])
    op.create_index("idx_schema_templates_curated", "schema_templates", ["is_curated"])


def downgrade() -> None:
    """Drop schema_templates table."""
    op.drop_index("idx_schema_templates_curated")
    op.drop_index("idx_schema_templates_category")
    op.drop_table("schema_templates")
