"""Add artifact version identity fields.

Revision ID: 20260624_0021
Revises: 20260624_0020
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260624_0021"
down_revision = "20260624_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artifact_versions",
        sa.Column("artifact_identity_profile", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "artifact_versions",
        sa.Column("artifact_identity_digest", sa.String(length=71), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("artifact_versions", "artifact_identity_digest")
    op.drop_column("artifact_versions", "artifact_identity_profile")
