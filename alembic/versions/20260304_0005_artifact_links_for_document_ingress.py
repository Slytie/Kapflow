"""Add artifact_links table for canonical attachment linkage.

Revision ID: 20260304_0005
Revises: 20260303_0004
Create Date: 2026-03-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260304_0005"
down_revision = "20260303_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact_links",
        sa.Column("artifact_version_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=False),
        sa.Column("subject_kind", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=128), nullable=False),
        sa.Column("relation_kind", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"],
            ["artifact_versions.artifact_version_id"],
        ),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.PrimaryKeyConstraint(
            "artifact_version_id",
            "subject_kind",
            "subject_id",
            name="pk_artifact_links",
        ),
        sa.UniqueConstraint(
            "artifact_version_id",
            "subject_kind",
            "subject_id",
            name="uq_artifact_links_subject",
        ),
    )
    op.create_index(
        "ix_artifact_links_subject",
        "artifact_links",
        ["workflow_run_id", "subject_kind", "subject_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_artifact_links_subject", table_name="artifact_links")
    op.drop_table("artifact_links")

