"""Add Stage07 flags table and task-run flag lineage column.

Revision ID: 20260303_0004
Revises: 20260303_0003
Create Date: 2026-03-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260303_0004"
down_revision = "20260303_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flags",
        sa.Column("flag_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("partition_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("assigned_group", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column("source_event_id", sa.String(length=128), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.PrimaryKeyConstraint("flag_id", name="pk_flags"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "dedupe_key",
            name="uq_flags_workflow_dedupe_key",
        ),
    )
    op.create_index(
        "ix_flags_workflow_state",
        "flags",
        ["workflow_run_id", "state"],
        unique=False,
    )
    op.create_index(
        "ix_flags_scope_lookup",
        "flags",
        ["tenant_id", "domain_id", "workflow_id", "partition_key", "state"],
        unique=False,
    )

    with op.batch_alter_table("task_runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("spawned_from_flag_id", sa.String(length=128), nullable=True))
        batch_op.create_index(
            "ix_task_runs_spawned_from_flag_id",
            ["spawned_from_flag_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_task_runs_spawned_from_flag_id_flags",
            "flags",
            ["spawned_from_flag_id"],
            ["flag_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("task_runs", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_task_runs_spawned_from_flag_id_flags",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_task_runs_spawned_from_flag_id")
        batch_op.drop_column("spawned_from_flag_id")

    op.drop_index("ix_flags_scope_lookup", table_name="flags")
    op.drop_index("ix_flags_workflow_state", table_name="flags")
    op.drop_table("flags")
