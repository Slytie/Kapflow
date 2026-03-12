from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
from typing import Any

import yaml

from onetruth.application.services.example_document_corpus import load_example_document_corpus

from .runtime_cli import REPO_ROOT, run_cli, stderr_json, stdout_json

SCHEDULE_TEMPLATE_PACK_ROOT = REPO_ROOT / "fixtures/workflows/schedule_planning/template_pack"
EXAMPLE_DOCUMENT_CORPUS_PATH = REPO_ROOT / "fixtures/example_document_corpus/manifest.yaml"

ACTION_TO_COMMAND = {
    "tasks.create": ("tasks", "create"),
    "tasks.claim": ("tasks", "claim"),
    "tasks.complete": ("tasks", "complete"),
    "tasks.confirm-review": ("tasks", "confirm-review"),
    "flags.create": ("flags", "create"),
    "flags.transition": ("flags", "transition"),
    "stage07.activate-issue": ("stage07", "activate-issue"),
    "maintenance.sweep-leases": ("maintenance", "sweep-leases"),
    "maintenance.reconcile-stage07": ("maintenance", "reconcile-stage07"),
    "maintenance.reconcile-executions": ("maintenance", "reconcile-executions"),
    "execution-sessions.create": ("execution-sessions", "create"),
    "execution-sessions.transition": ("execution-sessions", "transition"),
    "tool-executions.request": ("tool-executions", "request"),
    "approvals.request": ("approvals", "request"),
    "approvals.respond": ("approvals", "respond"),
    "artifacts.ingest": ("artifacts", "ingest"),
    "artifacts.seed-corpus": ("artifacts", "seed-corpus"),
    "artifacts.create-version": ("artifacts", "create-version"),
    "pointers.promote": ("pointers", "promote"),
    "handoffs.materialize-weekly-seeds": ("handoffs", "materialize-weekly-seeds"),
    "handoffs.activate-live-dispatch": ("handoffs", "activate-live-dispatch"),
    "handoffs.notify-only": ("handoffs", "notify-only"),
    "schedule-control.build-weekly": ("schedule-control", "build-weekly"),
}

_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")


