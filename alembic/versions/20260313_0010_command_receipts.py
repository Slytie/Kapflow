"""Add scoped command receipts for public mutation replay.

Revision ID: 20260313_0010
Revises: 20260307_0009
Create Date: 2026-03-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260313_0010"
down_revision = "20260307_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "command_receipts",
        sa.Column("command_receipt_id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("command_name", sa.String(length=128), nullable=False),
        sa.Column("scope_key", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
        sa.Column("domain_id", sa.String(length=128), nullable=True),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.PrimaryKeyConstraint("command_receipt_id", name="pk_command_receipts"),
        sa.UniqueConstraint(
            "command_name",
            "scope_key",
            "idempotency_key",
            name="uq_command_receipts_scope_idempotency",
        ),
    )
    op.create_index(
        "ix_command_receipts_workflow_run_id",
        "command_receipts",
        ["workflow_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_command_receipts_scope_lookup",
        "command_receipts",
        ["tenant_id", "domain_id", "command_name", "scope_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_command_receipts_scope_lookup", table_name="command_receipts")
    op.drop_index("ix_command_receipts_workflow_run_id", table_name="command_receipts")
    op.drop_table("command_receipts")
