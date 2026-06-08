from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, Iterable

from onetruth.capex_platform.source_refs import (
    SourceRefResolutionError,
    require_meaningful_source_refs,
)
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.capex_closure_governance import (
    create_closure_gate_evaluation,
    create_closure_snapshot,
    create_waiver,
    get_closure_gate_evaluation,
    get_waiver,
    list_current_closure_snapshots,
    mark_closure_snapshot_stale,
)


DEFAULT_CLOSURE_POLICY_VERSION = "capex.closure.v1"


@dataclass(frozen=True)
class ClosureDimensionInput:
    dimension_id: str
    source_refs: tuple[str, ...] = ()
    waiver_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClosureRecurrenceRule:
    rule_id: str
    trigger_kind: str
    action: str = "mark_stale"


class ClosureRecurrenceRuleRegistry:
    def __init__(self, rules: Iterable[ClosureRecurrenceRule] = ()) -> None:
        by_id: dict[str, ClosureRecurrenceRule] = {}
        for rule in rules:
            if rule.rule_id in by_id:
                raise ValueError(f"duplicate closure recurrence rule_id: {rule.rule_id}")
            by_id[rule.rule_id] = rule
        self._rules = tuple(by_id.values())

    @property
    def rules(self) -> tuple[ClosureRecurrenceRule, ...]:
        return self._rules

    def rules_for_trigger(self, trigger_kind: str) -> tuple[ClosureRecurrenceRule, ...]:
        return tuple(rule for rule in self._rules if rule.trigger_kind == trigger_kind)


DEFAULT_RECURRENCE_RULE_REGISTRY = ClosureRecurrenceRuleRegistry(
    (
        ClosureRecurrenceRule(
            rule_id="source_occurrence_basis_changed",
            trigger_kind="basis_ref_changed",
        ),
        ClosureRecurrenceRule(
            rule_id="waiver_lifecycle_changed",
            trigger_kind="waiver_lifecycle_changed",
        ),
    )
)


