from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT, run_cli, stderr_json, stdout_json

SCHEDULE_TEMPLATE_PACK_ROOT = REPO_ROOT / "fixtures/workflows/schedule_planning/template_pack"
EXAMPLE_CORPUS_MANIFEST = REPO_ROOT / "fixtures/example_document_corpus/manifest.yaml"


def _create_workflow_run(db_url: str, activation_key: str) -> dict[str, object]:
    payload = {
        "workflow_id": "schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "SD-2026-03-10",
        "logical_date": "2026-03-10",
        "activation_key": activation_key,
        "idempotency_key": f"idem:{activation_key}",
    }
    result = run_cli("--db-url", db_url, "runs", "create", "--json", json.dumps(payload))
    return stdout_json(result)["workflow_run"]


def _create_task_with_human_task(db_url: str, workflow_run_id: str, activation_key: str) -> dict[str, object]:
    payload = {
        "workflow_run_id": workflow_run_id,
        "stage_id": "Stage06",
        "task_kind": "review_packet",
        "activation_key": activation_key,
        "candidate_roles": ["dispatch_supervisor"],
        "owner_role": "dispatch_supervisor",
        "create_human_task": True,
        "idempotency_key": f"idem:task:{activation_key}",
    }
    result = run_cli("--db-url", db_url, "tasks", "create", "--json", json.dumps(payload))
    return stdout_json(result)["result"]


def _request_approval(db_url: str, workflow_run_id: str, task_run_id: str) -> dict[str, object]:
    payload = {
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "approval_kind": "business_decision",
        "scope_kind": "stage",
        "scope_ref": "Stage06",
        "action": "publish_schedule",
        "candidate_roles": ["dispatch_supervisor"],
        "required_role": "dispatch_supervisor",
        "idempotency_key": f"idem:approval:{workflow_run_id}",
    }
    result = run_cli("--db-url", db_url, "approvals", "request", "--json", json.dumps(payload))
    return stdout_json(result)["approval"]


def _create_flag(db_url: str, workflow_run_id: str) -> dict[str, object]:
    payload = {
        "workflow_run_id": workflow_run_id,
        "kind": "traffic_disruption",
        "severity": "high",
        "summary": "Traffic incident requires route adjustment.",
        "details_json": {"zone_id": "berlin-east"},
        "created_by_actor_id": "human:dispatcher-1",
        "created_by_actor_type": "human",
        "idempotency_key": f"idem:flag:{workflow_run_id}",
    }
    result = run_cli("--db-url", db_url, "flags", "create", "--json", json.dumps(payload))
    return stdout_json(result)["flag"]


def test_example_doc_ingress_creates_canonical_artifact_and_links(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    run_cli("--db-url", db_url, "init-db")

    workflow = _create_workflow_run(db_url, "ingress-links-workflow")
    workflow_run_id = str(workflow["workflow_run_id"])
    task_result = _create_task_with_human_task(db_url, workflow_run_id, "ingress-links-task")
    task_run_id = str(task_result["task_run"]["task_run_id"])
    human_task_id = str(task_result["human_task"]["human_task_id"])
    approval = _request_approval(db_url, workflow_run_id, task_run_id)
    approval_id = str(approval["approval_id"])
    flag = _create_flag(db_url, workflow_run_id)
    flag_id = str(flag["flag_id"])

    source = (
        SCHEDULE_TEMPLATE_PACK_ROOT
        / "Stage06_Supervisor_Review_Publish/Stage06_Supervisor_Review_Publish_Document_Example_COMPLETED.docx"
    )
    ingest_payload = {
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "artifact_kind": "schedule.supervisor_review.doc",
        "artifact_role": "evidence",
        "source_path": str(source),
        "file_name": source.name,
        "idempotency_key": "idem:ingest:links",
        "links": [
            {"subject_kind": "workflow_run", "subject_id": workflow_run_id},
            {"subject_kind": "human_task", "subject_id": human_task_id},
            {"subject_kind": "approval", "subject_id": approval_id},
            {"subject_kind": "flag", "subject_id": flag_id},
        ],
    }
    ingest = run_cli("--db-url", db_url, "artifacts", "ingest", "--json", json.dumps(ingest_payload))
    parsed_ingest = stdout_json(ingest)
    artifact = parsed_ingest["artifact_version"]
    artifact_version_id = artifact["artifact_version_id"]

    task_linked = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "list-linked",
            "--workflow-run-id",
            workflow_run_id,
            "--subject-kind",
            "human_task",
            "--subject-id",
            human_task_id,
            "--json",
        )
    )["artifact_versions"]
    approval_linked = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "list-linked",
            "--workflow-run-id",
            workflow_run_id,
            "--subject-kind",
            "approval",
            "--subject-id",
            approval_id,
            "--json",
        )
    )["artifact_versions"]
    flag_linked = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "list-linked",
            "--workflow-run-id",
            workflow_run_id,
            "--subject-kind",
            "flag",
            "--subject-id",
            flag_id,
            "--json",
        )
    )["artifact_versions"]

    assert task_linked and task_linked[0]["artifact_version_id"] == artifact_version_id
    assert approval_linked and approval_linked[0]["artifact_version_id"] == artifact_version_id
    assert flag_linked and flag_linked[0]["artifact_version_id"] == artifact_version_id

    events = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "events",
            "list",
            "--run-id",
            workflow_run_id,
            "--json",
        )
    )
    created_events = [event for event in events if event["event_type"] == "artifact.version.created"]
    assert len(created_events) == 1
    link_types = {link["type"] for link in created_events[0]["links"]}
    assert {"workflow_run", "artifact_version", "human_task", "approval", "flag"} <= link_types


