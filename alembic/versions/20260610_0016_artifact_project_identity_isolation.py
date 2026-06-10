"""Add project identity to artifact versions and provenance edges.

Revision ID: 20260610_0016
Revises: 20260608_0015
Create Date: 2026-06-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260610_0016"
down_revision = "20260608_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artifact_versions",
        sa.Column("project_id", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE artifact_versions
        SET project_id = (
            SELECT workflow_runs.project_id
            FROM workflow_runs
            WHERE workflow_runs.workflow_run_id = artifact_versions.workflow_run_id
        )
        WHERE project_id IS NULL
        """
    )
    op.create_index(
        "ix_artifact_versions_project_scope",
        "artifact_versions",
        ["tenant_id", "domain_id", "project_id", "artifact_kind", "created_at"],
        unique=False,
    )

    op.add_column(
        "artifact_provenance_edges",
        sa.Column("project_id", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE artifact_provenance_edges
        SET project_id = (
            SELECT artifact_versions.project_id
            FROM artifact_versions
            WHERE artifact_versions.artifact_version_id =
                artifact_provenance_edges.output_artifact_version_id
        )
        WHERE project_id IS NULL
        """
    )
    op.create_index(
        "ix_artifact_provenance_edges_project",
        "artifact_provenance_edges",
        ["project_id", "output_artifact_version_id", "edge_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_artifact_provenance_edges_project",
        table_name="artifact_provenance_edges",
    )
    op.drop_column("artifact_provenance_edges", "project_id")
    op.drop_index("ix_artifact_versions_project_scope", table_name="artifact_versions")
    op.drop_column("artifact_versions", "project_id")
