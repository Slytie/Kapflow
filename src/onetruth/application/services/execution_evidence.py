from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

EXECUTION_SEMANTICS_ARTIFACT_ROLE = "execution_semantics_evidence"
EXECUTION_COMPILED_SPEC_ARTIFACT_KIND = "execution.compiled_spec.json"
EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND = "execution.compile_source_manifest.json"
EXECUTION_TRACE_ARTIFACT_KIND = "execution.trace.json"


@dataclass(frozen=True)
class PreparedExecutionEvidenceArtifact:
    artifact_kind: str
    artifact_role: str
    file_name: str
    media_type: str
    payload_json: dict[str, Any]
    metadata_json: dict[str, Any]
    links: list[dict[str, str]]
    idempotency_suffix: str

    def payload_bytes(self) -> bytes:
        return json.dumps(
            self.payload_json,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


def build_execution_evidence_links(
    *,
    execution_session_id: str,
    tool_execution_id: str | None = None,
    policy_decision_id: str | None = None,
    relation_kind: str = "execution_evidence",
    extra_links: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = [
        {
            "subject_kind": "execution_session",
            "subject_id": str(execution_session_id),
            "relation_kind": relation_kind,
        }
    ]
    if tool_execution_id is not None:
        links.append(
            {
                "subject_kind": "tool_execution",
                "subject_id": str(tool_execution_id),
                "relation_kind": relation_kind,
            }
        )
    if policy_decision_id is not None:
        links.append(
            {
                "subject_kind": "policy_decision",
                "subject_id": str(policy_decision_id),
                "relation_kind": relation_kind,
            }
        )

    if extra_links:
        links.extend(extra_links)

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in links:
        key = (str(item["subject_kind"]), str(item["subject_id"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "subject_kind": str(item["subject_kind"]),
                "subject_id": str(item["subject_id"]),
                "relation_kind": str(item.get("relation_kind") or relation_kind),
            }
        )
    return deduped


def prepare_pinned_execution_semantics_artifacts(
    *,
    workflow_run_id: str,
    task_run_id: str,
    execution_session: Mapping[str, Any],
    tool_execution: Mapping[str, Any] | None = None,
    policy_decision: Mapping[str, Any] | None = None,
    execution_semantics: Mapping[str, Any] | None = None,
) -> list[PreparedExecutionEvidenceArtifact]:
    execution_session_id = _required_string(
        execution_session.get("execution_session_id"),
        "execution_session.execution_session_id",
    )
    execution_spec_id = _required_string(
        execution_session.get("execution_spec_id"),
        "execution_session.execution_spec_id",
    )
    owner_mode = _required_string(
        execution_session.get("owner_mode"),
        "execution_session.owner_mode",
    )

    semantics = _mapping_or_empty(execution_semantics)
    compiled_override = _mapping_or_empty(semantics.get("compiled_execution_spec"))
    manifest_override = _mapping_or_empty(semantics.get("compile_source_manifest"))

    compiled_spec = {
        "schema_version": "1.0",
        "kind": "compiled_execution_spec",
        "workflow_run_id": str(workflow_run_id),
        "task_run_id": str(task_run_id),
        "execution_session_id": execution_session_id,
        "execution_spec_id": execution_spec_id,
        "owner_mode": owner_mode,
        "principal_actor": (
            dict(execution_session["principal_actor"])
            if isinstance(execution_session.get("principal_actor"), dict)
            else None
        ),
        "budget": (
            dict(execution_session["budget"])
            if isinstance(execution_session.get("budget"), dict)
            else None
        ),
    }
    compiled_spec.update(compiled_override)
    compiled_spec["schema_version"] = str(compiled_spec.get("schema_version") or "1.0")
    compiled_spec["kind"] = str(compiled_spec.get("kind") or "compiled_execution_spec")
    compiled_spec["execution_session_id"] = execution_session_id
    compiled_spec["execution_spec_id"] = execution_spec_id
    compiled_spec_digest = _sha256_json(compiled_spec)

    manifest = {
        "schema_version": "1.0",
        "kind": "execution_compile_source_manifest",
        "workflow_run_id": str(workflow_run_id),
        "task_run_id": str(task_run_id),
        "execution_session_id": execution_session_id,
        "execution_spec_id": execution_spec_id,
        "compiled_spec_digest": compiled_spec_digest,
        "source_refs": [
            {
                "source_kind": "execution_session_payload",
                "execution_spec_id": execution_spec_id,
            }
        ],
    }
    manifest.update(manifest_override)
    manifest["schema_version"] = str(manifest.get("schema_version") or "1.0")
    manifest["kind"] = str(manifest.get("kind") or "execution_compile_source_manifest")
    manifest["execution_session_id"] = execution_session_id
    manifest["execution_spec_id"] = execution_spec_id
    manifest["compiled_spec_digest"] = compiled_spec_digest
    manifest_digest = _sha256_json(manifest)

    tool_execution_id = _optional_string(
        tool_execution.get("tool_execution_id") if tool_execution is not None else None
    )
    policy_decision_id = _optional_string(
        policy_decision.get("policy_decision_id") if policy_decision is not None else None
    )
    links = build_execution_evidence_links(
        execution_session_id=execution_session_id,
        tool_execution_id=tool_execution_id,
        policy_decision_id=policy_decision_id,
    )
    shared_metadata = {
        "execution_session_id": execution_session_id,
        "execution_spec_id": execution_spec_id,
        "compiled_spec_digest": compiled_spec_digest,
        "compile_source_manifest_digest": manifest_digest,
    }

    return [
        PreparedExecutionEvidenceArtifact(
            artifact_kind=EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
            artifact_role=EXECUTION_SEMANTICS_ARTIFACT_ROLE,
            file_name=f"execution-compiled-spec-{execution_session_id}.json",
            media_type="application/json",
            payload_json=compiled_spec,
            metadata_json={
                **shared_metadata,
                "evidence_kind": "compiled_execution_spec",
                "document_digest": compiled_spec_digest,
            },
            links=links,
            idempotency_suffix="compiled-spec",
        ),
        PreparedExecutionEvidenceArtifact(
            artifact_kind=EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
            artifact_role=EXECUTION_SEMANTICS_ARTIFACT_ROLE,
            file_name=f"execution-compile-source-manifest-{execution_session_id}.json",
            media_type="application/json",
            payload_json=manifest,
            metadata_json={
                **shared_metadata,
                "evidence_kind": "compile_source_manifest",
                "document_digest": manifest_digest,
            },
            links=links,
            idempotency_suffix="compile-source-manifest",
        ),
    ]


def prepare_execution_trace_artifact(
    *,
    execution_session_id: str,
    trace_payload: Mapping[str, Any],
    file_name: str = "execution-trace.json",
    tool_execution_id: str | None = None,
    policy_decision_id: str | None = None,
) -> PreparedExecutionEvidenceArtifact:
    payload_json = {
        "schema_version": "1.0",
        "kind": "execution_trace",
        "execution_session_id": str(execution_session_id),
        "trace": dict(trace_payload),
    }
    digest = _sha256_json(payload_json)
    return PreparedExecutionEvidenceArtifact(
        artifact_kind=EXECUTION_TRACE_ARTIFACT_KIND,
        artifact_role="execution_trace_evidence",
        file_name=file_name,
        media_type="application/json",
        payload_json=payload_json,
        metadata_json={
            "execution_session_id": str(execution_session_id),
            "evidence_kind": "execution_trace",
            "document_digest": digest,
        },
        links=build_execution_evidence_links(
            execution_session_id=str(execution_session_id),
            tool_execution_id=tool_execution_id,
            policy_decision_id=policy_decision_id,
            relation_kind="execution_trace",
        ),
        idempotency_suffix="execution-trace",
    )


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _required_string(value: Any, field: str) -> str:
    text = _optional_string(value)
    if text is None:
        raise ValueError(f"{field} must be a non-empty string")
    return text


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _sha256_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