def test_manifest_seed_is_deterministic_and_round_trips_digest_metadata(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    run_cli("--db-url", db_url, "init-db")

    workflow_a = _create_workflow_run(db_url, "seed-workflow-a")
    workflow_b = _create_workflow_run(db_url, "seed-workflow-b")
    workflow_run_id_a = str(workflow_a["workflow_run_id"])
    workflow_run_id_b = str(workflow_b["workflow_run_id"])

    seed_payload_a = {
        "workflow_run_id": workflow_run_id_a,
        "seed_set_id": "stage06_review_ready_example_set",
        "manifest_path": str(EXAMPLE_CORPUS_MANIFEST),
        "idempotency_prefix": "seed:a",
    }
    seed_payload_b = {
        "workflow_run_id": workflow_run_id_b,
        "seed_set_id": "stage06_review_ready_example_set",
        "manifest_path": str(EXAMPLE_CORPUS_MANIFEST),
        "idempotency_prefix": "seed:b",
    }

    seeded_a = stdout_json(
        run_cli("--db-url", db_url, "artifacts", "seed-corpus", "--json", json.dumps(seed_payload_a))
    )["artifact_versions"]
    seeded_b = stdout_json(
        run_cli("--db-url", db_url, "artifacts", "seed-corpus", "--json", json.dumps(seed_payload_b))
    )["artifact_versions"]

    fixture_to_digest_a = {
        artifact["metadata_json"]["fixture_id"]: artifact["content_digest"] for artifact in seeded_a
    }
    fixture_to_digest_b = {
        artifact["metadata_json"]["fixture_id"]: artifact["content_digest"] for artifact in seeded_b
    }
    assert fixture_to_digest_a == fixture_to_digest_b
    assert len(fixture_to_digest_a) == 2

    # Validate digest/byte_size against source bytes.
    for artifact in seeded_a:
        fixture_id = artifact["metadata_json"]["fixture_id"]
        source_path = artifact["metadata_json"]["ingress_source_path"]
        content = Path(source_path).read_bytes()
        expected_digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
        assert artifact["content_digest"] == expected_digest
        assert artifact["byte_size"] == len(content)
        assert fixture_id.startswith("schedule.")

    # Seed retry with identical idempotency prefix fails closed.
    retry = run_cli(
        "--db-url",
        db_url,
        "artifacts",
        "seed-corpus",
        "--json",
        json.dumps(seed_payload_a),
        expect_ok=False,
    )
    assert retry.returncode != 0
    assert stderr_json(retry)["error_code"] == "duplicate_idempotency_key"


def test_artifact_download_command_writes_original_bytes(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    run_cli("--db-url", db_url, "init-db")
    workflow = _create_workflow_run(db_url, "download-artifact-workflow")
    workflow_run_id = str(workflow["workflow_run_id"])

    source = (
        SCHEDULE_TEMPLATE_PACK_ROOT
        / "Stage07_Intraday_Exception_Control/Stage07_Intraday_Exception_Control_Spreadsheet_Example_COMPLETED.xlsx"
    )
    ingest_payload = {
        "workflow_run_id": workflow_run_id,
        "artifact_kind": "schedule.replan_delta.workbook",
        "artifact_role": "official_output",
        "source_path": str(source),
        "file_name": source.name,
        "idempotency_key": "idem:ingest:download",
        "links": [
            {"subject_kind": "workflow_run", "subject_id": workflow_run_id},
        ],
    }
    ingested = stdout_json(
        run_cli("--db-url", db_url, "artifacts", "ingest", "--json", json.dumps(ingest_payload))
    )["artifact_version"]
    artifact_version_id = str(ingested["artifact_version_id"])

    output_path = tmp_path / "downloaded" / source.name
    download = run_cli(
        "--db-url",
        db_url,
        "artifacts",
        "download",
        "--artifact-version-id",
        artifact_version_id,
        "--output-path",
        str(output_path),
        "--json",
    )
    payload = stdout_json(download)
    assert payload["status"] == "ok"
    assert payload["artifact_version"]["artifact_version_id"] == artifact_version_id
    assert output_path.read_bytes() == source.read_bytes()
