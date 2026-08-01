"""Lantern OS baseline schema.

Revision ID: 20260801_0001
Revises:
Create Date: 2026-08-01
"""

import sqlalchemy as sa
from alembic import op

revision = "20260801_0001"
down_revision = None
branch_labels = None
depends_on = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "schema_meta" not in existing:
        op.create_table(
            "schema_meta",
            sa.Column("key", sa.String(100), primary_key=True),
            sa.Column("value", sa.String(100), nullable=False),
        )
    if "tasks" not in existing:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(240), nullable=False),
            sa.Column("workstream", sa.String(100), nullable=False, server_default="Operations"),
            sa.Column("priority", sa.String(20), nullable=False, server_default="P1"),
            sa.Column("revenue_impact", sa.String(20), nullable=False, server_default="Medium"),
            sa.Column("due_date", sa.String(10)),
            sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if "opportunities" not in existing:
        op.create_table(
            "opportunities",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("account", sa.String(200), nullable=False),
            sa.Column("stage", sa.String(50), nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column("probability", sa.Float(), nullable=False),
            sa.Column("next_action", sa.Text(), nullable=False, server_default=""),
            sa.Column("next_date", sa.String(10)),
        )
    if "research" not in existing:
        op.create_table(
            "research",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(240), nullable=False),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("commercial_output", sa.Text(), nullable=False),
            sa.Column("next_action", sa.Text(), nullable=False, server_default=""),
        )
    if "milestones" not in existing:
        op.create_table(
            "milestones",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(240), nullable=False),
            sa.Column("target_date", sa.String(10), nullable=False),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("owner", sa.String(120), nullable=False, server_default="Founder"),
        )
    if "settings" not in existing:
        op.create_table(
            "settings",
            sa.Column("key", sa.String(100), primary_key=True),
            sa.Column("value", sa.Text(), nullable=False),
        )
    if "kpis" not in existing:
        op.create_table(
            "kpis",
            sa.Column("key", sa.String(100), primary_key=True),
            sa.Column("label", sa.String(200), nullable=False),
            sa.Column("target", sa.Float(), nullable=False, server_default="0"),
            sa.Column("actual", sa.Float(), nullable=False, server_default="0"),
            sa.Column("unit", sa.String(30), nullable=False, server_default="count"),
        )


def downgrade() -> None:
    existing = _existing_tables()
    for table in (
        "kpis",
        "settings",
        "milestones",
        "research",
        "opportunities",
        "tasks",
        "schema_meta",
    ):
        if table in existing:
            op.drop_table(table)
