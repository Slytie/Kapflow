"""Add command receipt hash profile and effect ledger entries.

Revision ID: 20260624_0019
Revises: 20260624_0018
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260624_0019"
down_revision = "20260624_0018"
branch_labels = None
depends_on = None

COMMAND_RECEIPT_INPUT_HASH_PROFILE = (
    "onetruth.command_receipt_input.canonical_json.sha256.v1"
)


def upgrade() -> None:
    op.alter_column(
        "command_receipts",
        "request_fingerprint",
        existing_type=sa.String(length=64),
        type_=sa.String(length=71),
        existing_nullable=False,
    )
    op.add_column(
        "command_receipts",
        sa.Column(
            "request_fingerprint_profile",
            sa.String(length=128),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE command_receipts
            SET request_fingerprint_profile = :profile
            WHERE request_fingerprint_profile IS NULL
               OR request_fingerprint_profile = ''
            """
        ).bindparams(profile=COMMAND_RECEIPT_INPUT_HASH_PROFILE)
    )
    op.execute(
        """
        UPDATE command_receipts
        SET request_fingerprint = 'sha256:' || request_fingerprint
        WHERE length(request_fingerprint) = 64
          AND request_fingerprint NOT LIKE 'sha256:%'
        """
    )
    op.alter_column(
        "command_receipts",
        "request_fingerprint_profile",
        existing_type=sa.String(length=128),
        nullable=False,
    )

    op.create_table(
        "effect_ledger_entries",
        sa.Column("effect_ledger_entry_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("domain_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=128), nullable=True),
        sa.Column("command_name", sa.String(length=128), nullable=False),
        sa.Column("scope_key", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=71), nullable=False),
        sa.Column("request_fingerprint_profile", sa.String(length=128), nullable=False),
        sa.Column("effect_key", sa.String(length=255), nullable=False),
        sa.Column("effect_kind", sa.String(length=64), nullable=False),
        sa.Column("target_kind", sa.String(length=64), nullable=False),
        sa.Column("target_ref", sa.String(length=255), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.PrimaryKeyConstraint(
            "effect_ledger_entry_id",
            name="pk_effect_ledger_entries",
        ),
        sa.UniqueConstraint(
            "command_name",
            "scope_key",
            "idempotency_key",
            "effect_key",
            name="uq_effect_ledger_command_effect",
        ),
    )
    op.create_index(
        "ix_effect_ledger_entries_scope_status",
        "effect_ledger_entries",
        ["tenant_id", "domain_id", "command_name", "scope_key", "status"],
        unique=False,
    )
    op.create_index(
        "ix_effect_ledger_entries_target",
        "effect_ledger_entries",
        ["target_kind", "target_ref"],
        unique=False,
    )
    op.create_index(
        "ix_effect_ledger_entries_workflow_run_id",
        "effect_ledger_entries",
        ["workflow_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_effect_ledger_entries_workflow_run_id",
        table_name="effect_ledger_entries",
    )
    op.drop_index("ix_effect_ledger_entries_target", table_name="effect_ledger_entries")
    op.drop_index(
        "ix_effect_ledger_entries_scope_status",
        table_name="effect_ledger_entries",
    )
    op.drop_table("effect_ledger_entries")
    op.execute(
        """
        UPDATE command_receipts
        SET request_fingerprint = substr(request_fingerprint, 8)
        WHERE request_fingerprint LIKE 'sha256:%'
          AND length(request_fingerprint) = 71
        """
    )
    op.drop_column("command_receipts", "request_fingerprint_profile")
    op.alter_column(
        "command_receipts",
        "request_fingerprint",
        existing_type=sa.String(length=71),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
