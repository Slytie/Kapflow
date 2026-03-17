from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

from onetruth.api.main import create_app
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

REQUEST_ID_PATTERN = re.compile(r"^httpreq_[0-9a-f]{32}$")
SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)


def test_boundary_logging_records_successful_receipt_backed_mutation(caplog, tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_flag")
    flag_id = created["flag"]["flag_id"]

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager"],
    )

    with caplog.at_level(logging.INFO, logger="onetruth.api.boundary"):
        raw = client.request_raw(
            "POST",
            f"/api/v1/flags/{flag_id}/transition",
            payload={
                "to_state": "triage",
                "reason": "investigating issue",
                "idempotency_key": f"api:{harness.scenario_id}:flags.transition:triage",
            },
        )

    payload = json.loads(raw.body.decode("utf-8"))
    assert raw.status_code == 200
    assert payload["status"] == "ok"

    events = _boundary_events(caplog)
    started = _single_event(events, "request_started")
    finished = _single_event(events, "request_finished")

    assert started["route_name"] == "flags.transition"
    assert started["route_params"] == {"flag_id": flag_id}
    assert "tenant_id" not in started
    assert "domain_id" not in started
    assert "actor_type" not in started

    assert finished["request_id"] == raw.headers["x-request-id"]
    assert REQUEST_ID_PATTERN.fullmatch(finished["request_id"])
    assert finished["route_name"] == "flags.transition"
    assert finished["route_params"] == {"flag_id": flag_id}
    assert finished["status_code"] == 200
    assert finished["response_kind"] == "json"
    assert isinstance(finished["latency_ms"], int)
    assert finished["latency_ms"] >= 0
    assert finished["tenant_id"] == "tenant-a"
    assert finished["domain_id"] == "domain-x"
    assert finished["actor_type"] == "human"
    assert finished["command"] == "api.flags.transition"
    assert finished["idempotent_replay"] is False
    assert finished["flag_id"] == flag_id
    assert finished["receipt_command_name"] == "flags.transition"
    assert finished["receipt_idempotency_key"] == f"api:{harness.scenario_id}:flags.transition:triage"
    assert finished["receipt_scope_key"] == f'["{flag_id}"]'


def test_boundary_logging_does_not_leak_token_or_payload_on_forbidden_mutation(caplog, tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_flag")
    flag_id = created["flag"]["flag_id"]

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:auditor-1",
        actor_type="human",
        actor_roles=["auditor"],
    )
    secret_reason = "secret-reason-should-not-log"
    secret_token = "Bearer secret-token-should-not-log"

    with caplog.at_level(logging.INFO, logger="onetruth.api.boundary"):
        raw = client.request_raw(
            "POST",
            f"/api/v1/flags/{flag_id}/transition",
            payload={
                "to_state": "triage",
                "reason": secret_reason,
                "idempotency_key": f"api:{harness.scenario_id}:flags.transition:forbidden",
            },
            headers={"authorization": secret_token},
        )

    payload = json.loads(raw.body.decode("utf-8"))
    assert raw.status_code == 403
    assert payload["error"]["code"] == "flag_transition_forbidden"

    events = _boundary_events(caplog)
    finished = _single_event(events, "request_finished")
    joined_messages = "\n".join(record.getMessage() for record in caplog.records)

    assert finished["request_id"] == raw.headers["x-request-id"]
    assert finished["route_name"] == "flags.transition"
    assert finished["route_params"] == {"flag_id": flag_id}
    assert finished["status_code"] == 403
    assert finished["response_kind"] == "json"
    assert finished["error_code"] == "flag_transition_forbidden"
    assert finished["tenant_id"] == "tenant-a"
    assert finished["domain_id"] == "domain-x"
    assert finished["actor_type"] == "human"
    assert secret_reason not in joined_messages
    assert secret_token not in joined_messages


def test_boundary_logging_records_internal_error_without_leaking_exception_message(caplog) -> None:
    def _boom(_headers: dict[str, str]) -> Any:
        raise RuntimeError("do not leak me")

    app = create_app(
        db_url="sqlite:///:memory:",
        principal_resolver=_boom,
    )

    with caplog.at_level(logging.INFO, logger="onetruth.api.boundary"):
        status, headers, body = _invoke(
            app,
            method="GET",
            path="/api/v1/workflow-runs",
        )

    payload = json.loads(body.decode("utf-8"))
    assert status == 500
    assert payload["error"]["code"] == "internal_error"

    events = _boundary_events(caplog)
    failed = _single_event(events, "request_failed")
    finished = _single_event(events, "request_finished")
    joined_messages = "\n".join(record.getMessage() for record in caplog.records)

    assert failed["request_id"] == headers["x-request-id"]
    assert failed["route_name"] == "workflow_runs.list"
    assert failed["route_params"] == {}
    assert failed["status_code"] == 500
    assert failed["response_kind"] == "json"
    assert failed["error_code"] == "internal_error"
    assert failed["exception_class"] == "RuntimeError"

    assert finished["request_id"] == headers["x-request-id"]
    assert finished["status_code"] == 500
    assert finished["error_code"] == "internal_error"
    assert "do not leak me" not in joined_messages


def _boundary_events(caplog) -> list[dict[str, Any]]:
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "onetruth.api.boundary"
    ]


def _single_event(events: list[dict[str, Any]], event_name: str) -> dict[str, Any]:
    matching = [event for event in events if event["event"] == event_name]
    assert len(matching) == 1
    return matching[0]


def _invoke(
    app,
    *,
    method: str = "GET",
    path: str = "/",
    headers: dict[str, str] | None = None,
    body: bytes = b"",
    scope_type: str = "http",
) -> tuple[int, dict[str, str], bytes]:
    raw_headers = [
        (key.encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": scope_type,
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
    }

    async def _call() -> list[dict[str, object]]:
        sent: list[dict[str, object]] = []
        sent_request = False

        async def receive() -> dict[str, object]:
            nonlocal sent_request
            if sent_request:
                return {"type": "http.disconnect"}
            sent_request = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            sent.append(message)

        await app(scope, receive, send)
        return sent

    messages = asyncio.run(_call())
    start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    start_headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in start.get("headers", [])
    }
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), start_headers, response_body
