"""Add CAPEX authorization projection read models.

Revision ID: 20260605_0012
Revises: 20260604_0011
Create Date: 2026-06-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260605_0012"
down_revision = "20260604_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capex_project_authorization",
        sa.Column("project_authorization_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("direct_role", sa.String(length=64), nullable=False),
        sa.Column("effective_role", sa.String(length=64), nullable=False),
        sa.Column("source_membership_id", sa.String(length=128), nullable=False),
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
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.ForeignKeyConstraint(
            ["source_membership_id"],
            ["project_memberships.project_membership_id"],
        ),
        sa.PrimaryKeyConstraint(
            "project_authorization_id",
            name="pk_capex_project_authorization",
        ),
        sa.UniqueConstraint(
            "project_id",
            "actor_type",
            "actor_id",
            name="uq_capex_project_authorization_actor",
        ),
    )
    op.create_index(
        "ix_capex_project_authorization_actor_lookup",
        "capex_project_authorization",
        ["tenant_id", "domain_id", "actor_type", "actor_id", "state"],
        unique=False,
    )
    op.create_index(
        "ix_capex_project_authorization_project_state",
        "capex_project_authorization",
        ["project_id", "state"],
        unique=False,
    )

    op.create_table(
        "capex_project_feature",
        sa.Column("project_feature_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("feature_key", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
        sa.PrimaryKeyConstraint("project_feature_id", name="pk_capex_project_feature"),
        sa.UniqueConstraint(
            "project_id",
            "feature_key",
            name="uq_capex_project_feature_key",
        ),
    )
    op.create_index(
        "ix_capex_project_feature_lookup",
        "capex_project_feature",
        ["tenant_id", "domain_id", "feature_key", "state"],
        unique=False,
    )

    op.create_table(
        "capex_user_project_view",
        sa.Column("user_project_view_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("project_key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("project_state", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
        sa.Column("project_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("project_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("caller_role", sa.String(length=64), nullable=False),
        sa.Column("authorization_state", sa.String(length=32), nullable=False),
        sa.Column("source_authorization_id", sa.String(length=255), nullable=False),
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
            ["source_authorization_id"],
            ["capex_project_authorization.project_authorization_id"],
        ),
        sa.PrimaryKeyConstraint(
            "user_project_view_id",
            name="pk_capex_user_project_view",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "actor_type",
            "actor_id",
            "project_id",
            name="uq_capex_user_project_view_actor_project",
        ),
    )
    op.create_index(
        "ix_capex_user_project_view_actor_lookup",
        "capex_user_project_view",
        [
            "tenant_id",
            "domain_id",
            "actor_type",
            "actor_id",
            "authorization_state",
            "project_state",
            "project_key",
        ],
        unique=False,
    )

    _backfill_projection_rows()


def downgrade() -> None:
    op.drop_index(
        "ix_capex_user_project_view_actor_lookup",
        table_name="capex_user_project_view",
    )
    op.drop_table("capex_user_project_view")
    op.drop_index("ix_capex_project_feature_lookup", table_name="capex_project_feature")
    op.drop_table("capex_project_feature")
    op.drop_index(
        "ix_capex_project_authorization_project_state",
        table_name="capex_project_authorization",
    )
    op.drop_index(
        "ix_capex_project_authorization_actor_lookup",
        table_name="capex_project_authorization",
    )
    op.drop_table("capex_project_authorization")


def _backfill_projection_rows() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql(
        """
        INSERT INTO capex_project_authorization (
            project_authorization_id,
            project_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            direct_role,
            effective_role,
            source_membership_id,
            state,
            created_at,
            updated_at
        )
        SELECT
            'cpa:' || pm.project_id || ':' || pm.actor_type || ':' || pm.actor_id,
            pm.project_id,
            pm.tenant_id,
            pm.domain_id,
            pm.actor_type,
            pm.actor_id,
            pm.role,
            pm.role,
            pm.project_membership_id,
            'active',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM project_memberships pm
        JOIN capex_projects cp
          ON cp.project_id = pm.project_id
         AND cp.tenant_id = pm.tenant_id
         AND cp.domain_id = pm.domain_id
        WHERE pm.state = 'active'
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO capex_project_feature (
            project_feature_id,
            project_id,
            tenant_id,
            domain_id,
            feature_key,
            state,
            blocked_reason,
            metadata_json,
            created_at,
            updated_at
        )
        SELECT
            'cpf:' || cp.project_id || ':capex.runtime_activation',
            cp.project_id,
            cp.tenant_id,
            cp.domain_id,
            'capex.runtime_activation',
            'disabled',
            'capex_runtime_activation_blocked_by_future_gates',
            '{"owner_task_ref":"TASK-0563"}',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM capex_projects cp
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO capex_user_project_view (
            user_project_view_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            project_id,
            project_key,
            name,
            project_state,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            project_created_at,
            project_updated_at,
            caller_role,
            authorization_state,
            source_authorization_id,
            created_at,
            updated_at
        )
        SELECT
            'cpuv:' || cpa.project_id || ':' || cpa.actor_type || ':' || cpa.actor_id,
            cpa.tenant_id,
            cpa.domain_id,
            cpa.actor_type,
            cpa.actor_id,
            cp.project_id,
            cp.project_key,
            cp.name,
            cp.state,
            cp.metadata_json,
            cp.created_by_actor_id,
            cp.created_by_actor_type,
            cp.created_at,
            cp.updated_at,
            cpa.effective_role,
            cpa.state,
            cpa.project_authorization_id,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM capex_project_authorization cpa
        JOIN capex_projects cp
          ON cp.project_id = cpa.project_id
         AND cp.tenant_id = cpa.tenant_id
         AND cp.domain_id = cpa.domain_id
        WHERE cpa.state = 'active'
        """
    )
