from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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
    workflow_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    actor: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    links: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    integrity: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
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
    logical_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    blocked_on_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    blocked_on_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    spawned_from_task_run_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
    )
    spawn_rule_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    spawn_cause_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    spawn_cause_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    spawn_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spawn_budget_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
    owner_role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    assignee_actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    assignee_actor_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_approval_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
    task_run_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
        index=True,
    )
    approval_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by_task_run_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
    )
    candidate_roles: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    required_role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decided_by_actor_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
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

    artifact_version_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        nullable=False,
        index=True,
    )
    task_run_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
        index=True,
    )
    artifact_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_digest: Mapped[str] = mapped_column(String(255), nullable=False)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    parent_artifact_version_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    supersedes_artifact_version_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=True,
    )
    lineage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ArtifactPointer(Base):
    __tablename__ = "artifact_pointers"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "scope_kind",
            "scope_ref",
            "artifact_kind",
            name="uq_artifact_pointers_scope",
        ),
    )

    workflow_run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_runs.workflow_run_id"),
        primary_key=True,
    )
    pointer_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    scope_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_version_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("artifact_versions.artifact_version_id"),
        nullable=False,
    )
    promotion_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    promoted_by_task_run_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("task_runs.task_run_id"),
        nullable=True,
    )
    approved_by_approval_id: Mapped[str | None] = mapped_column(
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