def grant_waiver(
    connection: sqlite3.Connection,
    *,
    waiver_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
    scope_kind: str,
    scope_ref: str,
    reason: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
    policy_version: str = DEFAULT_CLOSURE_POLICY_VERSION,
    expires_at: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    created_at = now_iso or utc_now_iso()
    create_waiver(
        connection,
        waiver_id=waiver_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        scope_kind=scope_kind,
        scope_ref=scope_ref,
        state="active",
        reason=reason,
        policy_version=policy_version,
        metadata_json=metadata_json or {},
        created_by_actor_id=created_by_actor_id,
        created_by_actor_type=created_by_actor_type,
        created_at=created_at,
        expires_at=expires_at,
    )
    waiver = get_waiver(connection, waiver_id)
    if waiver is None:
        raise RuntimeError("waiver create failed")
    return waiver


def evaluate_closure_gate(
    connection: sqlite3.Connection,
    *,
    closure_gate_evaluation_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
    closure_target_kind: str,
    closure_target_ref: str,
    dimensions: tuple[ClosureDimensionInput, ...],
    created_by_actor_id: str,
    created_by_actor_type: str,
    policy_version: str = DEFAULT_CLOSURE_POLICY_VERSION,
    metadata_json: dict[str, Any] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    if not dimensions:
        raise ValueError("closure requires at least one required dimension")

    created_at = now_iso or utc_now_iso()
    required_dimensions: list[dict[str, Any]] = []
    satisfied_dimensions: list[dict[str, Any]] = []
    missing_dimensions: list[dict[str, Any]] = []
    waiver_refs: list[dict[str, Any]] = []
    basis_refs: list[str] = []

    for dimension in dimensions:
        required_dimensions.append({"dimension_id": dimension.dimension_id})
        source_ref_status = _resolve_dimension_source_refs(
            connection,
            dimension,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
        )
        basis_refs.extend(source_ref_status["basis_refs"])
        if source_ref_status["satisfied"]:
            satisfied_dimensions.append(
                {
                    "dimension_id": dimension.dimension_id,
                    "satisfied_by": "source_refs",
                    "source_refs": list(dimension.source_refs),
                }
            )
            continue

        waiver = _first_active_matching_waiver(
            connection,
            waiver_ids=dimension.waiver_ids,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
            closure_target_kind=closure_target_kind,
            closure_target_ref=closure_target_ref,
            dimension_id=dimension.dimension_id,
            now_iso=created_at,
        )
        if waiver is not None:
            waiver_ref = {
                "dimension_id": dimension.dimension_id,
                "waiver_id": waiver["waiver_id"],
                "satisfied_by": "waiver",
            }
            waiver_refs.append(waiver_ref)
            satisfied_dimensions.append(
                {
                    "dimension_id": dimension.dimension_id,
                    "satisfied_by": "waiver",
                    "waiver_id": waiver["waiver_id"],
                }
            )
            basis_refs.append(f"waiver:{waiver['waiver_id']}")
            continue

        missing_dimensions.append(
            {
                "dimension_id": dimension.dimension_id,
                "reason": source_ref_status["reason"] or "missing_source_refs",
            }
        )

    if missing_dimensions:
        result = "fail"
    elif waiver_refs:
        result = "satisfied_by_waiver"
    else:
        result = "pass"

    basis_version_vector = {
        "policy_version": policy_version,
        "basis_refs": sorted(set(basis_refs)),
    }
    create_closure_gate_evaluation(
        connection,
        closure_gate_evaluation_id=closure_gate_evaluation_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        closure_target_kind=closure_target_kind,
        closure_target_ref=closure_target_ref,
        policy_version=policy_version,
        required_dimensions_json=required_dimensions,
        satisfied_dimensions_json=satisfied_dimensions,
        missing_dimensions_json=missing_dimensions,
        waiver_refs_json=waiver_refs,
        basis_version_vector_json=basis_version_vector,
        result=result,
        metadata_json=metadata_json or {},
        created_by_actor_id=created_by_actor_id,
        created_by_actor_type=created_by_actor_type,
        created_at=created_at,
    )
    evaluation = get_closure_gate_evaluation(connection, closure_gate_evaluation_id)
    if evaluation is None:
        raise RuntimeError("closure gate evaluation create failed")
    return evaluation


def create_closure_snapshot_from_evaluation(
    connection: sqlite3.Connection,
    *,
    closure_snapshot_id: str,
    closure_gate_evaluation_id: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
    metadata_json: dict[str, Any] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    evaluation = get_closure_gate_evaluation(connection, closure_gate_evaluation_id)
    if evaluation is None:
        raise ValueError(f"closure evaluation not found: {closure_gate_evaluation_id}")
    if evaluation["result"] == "fail":
        raise ValueError("failed closure evaluation cannot create a closure snapshot")
    created_at = now_iso or utc_now_iso()
    create_closure_snapshot(
        connection,
        closure_snapshot_id=closure_snapshot_id,
        closure_gate_evaluation_id=closure_gate_evaluation_id,
        tenant_id=str(evaluation["tenant_id"]),
        domain_id=str(evaluation["domain_id"]),
        project_id=evaluation["project_id"] if evaluation["project_id"] is not None else None,
        closure_target_kind=str(evaluation["closure_target_kind"]),
        closure_target_ref=str(evaluation["closure_target_ref"]),
        policy_version=str(evaluation["policy_version"]),
        state="current",
        result=str(evaluation["result"]),
        basis_version_vector_json=dict(evaluation["basis_version_vector_json"]),
        metadata_json=metadata_json or {},
        created_by_actor_id=created_by_actor_id,
        created_by_actor_type=created_by_actor_type,
        created_at=created_at,
    )
    snapshot = connection.execute(
        """
        SELECT *
        FROM capex_closure_snapshots
        WHERE closure_snapshot_id = ?
        """,
        (closure_snapshot_id,),
    ).fetchone()
    if snapshot is None:
        raise RuntimeError("closure snapshot create failed")
    from onetruth.infrastructure.repositories.capex_closure_governance import (
        get_closure_snapshot,
    )

    created = get_closure_snapshot(connection, closure_snapshot_id)
    assert created is not None
    return created


def mark_stale_closure_snapshots_for_basis_refs(
    connection: sqlite3.Connection,
    *,
    changed_basis_refs: tuple[str, ...],
    tenant_id: str | None = None,
    domain_id: str | None = None,
    project_id: str | None = None,
    trigger_kind: str = "basis_ref_changed",
    registry: ClosureRecurrenceRuleRegistry = DEFAULT_RECURRENCE_RULE_REGISTRY,
    now_iso: str | None = None,
) -> tuple[str, ...]:
    if not changed_basis_refs:
        return ()
    rules = registry.rules_for_trigger(trigger_kind)
    if not rules:
        return ()
    now = now_iso or utc_now_iso()
    changed = set(changed_basis_refs)
    stale_ids: list[str] = []
    for snapshot in list_current_closure_snapshots(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    ):
        basis_refs = set(_strings_in(snapshot["basis_version_vector_json"]))
        intersection = sorted(basis_refs & changed)
        if not intersection:
            continue
        reason = f"{trigger_kind}:{','.join(intersection)}"
        mark_closure_snapshot_stale(
            connection,
            closure_snapshot_id=str(snapshot["closure_snapshot_id"]),
            stale_reason=reason,
            stale_at=now,
        )
        stale_ids.append(str(snapshot["closure_snapshot_id"]))
    return tuple(stale_ids)


def _resolve_dimension_source_refs(
    connection: sqlite3.Connection,
    dimension: ClosureDimensionInput,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
) -> dict[str, Any]:
    if not dimension.source_refs:
        return {"satisfied": False, "reason": "missing_source_refs", "basis_refs": []}
    try:
        resolutions = require_meaningful_source_refs(
            connection,
            dimension.source_refs,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
        )
    except SourceRefResolutionError as exc:
        return {
            "satisfied": False,
            "reason": "unresolved_source_refs",
            "basis_refs": [
                resolution.source_ref
                for resolution in exc.resolutions
                if resolution.source_ref
            ],
        }
    return {
        "satisfied": True,
        "reason": None,
        "basis_refs": [resolution.source_ref for resolution in resolutions],
    }


def _first_active_matching_waiver(
    connection: sqlite3.Connection,
    *,
    waiver_ids: tuple[str, ...],
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
    closure_target_kind: str,
    closure_target_ref: str,
    dimension_id: str,
    now_iso: str,
) -> dict[str, Any] | None:
    for waiver_id in waiver_ids:
        waiver = get_waiver(connection, waiver_id)
        if waiver is None:
            continue
        if not _waiver_is_active_in_scope(
            waiver,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
            closure_target_kind=closure_target_kind,
            closure_target_ref=closure_target_ref,
            dimension_id=dimension_id,
            now_iso=now_iso,
        ):
            continue
        return waiver
    return None


def _waiver_is_active_in_scope(
    waiver: dict[str, Any],
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str | None,
    closure_target_kind: str,
    closure_target_ref: str,
    dimension_id: str,
    now_iso: str,
) -> bool:
    if str(waiver["state"]) != "active":
        return False
    if str(waiver["tenant_id"]) != tenant_id or str(waiver["domain_id"]) != domain_id:
        return False
    waiver_project_id = waiver["project_id"] if waiver["project_id"] is not None else None
    if waiver_project_id != project_id:
        return False
    expires_at = waiver["expires_at"]
    if expires_at is not None and str(expires_at) < now_iso:
        return False
    scope_kind = str(waiver["scope_kind"])
    scope_ref = str(waiver["scope_ref"])
    if scope_kind == "closure_dimension":
        return scope_ref == dimension_id
    if scope_kind == "closure_target":
        return scope_ref == f"{closure_target_kind}:{closure_target_ref}"
    if scope_kind == "capex_project":
        return project_id is not None and scope_ref == project_id
    return False


def _strings_in(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        found: list[str] = []
        for key, child in value.items():
            found.extend(_strings_in(key))
            found.extend(_strings_in(child))
        return tuple(found)
    if isinstance(value, list):
        found = []
        for child in value:
            found.extend(_strings_in(child))
        return tuple(found)
    return ()


__all__ = [
    "ClosureDimensionInput",
    "ClosureRecurrenceRule",
    "ClosureRecurrenceRuleRegistry",
    "DEFAULT_CLOSURE_POLICY_VERSION",
    "DEFAULT_RECURRENCE_RULE_REGISTRY",
    "create_closure_snapshot_from_evaluation",
    "evaluate_closure_gate",
    "grant_waiver",
    "mark_stale_closure_snapshots_for_basis_refs",
]
