"""Canonicalize artifact pointer identity around pointer_id.

Revision ID: 20260307_0008
Revises: 20260307_0007
Create Date: 2026-03-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260307_0008"
down_revision = "20260307_0007"
branch_labels = None
depends_on = None


_POINTER_COLUMNS = [
    "pointer_id",
    "workflow_run_id",
    "pointer_key",
    "tenant_id",
    "domain_id",
    "dataset_key",
    "partition_kind",
    "partition_key",
    "stream_key",
    "registry_kind",
    "scope_kind",
    "scope_ref",
    "artifact_kind",
    "artifact_version_id",
    "promotion_reason",
    "promoted_by_task_run_id",
    "approved_by_approval_id",
    "generation",
    "updated_at",
]


def upgrade() -> None:
    bind = op.get_bind()
    null_pointer_ids = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM artifact_pointers WHERE pointer_id IS NULL OR TRIM(pointer_id) = ''"
        )
    ).scalar_one()
    if int(null_pointer_ids) > 0:
        raise RuntimeError(
            "cannot upgrade artifact_pointers identity: found rows without canonical pointer_id; "
            "backfill pointer_id deterministically before upgrading"
        )

    op.rename_table("artifact_pointers", "artifact_pointers_legacy_identity")
    op.create_table(
        "artifact_pointers",
        sa.Column("pointer_id", sa.String(length=512), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("pointer_key", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
        sa.Column("domain_id", sa.String(length=128), nullable=True),
        sa.Column("dataset_key", sa.String(length=255), nullable=True),
        sa.Column("partition_kind", sa.String(length=64), nullable=True),
        sa.Column("partition_key", sa.String(length=255), nullable=True),
        sa.Column("stream_key", sa.String(length=255), nullable=True),
        sa.Column("registry_kind", sa.String(length=64), nullable=True),
        sa.Column("scope_kind", sa.String(length=64), nullable=False),
        sa.Column("scope_ref", sa.String(length=255), nullable=False),
        sa.Column("artifact_kind", sa.String(length=128), nullable=False),
        sa.Column("artifact_version_id", sa.String(length=128), nullable=False),
        sa.Column("promotion_reason", sa.String(length=255), nullable=True),
        sa.Column("promoted_by_task_run_id", sa.String(length=128), nullable=True),
        sa.Column("approved_by_approval_id", sa.String(length=128), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["artifact_version_id"], ["artifact_versions.artifact_version_id"]),
        sa.ForeignKeyConstraint(["promoted_by_task_run_id"], ["task_runs.task_run_id"]),
        sa.ForeignKeyConstraint(["approved_by_approval_id"], ["approvals.approval_id"]),
        sa.PrimaryKeyConstraint("pointer_id", name="pk_artifact_pointers"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "pointer_key",
            name="uq_artifact_pointers_workflow_pointer",
        ),
        sa.UniqueConstraint(
            "workflow_run_id",
            "scope_kind",
            "scope_ref",
            "artifact_kind",
            name="uq_artifact_pointers_scope",
        ),
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO artifact_pointers ({", ".join(_POINTER_COLUMNS)})
            SELECT {", ".join(_POINTER_COLUMNS)}
            FROM artifact_pointers_legacy_identity
            """
        )
    )
    op.drop_table("artifact_pointers_legacy_identity")

    op.create_index(
        "ix_artifact_pointers_workflow_scope",
        "artifact_pointers",
        ["workflow_run_id", "scope_kind", "scope_ref"],
        unique=False,
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


def downgrade() -> None:
    op.rename_table("artifact_pointers", "artifact_pointers_pointerid_identity")
    op.create_table(
        "artifact_pointers",
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("pointer_key", sa.String(length=255), nullable=False),
        sa.Column("pointer_id", sa.String(length=512), nullable=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
        sa.Column("domain_id", sa.String(length=128), nullable=True),
        sa.Column("dataset_key", sa.String(length=255), nullable=True),
        sa.Column("partition_kind", sa.String(length=64), nullable=True),
        sa.Column("partition_key", sa.String(length=255), nullable=True),
        sa.Column("stream_key", sa.String(length=255), nullable=True),
        sa.Column("registry_kind", sa.String(length=64), nullable=True),
        sa.Column("scope_kind", sa.String(length=64), nullable=False),
        sa.Column("scope_ref", sa.String(length=255), nullable=False),
        sa.Column("artifact_kind", sa.String(length=128), nullable=False),
        sa.Column("artifact_version_id", sa.String(length=128), nullable=False),
        sa.Column("promotion_reason", sa.String(length=255), nullable=True),
        sa.Column("promoted_by_task_run_id", sa.String(length=128), nullable=True),
        sa.Column("approved_by_approval_id", sa.String(length=128), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(["artifact_version_id"], ["artifact_versions.artifact_version_id"]),
        sa.ForeignKeyConstraint(["promoted_by_task_run_id"], ["task_runs.task_run_id"]),
        sa.ForeignKeyConstraint(["approved_by_approval_id"], ["approvals.approval_id"]),
        sa.PrimaryKeyConstraint("workflow_run_id", "pointer_key", name="pk_artifact_pointers"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "scope_kind",
            "scope_ref",
            "artifact_kind",
            name="uq_artifact_pointers_scope",
        ),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO artifact_pointers (
                workflow_run_id,
                pointer_key,
                pointer_id,
                tenant_id,
                domain_id,
                dataset_key,
                partition_kind,
                partition_key,
                stream_key,
                registry_kind,
                scope_kind,
                scope_ref,
                artifact_kind,
                artifact_version_id,
                promotion_reason,
                promoted_by_task_run_id,
                approved_by_approval_id,
                generation,
                updated_at
            )
            SELECT
                workflow_run_id,
                pointer_key,
                pointer_id,
                tenant_id,
                domain_id,
                dataset_key,
                partition_kind,
                partition_key,
                stream_key,
                registry_kind,
                scope_kind,
                scope_ref,
                artifact_kind,
                artifact_version_id,
                promotion_reason,
                promoted_by_task_run_id,
                approved_by_approval_id,
                generation,
                updated_at
            FROM artifact_pointers_pointerid_identity
            """
        )
    )
    op.drop_table("artifact_pointers_pointerid_identity")

    op.create_index(
        "ix_artifact_pointers_workflow_scope",
        "artifact_pointers",
        ["workflow_run_id", "scope_kind", "scope_ref"],
        unique=False,
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
