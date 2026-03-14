from __future__ import annotations

import base64
import json
from pathlib import Path

from onetruth.api.route_registry import JSON_ARTIFACT_BODY, JSON_COMMAND_BODY
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

ATTACHMENT_SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
CONFIRM_REVIEW_SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_publish_ready_confirm_review.yaml"
)
TEMPLATE_PACK_ROOT = REPO_ROOT / "fixtures/workflows/schedule_planning/template_pack"
STAGE06_DOC = (
    TEMPLATE_PACK_ROOT
    / "Stage06_Supervisor_Review_Publish/Stage06_Supervisor_Review_Publish_Document_Example_COMPLETED.docx"
)


def _api_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager"],
    )


def _encoded_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _artifact_version_ids(
    client: RuntimeApiClient,
    *,
    workflow_run_id: str,
) -> set[str]:
    listed = client.get(
        "/api/v1/artifacts",
        query={"workflow_run_id": workflow_run_id},
    )
    assert listed.status_code == 200
    return {
        str(row["artifact_version_id"])
        for row in listed.payload["artifact_versions"]
    }


def _artifact_created_event_count(harness: RuntimeScenarioHarness) -> int:
    return sum(
        1
        for event in harness.list_events()
        if event["event_type"] == "artifact.version.created"
    )


def _json_size(payload: dict[str, object]) -> int:
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def test_root_ingest_accepts_request_bytes_and_strips_reserved_provenance(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(ATTACHMENT_SCENARIO_PATH, tmp_path).prepare()
    client = _api_client(harness)

    response = client.post(
        "/api/v1/artifacts/ingest",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "metadata_json": {
                "note": "request-byte-ingress",
                "seed_source_path": "fixtures/should/not/persist.docx",
                "ingress_source_path": "fixtures/should/not/persist.docx",
            },
            "idempotency_key": f"api:{harness.scenario_id}:artifacts.ingest:request-bytes",
        },
    )

    assert response.status_code == 200
    artifact = response.payload["artifact_version"]
    metadata = artifact["metadata_json"]
    assert metadata["ingress_kind"] == "request_bytes"
    assert metadata["note"] == "request-byte-ingress"
    assert "seed_source_path" not in metadata
    assert "ingress_source_path" not in metadata


def test_command_route_limit_is_smaller_than_artifact_ingress_limit(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(ATTACHMENT_SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])
    client = _api_client(harness)
    medium_padding = "x" * (JSON_COMMAND_BODY.max_bytes or 0)

    claim_payload = {
        "lease_seconds": 300,
        "idempotency_key": f"api:{harness.scenario_id}:claim:command-body-limit",
        "padding": medium_padding,
    }
    artifact_payload = {
        "artifact_kind": "schedule.supervisor_review.doc",
        "artifact_role": "evidence",
        "content_base64": _encoded_file(STAGE06_DOC),
        "file_name": STAGE06_DOC.name,
        "idempotency_key": f"api:{harness.scenario_id}:artifact-upload:artifact-body-limit",
        "padding": medium_padding,
    }

    assert _json_size(claim_payload) > (JSON_COMMAND_BODY.max_bytes or 0)
    assert _json_size(artifact_payload) > (JSON_COMMAND_BODY.max_bytes or 0)
    assert _json_size(artifact_payload) < (JSON_ARTIFACT_BODY.max_bytes or 0)

    denied_claim = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload=claim_payload,
    )
    assert denied_claim.status_code == 413
    assert denied_claim.payload["error"]["code"] == "payload_too_large"

    persisted = harness.show_task(human_task_id)["human_task"]
    assert persisted["state"] == "OPEN"
    assert persisted["assignee_actor_id"] is None

    uploaded = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload=artifact_payload,
    )
    assert uploaded.status_code == 200
    assert uploaded.payload["artifact_version"]["metadata_json"]["ingress_kind"] == "request_bytes"


def test_subject_upload_accepts_request_bytes(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(ATTACHMENT_SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])
    client = _api_client(harness)

    uploaded = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "idempotency_key": f"api:{harness.scenario_id}:human-task-upload:request-bytes",
        },
    )

    assert uploaded.status_code == 200
    artifact = uploaded.payload["artifact_version"]
    assert artifact["metadata_json"]["ingress_kind"] == "request_bytes"

    downloaded = client.get(
        f"/api/v1/artifacts/{artifact['artifact_version_id']}/download"
    )
    assert downloaded.status_code == 200
    assert base64.b64decode(downloaded.payload["content_base64"]) == STAGE06_DOC.read_bytes()