class RuntimeScenarioHarness:
    def __init__(self, *, scenario_path: Path, tmp_path: Path) -> None:
        with scenario_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
        if not isinstance(loaded, dict):
            raise AssertionError("scenario must parse as a mapping")
        self.scenario_path = scenario_path
        self.scenario = loaded
        self.tmp_path = tmp_path
        self.db_path = tmp_path / "runtime.db"
        self.db_url = f"sqlite:///{self.db_path}"
        self.artifact_root = tmp_path / "artifacts"
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.workflow_run: dict[str, Any] | None = None
        self.context: dict[str, Any] = {
            "scenario_id": self.scenario_id,
            "artifact_root": str(self.artifact_root),
            "db_url": self.db_url,
        }
        self.step_outputs: dict[str, dict[str, Any]] = {}
        self._corpus = None

    @classmethod
    def from_yaml(cls, scenario_path: Path, tmp_path: Path) -> "RuntimeScenarioHarness":
        return cls(scenario_path=scenario_path, tmp_path=tmp_path)

    @property
    def scenario_id(self) -> str:
        scenario_id = self.scenario.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise AssertionError("scenario_id must be a non-empty string")
        return scenario_id

    @property
    def workflow_run_id(self) -> str:
        if self.workflow_run is None:
            raise AssertionError("workflow run has not been created yet")
        return str(self.workflow_run["workflow_run_id"])

    def prepare(self) -> "RuntimeScenarioHarness":
        run_cli("--db-url", self.db_url, "init-db")
        self._create_workflow_run()
        self._seed_artifacts()
        return self

    def run_steps(self) -> dict[str, dict[str, Any]]:
        for step in self.scenario.get("steps", []):
            if not isinstance(step, dict):
                raise AssertionError("scenario steps must be mappings")
            self.run_step(step)
        return self.step_outputs

    def run_step(self, step: dict[str, Any]) -> dict[str, Any]:
        step_id = str(step["id"])
        action = str(step["action"])
        if action not in ACTION_TO_COMMAND:
            raise AssertionError(f"unsupported scenario action: {action}")
        payload = self._resolve(step.get("payload", {}))
        if not isinstance(payload, dict):
            raise AssertionError(f"step payload must resolve to object: {step_id}")

        resolved_action = action
        if action in {"artifacts.create-version", "artifacts.ingest"}:
            if payload.get("source_path") is not None or payload.get("fixture_id") is not None:
                self._materialize_artifact_payload(step_id, payload)
                if action == "artifacts.create-version":
                    resolved_action = "artifacts.ingest"

        expected_error_code = step.get("expect_error_code")
        if expected_error_code is not None:
            result = self.run_action(
                action=resolved_action,
                payload=payload,
                expect_error_code=str(expected_error_code),
            )
        else:
            result = self.run_action(action=resolved_action, payload=payload)

        alias = str(step.get("save_as") or step_id)
        self.step_outputs[step_id] = result
        self.context[step_id] = result
        self.context[alias] = result
        return result

    def run_named_step(self, step_id: str) -> dict[str, Any]:
        for step in self.scenario.get("steps", []):
            if isinstance(step, dict) and str(step.get("id")) == step_id:
                return self.run_step(step)
        raise AssertionError(f"step id not found in scenario: {step_id}")

    def output(self, key: str) -> dict[str, Any]:
        if key not in self.context or not isinstance(self.context[key], dict):
            raise AssertionError(f"missing scenario output key: {key}")
        return self.context[key]

    def run_action(
        self,
        *,
        action: str,
        payload: dict[str, Any],
        expect_error_code: str | None = None,
    ) -> dict[str, Any]:
        command = ACTION_TO_COMMAND[action]
        result = run_cli(
            "--db-url",
            self.db_url,
            *command,
            "--json",
            json.dumps(payload, separators=(",", ":")),
            expect_ok=expect_error_code is None,
        )
        if expect_error_code is None:
            parsed = stdout_json(result)
            if parsed.get("status") != "ok":
                raise AssertionError(f"expected ok status for action {action}: {parsed}")
            return parsed

        if result.returncode == 0:
            raise AssertionError(
                f"expected action {action} to fail with {expect_error_code}, but it succeeded"
            )
        error = stderr_json(result)
        if error.get("error_code") != expect_error_code:
            raise AssertionError(
                f"expected error_code {expect_error_code}, got {error.get('error_code')}"
            )
        return {"status": "error", "error": error}

    def list_events(self) -> list[dict[str, Any]]:
        result = run_cli(
            "--db-url",
            self.db_url,
            "events",
            "list",
            "--run-id",
            self.workflow_run_id,
            "--json",
        )
        payload = stdout_json(result)
        if not isinstance(payload, list):
            raise AssertionError("events list payload must be a list")
        return payload

    def list_tasks(self) -> dict[str, Any]:
        result = run_cli(
            "--db-url",
            self.db_url,
            "tasks",
            "list",
            "--workflow-run-id",
            self.workflow_run_id,
            "--json",
        )
        return stdout_json(result)

    def show_task(self, human_task_id: str) -> dict[str, Any]:
        result = run_cli(
            "--db-url",
            self.db_url,
            "tasks",
            "show",
            "--human-task-id",
            human_task_id,
            "--json",
        )
        return stdout_json(result)

    def list_approvals(self) -> dict[str, Any]:
        result = run_cli(
            "--db-url",
            self.db_url,
            "approvals",
            "list",
            "--workflow-run-id",
            self.workflow_run_id,
            "--json",
        )
        return stdout_json(result)

    def list_flags(self) -> dict[str, Any]:
        result = run_cli(
            "--db-url",
            self.db_url,
            "flags",
            "list",
            "--workflow-run-id",
            self.workflow_run_id,
            "--json",
        )
        return stdout_json(result)

    def list_pointers(self) -> dict[str, Any]:
        result = run_cli(
            "--db-url",
            self.db_url,
            "pointers",
            "list",
            "--workflow-run-id",
            self.workflow_run_id,
            "--json",
        )
        return stdout_json(result)

    def list_artifacts(self) -> dict[str, Any]:
        result = run_cli(
            "--db-url",
            self.db_url,
            "artifacts",
            "list",
            "--workflow-run-id",
            self.workflow_run_id,
            "--json",
        )
        return stdout_json(result)

    def list_workflow_runs(self) -> dict[str, Any]:
        result = run_cli(
            "--db-url",
            self.db_url,
            "runs",
            "list",
            "--workflow-id",
            str(self.scenario["workflow_id"]),
            "--tenant-id",
            str(self.scenario["scope"]["tenant_id"]),
            "--domain-id",
            str(self.scenario["scope"]["domain_id"]),
            "--json",
        )
        return stdout_json(result)

    def query_rows(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def _create_workflow_run(self) -> None:
        scope = self.scenario.get("scope", {})
        activation_key = str(
            self.scenario.get("activation_key") or f"{self.scenario_id}:workflow-run"
        )
        payload = {
            "workflow_id": str(self.scenario["workflow_id"]),
            "workflow_version": str(self.scenario.get("workflow_version", "v1")),
            "tenant_id": str(scope["tenant_id"]),
            "domain_id": str(scope["domain_id"]),
            "partition_key": str(self.scenario["partition_key"]),
            "logical_date": self.scenario.get("logical_date"),
            "activation_key": activation_key,
            "idempotency_key": f"scenario:{self.scenario_id}:runs.create",
        }
        result = run_cli(
            "--db-url",
            self.db_url,
            "runs",
            "create",
            "--json",
            json.dumps(payload, separators=(",", ":")),
        )
        parsed = stdout_json(result)
        self.workflow_run = parsed["workflow_run"]
        self.context["workflow_run"] = self.workflow_run
        self.context["workflow_run_id"] = str(self.workflow_run["workflow_run_id"])

    def _seed_artifacts(self) -> None:
        seeded_context: dict[str, Any] = {}
        for index, seed_artifact in enumerate(self.scenario.get("seed_artifacts", [])):
            if not isinstance(seed_artifact, dict):
                raise AssertionError("seed_artifacts entries must be mappings")
            source_path = self._resolve_fixture_source_path(seed_artifact)
            artifact_kind = str(seed_artifact["artifact_kind"])
            payload = {
                "workflow_run_id": self.workflow_run_id,
                "artifact_kind": artifact_kind,
                "artifact_role": seed_artifact.get("artifact_role"),
                "media_type": str(seed_artifact["media_type"]),
                "source_path": str(source_path),
                "file_name": source_path.name,
                "storage_root": str(self.artifact_root),
                "metadata_json": {
                    "scenario_id": self.scenario_id,
                    "seed_source_path": str(source_path),
                    "seed_index": index,
                    **(seed_artifact.get("metadata_json") or {}),
                },
                "idempotency_key": (
                    f"scenario:{self.scenario_id}:seed:{index}:artifact:{artifact_kind}"
                ),
            }
            links = seed_artifact.get("links")
            if links is not None:
                payload["links"] = links
            result = self.run_action(action="artifacts.ingest", payload=payload)
            seeded_context[artifact_kind] = {
                "artifact_version": result["artifact_version"],
                "storage_uri": result["ingress"]["storage_uri"],
                "source_path": str(source_path),
                "content_digest": result["ingress"]["content_digest"],
                "byte_size": result["ingress"]["byte_size"],
            }
        self.context["seed_artifacts"] = seeded_context

    def _materialize_artifact_payload(self, step_id: str, payload: dict[str, Any]) -> None:
        source_path_value = payload.get("source_path")
        fixture_id = payload.get("fixture_id")
        if fixture_id is not None:
            source_path = self._resolve_fixture_source_path({"fixture_id": fixture_id})
            payload["source_path"] = str(source_path)
            payload.setdefault("file_name", source_path.name)
            payload.setdefault("media_type", _media_type_for_name(source_path.name))
        elif source_path_value is not None:
            source_path = self._resolve_fixture_source_path({"source_path": source_path_value})
            payload["source_path"] = str(source_path)
            payload.setdefault("file_name", source_path.name)
            payload.setdefault("media_type", _media_type_for_name(source_path.name))
        if payload.get("source_path") is not None:
            payload.setdefault("storage_root", str(self.artifact_root))
        metadata_json = payload.get("metadata_json")
        if metadata_json is None:
            metadata_json = {}
        if not isinstance(metadata_json, dict):
            raise AssertionError("metadata_json must resolve to an object")
        metadata_json.setdefault("scenario_id", self.scenario_id)
        metadata_json.setdefault("step_id", step_id)
        payload["metadata_json"] = metadata_json
        payload.pop("fixture_id", None)

    def _resolve_fixture_source_path(self, raw: dict[str, Any]) -> Path:
        fixture_id = raw.get("fixture_id")
        if fixture_id is not None:
            corpus = self._load_corpus()
            document = corpus.document_by_id(str(fixture_id))
            return document.source_path
        source_path = raw.get("source_path")
        if source_path is None:
            raise AssertionError("seed artifact requires source_path or fixture_id")
        source = Path(str(source_path))
        if not source.is_absolute():
            source = (SCHEDULE_TEMPLATE_PACK_ROOT / source).resolve()
        if not source.exists():
            raise AssertionError(f"scenario artifact source does not exist: {source}")
        return source

    def _load_corpus(self):
        if self._corpus is None:
            self._corpus = load_example_document_corpus(EXAMPLE_DOCUMENT_CORPUS_PATH)
        return self._corpus

    def _resolve(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve(item) for item in value]
        if isinstance(value, str):
            return self._resolve_placeholder(value)
        return value

    def _resolve_placeholder(self, raw: str) -> Any:
        full_match = re.fullmatch(_PLACEHOLDER_PATTERN, raw)
        if full_match is not None:
            return self._lookup_context(full_match.group(1))

        def _replace(match: re.Match[str]) -> str:
            return str(self._lookup_context(match.group(1)))

        return _PLACEHOLDER_PATTERN.sub(_replace, raw)

    def _lookup_context(self, key: str) -> Any:
        current: Any = self.context
        for part in key.split("."):
            if isinstance(current, list):
                index = int(part)
                current = current[index]
                continue
            if not isinstance(current, dict):
                raise AssertionError(f"invalid placeholder path segment: {part}")
            if part not in current:
                raise AssertionError(f"missing placeholder key in scenario context: {key}")
            current = current[part]
        return current


def _media_type_for_name(file_name: str) -> str:
    lower = file_name.lower()
    if lower.endswith(".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if lower.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"
