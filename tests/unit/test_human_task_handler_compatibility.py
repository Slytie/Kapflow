from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

import onetruth.application.handlers._shared.artifact_effects as artifact_effects
import onetruth.application.handlers._shared.command_boundary as command_boundary
import onetruth.application.handlers.human_tasks as new_human_tasks
import onetruth.application.handlers.workflow_task_lifecycle as legacy_handlers
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _freeze_handler_time(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = "2026-03-14T12:00:00Z"
    monkeypatch.setattr(command_boundary, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(artifact_effects, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(legacy_handlers, "utc_now_iso", lambda: fixed_now)
    monkeypatch.setattr(new_human_tasks, "utc_now_iso", lambda: fixed_now)


def _workflow_payload(workflow_run_id: str, activation_key: str) -> dict[str, str]:
    return {
        "workflow_run_id": workflow_run_id,
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "SD-2026-03-14",
        "logical_date": "2026-03-14",
        "activation_key": activation_key,
    }


def _task_payload(
    workflow_run_id: str,
    *,
    task_run_id: str,
    human_task_id: str,
    activation_key: str,
    stage_id: str,
    task_kind: str,
) -> dict[str, object]:
    return {
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "human_task_id": human_task_id,
        "stage_id": stage_id,
        "task_kind": task_kind,
        "activation_key": activation_key,
        "create_human_task": True,
        "candidate_roles": ["dispatch_supervisor"],
        "owner_role": "dispatch_supervisor",
        "idempotency_key": f"idem:tasks.create:{human_task_id}",
    }


def _artifact_payload(
    workflow_run_id: str,
    task_run_id: str,
    *,
    artifact_version_id: str,
    artifact_kind: str,
) -> dict[str, object]:
    return {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "artifact_kind": artifact_kind,
        "artifact_role": "review_input",
        "media_type": "application/json",
        "storage_uri": f"file:///tmp/{artifact_version_id}.json",
        "content_digest": f"sha256:{artifact_version_id}",
        "byte_size": 32,
        "metadata_json": {"fixture": artifact_kind},
        "idempotency_key": f"idem:artifact:{artifact_version_id}",
        "actor_id": "system:runtime",
        "actor_type": "system",
    }


def _claim_payload(human_task_id: str, *, actor_id: str, actor_roles: list[str]) -> dict[str, object]:
    return {
        "human_task_id": human_task_id,
        "actor_id": actor_id,
        "actor_type": "human",
        "actor_roles": actor_roles,
        "lease_seconds": 300,
        "idempotency_key": f"idem:claim:{human_task_id}:{actor_id}",
    }


def _complete_payload(
    human_task_id: str,
    *,
    actor_id: str,
    outcome: str,
    child_task_run_id: str | None = None,
    child_human_task_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "human_task_id": human_task_id,
        "actor_id": actor_id,
        "actor_type": "human",
        "outcome": outcome,
        "idempotency_key": f"idem:complete:{human_task_id}:{actor_id}:{outcome}",
    }
    if child_task_run_id is not None:
        payload["child_task_run_id"] = child_task_run_id
    if child_human_task_id is not None:
        payload["child_human_task_id"] = child_human_task_id
    return payload


def _confirm_review_payload(
    human_task_id: str,
    *,
    actor_id: str,
    reviewed_artifact_version_ids: list[str],
) -> dict[str, object]:
    return {
        "human_task_id": human_task_id,
        "actor_id": actor_id,
        "actor_type": "human",
        "reviewed_artifact_version_ids": reviewed_artifact_version_ids,
        "idempotency_key": f"idem:confirm-review:{human_task_id}:{actor_id}",
    }


def _human_task_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "human_task_id": row["human_task_id"],
        "workflow_run_id": row["workflow_run_id"],
        "task_run_id": row["task_run_id"],
        "task_kind": row["task_kind"],
        "state": row["state"],
        "candidate_roles": row["candidate_roles"],
        "owner_role": row["owner_role"],
        "assignee_actor_id": row.get("assignee_actor_id"),
        "assignee_actor_type": row.get("assignee_actor_type"),
        "claimed_at": row.get("claimed_at"),
        "claimed_until": row.get("claimed_until"),
        "completed_at": row.get("completed_at"),
        "lease_version": row.get("lease_version"),
        "generation": row.get("generation"),
    }


def _task_run_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "task_run_id": row["task_run_id"],
        "workflow_run_id": row["workflow_run_id"],
        "stage_id": row["stage_id"],
        "task_kind": row["task_kind"],
        "state": row["state"],
        "generation": row["generation"],
        "activation_key": row["activation_key"],
        "blocked_on_kind": row["blocked_on_kind"],
        "blocked_on_ref": row["blocked_on_ref"],
        "spawned_from_flag_id": row["spawned_from_flag_id"],
        "spawned_from_task_run_id": row["spawned_from_task_run_id"],
        "spawn_rule_id": row["spawn_rule_id"],
        "spawn_cause_kind": row["spawn_cause_kind"],
        "spawn_cause_event_id": row["spawn_cause_event_id"],
        "spawn_depth": row["spawn_depth"],
        "spawn_budget_key": row["spawn_budget_key"],
    }


def _artifact_summary(row: dict[str, object]) -> dict[str, object]:
    metadata = dict(row["metadata_json"])
    links = [
        {
            "subject_kind": str(link["subject_kind"]),
            "subject_id": str(link["subject_id"]),
            "relation_kind": str(link["relation_kind"]),
        }
        for link in row["links"]
    ]
    return {
        "artifact_version_id": row["artifact_version_id"],
        "workflow_run_id": row["workflow_run_id"],
        "task_run_id": row["task_run_id"],
        "artifact_kind": row["artifact_kind"],
        "artifact_role": row["artifact_role"],
        "media_type": row["media_type"],
        "storage_uri": row["storage_uri"],
        "content_digest": row["content_digest"],
        "byte_size": row["byte_size"],
        "metadata_json": metadata,
        "links": sorted(
            links,
            key=lambda item: (item["subject_kind"], item["subject_id"], item["relation_kind"]),
        ),
    }


def _relevant_event_payloads(connection: sqlite3.Connection, workflow_run_id: str) -> list[tuple[str, dict[str, object]]]:
    relevant_types = {
        "task.created",
        "task.claimed",
        "task.completed",
        "task.run.created",
        "task.run.state_changed",
        "artifact.version.created",
    }
    payloads: list[tuple[str, dict[str, object]]] = []
    for event in list_events(connection, run_id=workflow_run_id):
        event_type = str(event["event_type"])
        if event_type not in relevant_types:
            continue
        payload = dict(event["payload"])
        payload.pop("spawn_cause_event_id", None)
        payloads.append((event_type, payload))
    return payloads


def _create_review_task(connection: sqlite3.Connection, workflow_run_id: str) -> None:
    legacy_handlers.create_task_run_command(
        connection,
        _task_payload(
            workflow_run_id,
            task_run_id="tr-stage06-review",
            human_task_id="ht-stage06-review",
            activation_key="stage06-review",
            stage_id="Stage06",
            task_kind="review_packet",
        ),
    )


def _create_final_review_task(connection: sqlite3.Connection, workflow_run_id: str) -> None:
    legacy_handlers.create_task_run_command(
        connection,
        _task_payload(
            workflow_run_id,
            task_run_id="tr-stage06-final-review",
            human_task_id="ht-stage06-final-review",
            activation_key="stage06-final-review",
            stage_id="Stage06",
            task_kind="final_review",
        ),
    )


def _seed_final_review_artifacts(connection: sqlite3.Connection, workflow_run_id: str) -> list[str]:
    artifact_ids = ["av-stage06-publish-packet", "av-stage06-published-schedule"]
    artifact_kinds = [
        "schedule.stage06.publish_packet",
        "schedule.published_schedule.workbook",
    ]
    for artifact_version_id, artifact_kind in zip(artifact_ids, artifact_kinds, strict=True):
        legacy_handlers.create_artifact_version_command(
            connection,
            _artifact_payload(
                workflow_run_id,
                "tr-stage06-final-review",
                artifact_version_id=artifact_version_id,
                artifact_kind=artifact_kind,
            ),
        )
    return artifact_ids


def test_human_task_handler_compatibility_keeps_legacy_and_new_mutations_in_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_handler_time(monkeypatch)
    legacy_connection = _connection()
    new_connection = _connection()
    workflow_run_id = "wr-human-task-compat"

    legacy_handlers.create_workflow_run_command(
        legacy_connection,
        _workflow_payload(workflow_run_id, "human-task-compat"),
    )
    legacy_handlers.create_workflow_run_command(
        new_connection,
        _workflow_payload(workflow_run_id, "human-task-compat"),
    )
    _create_review_task(legacy_connection, workflow_run_id)
    _create_review_task(new_connection, workflow_run_id)

    legacy_claimed = legacy_handlers.claim_human_task_command(
        legacy_connection,
        _claim_payload(
            "ht-stage06-review",
            actor_id="human:dispatch-supervisor-1",
            actor_roles=["dispatch_supervisor"],
        ),
    )
    new_claimed = new_human_tasks.claim_human_task_command(
        new_connection,
        _claim_payload(
            "ht-stage06-review",
            actor_id="human:dispatch-supervisor-1",
            actor_roles=["dispatch_supervisor"],
        ),
    )
    assert _human_task_summary(legacy_claimed["human_task"]) == _human_task_summary(
        new_claimed["human_task"]
    )
    assert _task_run_summary(legacy_claimed["task_run"]) == _task_run_summary(new_claimed["task_run"])

    legacy_completed = legacy_handlers.complete_human_task_command(
        legacy_connection,
        _complete_payload(
            "ht-stage06-review",
            actor_id="human:dispatch-supervisor-1",
            outcome="draft_is_publish_ready",
            child_task_run_id="tr-stage06-final-review-child",
            child_human_task_id="ht-stage06-final-review-child",
        ),
    )
    new_completed = new_human_tasks.complete_human_task_command(
        new_connection,
        _complete_payload(
            "ht-stage06-review",
            actor_id="human:dispatch-supervisor-1",
            outcome="draft_is_publish_ready",
            child_task_run_id="tr-stage06-final-review-child",
            child_human_task_id="ht-stage06-final-review-child",
        ),
    )
    assert _human_task_summary(legacy_completed["human_task"]) == _human_task_summary(
        new_completed["human_task"]
    )
    assert _task_run_summary(legacy_completed["task_run"]) == _task_run_summary(
        new_completed["task_run"]
    )
    assert legacy_completed["spawned_children"] == new_completed["spawned_children"]
    assert _relevant_event_payloads(legacy_connection, workflow_run_id) == _relevant_event_payloads(
        new_connection,
        workflow_run_id,
    )

    legacy_handlers.create_workflow_run_command(
        legacy_connection,
        _workflow_payload("wr-final-review-compat", "final-review-compat"),
    )
    legacy_handlers.create_workflow_run_command(
        new_connection,
        _workflow_payload("wr-final-review-compat", "final-review-compat"),
    )
    _create_final_review_task(legacy_connection, "wr-final-review-compat")
    _create_final_review_task(new_connection, "wr-final-review-compat")
    legacy_handlers.claim_human_task_command(
        legacy_connection,
        _claim_payload(
            "ht-stage06-final-review",
            actor_id="human:dispatch-supervisor-2",
            actor_roles=["dispatch_supervisor"],
        ),
    )
    new_human_tasks.claim_human_task_command(
        new_connection,
        _claim_payload(
            "ht-stage06-final-review",
            actor_id="human:dispatch-supervisor-2",
            actor_roles=["dispatch_supervisor"],
        ),
    )
    reviewed_artifact_version_ids = _seed_final_review_artifacts(
        legacy_connection,
        "wr-final-review-compat",
    )
    _seed_final_review_artifacts(
        new_connection,
        "wr-final-review-compat",
    )

    storage_root = tmp_path / "review-confirmation-storage"
    legacy_confirmed = legacy_handlers.confirm_human_task_review_command(
        legacy_connection,
        _confirm_review_payload(
            "ht-stage06-final-review",
            actor_id="human:dispatch-supervisor-2",
            reviewed_artifact_version_ids=reviewed_artifact_version_ids,
        ),
        storage_root=storage_root,
    )
    new_confirmed = new_human_tasks.confirm_human_task_review_command(
        new_connection,
        _confirm_review_payload(
            "ht-stage06-final-review",
            actor_id="human:dispatch-supervisor-2",
            reviewed_artifact_version_ids=reviewed_artifact_version_ids,
        ),
        storage_root=storage_root,
    )
    assert _artifact_summary(legacy_confirmed["artifact_version"]) == _artifact_summary(
        new_confirmed["artifact_version"]
    )
    assert _relevant_event_payloads(
        legacy_connection,
        "wr-final-review-compat",
    ) == _relevant_event_payloads(
        new_connection,
        "wr-final-review-compat",
    )


@pytest.mark.parametrize(
    ("command_name", "legacy_call", "new_call", "expected_code"),
    [
        (
            "claim",
            lambda connection: legacy_handlers.claim_human_task_command(
                connection,
                _claim_payload(
                    "ht-stage06-review",
                    actor_id="human:schedule-planner-1",
                    actor_roles=["schedule_planner"],
                ),
            ),
            lambda connection: new_human_tasks.claim_human_task_command(
                connection,
                _claim_payload(
                    "ht-stage06-review",
                    actor_id="human:schedule-planner-1",
                    actor_roles=["schedule_planner"],
                ),
            ),
            "task_claim_forbidden",
        ),
        (
            "complete",
            lambda connection: legacy_handlers.complete_human_task_command(
                connection,
                _complete_payload(
                    "ht-stage06-review",
                    actor_id="human:dispatch-supervisor-2",
                    outcome="draft_is_publish_ready",
                ),
            ),
            lambda connection: new_human_tasks.complete_human_task_command(
                connection,
                _complete_payload(
                    "ht-stage06-review",
                    actor_id="human:dispatch-supervisor-2",
                    outcome="draft_is_publish_ready",
                ),
            ),
            "task_complete_forbidden",
        ),
        (
            "confirm-review",
            lambda connection: legacy_handlers.confirm_human_task_review_command(
                connection,
                _confirm_review_payload(
                    "ht-stage06-final-review",
                    actor_id="human:dispatch-supervisor-9",
                    reviewed_artifact_version_ids=[
                        "av-stage06-publish-packet",
                        "av-stage06-published-schedule",
                    ],
                ),
                storage_root=Path("/tmp/human-task-handler-compat"),
            ),
            lambda connection: new_human_tasks.confirm_human_task_review_command(
                connection,
                _confirm_review_payload(
                    "ht-stage06-final-review",
                    actor_id="human:dispatch-supervisor-9",
                    reviewed_artifact_version_ids=[
                        "av-stage06-publish-packet",
                        "av-stage06-published-schedule",
                    ],
                ),
                storage_root=Path("/tmp/human-task-handler-compat"),
            ),
            "task_confirm_review_forbidden",
        ),
    ],
)
def test_human_task_handler_compatibility_preserves_forbidden_error_details(
    command_name: str,
    legacy_call,
    new_call,
    expected_code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_handler_time(monkeypatch)
    legacy_connection = _connection()
    new_connection = _connection()

    if command_name in {"claim", "complete"}:
        workflow_run_id = "wr-human-task-forbidden"
        legacy_handlers.create_workflow_run_command(
            legacy_connection,
            _workflow_payload(workflow_run_id, "human-task-forbidden"),
        )
        legacy_handlers.create_workflow_run_command(
            new_connection,
            _workflow_payload(workflow_run_id, "human-task-forbidden"),
        )
        _create_review_task(legacy_connection, workflow_run_id)
        _create_review_task(new_connection, workflow_run_id)
        if command_name == "complete":
            legacy_handlers.claim_human_task_command(
                legacy_connection,
                _claim_payload(
                    "ht-stage06-review",
                    actor_id="human:dispatch-supervisor-1",
                    actor_roles=["dispatch_supervisor"],
                ),
            )
            new_human_tasks.claim_human_task_command(
                new_connection,
                _claim_payload(
                    "ht-stage06-review",
                    actor_id="human:dispatch-supervisor-1",
                    actor_roles=["dispatch_supervisor"],
                ),
            )
    else:
        workflow_run_id = "wr-final-review-forbidden"
        legacy_handlers.create_workflow_run_command(
            legacy_connection,
            _workflow_payload(workflow_run_id, "final-review-forbidden"),
        )
        legacy_handlers.create_workflow_run_command(
            new_connection,
            _workflow_payload(workflow_run_id, "final-review-forbidden"),
        )
        _create_final_review_task(legacy_connection, workflow_run_id)
        _create_final_review_task(new_connection, workflow_run_id)
        legacy_handlers.claim_human_task_command(
            legacy_connection,
            _claim_payload(
                "ht-stage06-final-review",
                actor_id="human:dispatch-supervisor-2",
                actor_roles=["dispatch_supervisor"],
            ),
        )
        new_human_tasks.claim_human_task_command(
            new_connection,
            _claim_payload(
                "ht-stage06-final-review",
                actor_id="human:dispatch-supervisor-2",
                actor_roles=["dispatch_supervisor"],
            ),
        )
        _seed_final_review_artifacts(legacy_connection, workflow_run_id)
        _seed_final_review_artifacts(new_connection, workflow_run_id)

    with pytest.raises(legacy_handlers.CommandError) as legacy_exc:
        legacy_call(legacy_connection)
    with pytest.raises(new_human_tasks.CommandError) as new_exc:
        new_call(new_connection)

    assert legacy_exc.value.code == expected_code
    assert new_exc.value.code == legacy_exc.value.code
    assert new_exc.value.details == legacy_exc.value.details
