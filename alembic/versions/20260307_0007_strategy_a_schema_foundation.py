"""Expand schema for Strategy A' pointer identity, provenance DAG, and input bindings.

Revision ID: 20260307_0007
Revises: 20260304_0006
Create Date: 2026-03-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260307_0007"
down_revision = "20260304_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artifact_versions",
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "artifact_versions",
        sa.Column("domain_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "artifact_versions",
        sa.Column("dataset_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "artifact_versions",
        sa.Column("partition_kind", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "artifact_versions",
        sa.Column("partition_key", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_artifact_versions_canonical_address",
        "artifact_versions",
        ["tenant_id", "domain_id", "dataset_key", "partition_kind", "partition_key"],
        unique=False,
    )

    op.add_column(
        "artifact_pointers",
        sa.Column("pointer_id", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "artifact_pointers",
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "artifact_pointers",
        sa.Column("domain_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "artifact_pointers",
        sa.Column("dataset_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "artifact_pointers",
        sa.Column("partition_kind", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "artifact_pointers",
        sa.Column("partition_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "artifact_pointers",
        sa.Column("stream_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "artifact_pointers",
        sa.Column("registry_kind", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_artifact_pointers_pointer_id",
        "artifact_pointers",
        ["pointer_id"],
        unique=True,
    )
    op.create_index(
        "ix_artifact_pointers_canonical_lookup",
        "artifact_pointers",
        ["tenant_id", "domain_id", "dataset_key", "partition_kind", "partition_key", "stream_key"],
        unique=False,
    )

    op.create_table(
        "artifact_provenance_edges",
        sa.Column("edge_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=True),
        sa.Column("output_artifact_version_id", sa.String(length=128), nullable=False),
        sa.Column("input_artifact_version_id", sa.String(length=128), nullable=False),
        sa.Column("edge_type", sa.String(length=64), nullable=False),
        sa.Column("edge_order", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.workflow_run_id"],
        ),
        sa.ForeignKeyConstraint(
            ["output_artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["input_artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.PrimaryKeyConstraint("edge_id", name="pk_artifact_provenance_edges"),
        sa.UniqueConstraint(
            "output_artifact_version_id",
            "input_artifact_version_id",
            "edge_type",
            "edge_order",
            name="uq_artifact_provenance_edges_dedup",
        ),
    )
    op.create_index(
        "ix_artifact_provenance_edges_output",
        "artifact_provenance_edges",
        ["output_artifact_version_id", "edge_type", "edge_order"],
        unique=False,
    )
    op.create_index(
        "ix_artifact_provenance_edges_input",
        "artifact_provenance_edges",
        ["input_artifact_version_id", "edge_type"],
        unique=False,
    )

    op.create_table(
        "workflow_run_inputs",
        sa.Column("workflow_run_input_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("binding_key", sa.String(length=255), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("artifact_version_id", sa.String(length=128), nullable=True),
        sa.Column("pointer_key", sa.String(length=255), nullable=True),
        sa.Column("pointer_generation", sa.Integer(), nullable=True),
        sa.Column("pointer_artifact_version_id", sa.String(length=128), nullable=True),
        sa.Column("captured_by_task_run_id", sa.String(length=128), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.workflow_run_id"],
        ),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["pointer_artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["captured_by_task_run_id"],
            ["task_runs.task_run_id"],
        ),
        sa.PrimaryKeyConstraint("workflow_run_input_id", name="pk_workflow_run_inputs"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "binding_key",
            name="uq_workflow_run_inputs_binding",
        ),
    )
    op.create_index(
        "ix_workflow_run_inputs_workflow_run_id",
        "workflow_run_inputs",
        ["workflow_run_id"],
        unique=False,
    )

    op.create_table(
        "task_input_bindings",
        sa.Column("task_input_binding_id", sa.String(length=128), nullable=False),
        sa.Column("task_run_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("binding_key", sa.String(length=255), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("artifact_version_id", sa.String(length=128), nullable=True),
        sa.Column("pointer_key", sa.String(length=255), nullable=True),
        sa.Column("pointer_generation", sa.Integer(), nullable=True),
        sa.Column("pointer_artifact_version_id", sa.String(length=128), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["task_run_id"],
            ["task_runs.task_run_id"],
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.workflow_run_id"],
        ),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["pointer_artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.PrimaryKeyConstraint("task_input_binding_id", name="pk_task_input_bindings"),
        sa.UniqueConstraint(
            "task_run_id",
            "binding_key",
            name="uq_task_input_bindings_binding",
        ),
    )
    op.create_index(
        "ix_task_input_bindings_task_run_id",
        "task_input_bindings",
        ["task_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_input_bindings_task_run_id", table_name="task_input_bindings")
    op.drop_table("task_input_bindings")

    op.drop_index("ix_workflow_run_inputs_workflow_run_id", table_name="workflow_run_inputs")
    op.drop_table("workflow_run_inputs")

    op.drop_index("ix_artifact_provenance_edges_input", table_name="artifact_provenance_edges")
    op.drop_index("ix_artifact_provenance_edges_output", table_name="artifact_provenance_edges")
    op.drop_table("artifact_provenance_edges")

    op.drop_index("ix_artifact_pointers_canonical_lookup", table_name="artifact_pointers")
    op.drop_index("ix_artifact_pointers_pointer_id", table_name="artifact_pointers")
    op.drop_column("artifact_pointers", "registry_kind")
    op.drop_column("artifact_pointers", "stream_key")
    op.drop_column("artifact_pointers", "partition_key")
    op.drop_column("artifact_pointers", "partition_kind")
    op.drop_column("artifact_pointers", "dataset_key")
    op.drop_column("artifact_pointers", "domain_id")
    op.drop_column("artifact_pointers", "tenant_id")
    op.drop_column("artifact_pointers", "pointer_id")

    op.drop_index("ix_artifact_versions_canonical_address", table_name="artifact_versions")
    op.drop_column("artifact_versions", "partition_key")
    op.drop_column("artifact_versions", "partition_kind")
    op.drop_column("artifact_versions", "dataset_key")
    op.drop_column("artifact_versions", "domain_id")
    op.drop_column("artifact_versions", "tenant_id")

