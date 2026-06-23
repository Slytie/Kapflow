from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.corpus_baseline_workflow import (
    CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
)


GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION = (
    "capex.governance_commitment_chain.outputs.v1"
)
GOVERNANCE_COMMITMENT_CHAIN_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)

COMMITMENT_EVENT_TYPES = frozenset(
    {
        "approval",
        "budget",
        "quote",
        "order",
        "revision",
        "settlement",
        "responsibility_shift",
    }
)
COMMITMENT_TYPES = frozenset(
    {
        "approval",
        "budget",
        "quote",
        "purchase_order",
        "change_order",
        "settlement",
        "responsibility",
    }
)
OFFICIALNESS_SCOPES = frozenset({"external", "internal", "mixed", "draft"})
COMMERCIAL_STATUSES = frozenset(
    {"draft", "proposed", "approved", "ordered", "revised", "settled", "voided"}
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "document_text",
    "extracted_text",
    "file_name",
    "filename",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_file",
    "raw_filename",
    "source_filename",
}


@dataclass(frozen=True)
class GovernanceCommitmentChainError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_governance_commitment_chain_outputs(
    *,
    corpus_baseline_outputs: Mapping[str, Any],
    commitment_observations: Sequence[Mapping[str, Any]],
    workflow_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only governance commitment outputs from sanitized observations."""

    _require_corpus_baseline(corpus_baseline_outputs)
    tenant_id = _require_nonempty(corpus_baseline_outputs.get("tenant_id"), "tenant_id")
    domain_id = _require_nonempty(corpus_baseline_outputs.get("domain_id"), "domain_id")
    project_id = _require_nonempty(corpus_baseline_outputs.get("project_id"), "project_id")
    available_source_refs = _available_source_refs(corpus_baseline_outputs)
    if not commitment_observations:
        raise GovernanceCommitmentChainError(
            "commitment_observations_required",
            {"field": "commitment_observations"},
        )

    commitment_rows: list[dict[str, Any]] = []
    expenditure_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    seen_commitment_ids: set[str] = set()
    for index, observation in enumerate(commitment_observations):
        if not isinstance(observation, Mapping):
            raise GovernanceCommitmentChainError(
                "commitment_observation_must_be_object",
                {"index": index},
            )
        commitment_row, ledger_rows, flags = _commitment_row(
            index=index,
            observation=observation,
            available_source_refs=available_source_refs,
        )
        if commitment_row["commitment_id"] in seen_commitment_ids:
            raise GovernanceCommitmentChainError(
                "commitment_duplicate_id",
                {"index": index, "commitment_id": commitment_row["commitment_id"]},
            )
        seen_commitment_ids.add(commitment_row["commitment_id"])
        commitment_rows.append(commitment_row)
        expenditure_rows.extend(ledger_rows)
        flag_rows.extend(flags)

    commitment_rows = sorted(commitment_rows, key=lambda row: row["commitment_id"])
    expenditure_rows = sorted(expenditure_rows, key=lambda row: row["ledger_entry_id"])
    flag_rows = sorted(flag_rows, key=lambda row: row["flag_id"])
    return {
        "schema_version": GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION,
        "activation_posture": GOVERNANCE_COMMITMENT_CHAIN_ACTIVATION_POSTURE,
        "workflow_id": _require_nonempty(workflow_id, "workflow_id"),
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "project_id": project_id,
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "basis": {
            "corpus_baseline_workflow_id": _require_nonempty(
                corpus_baseline_outputs.get("workflow_id"),
                "corpus_baseline_outputs.workflow_id",
            ),
            "packet_register_id": _require_nonempty(
                corpus_baseline_outputs.get("basis", {}).get("packet_register_id")
                if isinstance(corpus_baseline_outputs.get("basis"), Mapping)
                else None,
                "corpus_baseline_outputs.basis.packet_register_id",
            ),
        },
        "commitment_chain": {
            "schema_version": "capex.commitment_chain.v1",
            "rows": commitment_rows,
            "row_count": len(commitment_rows),
            "snapshot_digest": _digest(commitment_rows),
        },
        "expenditure_ledger": {
            "schema_version": "capex.expenditure_ledger.v1",
            "rows": expenditure_rows,
            "row_count": len(expenditure_rows),
            "snapshot_digest": _digest(expenditure_rows),
        },
        "commitment_flags": {
            "schema_version": "capex.commitment_flags.v1",
            "rows": flag_rows,
            "row_count": len(flag_rows),
            "snapshot_digest": _digest(flag_rows),
        },
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_approvals": False,
            "closes_technical_rca": False,
            "creates_reviewed_baseline": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "authored_workflow_pack_activation",
            "workflow_run_creation",
            "public_route_activation",
            "frontend_route_activation",
            "approval_response_mutation",
            "technical_rca_closure",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_governance_commitment_chain_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def governance_commitment_chain_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_governance_commitment_chain_bytes(outputs)
    ).hexdigest()


def _commitment_row(
    *,
    index: int,
    observation: Mapping[str, Any],
    available_source_refs: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    _reject_raw_material(observation, path=f"commitment_observations[{index}]")
    commitment_id = _require_nonempty(
        observation.get("commitment_id"),
        f"commitment_observations[{index}].commitment_id",
    )
    commitment_type = _allowed(
        observation.get("commitment_type"),
        COMMITMENT_TYPES,
        "commitment_type",
        index,
    )
    commercial_status = _allowed(
        observation.get("commercial_status"),
        COMMERCIAL_STATUSES,
        "commercial_status",
        index,
    )
    officialness_scope = _allowed(
        observation.get("officialness_scope"),
        OFFICIALNESS_SCOPES,
        "officialness_scope",
        index,
    )
    source_refs = _source_refs(observation.get("source_refs"), available_source_refs, index)
    events = _events(observation.get("events"), index=index)
    if any(event["event_type"] == "settlement" for event in events) and bool(
        observation.get("closes_technical_rca", False)
    ):
        raise GovernanceCommitmentChainError(
            "settlement_must_not_close_technical_rca",
            {"index": index, "commitment_id": commitment_id},
        )

    revisions = [
        {
            "event_id": event["event_id"],
            "revision_id": event.get("revision_id"),
            "effective_at": event["effective_at"],
        }
        for event in events
        if event["event_type"] in {"order", "revision"}
    ]
    ledger_rows = [
        {
            "ledger_entry_id": f"{commitment_id}:{event['event_id']}",
            "commitment_id": commitment_id,
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "amount_cents": event.get("amount_cents"),
            "currency": event.get("currency"),
            "commercial_status": commercial_status,
            "source_refs": source_refs,
        }
        for event in events
        if event["event_type"] in {"budget", "quote", "order", "revision", "settlement"}
    ]
    flag_rows = _flag_rows(
        commitment_id=commitment_id,
        observation=observation,
        source_refs=source_refs,
        events=events,
    )
    row = {
        "commitment_id": commitment_id,
        "commitment_type": commitment_type,
        "commercial_status": commercial_status,
        "officialness_scope": officialness_scope,
        "source_refs": source_refs,
        "events": events,
        "revision_history": revisions,
        "current_revision_id": revisions[-1]["revision_id"] if revisions else None,
        "responsibility_shift": _optional_text(observation.get("responsibility_shift")),
        "technical_rca_status": "not_closed_by_commercial_settlement",
        "official_truth": False,
    }
    return row, ledger_rows, flag_rows


def _events(value: Any, *, index: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise GovernanceCommitmentChainError(
            "commitment_events_required",
            {"index": index},
        )
    rows: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    for event_index, raw_event in enumerate(value):
        if not isinstance(raw_event, Mapping):
            raise GovernanceCommitmentChainError(
                "commitment_event_must_be_object",
                {"index": index, "event_index": event_index},
            )
        event_type = _allowed(
            raw_event.get("event_type"),
            COMMITMENT_EVENT_TYPES,
            "event_type",
            index,
            event_index=event_index,
        )
        event_id = _require_nonempty(
            raw_event.get("event_id"),
            f"commitment_observations[{index}].events[{event_index}].event_id",
        )
        if event_id in seen_event_ids:
            raise GovernanceCommitmentChainError(
                "commitment_duplicate_event_id",
                {"index": index, "event_id": event_id},
            )
        seen_event_ids.add(event_id)
        amount_cents = raw_event.get("amount_cents")
        if amount_cents is not None and (
            not isinstance(amount_cents, int) or amount_cents < 0
        ):
            raise GovernanceCommitmentChainError(
                "commitment_amount_invalid",
                {"index": index, "event_id": event_id},
            )
        rows.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "effective_at": _require_nonempty(
                    raw_event.get("effective_at"),
                    f"commitment_observations[{index}].events[{event_index}].effective_at",
                ),
                "revision_id": _optional_text(raw_event.get("revision_id")),
                "amount_cents": amount_cents,
                "currency": _optional_text(raw_event.get("currency")),
                "responsibility_from": _optional_text(raw_event.get("responsibility_from")),
                "responsibility_to": _optional_text(raw_event.get("responsibility_to")),
            }
        )
    return sorted(rows, key=lambda row: (row["effective_at"], row["event_id"]))


def _flag_rows(
    *,
    commitment_id: str,
    observation: Mapping[str, Any],
    source_refs: list[str],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if any(event["event_type"] == "settlement" for event in events):
        rows.append(
            {
                "flag_id": f"{commitment_id}:settlement-not-technical-rca",
                "commitment_id": commitment_id,
                "flag_type": "settlement_not_technical_rca",
                "severity": "medium",
                "source_refs": source_refs,
            }
        )
    for flag_index, raw_flag in enumerate(observation.get("flags") or []):
        if not isinstance(raw_flag, Mapping):
            raise GovernanceCommitmentChainError(
                "commitment_flag_must_be_object",
                {"commitment_id": commitment_id, "flag_index": flag_index},
            )
        rows.append(
            {
                "flag_id": _require_nonempty(
                    raw_flag.get("flag_id"),
                    f"commitment_observations[].flags[{flag_index}].flag_id",
                ),
                "commitment_id": commitment_id,
                "flag_type": _require_nonempty(
                    raw_flag.get("flag_type"),
                    f"commitment_observations[].flags[{flag_index}].flag_type",
                ),
                "severity": _require_nonempty(
                    raw_flag.get("severity"),
                    f"commitment_observations[].flags[{flag_index}].severity",
                ),
                "source_refs": source_refs,
            }
        )
    return rows


def _require_corpus_baseline(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION:
        raise GovernanceCommitmentChainError(
            "commitment_requires_corpus_baseline_outputs",
            {
                "expected_schema_version": CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _available_source_refs(corpus_baseline_outputs: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for artifact in corpus_baseline_outputs.get("generated_artifacts") or []:
        if not isinstance(artifact, Mapping):
            continue
        envelope = artifact.get("envelope")
        if not isinstance(envelope, Mapping):
            continue
        for source_ref in envelope.get("source_refs") or []:
            refs.add(str(source_ref))
    if not refs:
        raise GovernanceCommitmentChainError(
            "commitment_source_basis_required",
            {"field": "corpus_baseline_outputs.generated_artifacts[].envelope.source_refs"},
        )
    return refs


def _source_refs(value: Any, available_source_refs: set[str], index: int) -> list[str]:
    if not isinstance(value, list) or not value:
        raise GovernanceCommitmentChainError(
            "commitment_source_refs_required",
            {"index": index},
        )
    refs: list[str] = []
    for ref_index, raw_ref in enumerate(value):
        source_ref = _require_nonempty(
            raw_ref,
            f"commitment_observations[{index}].source_refs[{ref_index}]",
        )
        if source_ref not in available_source_refs:
            raise GovernanceCommitmentChainError(
                "commitment_source_ref_not_in_corpus_baseline",
                {"index": index, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise GovernanceCommitmentChainError(
                "commitment_duplicate_source_ref",
                {"index": index, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field_name: str,
    index: int,
    *,
    event_index: int | None = None,
) -> str:
    normalized = _require_nonempty(
        value,
        (
            f"commitment_observations[{index}].events[{event_index}].{field_name}"
            if event_index is not None
            else f"commitment_observations[{index}].{field_name}"
        ),
    )
    if normalized not in allowed:
        raise GovernanceCommitmentChainError(
            f"commitment_{field_name}_invalid",
            {
                "index": index,
                "event_index": event_index,
                field_name: normalized,
                "allowed": sorted(allowed),
            },
        )
    return normalized


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_RAW_KEYS or key_text.startswith("raw_"):
                raise GovernanceCommitmentChainError(
                    "commitment_raw_field_forbidden",
                    {"path": path, "field": key_text},
                )
            _reject_raw_material(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, list | tuple):
        for index, nested in enumerate(value):
            _reject_raw_material(nested, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        if lowered.startswith("data:") or "base64," in lowered:
            raise GovernanceCommitmentChainError(
                "commitment_inline_content_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise GovernanceCommitmentChainError(
                "commitment_raw_value_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise GovernanceCommitmentChainError(
                "commitment_raw_value_forbidden",
                {"path": path},
            )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _require_nonempty(value: Any, field_name: str) -> str:
    if value is None:
        raise GovernanceCommitmentChainError(
            "commitment_required_field_missing",
            {"field": field_name},
        )
    normalized = str(value).strip()
    if not normalized:
        raise GovernanceCommitmentChainError(
            "commitment_required_field_missing",
            {"field": field_name},
        )
    return normalized


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "COMMERCIAL_STATUSES",
    "COMMITMENT_EVENT_TYPES",
    "COMMITMENT_TYPES",
    "GOVERNANCE_COMMITMENT_CHAIN_ACTIVATION_POSTURE",
    "GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION",
    "GovernanceCommitmentChainError",
    "build_governance_commitment_chain_outputs",
    "canonical_governance_commitment_chain_bytes",
    "governance_commitment_chain_digest",
]
