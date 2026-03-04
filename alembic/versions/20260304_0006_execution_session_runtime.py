"""Add execution session, tool execution, and policy decision tables.

Revision ID: 20260304_0006
Revises: 20260304_0005
Create Date: 2026-03-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260304_0006"
down_revision = "20260304_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_sessions",
        sa.Column("execution_session_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("task_run_id", sa.String(length=128), nullable=False),
        sa.Column("execution_spec_id", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("owner_mode", sa.String(length=32), nullable=False),
        sa.Column("principal_actor", sa.JSON(), nullable=True),
        sa.Column("budget", sa.JSON(), nullable=True),
        sa.Column(
            "tool_call_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
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
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["task_run_id"], ["task_runs.task_run_id"]),
        sa.PrimaryKeyConstraint("execution_session_id", name="pk_execution_sessions"),
    )
    op.create_index(
        "ix_execution_sessions_workflow_state",
        "execution_sessions",
        ["workflow_run_id", "state"],
        unique=False,
    )
    op.create_index(
        "ix_execution_sessions_task_run_id",
        "execution_sessions",
        ["task_run_id"],
        unique=False,
    )

    op.create_table(
        "tool_executions",
        sa.Column("tool_execution_id", sa.String(length=128), nullable=False),
        sa.Column("execution_session_id", sa.String(length=128), nullable=False),
        sa.Column("tool_class", sa.String(length=128), nullable=False),
        sa.Column("tool_name", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "attempt_no",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("policy_decision_id", sa.String(length=128), nullable=True),
        sa.Column("output_artifact_version_ids", sa.JSON(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["execution_session_id"],
            ["execution_sessions.execution_session_id"],
        ),
        sa.PrimaryKeyConstraint("tool_execution_id", name="pk_tool_executions"),
        sa.UniqueConstraint(
            "execution_session_id",
            "idempotency_key",
            name="uq_tool_executions_session_idempotency",
        ),
    )
    op.create_index(
        "ix_tool_executions_session_state",
        "tool_executions",
        ["execution_session_id", "state"],
        unique=False,
    )

    op.create_table(
        "policy_decisions",
        sa.Column("policy_decision_id", sa.String(length=128), nullable=False),
        sa.Column("principal_actor", sa.JSON(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.Column("required_approval_action", sa.String(length=128), nullable=True),
        sa.Column("tool_execution_id", sa.String(length=128), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tool_execution_id"],
            ["tool_executions.tool_execution_id"],
        ),
        sa.PrimaryKeyConstraint("policy_decision_id", name="pk_policy_decisions"),
        sa.UniqueConstraint(
            "tool_execution_id",
            name="uq_policy_decisions_tool_execution_id",
        ),
    )
    op.create_index(
        "ix_policy_decisions_tool_execution",
        "policy_decisions",
        ["tool_execution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_policy_decisions_tool_execution", table_name="policy_decisions")
    op.drop_table("policy_decisions")

    op.drop_index("ix_tool_executions_session_state", table_name="tool_executions")
    op.drop_table("tool_executions")

    op.drop_index("ix_execution_sessions_task_run_id", table_name="execution_sessions")
    op.drop_index("ix_execution_sessions_workflow_state", table_name="execution_sessions")
    op.drop_table("execution_sessions")
