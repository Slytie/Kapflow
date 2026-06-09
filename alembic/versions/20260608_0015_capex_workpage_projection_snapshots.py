"""Add CAPEX workpage projection snapshot runtime state.

Revision ID: 20260608_0015
Revises: 20260608_0014
Create Date: 2026-06-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260608_0015"
down_revision = "20260608_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capex_workpage_projection_snapshots",
        sa.Column("projection_snapshot_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("workpage_kind", sa.String(length=128), nullable=False),
        sa.Column("projection_kind", sa.String(length=128), nullable=False),
        sa.Column("renderer_version", sa.String(length=64), nullable=False),
        sa.Column("basis_version_vector_json", sa.JSON(), nullable=False),
        sa.Column("basis_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("payload_metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
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
            "projection_snapshot_id",
            name="pk_capex_workpage_projection_snapshots",
        ),
    )
    op.create_index(
        "ix_capex_workpage_projection_snapshots_scope_state",
        "capex_workpage_projection_snapshots",
        ["tenant_id", "domain_id", "project_id", "workpage_kind", "state"],
        unique=False,
    )
    op.create_index(
        "ix_capex_workpage_projection_snapshots_basis",
        "capex_workpage_projection_snapshots",
        ["tenant_id", "domain_id", "project_id", "basis_hash"],
        unique=False,
    )

    op.create_table(
        "capex_workpage_projection_rows",
        sa.Column("projection_row_id", sa.String(length=255), nullable=False),
        sa.Column("projection_snapshot_id", sa.String(length=255), nullable=False),
        sa.Column("row_key", sa.String(length=255), nullable=False),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("subject_kind", sa.String(length=128), nullable=False),
        sa.Column("subject_ref", sa.String(length=255), nullable=False),
        sa.Column("row_payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["projection_snapshot_id"],
            ["capex_workpage_projection_snapshots.projection_snapshot_id"],
        ),
        sa.PrimaryKeyConstraint(
            "projection_row_id",
            name="pk_capex_workpage_projection_rows",
        ),
        sa.UniqueConstraint(
            "projection_snapshot_id",
            "row_key",
            name="uq_capex_workpage_projection_rows_snapshot_key",
        ),
    )
    op.create_index(
        "ix_capex_workpage_projection_rows_snapshot_order",
        "capex_workpage_projection_rows",
        ["projection_snapshot_id", "row_order", "row_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_capex_workpage_projection_rows_snapshot_order",
        table_name="capex_workpage_projection_rows",
    )
    op.drop_table("capex_workpage_projection_rows")
    op.drop_index(
        "ix_capex_workpage_projection_snapshots_basis",
        table_name="capex_workpage_projection_snapshots",
    )
    op.drop_index(
        "ix_capex_workpage_projection_snapshots_scope_state",
        table_name="capex_workpage_projection_snapshots",
    )
    op.drop_table("capex_workpage_projection_snapshots")
