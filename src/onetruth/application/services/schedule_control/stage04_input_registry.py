from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from onetruth.application.handlers._shared.command_boundary import CommandError


_REPO_ROOT = Path(__file__).resolve().parents[5]
_WORKFLOW_CONTRACT_PATH = (
    _REPO_ROOT / "docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml"
)
_ARTIFACT_MAP_PATH = (
    _REPO_ROOT / "docs/workflows/weekly_schedule_planning/v1/ARTIFACT_MAP.yaml"
)
_EXECUTION_PROFILE_PATH = (
    _REPO_ROOT / "docs/workflows/weekly_schedule_planning/v1/EXECUTION_PROFILE.yaml"
)


@dataclass(frozen=True)
class WeeklyStage04InputSlot:
    slot_key: str
    dataset_key: str
    source_stage_id: str
    required_at_runtime: bool
    required_in_stage04_profile: bool

    @property
    def alias_key(self) -> str:
        if "." not in self.dataset_key:
            return self.dataset_key
        return self.dataset_key.split(".", maxsplit=1)[1]


_WEEKLY_STAGE04_INPUT_SLOTS: tuple[WeeklyStage04InputSlot, ...] = (
    WeeklyStage04InputSlot(
        slot_key="route_slot_requirements",
        dataset_key="planning.route_slot_requirements.workbook",
        source_stage_id="Stage04",
        required_at_runtime=True,
        required_in_stage04_profile=True,
    ),
    WeeklyStage04InputSlot(
        slot_key="driver_capabilities",
        dataset_key="planning.driver_capabilities.workbook",
        source_stage_id="Stage04",
        required_at_runtime=True,
        required_in_stage04_profile=True,
    ),
    WeeklyStage04InputSlot(
        slot_key="approved_availability",
        dataset_key="planning.approved_availability.workbook",
        source_stage_id="Stage02",
        required_at_runtime=False,
        required_in_stage04_profile=False,
    ),
    WeeklyStage04InputSlot(
        slot_key="actual_hours",
        dataset_key="planning.actual_hours_snapshot.workbook",
        source_stage_id="Stage03",
        required_at_runtime=False,
        required_in_stage04_profile=False,
    ),
    WeeklyStage04InputSlot(
        slot_key="route_horizon",
        dataset_key="planning.route_horizon.workbook",
        source_stage_id="Stage01",
        required_at_runtime=False,
        required_in_stage04_profile=False,
    ),
)


@lru_cache(maxsize=1)
def weekly_stage04_input_slots() -> dict[str, WeeklyStage04InputSlot]:
    workflow_contract = _load_yaml_mapping(_WORKFLOW_CONTRACT_PATH)
    artifact_map = _load_yaml_mapping(_ARTIFACT_MAP_PATH)
    execution_profile = _load_yaml_mapping(_EXECUTION_PROFILE_PATH)
    _validate_authored_slot_registry(
        workflow_contract=workflow_contract,
        artifact_map=artifact_map,
        execution_profile=execution_profile,
    )
    return {slot.slot_key: slot for slot in _WEEKLY_STAGE04_INPUT_SLOTS}


def resolve_weekly_stage04_input_artifacts(
    *,
    artifacts: list[dict[str, Any]],
    stage_spec: Mapping[str, Any],
) -> dict[str, dict[str, Any] | None]:
    slots = weekly_stage04_input_slots()
    _validate_stage04_required_bindings(stage_spec=stage_spec, slots=slots)

    resolved: dict[str, dict[str, Any] | None] = {slot_key: None for slot_key in slots}
    for artifact in sorted(
        artifacts,
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("artifact_version_id") or ""),
        ),
    ):
        for slot_key, slot in slots.items():
            if _artifact_matches_dataset_key(artifact=artifact, dataset_key=slot.dataset_key):
                resolved[slot_key] = artifact

    missing_slots = [
        {"slot_key": slot.slot_key, "dataset_key": slot.dataset_key}
        for slot in slots.values()
        if slot.required_at_runtime and resolved[slot.slot_key] is None
    ]
    if missing_slots:
        raise CommandError(
            code="stage04_input_artifact_missing",
            message="required Stage04 input artifacts are missing for weekly Stage04 agent execution",
            details={"missing_slots": missing_slots},
        )

    return resolved


def _validate_authored_slot_registry(
    *,
    workflow_contract: Mapping[str, Any],
    artifact_map: Mapping[str, Any],
    execution_profile: Mapping[str, Any],
) -> None:
    contract_stage_artifacts = _workflow_contract_stage_artifacts(workflow_contract)
    artifact_map_stage_artifacts = _artifact_map_stage_artifacts(artifact_map)
    profile_stage_keys = _execution_profile_required_evidence_keys(execution_profile)

    errors: list[dict[str, str]] = []
    stage04_profile_keys = profile_stage_keys.get("Stage04", set())
    for slot in _WEEKLY_STAGE04_INPUT_SLOTS:
        source_stage_artifacts = contract_stage_artifacts.get(slot.source_stage_id, set())
        if slot.dataset_key not in source_stage_artifacts:
            errors.append(
                {
                    "slot_key": slot.slot_key,
                    "reason": "missing_from_workflow_contract",
                    "dataset_key": slot.dataset_key,
                    "stage_id": slot.source_stage_id,
                }
            )
        artifact_map_keys = artifact_map_stage_artifacts.get(slot.source_stage_id, set())
        if slot.dataset_key not in artifact_map_keys:
            errors.append(
                {
                    "slot_key": slot.slot_key,
                    "reason": "missing_from_artifact_map",
                    "dataset_key": slot.dataset_key,
                    "stage_id": slot.source_stage_id,
                }
            )
        source_stage_profile_keys = profile_stage_keys.get(slot.source_stage_id, set())
        if slot.dataset_key not in source_stage_profile_keys:
            errors.append(
                {
                    "slot_key": slot.slot_key,
                    "reason": "missing_from_execution_profile",
                    "dataset_key": slot.dataset_key,
                    "stage_id": slot.source_stage_id,
                }
            )
        if slot.required_in_stage04_profile and slot.dataset_key not in stage04_profile_keys:
            errors.append(
                {
                    "slot_key": slot.slot_key,
                    "reason": "missing_from_stage04_required_evidence",
                    "dataset_key": slot.dataset_key,
                    "stage_id": "Stage04",
                }
            )

    if errors:
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="weekly Stage04 authored input registry drifted from repo-native workflow source",
            details={"slot_registry_errors": errors},
        )