def test_artifact_ingress_rejects_oversize_request_without_side_effects(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(ATTACHMENT_SCENARIO_PATH, tmp_path).prepare()
    client = _api_client(harness)
    before_ids = _artifact_version_ids(client, workflow_run_id=harness.workflow_run_id)
    before_event_count = _artifact_created_event_count(harness)
    oversize_payload = {
        "workflow_run_id": harness.workflow_run_id,
        "artifact_kind": "schedule.supervisor_review.doc",
        "artifact_role": "evidence",
        "content_base64": _encoded_file(STAGE06_DOC),
        "file_name": STAGE06_DOC.name,
        "idempotency_key": f"api:{harness.scenario_id}:artifacts.ingest:oversize",
        "padding": "x" * (JSON_ARTIFACT_BODY.max_bytes or 0),
    }
    assert _json_size(oversize_payload) > (JSON_ARTIFACT_BODY.max_bytes or 0)

    response = client.post(
        "/api/v1/artifacts/ingest",
        payload=oversize_payload,
    )

    assert response.status_code == 413
    assert response.payload["error"]["code"] == "payload_too_large"
    assert response.payload["error"]["details"] == {
        "max_bytes": JSON_ARTIFACT_BODY.max_bytes,
    }
    after_ids = _artifact_version_ids(client, workflow_run_id=harness.workflow_run_id)
    after_event_count = _artifact_created_event_count(harness)
    assert after_ids == before_ids
    assert after_event_count == before_event_count


def test_subject_upload_remains_broad_for_in_scope_non_candidate_actor(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(ATTACHMENT_SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])
    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:auditor-2",
        actor_type="human",
        actor_roles=["auditor"],
    )

    uploaded = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "idempotency_key": f"api:{harness.scenario_id}:human-task-upload:broad-collaboration",
        },
    )

    assert uploaded.status_code == 200
    assert uploaded.payload["artifact_version"]["metadata_json"]["ingress_kind"] == "request_bytes"


def test_shared_http_rejects_source_path_without_side_effects(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(ATTACHMENT_SCENARIO_PATH, tmp_path).prepare()
    client = _api_client(harness)
    before_ids = _artifact_version_ids(client, workflow_run_id=harness.workflow_run_id)
    before_event_count = _artifact_created_event_count(harness)

    response = client.post(
        "/api/v1/artifacts/ingest",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "source_path": str(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "idempotency_key": f"api:{harness.scenario_id}:artifacts.ingest:source-path-reject",
        },
    )

    assert response.status_code == 400
    assert response.payload["error"]["code"] == "invalid_artifact_ingress"
    after_ids = _artifact_version_ids(client, workflow_run_id=harness.workflow_run_id)
    after_event_count = _artifact_created_event_count(harness)
    assert after_ids == before_ids
    assert after_event_count == before_event_count


def test_shared_http_rejects_storage_root_without_side_effects(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(ATTACHMENT_SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])
    client = _api_client(harness)
    before_ids = _artifact_version_ids(client, workflow_run_id=harness.workflow_run_id)
    before_event_count = _artifact_created_event_count(harness)

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": _encoded_file(STAGE06_DOC),
            "file_name": STAGE06_DOC.name,
            "storage_root": str(tmp_path / "forbidden-http-root"),
            "idempotency_key": f"api:{harness.scenario_id}:human-task-upload:storage-root-reject",
        },
    )

    assert response.status_code == 400
    assert response.payload["error"]["code"] == "invalid_artifact_ingress"
    after_ids = _artifact_version_ids(client, workflow_run_id=harness.workflow_run_id)
    after_event_count = _artifact_created_event_count(harness)
    assert after_ids == before_ids
    assert after_event_count == before_event_count


def test_confirm_review_rejects_storage_root(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(
        CONFIRM_REVIEW_SCENARIO_PATH,
        tmp_path,
    ).prepare()
    harness.run_named_step("create_stage06_final_review")
    harness.run_named_step("claim_stage06_final_review")
    packet = harness.run_named_step("create_draft_publish_packet")
    workbook = harness.run_named_step("create_draft_published_schedule")
    human_task_id = str(
        harness.output("create_stage06_final_review")["result"]["human_task"]["human_task_id"]
    )
    reviewed_ids = [
        str(packet["artifact_version"]["artifact_version_id"]),
        str(workbook["artifact_version"]["artifact_version_id"]),
    ]
    client = _api_client(harness)
    before_event_count = _artifact_created_event_count(harness)

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": reviewed_ids,
            "storage_root": str(tmp_path / "forbidden-confirm-root"),
            "idempotency_key": f"api:{harness.scenario_id}:confirm-review:storage-root-reject",
        },
    )

    assert response.status_code == 400
    assert response.payload["error"]["code"] == "invalid_artifact_ingress"
    assert _artifact_created_event_count(harness) == before_event_count
