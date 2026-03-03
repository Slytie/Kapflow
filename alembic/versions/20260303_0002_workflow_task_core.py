"""Add workflow/task/human-task core tables.

Revision ID: 20260303_0002
Revises: 20260303_0001
Create Date: 2026-03-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260303_0002"
down_revision = "20260303_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_version", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("partition_key", sa.String(length=128), nullable=False),
        sa.Column("logical_date", sa.String(length=64), nullable=True),
        sa.Column("activation_key", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
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
        sa.PrimaryKeyConstraint("workflow_run_id", name="pk_workflow_runs"),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "workflow_id",
            "partition_key",
            "activation_key",
            name="uq_workflow_runs_activation_scope",
        ),
    )
    op.create_index(
        "ix_workflow_runs_scope_lookup",
        "workflow_runs",
        ["tenant_id", "domain_id", "workflow_id", "partition_key"],
        unique=False,
    )

    op.create_table(
        "task_runs",
        sa.Column("task_run_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("stage_id", sa.String(length=128), nullable=False),
        sa.Column("task_kind", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("activation_key", sa.String(length=255), nullable=False),
        sa.Column("blocked_on_kind", sa.String(length=64), nullable=True),
        sa.Column("blocked_on_ref", sa.String(length=255), nullable=True),
        sa.Column("spawned_from_task_run_id", sa.String(length=128), nullable=True),
        sa.Column("spawn_rule_id", sa.String(length=128), nullable=True),
        sa.Column("spawn_cause_kind", sa.String(length=64), nullable=True),
        sa.Column("spawn_cause_event_id", sa.String(length=128), nullable=True),
        sa.Column("spawn_depth", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("spawn_budget_key", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["spawned_from_task_run_id"], ["task_runs.task_run_id"]),
        sa.PrimaryKeyConstraint("task_run_id", name="pk_task_runs"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "activation_key",
            name="uq_task_runs_activation_scope",
        ),
    )
    op.create_index(
        "ix_task_runs_workflow_run_id",
        "task_runs",
        ["workflow_run_id"],
        unique=False,
    )

    op.create_table(
        "human_tasks",
        sa.Column("human_task_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("task_run_id", sa.String(length=128), nullable=False),
        sa.Column("task_kind", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("candidate_roles", sa.JSON(), nullable=False),
        sa.Column("owner_role", sa.String(length=128), nullable=True),
        sa.Column("assignee_actor_id", sa.String(length=128), nullable=True),
        sa.Column("assignee_actor_type", sa.String(length=32), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_approval_id", sa.String(length=128), nullable=True),
        sa.Column("reopen_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("generation", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["task_run_id"], ["task_runs.task_run_id"]),
        sa.PrimaryKeyConstraint("human_task_id", name="pk_human_tasks"),
        sa.UniqueConstraint("task_run_id", name="uq_human_tasks_task_run_id"),
    )
    op.create_index(
        "ix_human_tasks_workflow_state",
        "human_tasks",
        ["workflow_run_id", "state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_human_tasks_workflow_state", table_name="human_tasks")
    op.drop_table("human_tasks")
    op.drop_index("ix_task_runs_workflow_run_id", table_name="task_runs")
    op.drop_table("task_runs")
    op.drop_index("ix_workflow_runs_scope_lookup", table_name="workflow_runs")
    op.drop_table("workflow_runs")

