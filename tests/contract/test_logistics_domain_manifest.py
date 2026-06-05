from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from onetruth.application.services import logistics_approval_response_hooks as hooks
from onetruth.application.services.logistics_workpage_action_registry import (
    LOGISTICS_WORKPAGE_ACTION_PACK,
)
from onetruth.application.services.logistics_workpage_descriptors import (
    LOGISTICS_WORKPAGE_DESCRIPTOR_PACK,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
LOGISTICS_MANIFEST_PATH = REPO_ROOT / "docs" / "domains" / "logistics" / "domain.yaml"
LOGISTICS_FAMILY_PATH = (
    REPO_ROOT
    / "docs"
    / "workflows"
    / "logistics_ops_family"
    / "v1"
    / "WORKFLOW_FAMILY.yaml"
)

DESCRIPTOR_PACK_REF = (
    "onetruth.application.services.logistics_workpage_descriptors."
    "LOGISTICS_WORKPAGE_DESCRIPTOR_PACK"
)
ACTION_PACK_REF = (
    "onetruth.application.services.logistics_workpage_action_registry."
    "LOGISTICS_WORKPAGE_ACTION_PACK"
)
HOOKS_REF_PREFIX = (
    "onetruth.application.services.logistics_approval_response_hooks."
)
HOOKS_REGISTRY_PACK_REF = f"{HOOKS_REF_PREFIX}LOGISTICS_APPROVAL_RESPONSE_EFFECT_PACK"
HOOKS_REGISTRY_REF = f"{HOOKS_REF_PREFIX}LOGISTICS_APPROVAL_RESPONSE_EFFECT_REGISTRY"


def _manifest() -> dict[str, Any]:
    payload = yaml.safe_load(LOGISTICS_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _family() -> dict[str, Any]:
    payload = yaml.safe_load(LOGISTICS_FAMILY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload["family"]


def _by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row[key]): row for row in rows}


def _normalized_subjects(rows: list[dict[str, Any]]) -> set[tuple[tuple[str, str], ...]]:
    return {tuple(sorted((str(key), str(value)) for key, value in row.items())) for row in rows}


def test_logistics_domain_workflow_rows_match_family_yaml() -> None:
    manifest_workflows = _by_key(_manifest()["workflows"], "module_id")
    family_modules = _by_key(_family()["modules"], "module_id")

    assert set(manifest_workflows) == set(family_modules)

    for module_id, family_module in family_modules.items():
        manifest_row = manifest_workflows[module_id]
        workflow_pack = family_module["workflow_pack_ref"]
        assert manifest_row["workflow_id"] == workflow_pack["workflow_id"]
        assert manifest_row["pack_path"] == workflow_pack["path"]
        assert manifest_row["partition_kind"] == family_module["partition"]["kind"]
        assert manifest_row["family_status"] == family_module["status"]


def test_logistics_domain_workflow_readiness_records_ready_slice_and_deferred_work() -> None:
    readiness_by_module = {
        str(row["module_id"]): str(row["readiness"]) for row in _manifest()["workflows"]
    }

    assert readiness_by_module == {
        "availability_request": "incubation",
        "weekly_schedule_planning": "ready",
        "live_dispatch": "ready",
        "dispatch_reporting": "ready",
        "timecard_audit": "disabled",
    }


def test_logistics_domain_workpage_rows_match_descriptor_pack_truth() -> None:
    manifest_workpages = _by_key(_manifest()["workpages"], "kind")
    descriptors = {
        descriptor.kind: descriptor
        for descriptor in LOGISTICS_WORKPAGE_DESCRIPTOR_PACK.descriptors
    }

    assert set(manifest_workpages) == set(descriptors)

    for kind, descriptor in descriptors.items():
        manifest_row = manifest_workpages[kind]
        assert manifest_row["workflow_id"] == descriptor.workflow_id
        assert manifest_row["descriptor_pack_ref"] == DESCRIPTOR_PACK_REF
        assert manifest_row["run_enabled"] is descriptor.run_enabled
        assert manifest_row["artifact_enabled"] is descriptor.artifact_enabled
        assert manifest_row["submit_enabled"] is descriptor.submit_enabled
        assert sorted(manifest_row["artifact_kinds"]) == sorted(descriptor.artifact_kinds)


def test_logistics_domain_workpage_action_subjects_match_action_pack_truth() -> None:
    manifest_workpages = _by_key(_manifest()["workpages"], "kind")
    expected_by_kind: dict[str, list[dict[str, str]]] = {
        kind: [] for kind in manifest_workpages
    }

    for rule in LOGISTICS_WORKPAGE_ACTION_PACK.human_task_rules:
        for stage_id, task_kind in sorted(rule.surfaces):
            expected_by_kind[rule.workpage_kind].append(
                {
                    "subject_kind": "human_task",
                    "workflow_id": rule.workflow_id,
                    "stage_id": stage_id,
                    "task_kind": task_kind,
                }
            )

    for rule in LOGISTICS_WORKPAGE_ACTION_PACK.approval_rules:
        for scope_ref in sorted(rule.scope_refs):
            expected_by_kind[rule.workpage_kind].append(
                {
                    "subject_kind": "approval",
                    "workflow_id": rule.workflow_id,
                    "scope_kind": "stage",
                    "scope_ref": scope_ref,
                }
            )

    for kind, expected_subjects in expected_by_kind.items():
        manifest_row = manifest_workpages[kind]
        expected_action_ref = ACTION_PACK_REF if expected_subjects else None
        assert manifest_row["action_pack_ref"] == expected_action_ref
        assert _normalized_subjects(manifest_row["action_subjects"]) == _normalized_subjects(
            expected_subjects
        )


def test_logistics_domain_approval_hook_side_effects_match_registered_hooks() -> None:
    manifest_hook_rows = {
        str(row["effect_id"]): row
        for row in _manifest()["side_effects"]
        if row["kind"] == "approval_response_hook"
    }
    registered_hooks = {
        hook.hook_id: hook for hook in hooks.LOGISTICS_APPROVAL_RESPONSE_HOOKS
    }

    assert set(manifest_hook_rows) == set(registered_hooks)
    assert manifest_hook_rows["logistics.weekly_publish_approval"][
        "workflow_id"
    ] == hooks.WEEKLY_WORKFLOW_ID
    assert manifest_hook_rows["logistics.weekly_publish_approval"]["details"] == {
        "approval_scope_kind": "stage",
        "approval_scope_ref": hooks.WEEKLY_STAGE06_SCOPE_REF,
        "requested_action": hooks.WEEKLY_PUBLISH_ACTION,
        "registry_pack_ref": HOOKS_REGISTRY_PACK_REF,
        "registry_ref": HOOKS_REGISTRY_REF,
        "event_effects": [
            "artifact.version.created",
            "artifact.pointer.promoted",
        ],
    }
    assert manifest_hook_rows["logistics.dispatch_reporting_finalize_approval"][
        "workflow_id"
    ] == hooks.DISPATCH_REPORTING_WORKFLOW_ID
    assert manifest_hook_rows["logistics.dispatch_reporting_finalize_approval"][
        "details"
    ] == {
        "approval_scope_kind": "stage",
        "approval_scope_ref": hooks.DISPATCH_REVIEW_APPROVAL_SCOPE_REF,
        "requested_action": hooks.DISPATCH_REVIEW_APPROVAL_ACTION,
        "registry_pack_ref": HOOKS_REGISTRY_PACK_REF,
        "registry_ref": HOOKS_REGISTRY_REF,
        "event_effects": [
            "artifact.version.created",
            "artifact.pointer.promoted",
            "workflow_family_edge",
        ],
    }

    for hook_id, registered_hook in registered_hooks.items():
        assert (
            manifest_hook_rows[hook_id]["source_ref"]
            == f"{HOOKS_REF_PREFIX}{registered_hook.handler.__name__}"
        )
        assert manifest_hook_rows[hook_id]["status"] == "ready"


def test_logistics_domain_handoff_side_effects_match_family_edges() -> None:
    manifest_edge_rows = {
        str(row["effect_id"]): row
        for row in _manifest()["side_effects"]
        if row["kind"] == "workflow_family_edge"
    }
    family_edges = _by_key(_family()["edges"], "edge_id")

    assert set(manifest_edge_rows) == set(family_edges)

    for edge_id, family_edge in family_edges.items():
        manifest_row = manifest_edge_rows[edge_id]
        assert manifest_row["source_ref"] == (
            "docs/workflows/logistics_ops_family/v1/WORKFLOW_FAMILY.yaml"
        )
        assert manifest_row["status"] == family_edge["status"]
        assert manifest_row["details"] == {
            "source_module_id": family_edge["source_module_id"],
            "target_module_id": family_edge["target_module_id"],
            "handoff_mode": family_edge["handoff_mode"],
        }
