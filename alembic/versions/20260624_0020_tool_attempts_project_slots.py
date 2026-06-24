"""Add tool execution attempts and CAPEX project runtime slots.

Revision ID: 20260624_0020
Revises: 20260624_0019
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260624_0020"
down_revision = "20260624_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_execution_attempts",
        sa.Column("tool_execution_attempt_id", sa.String(length=128), nullable=False),
        sa.Column("tool_execution_id", sa.String(length=128), nullable=False),
        sa.Column("execution_session_id", sa.String(length=128), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("active_tool_execution_id", sa.String(length=128), nullable=True),
        sa.Column("output_artifact_version_ids", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tool_execution_id"],
            ["tool_executions.tool_execution_id"],
        ),
        sa.ForeignKeyConstraint(
            ["execution_session_id"],
            ["execution_sessions.execution_session_id"],
        ),
        sa.PrimaryKeyConstraint(
            "tool_execution_attempt_id",
            name="pk_tool_execution_attempts",
        ),
        sa.UniqueConstraint(
            "tool_execution_id",
            "attempt_no",
            name="uq_tool_execution_attempts_tool_attempt_no",
        ),
        sa.UniqueConstraint(
            "tool_execution_id",
            "lease_token",
            name="uq_tool_execution_attempts_tool_lease",
        ),
        sa.UniqueConstraint(
            "active_tool_execution_id",
            name="uq_tool_execution_attempts_active_tool",
        ),
    )
    op.create_index(
        "ix_tool_execution_attempts_tool_state",
        "tool_execution_attempts",
        ["tool_execution_id", "state", "attempt_no"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_attempts_session_state",
        "tool_execution_attempts",
        ["execution_session_id", "state"],
        unique=False,
    )

    op.create_table(
        "capex_project_concurrency_policies",
        sa.Column("project_concurrency_policy_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("lock_family", sa.String(length=64), nullable=False),
        sa.Column("max_active_slots", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("policy_version", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.PrimaryKeyConstraint(
            "project_concurrency_policy_id",
            name="pk_capex_project_concurrency_policies",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "project_id",
            "lock_family",
            name="uq_capex_project_concurrency_policy_family",
        ),
    )
    op.create_index(
        "ix_capex_project_concurrency_policies_scope",
        "capex_project_concurrency_policies",
        ["tenant_id", "domain_id", "project_id", "state"],
        unique=False,
    )

    op.create_table(
        "capex_project_runtime_slots",
        sa.Column("project_runtime_slot_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("lock_family", sa.String(length=64), nullable=False),
        sa.Column("slot_key", sa.String(length=255), nullable=False),
        sa.Column("holder_ref", sa.String(length=255), nullable=False),
        sa.Column("lease_token", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("active_family_key", sa.String(length=512), nullable=True),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.PrimaryKeyConstraint(
            "project_runtime_slot_id",
            name="pk_capex_project_runtime_slots",
        ),
        sa.UniqueConstraint(
            "active_family_key",
            name="uq_capex_project_runtime_slots_active_family",
        ),
    )
    op.create_index(
        "ix_capex_project_runtime_slots_scope_state",
        "capex_project_runtime_slots",
        ["tenant_id", "domain_id", "project_id", "lock_family", "state"],
        unique=False,
    )
    op.create_index(
        "ix_capex_project_runtime_slots_slot_key",
        "capex_project_runtime_slots",
        ["tenant_id", "domain_id", "project_id", "lock_family", "slot_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_capex_project_runtime_slots_slot_key",
        table_name="capex_project_runtime_slots",
    )
    op.drop_index(
        "ix_capex_project_runtime_slots_scope_state",
        table_name="capex_project_runtime_slots",
    )
    op.drop_table("capex_project_runtime_slots")

    op.drop_index(
        "ix_capex_project_concurrency_policies_scope",
        table_name="capex_project_concurrency_policies",
    )
    op.drop_table("capex_project_concurrency_policies")

    op.drop_index(
        "ix_tool_execution_attempts_session_state",
        table_name="tool_execution_attempts",
    )
    op.drop_index(
        "ix_tool_execution_attempts_tool_state",
        table_name="tool_execution_attempts",
    )
    op.drop_table("tool_execution_attempts")
