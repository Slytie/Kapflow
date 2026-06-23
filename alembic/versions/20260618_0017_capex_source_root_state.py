"""Add CAPEX desktop source-root observation state.

Revision ID: 20260618_0017
Revises: 20260610_0016
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260618_0017"
down_revision = "20260610_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capex_source_root_bindings",
        sa.Column("source_root_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("observer_mode", sa.String(length=64), nullable=False),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column("redacted_path_hint", sa.Text(), nullable=True),
        sa.Column("permission_basis", sa.String(length=128), nullable=False),
        sa.Column("sync_health", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("root_marker", sa.String(length=255), nullable=True),
        sa.Column("latest_snapshot_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("owner_actor_id", sa.String(length=128), nullable=False),
        sa.Column("owner_actor_type", sa.String(length=32), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
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
            "source_root_id",
            name="pk_capex_source_root_bindings",
        ),
    )
    op.create_index(
        "ix_capex_source_root_bindings_scope_status",
        "capex_source_root_bindings",
        ["tenant_id", "domain_id", "project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_capex_source_root_bindings_observer",
        "capex_source_root_bindings",
        ["tenant_id", "domain_id", "project_id", "observer_mode", "sync_health"],
        unique=False,
    )

    op.create_table(
        "capex_source_root_sync_runs",
        sa.Column("sync_run_id", sa.String(length=255), nullable=False),
        sa.Column("source_root_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("observer_mode", sa.String(length=64), nullable=False),
        sa.Column("observation_basis", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("started_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("started_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["source_root_id"],
            ["capex_source_root_bindings.source_root_id"],
        ),
        sa.PrimaryKeyConstraint(
            "sync_run_id",
            name="pk_capex_source_root_sync_runs",
        ),
    )
    op.create_index(
        "ix_capex_source_root_sync_runs_root_status",
        "capex_source_root_sync_runs",
        ["source_root_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_capex_source_root_sync_runs_scope_status",
        "capex_source_root_sync_runs",
        ["tenant_id", "domain_id", "project_id", "status"],
        unique=False,
    )

    op.create_table(
        "capex_folder_tree_snapshots",
        sa.Column("folder_tree_snapshot_id", sa.String(length=255), nullable=False),
        sa.Column("source_root_id", sa.String(length=255), nullable=False),
        sa.Column("sync_run_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("observation_basis", sa.String(length=128), nullable=False),
        sa.Column("path_scope", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("manifest_digest", sa.String(length=255), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.ForeignKeyConstraint(
            ["source_root_id"],
            ["capex_source_root_bindings.source_root_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sync_run_id"],
            ["capex_source_root_sync_runs.sync_run_id"],
        ),
        sa.PrimaryKeyConstraint(
            "folder_tree_snapshot_id",
            name="pk_capex_folder_tree_snapshots",
        ),
    )
    op.create_index(
        "ix_capex_folder_tree_snapshots_root_observed",
        "capex_folder_tree_snapshots",
        ["source_root_id", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_capex_folder_tree_snapshots_scope_status",
        "capex_folder_tree_snapshots",
        ["tenant_id", "domain_id", "project_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_capex_folder_tree_snapshots_scope_status",
        table_name="capex_folder_tree_snapshots",
    )
    op.drop_index(
        "ix_capex_folder_tree_snapshots_root_observed",
        table_name="capex_folder_tree_snapshots",
    )
    op.drop_table("capex_folder_tree_snapshots")
    op.drop_index(
        "ix_capex_source_root_sync_runs_scope_status",
        table_name="capex_source_root_sync_runs",
    )
    op.drop_index(
        "ix_capex_source_root_sync_runs_root_status",
        table_name="capex_source_root_sync_runs",
    )
    op.drop_table("capex_source_root_sync_runs")
    op.drop_index(
        "ix_capex_source_root_bindings_observer",
        table_name="capex_source_root_bindings",
    )
    op.drop_index(
        "ix_capex_source_root_bindings_scope_status",
        table_name="capex_source_root_bindings",
    )
    op.drop_table("capex_source_root_bindings")