def _validate_stage04_required_bindings(
    *,
    stage_spec: Mapping[str, Any],
    slots: Mapping[str, WeeklyStage04InputSlot],
) -> None:
    required_keys = {
        str(item).strip()
        for item in stage_spec.get("required_evidence_keys") or []
        if str(item).strip()
    }
    missing_required_keys = sorted(
        slot.dataset_key
        for slot in slots.values()
        if slot.required_in_stage04_profile and slot.dataset_key not in required_keys
    )
    ambiguous_required_keys = [
        {
            "slot_key": slot.slot_key,
            "expected_dataset_key": slot.dataset_key,
            "conflicting_dataset_keys": conflicts,
        }
        for slot in slots.values()
        if slot.required_in_stage04_profile
        for conflicts in [sorted(_conflicting_alias_keys(required_keys, slot))]
        if conflicts
    ]
    if missing_required_keys or ambiguous_required_keys:
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="compiled Stage04 metadata has missing or ambiguous required artifact bindings",
            details={
                "required_evidence_keys": sorted(required_keys),
                "missing_required_evidence_keys": missing_required_keys,
                "ambiguous_required_evidence_keys": ambiguous_required_keys,
            },
        )


def _conflicting_alias_keys(
    required_keys: set[str],
    slot: WeeklyStage04InputSlot,
) -> set[str]:
    return {
        key
        for key in required_keys
        if key != slot.dataset_key and _dataset_alias_key(key) == slot.alias_key
    }


def _artifact_matches_dataset_key(*, artifact: Mapping[str, Any], dataset_key: str) -> bool:
    artifact_dataset_key = str(artifact.get("dataset_key") or "").strip()
    if artifact_dataset_key:
        return artifact_dataset_key == dataset_key
    artifact_kind = str(artifact.get("artifact_kind") or "").strip()
    return artifact_kind == dataset_key


def _workflow_contract_stage_artifacts(document: Mapping[str, Any]) -> dict[str, set[str]]:
    stages = document.get("stages")
    if not isinstance(stages, list):
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="weekly workflow contract must declare stages",
            details={"path": str(_WORKFLOW_CONTRACT_PATH)},
        )
    stage_artifacts: dict[str, set[str]] = {}
    for stage in stages:
        if not isinstance(stage, Mapping):
            continue
        stage_id = str(stage.get("id") or "").strip()
        artifacts = stage.get("artifacts")
        keys = {
            str(item.get("dataset_key") or "").strip()
            for item in artifacts or []
            if isinstance(item, Mapping) and str(item.get("dataset_key") or "").strip()
        }
        if stage_id:
            stage_artifacts[stage_id] = keys
    return stage_artifacts


def _artifact_map_stage_artifacts(document: Mapping[str, Any]) -> dict[str, set[str]]:
    artifact_sets = document.get("artifact_sets")
    if not isinstance(artifact_sets, Mapping):
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="weekly artifact map must declare artifact_sets",
            details={"path": str(_ARTIFACT_MAP_PATH)},
        )
    stage_artifacts: dict[str, set[str]] = {}
    for stage_id, artifacts in artifact_sets.items():
        stage_artifacts[str(stage_id)] = {
            str(item.get("key") or "").strip()
            for item in artifacts or []
            if isinstance(item, Mapping) and str(item.get("key") or "").strip()
        }
    return stage_artifacts


def _execution_profile_required_evidence_keys(
    document: Mapping[str, Any],
) -> dict[str, set[str]]:
    profile = document.get("profile")
    if not isinstance(profile, Mapping):
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="weekly execution profile must declare profile metadata",
            details={"path": str(_EXECUTION_PROFILE_PATH)},
        )
    stages = profile.get("stages")
    if not isinstance(stages, list):
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="weekly execution profile must declare stage entries",
            details={"path": str(_EXECUTION_PROFILE_PATH)},
        )
    stage_keys: dict[str, set[str]] = {}
    for stage in stages:
        if not isinstance(stage, Mapping):
            continue
        stage_id = str(stage.get("stage_id") or "").strip()
        keys = {
            str(item).strip()
            for item in stage.get("required_evidence_keys") or []
            if str(item).strip()
        }
        if stage_id:
            stage_keys[stage_id] = keys
    return stage_keys


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="weekly Stage04 authored metadata file is missing",
            details={"path": str(path)},
        ) from exc
    if not isinstance(loaded, dict):
        raise CommandError(
            code="invalid_weekly_stage04_control_spec",
            message="weekly Stage04 authored metadata must parse as an object",
            details={"path": str(path)},
        )
    return loaded


def _dataset_alias_key(dataset_key: str) -> str:
    if "." not in dataset_key:
        return dataset_key
    return dataset_key.split(".", maxsplit=1)[1]
