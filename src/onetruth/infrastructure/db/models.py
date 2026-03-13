from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for runtime persistence models."""


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_timeline_events_idempotency_key"),
    )

    sequence_no: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_at: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_run_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    actor: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    links: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    causation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    integrity: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ConsumerCursor(Base):
    __tablename__ = "consumer_cursors"

    consumer_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    domain_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class CommandReceipt(Base):
    __tablename__ = "command_receipts"
    __table_args__ = (
        UniqueConstraint(
            "command_name",
            "scope_key",
            "idempotency_key",
            name="uq_command_receipts_scope_idempotency",
        ),
        Index(
            "ix_command_receipts_workflow_run_id",
            "workflow_run_id",
        ),
        Index(
            "ix_command_receipts_scope_lookup",
            "tenant_id",
            "domain_id",
            "command_name",
            "scope_key",
        ),
    )

    command_receipt_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command_name: Mapped[str] = mapped_column(String(128), nullable=False)
    scope_key: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    domain_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    workflow_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "domain_id",
            "workflow_id",
            "partition_key",
            "activation_key",
            name="uq_workflow_runs_activation_scope",
        ),
    )

    workflow_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False)
    partition_key: Mapped[str] = mapped_column(String(128), nullable=False)
    logical_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    activation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class TaskRun(Base):
    __tablename__ = "task_runs"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "activation_key",
            name="uq_task_runs_activation_scope",
        ),
    )

    task_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    blocked_on_kind: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    blocked_on_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    spawned_from_flag_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("flags.flag_id"),
        nullable=True,
        index=True,
    )
    spawned_from_task_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
    )
    spawn_rule_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    spawn_cause_kind: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    spawn_cause_event_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    spawn_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spawn_budget_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class HumanTask(Base):
    __tablename__ = "human_tasks"
    __table_args__ = (
        UniqueConstraint("task_run_id", name="uq_human_tasks_task_run_id"),
    )

    human_task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    task_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=False,
    )
    task_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_roles: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    owner_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    assignee_actor_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    assignee_actor_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_approval_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reopen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class Approval(Base):
    __tablename__ = "approvals"

    approval_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    task_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
        index=True,
    )
    approval_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by_task_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
    )
    candidate_roles: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    required_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    response_kind: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    response_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by_actor_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decided_by_actor_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"
    __table_args__ = (
        Index(
            "ix_artifact_versions_canonical_address",
            "tenant_id",
            "domain_id",
            "dataset_key",
            "partition_kind",
            "partition_key",
        ),
    )

    artifact_version_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    domain_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    dataset_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    partition_kind: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    partition_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    task_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
        index=True,
    )
    artifact_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_digest: Mapped[str] = mapped_column(String(255), nullable=False)
    byte_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    parent_artifact_version_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    supersedes_artifact_version_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    lineage_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ArtifactPointer(Base):
    __tablename__ = "artifact_pointers"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "pointer_key",
            name="uq_artifact_pointers_workflow_pointer",
        ),
        UniqueConstraint(
            "workflow_run_id",
            "scope_kind",
            "scope_ref",
            "artifact_kind",
            name="uq_artifact_pointers_scope",
        ),
        Index("ix_artifact_pointers_pointer_id", "pointer_id", unique=True),
        Index(
            "ix_artifact_pointers_workflow_scope",
            "workflow_run_id",
            "scope_kind",
            "scope_ref",
        ),
        Index(
            "ix_artifact_pointers_canonical_lookup",
            "tenant_id",
            "domain_id",
            "dataset_key",
            "partition_kind",
            "partition_key",
            "stream_key",
        ),
    )

    pointer_id: Mapped[str] = mapped_column(String(512), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    pointer_key: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    domain_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    dataset_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    partition_kind: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    partition_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stream_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    registry_kind: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scope_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_version_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=False,
    )
    promotion_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    promoted_by_task_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
    )
    approved_by_approval_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("approvals.approval_id"),
        nullable=True,
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class ArtifactProvenanceEdge(Base):
    __tablename__ = "artifact_provenance_edges"
    __table_args__ = (
        UniqueConstraint(
            "output_artifact_version_id",
            "input_artifact_version_id",
            "edge_type",
            "edge_order",
            name="uq_artifact_provenance_edges_dedup",
        ),
        Index(
            "ix_artifact_provenance_edges_output",
            "output_artifact_version_id",
            "edge_type",
            "edge_order",
        ),
        Index(
            "ix_artifact_provenance_edges_input",
            "input_artifact_version_id",
            "edge_type",
        ),
    )

    edge_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=True,
    )
    output_artifact_version_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=False,
    )
    input_artifact_version_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=False,
    )
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    edge_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class WorkflowRunInput(Base):
    __tablename__ = "workflow_run_inputs"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "binding_key",
            name="uq_workflow_run_inputs_binding",
        ),
        Index("ix_workflow_run_inputs_workflow_run_id", "workflow_run_id"),
    )

    workflow_run_input_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
    )
    binding_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_version_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    pointer_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pointer_generation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pointer_artifact_version_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    captured_by_task_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class TaskInputBinding(Base):
    __tablename__ = "task_input_bindings"
    __table_args__ = (
        UniqueConstraint(
            "task_run_id",
            "binding_key",
            name="uq_task_input_bindings_binding",
        ),
        Index("ix_task_input_bindings_task_run_id", "task_run_id"),
    )

    task_input_binding_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    task_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=False,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
    )
    binding_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_version_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    pointer_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pointer_generation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pointer_artifact_version_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class EdgeExecution(Base):
    __tablename__ = "edge_executions"
    __table_args__ = (
        UniqueConstraint(
            "edge_id",
            "source_workflow_run_id",
            "source_artifact_version_id",
            "target_partition_key",
            name="uq_edge_executions_scope",
        ),
        UniqueConstraint(
            "edge_id",
            "correlation_key",
            name="uq_edge_executions_correlation",
        ),
        Index(
            "ix_edge_executions_source_scope",
            "source_workflow_run_id",
            "edge_id",
            "status",
        ),
        Index(
            "ix_edge_executions_target_scope",
            "target_workflow_run_id",
            "edge_id",
            "status",
        ),
    )

    edge_execution_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    edge_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
    )
    source_stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_artifact_version_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=False,
    )
    source_activation_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_workflow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_workflow_run_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=True,
    )
    target_stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_partition_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    target_partition_key: Mapped[str] = mapped_column(String(255), nullable=False)
    target_activation_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    correlation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    materialize_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    activation_idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    cursor_state_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    compensation_state_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    input_bindings_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    trigger_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seed_artifact_version_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ArtifactLink(Base):
    __tablename__ = "artifact_links"
    __table_args__ = (
        UniqueConstraint(
            "artifact_version_id",
            "subject_kind",
            "subject_id",
            name="uq_artifact_links_subject",
        ),
    )

    artifact_version_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        primary_key=True,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    subject_kind: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    relation_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="attachment")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    created_by_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_actor_type: Mapped[str] = mapped_column(String(32), nullable=False)


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "dedupe_key",
            name="uq_flags_workflow_dedupe_key",
        ),
    )

    flag_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    partition_key: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    assigned_group: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_event_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class ExecutionSession(Base):
    __tablename__ = "execution_sessions"

    execution_session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    task_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=False,
        index=True,
    )
    execution_spec_id: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_actor: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    budget: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    tool_call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ToolExecution(Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        UniqueConstraint(
            "execution_session_id",
            "idempotency_key",
            name="uq_tool_executions_session_idempotency",
        ),
    )

    tool_execution_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    execution_session_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("execution_sessions.execution_session_id"),
        nullable=False,
        index=True,
    )
    tool_class: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy_decision_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    output_artifact_version_ids: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"
    __table_args__ = (
        UniqueConstraint(
            "tool_execution_id",
            name="uq_policy_decisions_tool_execution_id",
        ),
    )

    policy_decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    principal_actor: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    required_approval_action: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_execution_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("tool_executions.tool_execution_id"),
        nullable=True,
        index=True,
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
