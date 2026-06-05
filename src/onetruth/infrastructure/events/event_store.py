from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

import yaml


class DuplicateEventIdError(ValueError):
    def __init__(self, event_id: str) -> None:
        super().__init__(f"event_id already exists: {event_id}")
        self.event_id = event_id


class DuplicateIdempotencyKeyError(ValueError):
    def __init__(self, idempotency_key: str, existing_event_id: str) -> None:
        super().__init__(
            f"idempotency_key already exists: {idempotency_key} (event_id={existing_event_id})"
        )
        self.idempotency_key = idempotency_key
        self.existing_event_id = existing_event_id


_REQUIRED_LINK_TYPES_BY_EVENT: dict[str, set[str]] | None = None


def create_sqlite_substrate(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS timeline_events (
            sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            workflow_run_id TEXT,
            project_id TEXT,
            actor TEXT NOT NULL,
            links TEXT NOT NULL,
            payload TEXT NOT NULL,
            correlation_id TEXT,
            causation_id TEXT,
            idempotency_key TEXT UNIQUE,
            integrity TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS ix_timeline_events_workflow_run_id
            ON timeline_events (workflow_run_id);
        CREATE INDEX IF NOT EXISTS ix_timeline_events_project_id
            ON timeline_events (project_id);

        CREATE TABLE IF NOT EXISTS consumer_cursors (
            consumer_name TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            last_sequence_no INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (consumer_name, tenant_id, domain_id)
        );

        CREATE TABLE IF NOT EXISTS command_receipts (
            command_receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            command_name TEXT NOT NULL,
            scope_key TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            request_fingerprint TEXT NOT NULL,
            result_json TEXT NOT NULL,
            tenant_id TEXT,
            domain_id TEXT,
            workflow_run_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (command_name, scope_key, idempotency_key),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id)
        );

        CREATE INDEX IF NOT EXISTS ix_command_receipts_workflow_run_id
            ON command_receipts (workflow_run_id);
        CREATE INDEX IF NOT EXISTS ix_command_receipts_scope_lookup
            ON command_receipts (tenant_id, domain_id, command_name, scope_key);

        CREATE TABLE IF NOT EXISTS capex_projects (
            project_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            project_key TEXT NOT NULL,
            name TEXT NOT NULL,
            state TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_by_actor_id TEXT NOT NULL,
            created_by_actor_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (tenant_id, domain_id, project_key)
        );

        CREATE INDEX IF NOT EXISTS ix_capex_projects_scope_lookup
            ON capex_projects (tenant_id, domain_id, state, project_key);

        CREATE TABLE IF NOT EXISTS project_memberships (
            project_membership_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            role TEXT NOT NULL,
            state TEXT NOT NULL,
            granted_by_actor_id TEXT NOT NULL,
            granted_by_actor_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES capex_projects(project_id),
            UNIQUE (project_id, actor_type, actor_id)
        );

        CREATE INDEX IF NOT EXISTS ix_project_memberships_actor_lookup
            ON project_memberships (tenant_id, domain_id, actor_type, actor_id, state);

        CREATE TABLE IF NOT EXISTS capex_project_authorization (
            project_authorization_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            direct_role TEXT NOT NULL,
            effective_role TEXT NOT NULL,
            source_membership_id TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES capex_projects(project_id),
            FOREIGN KEY (source_membership_id) REFERENCES project_memberships(project_membership_id),
            UNIQUE (project_id, actor_type, actor_id)
        );

        CREATE INDEX IF NOT EXISTS ix_capex_project_authorization_actor_lookup
            ON capex_project_authorization (tenant_id, domain_id, actor_type, actor_id, state);
        CREATE INDEX IF NOT EXISTS ix_capex_project_authorization_project_state
            ON capex_project_authorization (project_id, state);

        CREATE TABLE IF NOT EXISTS capex_project_feature (
            project_feature_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            feature_key TEXT NOT NULL,
            state TEXT NOT NULL,
            blocked_reason TEXT,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES capex_projects(project_id),
            UNIQUE (project_id, feature_key)
        );

        CREATE INDEX IF NOT EXISTS ix_capex_project_feature_lookup
            ON capex_project_feature (tenant_id, domain_id, feature_key, state);

        CREATE TABLE IF NOT EXISTS capex_user_project_view (
            user_project_view_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            project_key TEXT NOT NULL,
            name TEXT NOT NULL,
            project_state TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_by_actor_id TEXT NOT NULL,
            created_by_actor_type TEXT NOT NULL,
            project_created_at TEXT NOT NULL,
            project_updated_at TEXT NOT NULL,
            caller_role TEXT NOT NULL,
            authorization_state TEXT NOT NULL,
            source_authorization_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES capex_projects(project_id),
            FOREIGN KEY (source_authorization_id) REFERENCES capex_project_authorization(project_authorization_id),
            UNIQUE (tenant_id, domain_id, actor_type, actor_id, project_id)
        );

        CREATE INDEX IF NOT EXISTS ix_capex_user_project_view_actor_lookup
            ON capex_user_project_view (
                tenant_id,
                domain_id,
                actor_type,
                actor_id,
                authorization_state,
                project_state,
                project_key
            );

        CREATE TABLE IF NOT EXISTS workflow_runs (
            workflow_run_id TEXT PRIMARY KEY,
            project_id TEXT,
            workflow_id TEXT NOT NULL,
            workflow_version TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            partition_key TEXT NOT NULL,
            logical_date TEXT,
            activation_key TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES capex_projects(project_id),
            UNIQUE (tenant_id, domain_id, workflow_id, partition_key, activation_key)
        );

        CREATE INDEX IF NOT EXISTS ix_workflow_runs_scope_lookup
            ON workflow_runs (tenant_id, domain_id, workflow_id, partition_key);
        CREATE INDEX IF NOT EXISTS ix_workflow_runs_project_scope
            ON workflow_runs (tenant_id, domain_id, project_id);

        CREATE TABLE IF NOT EXISTS flags (
            flag_id TEXT PRIMARY KEY,
            workflow_run_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            workflow_id TEXT NOT NULL,
            partition_key TEXT NOT NULL,
            kind TEXT NOT NULL,
            severity TEXT NOT NULL,
            state TEXT NOT NULL,
            summary TEXT NOT NULL,
            details_json TEXT NOT NULL,
            assigned_group TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            closed_at TEXT,
            created_by_actor_id TEXT NOT NULL,
            created_by_actor_type TEXT NOT NULL,
            source_event_id TEXT,
            dedupe_key TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            UNIQUE (workflow_run_id, dedupe_key)
        );

        CREATE INDEX IF NOT EXISTS ix_flags_workflow_state
            ON flags (workflow_run_id, state);

        CREATE INDEX IF NOT EXISTS ix_flags_scope_lookup
            ON flags (tenant_id, domain_id, workflow_id, partition_key, state);

        CREATE TABLE IF NOT EXISTS task_runs (
            task_run_id TEXT PRIMARY KEY,
            workflow_run_id TEXT NOT NULL,
            stage_id TEXT NOT NULL,
            task_kind TEXT NOT NULL,
            state TEXT NOT NULL,
            generation INTEGER NOT NULL DEFAULT 0,
            activation_key TEXT NOT NULL,
            blocked_on_kind TEXT,
            blocked_on_ref TEXT,
            spawned_from_flag_id TEXT,
            spawned_from_task_run_id TEXT,
            spawn_rule_id TEXT,
            spawn_cause_kind TEXT,
            spawn_cause_event_id TEXT,
            spawn_depth INTEGER NOT NULL DEFAULT 0,
            spawn_budget_key TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (spawned_from_flag_id) REFERENCES flags(flag_id),
            FOREIGN KEY (spawned_from_task_run_id) REFERENCES task_runs(task_run_id),
            UNIQUE (workflow_run_id, activation_key)
        );

        CREATE INDEX IF NOT EXISTS ix_task_runs_workflow_run_id
            ON task_runs (workflow_run_id);
        CREATE INDEX IF NOT EXISTS ix_task_runs_spawned_from_flag_id
            ON task_runs (spawned_from_flag_id);

        CREATE TABLE IF NOT EXISTS human_tasks (
            human_task_id TEXT PRIMARY KEY,
            workflow_run_id TEXT NOT NULL,
            task_run_id TEXT NOT NULL,
            task_kind TEXT NOT NULL,
            state TEXT NOT NULL,
            candidate_roles TEXT NOT NULL,
            owner_role TEXT,
            assignee_actor_id TEXT,
            assignee_actor_type TEXT,
            due_at TEXT,
            escalation_at TEXT,
            lease_version INTEGER NOT NULL DEFAULT 0,
            claimed_at TEXT,
            claimed_until TEXT,
            linked_approval_id TEXT,
            reopen_count INTEGER NOT NULL DEFAULT 0,
            generation INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (task_run_id) REFERENCES task_runs(task_run_id),
            UNIQUE (task_run_id)
        );

        CREATE INDEX IF NOT EXISTS ix_human_tasks_workflow_state
            ON human_tasks (workflow_run_id, state);

        CREATE TABLE IF NOT EXISTS approvals (
            approval_id TEXT PRIMARY KEY,
            workflow_run_id TEXT NOT NULL,
            task_run_id TEXT,
            approval_kind TEXT NOT NULL,
            scope_kind TEXT NOT NULL,
            scope_ref TEXT NOT NULL,
            state TEXT NOT NULL,
            requested_by_task_run_id TEXT,
            candidate_roles TEXT NOT NULL,
            required_role TEXT,
            requested_at TEXT NOT NULL,
            responded_at TEXT,
            response_kind TEXT,
            response_reason TEXT,
            decided_by_actor_id TEXT,
            decided_by_actor_type TEXT,
            generation INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (task_run_id) REFERENCES task_runs(task_run_id),
            FOREIGN KEY (requested_by_task_run_id) REFERENCES task_runs(task_run_id)
        );

        CREATE INDEX IF NOT EXISTS ix_approvals_workflow_state
            ON approvals (workflow_run_id, state);

        CREATE TABLE IF NOT EXISTS artifact_versions (
            artifact_version_id TEXT PRIMARY KEY,
            workflow_run_id TEXT NOT NULL,
            tenant_id TEXT,
            domain_id TEXT,
            dataset_key TEXT,
            partition_kind TEXT,
            partition_key TEXT,
            task_run_id TEXT,
            artifact_kind TEXT NOT NULL,
            artifact_role TEXT,
            media_type TEXT NOT NULL,
            storage_uri TEXT NOT NULL,
            content_digest TEXT NOT NULL,
            byte_size INTEGER,
            metadata_json TEXT NOT NULL,
            parent_artifact_version_id TEXT,
            supersedes_artifact_version_id TEXT,
            lineage_note TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (task_run_id) REFERENCES task_runs(task_run_id),
            FOREIGN KEY (parent_artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            FOREIGN KEY (supersedes_artifact_version_id) REFERENCES artifact_versions(artifact_version_id)
        );

        CREATE INDEX IF NOT EXISTS ix_artifact_versions_workflow_kind
            ON artifact_versions (workflow_run_id, artifact_kind, created_at);
        CREATE INDEX IF NOT EXISTS ix_artifact_versions_canonical_address
            ON artifact_versions (tenant_id, domain_id, dataset_key, partition_kind, partition_key);

        CREATE TABLE IF NOT EXISTS artifact_links (
            artifact_version_id TEXT NOT NULL,
            workflow_run_id TEXT NOT NULL,
            subject_kind TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            relation_kind TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by_actor_id TEXT NOT NULL,
            created_by_actor_type TEXT NOT NULL,
            PRIMARY KEY (artifact_version_id, subject_kind, subject_id),
            UNIQUE (artifact_version_id, subject_kind, subject_id),
            FOREIGN KEY (artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id)
        );

        CREATE INDEX IF NOT EXISTS ix_artifact_links_subject
            ON artifact_links (workflow_run_id, subject_kind, subject_id, created_at);

        CREATE TABLE IF NOT EXISTS artifact_pointers (
            pointer_id TEXT NOT NULL PRIMARY KEY,
            workflow_run_id TEXT NOT NULL,
            pointer_key TEXT NOT NULL,
            tenant_id TEXT,
            domain_id TEXT,
            dataset_key TEXT,
            partition_kind TEXT,
            partition_key TEXT,
            stream_key TEXT,
            registry_kind TEXT,
            scope_kind TEXT NOT NULL,
            scope_ref TEXT NOT NULL,
            artifact_kind TEXT NOT NULL,
            artifact_version_id TEXT NOT NULL,
            promotion_reason TEXT,
            promoted_by_task_run_id TEXT,
            approved_by_approval_id TEXT,
            generation INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (workflow_run_id, pointer_key),
            UNIQUE (workflow_run_id, scope_kind, scope_ref, artifact_kind),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            FOREIGN KEY (promoted_by_task_run_id) REFERENCES task_runs(task_run_id),
            FOREIGN KEY (approved_by_approval_id) REFERENCES approvals(approval_id)
        );

        CREATE INDEX IF NOT EXISTS ix_artifact_pointers_workflow_scope
            ON artifact_pointers (workflow_run_id, scope_kind, scope_ref);
        CREATE UNIQUE INDEX IF NOT EXISTS ix_artifact_pointers_pointer_id
            ON artifact_pointers (pointer_id);
        CREATE INDEX IF NOT EXISTS ix_artifact_pointers_canonical_lookup
            ON artifact_pointers (
                tenant_id,
                domain_id,
                dataset_key,
                partition_kind,
                partition_key,
                stream_key
            );

        CREATE TABLE IF NOT EXISTS artifact_provenance_edges (
            edge_id TEXT PRIMARY KEY,
            workflow_run_id TEXT,
            output_artifact_version_id TEXT NOT NULL,
            input_artifact_version_id TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            edge_order INTEGER,
            metadata_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (output_artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            FOREIGN KEY (input_artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            UNIQUE (output_artifact_version_id, input_artifact_version_id, edge_type, edge_order)
        );

        CREATE INDEX IF NOT EXISTS ix_artifact_provenance_edges_output
            ON artifact_provenance_edges (output_artifact_version_id, edge_type, edge_order);
        CREATE INDEX IF NOT EXISTS ix_artifact_provenance_edges_input
            ON artifact_provenance_edges (input_artifact_version_id, edge_type);

        CREATE TABLE IF NOT EXISTS workflow_run_inputs (
            workflow_run_input_id TEXT PRIMARY KEY,
            workflow_run_id TEXT NOT NULL,
            binding_key TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            artifact_version_id TEXT,
            pointer_key TEXT,
            pointer_generation INTEGER,
            pointer_artifact_version_id TEXT,
            captured_by_task_run_id TEXT,
            captured_at TEXT NOT NULL,
            metadata_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            FOREIGN KEY (pointer_artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            FOREIGN KEY (captured_by_task_run_id) REFERENCES task_runs(task_run_id),
            UNIQUE (workflow_run_id, binding_key)
        );

        CREATE INDEX IF NOT EXISTS ix_workflow_run_inputs_workflow_run_id
            ON workflow_run_inputs (workflow_run_id);

        CREATE TABLE IF NOT EXISTS task_input_bindings (
            task_input_binding_id TEXT PRIMARY KEY,
            task_run_id TEXT NOT NULL,
            workflow_run_id TEXT NOT NULL,
            binding_key TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            artifact_version_id TEXT,
            pointer_key TEXT,
            pointer_generation INTEGER,
            pointer_artifact_version_id TEXT,
            captured_at TEXT NOT NULL,
            metadata_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (task_run_id) REFERENCES task_runs(task_run_id),
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            FOREIGN KEY (pointer_artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            UNIQUE (task_run_id, binding_key)
        );

        CREATE INDEX IF NOT EXISTS ix_task_input_bindings_task_run_id
            ON task_input_bindings (task_run_id);

        CREATE TABLE IF NOT EXISTS edge_executions (
            edge_execution_id TEXT PRIMARY KEY,
            edge_id TEXT NOT NULL,
            source_workflow_run_id TEXT NOT NULL,
            source_stage_id TEXT NOT NULL,
            source_artifact_version_id TEXT NOT NULL,
            source_activation_key TEXT,
            target_workflow_id TEXT NOT NULL,
            target_workflow_run_id TEXT,
            target_stage_id TEXT NOT NULL,
            target_partition_kind TEXT NOT NULL,
            target_partition_key TEXT NOT NULL,
            target_activation_key TEXT,
            correlation_key TEXT NOT NULL,
            materialize_idempotency_key TEXT NOT NULL,
            activation_idempotency_key TEXT,
            status TEXT NOT NULL,
            cursor_state_json TEXT,
            compensation_state_json TEXT,
            input_bindings_json TEXT,
            trigger_ref TEXT,
            seed_artifact_version_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            activated_at TEXT,
            FOREIGN KEY (source_workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (source_artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            FOREIGN KEY (target_workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (seed_artifact_version_id) REFERENCES artifact_versions(artifact_version_id),
            UNIQUE (edge_id, source_workflow_run_id, source_artifact_version_id, target_partition_key),
            UNIQUE (edge_id, correlation_key)
        );

        CREATE INDEX IF NOT EXISTS ix_edge_executions_source_scope
            ON edge_executions (source_workflow_run_id, edge_id, status);
        CREATE INDEX IF NOT EXISTS ix_edge_executions_target_scope
            ON edge_executions (target_workflow_run_id, edge_id, status);

        CREATE TABLE IF NOT EXISTS execution_sessions (
            execution_session_id TEXT PRIMARY KEY,
            workflow_run_id TEXT NOT NULL,
            task_run_id TEXT NOT NULL,
            execution_spec_id TEXT NOT NULL,
            state TEXT NOT NULL,
            owner_mode TEXT NOT NULL,
            principal_actor TEXT,
            budget TEXT,
            tool_call_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            closed_at TEXT,
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(workflow_run_id),
            FOREIGN KEY (task_run_id) REFERENCES task_runs(task_run_id)
        );

        CREATE INDEX IF NOT EXISTS ix_execution_sessions_workflow_state
            ON execution_sessions (workflow_run_id, state);
        CREATE INDEX IF NOT EXISTS ix_execution_sessions_task_run_id
            ON execution_sessions (task_run_id);

        CREATE TABLE IF NOT EXISTS tool_executions (
            tool_execution_id TEXT PRIMARY KEY,
            execution_session_id TEXT NOT NULL,
            tool_class TEXT NOT NULL,
            tool_name TEXT,
            state TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            attempt_no INTEGER NOT NULL DEFAULT 0,
            policy_decision_id TEXT,
            output_artifact_version_ids TEXT,
            requested_at TEXT NOT NULL,
            completed_at TEXT,
            error_code TEXT,
            FOREIGN KEY (execution_session_id) REFERENCES execution_sessions(execution_session_id),
            UNIQUE (execution_session_id, idempotency_key)
        );

        CREATE INDEX IF NOT EXISTS ix_tool_executions_session_state
            ON tool_executions (execution_session_id, state);

        CREATE TABLE IF NOT EXISTS policy_decisions (
            policy_decision_id TEXT PRIMARY KEY,
            principal_actor TEXT NOT NULL,
            decision TEXT NOT NULL,
            reason_code TEXT,
            required_approval_action TEXT,
            tool_execution_id TEXT,
            decided_at TEXT NOT NULL,
            FOREIGN KEY (tool_execution_id) REFERENCES tool_executions(tool_execution_id),
            UNIQUE (tool_execution_id)
        );

        CREATE INDEX IF NOT EXISTS ix_policy_decisions_tool_execution
            ON policy_decisions (tool_execution_id);
        """
    )
    connection.commit()


def append_event(connection: sqlite3.Connection, envelope: dict[str, Any]) -> str:
    _require_required_fields(envelope)
    _require_required_links_for_event(envelope)
    event_id = str(envelope["event_id"])

    duplicate = connection.execute(
        "SELECT event_id FROM timeline_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    if duplicate:
        raise DuplicateEventIdError(event_id)

    idempotency_key = envelope.get("idempotency_key")
    if isinstance(idempotency_key, str):
        prior = connection.execute(
            "SELECT event_id FROM timeline_events WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if prior:
            raise DuplicateIdempotencyKeyError(idempotency_key, str(prior["event_id"]))

    payload = {
        "event_id": event_id,
        "event_type": envelope["event_type"],
        "schema_version": envelope["schema_version"],
        "occurred_at": envelope["occurred_at"],
        "recorded_at": envelope["recorded_at"],
        "tenant_id": envelope["tenant_id"],
        "domain_id": envelope["domain_id"],
        "workflow_run_id": _extract_workflow_run_id(envelope["links"]),
        "project_id": _extract_project_id(connection, envelope["links"]),
        "actor": json.dumps(envelope["actor"], separators=(",", ":")),
        "links": json.dumps(envelope["links"], separators=(",", ":")),
        "payload": json.dumps(envelope["payload"], separators=(",", ":")),
        "correlation_id": envelope.get("correlation_id"),
        "causation_id": envelope.get("causation_id"),
        "idempotency_key": idempotency_key,
        "integrity": (
            json.dumps(envelope["integrity"], separators=(",", ":"))
            if "integrity" in envelope and envelope["integrity"] is not None
            else None
        ),
    }

    connection.execute(
        """
        INSERT INTO timeline_events (
            event_id,
            event_type,
            schema_version,
            occurred_at,
            recorded_at,
            tenant_id,
            domain_id,
            workflow_run_id,
            project_id,
            actor,
            links,
            payload,
            correlation_id,
            causation_id,
            idempotency_key,
            integrity
        )
        VALUES (
            :event_id,
            :event_type,
            :schema_version,
            :occurred_at,
            :recorded_at,
            :tenant_id,
            :domain_id,
            :workflow_run_id,
            :project_id,
            :actor,
            :links,
            :payload,
            :correlation_id,
            :causation_id,
            :idempotency_key,
            :integrity
        )
        """,
        payload,
    )
    return event_id


def list_events(
    connection: sqlite3.Connection,
    run_id: str | None = None,
    since_event_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    params: list[Any] = []
    query = """
        SELECT
            sequence_no,
            event_id,
            event_type,
            schema_version,
            occurred_at,
            recorded_at,
            tenant_id,
            domain_id,
            project_id,
            actor,
            links,
            payload,
            correlation_id,
            causation_id,
            idempotency_key,
            integrity
        FROM timeline_events
    """
    where_clauses: list[str] = []
    if run_id is not None:
        where_clauses.append("workflow_run_id = ?")
        params.append(run_id)

    if since_event_id is not None:
        row = connection.execute(
            "SELECT sequence_no FROM timeline_events WHERE event_id = ?",
            (since_event_id,),
        ).fetchone()
        if row is None:
            return []
        where_clauses.append("sequence_no > ?")
        params.append(int(row["sequence_no"]))

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY sequence_no ASC LIMIT ?"
    params.append(_coerce_limit(limit))

    rows = connection.execute(query, params).fetchall()
    return [_row_to_envelope(row) for row in rows]


def _coerce_limit(limit: int) -> int:
    return max(1, min(limit, 1000))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def event_id_for_type(event_type: str) -> str:
    compact_type = event_type.replace(".", "-")
    return f"{compact_type}-{uuid4()}"


def get_event_by_idempotency_key(
    connection: sqlite3.Connection,
    idempotency_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT event_id, event_type, idempotency_key
        FROM timeline_events
        WHERE idempotency_key = ?
        """,
        (idempotency_key,),
    ).fetchone()
    if row is None:
        return None
    return {
        "event_id": row["event_id"],
        "event_type": row["event_type"],
        "idempotency_key": row["idempotency_key"],
    }


def get_command_receipt(
    connection: sqlite3.Connection,
    *,
    command_name: str,
    scope_key: str,
    idempotency_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            command_name,
            scope_key,
            idempotency_key,
            request_fingerprint,
            result_json,
            tenant_id,
            domain_id,
            workflow_run_id,
            created_at
        FROM command_receipts
        WHERE command_name = ? AND scope_key = ? AND idempotency_key = ?
        """,
        (command_name, scope_key, idempotency_key),
    ).fetchone()
    if row is None:
        return None
    return {
        "command_name": row["command_name"],
        "scope_key": row["scope_key"],
        "idempotency_key": row["idempotency_key"],
        "request_fingerprint": row["request_fingerprint"],
        "result_json": json.loads(row["result_json"]),
        "tenant_id": row["tenant_id"],
        "domain_id": row["domain_id"],
        "workflow_run_id": row["workflow_run_id"],
        "created_at": row["created_at"],
    }


def create_command_receipt(
    connection: sqlite3.Connection,
    *,
    command_name: str,
    scope_key: str,
    idempotency_key: str,
    request_fingerprint: str,
    result_json: dict[str, Any],
    tenant_id: str | None,
    domain_id: str | None,
    workflow_run_id: str | None,
    created_at: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO command_receipts (
            command_name,
            scope_key,
            idempotency_key,
            request_fingerprint,
            result_json,
            tenant_id,
            domain_id,
            workflow_run_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
        """,
        (
            command_name,
            scope_key,
            idempotency_key,
            request_fingerprint,
            json.dumps(result_json, separators=(",", ":"), sort_keys=True),
            tenant_id,
            domain_id,
            workflow_run_id,
            created_at,
        ),
    )


def _extract_workflow_run_id(links: Any) -> str | None:
    if not isinstance(links, list):
        return None
    for link in links:
        if not isinstance(link, dict):
            continue
        if link.get("type") == "workflow_run":
            link_id = link.get("id")
            if isinstance(link_id, str):
                return link_id
    return None


def _extract_project_id(connection: sqlite3.Connection, links: Any) -> str | None:
    if not isinstance(links, list):
        return None
    workflow_run_id: str | None = None
    for link in links:
        if not isinstance(link, dict):
            continue
        link_type = link.get("type")
        link_id = link.get("id")
        if link_type == "capex_project" and isinstance(link_id, str):
            return link_id
        if link_type == "workflow_run" and isinstance(link_id, str):
            workflow_run_id = link_id
    if workflow_run_id is None:
        return None
    row = connection.execute(
        """
        SELECT project_id
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchone()
    if row is None or row["project_id"] is None:
        return None
    return str(row["project_id"])


def _require_required_fields(envelope: dict[str, Any]) -> None:
    required_fields = [
        "event_id",
        "event_type",
        "schema_version",
        "occurred_at",
        "recorded_at",
        "tenant_id",
        "domain_id",
        "actor",
        "links",
        "payload",
    ]
    missing = [name for name in required_fields if name not in envelope]
    if missing:
        raise ValueError(f"missing required envelope fields: {', '.join(missing)}")


def _require_required_links_for_event(envelope: dict[str, Any]) -> None:
    event_type = str(envelope["event_type"])
    required_links = _required_link_types_by_event().get(event_type)
    if not required_links:
        return

    links = envelope.get("links")
    if not isinstance(links, list):
        raise ValueError(f"event_type {event_type} links must be a list")

    actual_link_types: set[str] = set()
    for link in links:
        if not isinstance(link, dict):
            continue
        link_type = link.get("type")
        if isinstance(link_type, str) and link_type.strip():
            actual_link_types.add(link_type.strip())

    missing = sorted(required_links - actual_link_types)
    if missing:
        missing_tokens = ", ".join(missing)
        raise ValueError(
            f"event_type {event_type} missing required link types: {missing_tokens}"
        )


def _required_link_types_by_event() -> dict[str, set[str]]:
    global _REQUIRED_LINK_TYPES_BY_EVENT
    if _REQUIRED_LINK_TYPES_BY_EVENT is not None:
        return _REQUIRED_LINK_TYPES_BY_EVENT

    registry_path = _resolve_event_registry_path()
    loaded = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"event registry must be an object: {registry_path}")

    event_types = loaded.get("event_types")
    if not isinstance(event_types, list):
        raise ValueError(f"event registry event_types must be a list: {registry_path}")

    resolved: dict[str, set[str]] = {}
    for raw in event_types:
        if not isinstance(raw, dict):
            continue
        event_type = str(raw.get("id") or "").strip()
        if not event_type:
            continue
        required_links = raw.get("required_links")
        if required_links is None:
            resolved[event_type] = set()
            continue
        if not isinstance(required_links, list):
            raise ValueError(
                f"event registry required_links must be a list for event type {event_type}"
            )
        resolved[event_type] = {
            str(link_type).strip()
            for link_type in required_links
            if str(link_type).strip()
        }

    _REQUIRED_LINK_TYPES_BY_EVENT = resolved
    return resolved


def _resolve_event_registry_path() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "schemas" / "events" / "event_type_registry.yaml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("unable to resolve schemas/events/event_type_registry.yaml")


def _row_to_envelope(row: sqlite3.Row) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "sequence_no": int(row["sequence_no"]),
        "event_id": row["event_id"],
        "event_type": row["event_type"],
        "schema_version": row["schema_version"],
        "occurred_at": row["occurred_at"],
        "recorded_at": row["recorded_at"],
        "tenant_id": row["tenant_id"],
        "domain_id": row["domain_id"],
        "actor": json.loads(row["actor"]),
        "links": json.loads(row["links"]),
        "payload": json.loads(row["payload"]),
    }
    if row["correlation_id"] is not None:
        envelope["correlation_id"] = row["correlation_id"]
    if row["causation_id"] is not None:
        envelope["causation_id"] = row["causation_id"]
    if row["idempotency_key"] is not None:
        envelope["idempotency_key"] = row["idempotency_key"]
    if "project_id" in row.keys() and row["project_id"] is not None:
        envelope["project_id"] = row["project_id"]
    if row["integrity"] is not None:
        envelope["integrity"] = json.loads(row["integrity"])
    return envelope
