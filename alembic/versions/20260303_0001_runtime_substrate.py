"""Create runtime substrate timeline and cursor tables.

Revision ID: 20260303_0001
Revises:
Create Date: 2026-03-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260303_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timeline_events",
        sa.Column("sequence_no", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.String(length=64), nullable=False),
        sa.Column("recorded_at", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=True),
        sa.Column("actor", sa.JSON(), nullable=False),
        sa.Column("links", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("causation_id", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("integrity", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("event_id", name="uq_timeline_events_event_id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_timeline_events_idempotency_key",
        ),
    )
    op.create_index(
        "ix_timeline_events_workflow_run_id",
        "timeline_events",
        ["workflow_run_id"],
        unique=False,
    )

    op.create_table(
        "consumer_cursors",
        sa.Column("consumer_name", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column(
            "last_sequence_no",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "consumer_name",
            "tenant_id",
            "domain_id",
            name="pk_consumer_cursors",
        ),
    )


def downgrade() -> None:
    op.drop_table("consumer_cursors")
    op.drop_index("ix_timeline_events_workflow_run_id", table_name="timeline_events")
    op.drop_table("timeline_events")

