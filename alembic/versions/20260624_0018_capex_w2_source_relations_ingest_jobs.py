"""Add CAPEX W2 source relation and ingest job state.

Revision ID: 20260624_0018
Revises: 20260618_0017
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260624_0018"
down_revision = "20260618_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capex_source_occurrence_relations",
        sa.Column("source_occurrence_relation_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("source_occurrence_id", sa.String(length=255), nullable=False),
        sa.Column("target_source_occurrence_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("basis_ref", sa.String(length=512), nullable=False),
        sa.Column("policy_version", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
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
            ["source_occurrence_id"],
            ["capex_source_occurrences.source_occurrence_id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_source_occurrence_id"],
            ["capex_source_occurrences.source_occurrence_id"],
        ),
        sa.PrimaryKeyConstraint(
            "source_occurrence_relation_id",
            name="pk_capex_source_occurrence_relations",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "project_id",
            "relation_type",
            "source_occurrence_id",
            "target_source_occurrence_id",
            name="uq_capex_source_occurrence_relations_pair",
        ),
    )
    op.create_index(
        "ix_capex_source_occurrence_relations_source",
        "capex_source_occurrence_relations",
        ["source_occurrence_id", "relation_type", "status"],
        unique=False,
    )
    op.create_index(
        "ix_capex_source_occurrence_relations_target",
        "capex_source_occurrence_relations",
        ["target_source_occurrence_id", "relation_type", "status"],
        unique=False,
    )
    op.create_index(
        "ix_capex_source_occurrence_relations_scope_type",
        "capex_source_occurrence_relations",
        ["tenant_id", "domain_id", "project_id", "relation_type", "status"],
        unique=False,
    )

    op.create_table(
        "capex_ingest_batches",
        sa.Column("ingest_batch_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("intake_ref", sa.String(length=512), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "descriptor_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_actor_id", sa.String(length=128), nullable=False),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=False),
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
        sa.PrimaryKeyConstraint("ingest_batch_id", name="pk_capex_ingest_batches"),
        sa.UniqueConstraint(
            "tenant_id",
            "domain_id",
            "project_id",
            "idempotency_key",
            name="uq_capex_ingest_batches_scope_idempotency",
        ),
    )
    op.create_index(
        "ix_capex_ingest_batches_scope_status",
        "capex_ingest_batches",
        ["tenant_id", "domain_id", "project_id", "status"],
        unique=False,
    )

    op.create_table(
        "capex_ingest_jobs",
        sa.Column("ingest_job_id", sa.String(length=255), nullable=False),
        sa.Column("ingest_batch_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("job_kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("command_receipt_id", sa.Integer(), nullable=True),
        sa.Column("planned_task_refs_json", sa.JSON(), nullable=False),
        sa.Column("planned_artifact_refs_json", sa.JSON(), nullable=False),
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
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingest_batch_id"],
            ["capex_ingest_batches.ingest_batch_id"],
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.ForeignKeyConstraint(
            ["command_receipt_id"],
            ["command_receipts.command_receipt_id"],
        ),
        sa.PrimaryKeyConstraint("ingest_job_id", name="pk_capex_ingest_jobs"),
        sa.UniqueConstraint(
            "ingest_batch_id",
            "job_kind",
            "idempotency_key",
            name="uq_capex_ingest_jobs_batch_kind_idempotency",
        ),
    )
    op.create_index(
        "ix_capex_ingest_jobs_batch_status",
        "capex_ingest_jobs",
        ["ingest_batch_id", "status", "priority", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_capex_ingest_jobs_scope_status",
        "capex_ingest_jobs",
        ["tenant_id", "domain_id", "project_id", "status"],
        unique=False,
    )

    op.create_table(
        "capex_ingest_attempts",
        sa.Column("ingest_attempt_id", sa.String(length=255), nullable=False),
        sa.Column("ingest_job_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("execution_session_id", sa.String(length=128), nullable=True),
        sa.Column("command_receipt_id", sa.Integer(), nullable=True),
        sa.Column("lease_token", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["ingest_job_id"],
            ["capex_ingest_jobs.ingest_job_id"],
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.ForeignKeyConstraint(
            ["execution_session_id"],
            ["execution_sessions.execution_session_id"],
        ),
        sa.ForeignKeyConstraint(
            ["command_receipt_id"],
            ["command_receipts.command_receipt_id"],
        ),
        sa.PrimaryKeyConstraint(
            "ingest_attempt_id",
            name="pk_capex_ingest_attempts",
        ),
        sa.UniqueConstraint(
            "ingest_job_id",
            "attempt_no",
            name="uq_capex_ingest_attempts_job_attempt_no",
        ),
    )
    op.create_index(
        "ix_capex_ingest_attempts_job_status",
        "capex_ingest_attempts",
        ["ingest_job_id", "status", "attempt_no"],
        unique=False,
    )
    op.create_index(
        "ix_capex_ingest_attempts_execution_session",
        "capex_ingest_attempts",
        ["execution_session_id"],
        unique=False,
    )

    op.create_table(
        "capex_ingest_job_logs",
        sa.Column("ingest_job_log_id", sa.String(length=255), nullable=False),
        sa.Column("ingest_job_id", sa.String(length=255), nullable=False),
        sa.Column("ingest_attempt_id", sa.String(length=255), nullable=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("log_kind", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("message_code", sa.String(length=128), nullable=False),
        sa.Column("message_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["ingest_job_id"],
            ["capex_ingest_jobs.ingest_job_id"],
        ),
        sa.ForeignKeyConstraint(
            ["ingest_attempt_id"],
            ["capex_ingest_attempts.ingest_attempt_id"],
        ),
        sa.ForeignKeyConstraint(["project_id"], ["capex_projects.project_id"]),
        sa.PrimaryKeyConstraint(
            "ingest_job_log_id",
            name="pk_capex_ingest_job_logs",
        ),
    )
    op.create_index(
        "ix_capex_ingest_job_logs_job_created",
        "capex_ingest_job_logs",
        ["ingest_job_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_capex_ingest_job_logs_attempt_created",
        "capex_ingest_job_logs",
        ["ingest_attempt_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_capex_ingest_job_logs_scope_kind",
        "capex_ingest_job_logs",
        ["tenant_id", "domain_id", "project_id", "log_kind", "severity"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_capex_ingest_job_logs_scope_kind",
        table_name="capex_ingest_job_logs",
    )
    op.drop_index(
        "ix_capex_ingest_job_logs_attempt_created",
        table_name="capex_ingest_job_logs",
    )
    op.drop_index(
        "ix_capex_ingest_job_logs_job_created",
        table_name="capex_ingest_job_logs",
    )
    op.drop_table("capex_ingest_job_logs")
    op.drop_index(
        "ix_capex_ingest_attempts_execution_session",
        table_name="capex_ingest_attempts",
    )
    op.drop_index(
        "ix_capex_ingest_attempts_job_status",
        table_name="capex_ingest_attempts",
    )
    op.drop_table("capex_ingest_attempts")
    op.drop_index(
        "ix_capex_ingest_jobs_scope_status",
        table_name="capex_ingest_jobs",
    )
    op.drop_index(
        "ix_capex_ingest_jobs_batch_status",
        table_name="capex_ingest_jobs",
    )
    op.drop_table("capex_ingest_jobs")
    op.drop_index(
        "ix_capex_ingest_batches_scope_status",
        table_name="capex_ingest_batches",
    )
    op.drop_table("capex_ingest_batches")
    op.drop_index(
        "ix_capex_source_occurrence_relations_scope_type",
        table_name="capex_source_occurrence_relations",
    )
    op.drop_index(
        "ix_capex_source_occurrence_relations_target",
        table_name="capex_source_occurrence_relations",
    )
    op.drop_index(
        "ix_capex_source_occurrence_relations_source",
        table_name="capex_source_occurrence_relations",
    )
    op.drop_table("capex_source_occurrence_relations")
