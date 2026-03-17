from __future__ import annotations

from onetruth.api.boundary_logging import (
    _serialize_log_payload,
    extract_mutation_log_fields,
    log_request_finished,
    reset_request_metrics,
    snapshot_request_metrics,
)
from onetruth.api.dependencies import RequestContext


def setup_function() -> None:
    reset_request_metrics()


def test_extract_mutation_log_fields_keeps_allowlisted_values_only() -> None:
    payload = {
        "status": "ok",
        "command": "api.flags.transition",
        "idempotent_replay": False,
        "flag_id": "flag-001",
        "receipt": {
            "command_name": "flags.transition",
            "scope_key": '["flag-001"]',
            "idempotency_key": "idem-flag-001",
            "actor_id": "human:should-not-log",
        },
        "artifact_version": {
            "artifact_version_id": "av-001",
            "workflow_run_id": "wr-001",
            "metadata_json": {
                "content_base64": "secret-content-should-not-log",
            },
        },
        "result": {
            "workflow_run_id": "wr-should-not-win",
            "human_task": {
                "human_task_id": "ht-too-deep",
            },
            "nested": {
                "approval_id": "apr-too-deep",
            },
        },
        "authorization": "Bearer should-not-log",
        "content_base64": "also-should-not-log",
        "storage_root": "/tmp/should-not-log",
        "response_reason": "should-not-log",
    }

    assert extract_mutation_log_fields(payload) == {
        "command": "api.flags.transition",
        "idempotent_replay": False,
        "flag_id": "flag-001",
        "receipt_command_name": "flags.transition",
        "receipt_scope_key": '["flag-001"]',
        "receipt_idempotency_key": "idem-flag-001",
        "artifact_version_id": "av-001",
        "workflow_run_id": "wr-001",
    }


def test_serialize_log_payload_does_not_contain_ignored_values() -> None:
    serialized = _serialize_log_payload(
        {
            "event": "request_finished",
            "request_id": "httpreq_test_001",
            **extract_mutation_log_fields(
                {
                    "command": "api.flags.transition",
                    "flag_id": "flag-001",
                    "receipt": {
                        "command_name": "flags.transition",
                        "scope_key": '["flag-001"]',
                        "idempotency_key": "idem-flag-001",
                    },
                    "artifact_version": {
                        "artifact_version_id": "av-001",
                        "workflow_run_id": "wr-001",
                        "metadata_json": {"content_base64": "secret-content-should-not-log"},
                    },
                    "authorization": "Bearer should-not-log",
                    "storage_root": "/tmp/should-not-log",
                    "result": {"human_task": {"human_task_id": "ht-too-deep"}},
                }
            ),
        }
    )

    assert "secret-content-should-not-log" not in serialized
    assert "Bearer should-not-log" not in serialized
    assert "/tmp/should-not-log" not in serialized
    assert "ht-too-deep" not in serialized


def test_snapshot_request_metrics_aggregates_only_safe_route_buckets() -> None:
    context = RequestContext(
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=("dispatch_supervisor",),
    )

    log_request_finished(
        request_id="httpreq_001",
        boundary_profile="ci_test",
        method="get",
        path="/api/v1/flags/flag-001",
        route_name="flags.detail",
        route_params={"flag_id": "flag-001"},
        request_context=context,
        status_code=200,
        latency_ms=12,
        response_kind="json",
        response_payload={"command": "api.flags.detail", "flag_id": "flag-001"},
    )
    log_request_finished(
        request_id="httpreq_002",
        boundary_profile="ci_test",
        method="GET",
        path="/api/v1/flags/flag-001",
        route_name="flags.detail",
        route_params={"flag_id": "flag-001"},
        request_context=context,
        status_code=200,
        latency_ms=18,
        response_kind="json",
        response_payload={"command": "api.flags.detail", "flag_id": "flag-001"},
    )

    assert snapshot_request_metrics() == [
        {
            "route_name": "flags.detail",
            "method": "GET",
            "status_family": "2xx",
            "count": 2,
            "latency_ms_total": 30,
        }
    ]


def test_snapshot_request_metrics_normalizes_missing_route_name_to_unmatched() -> None:
    log_request_finished(
        request_id="httpreq_003",
        boundary_profile="shared_env",
        method="GET",
        path="/api/v1/not-a-route/tenant-a",
        route_name=None,
        route_params=None,
        request_context=None,
        status_code=404,
        latency_ms=7,
        response_kind="json",
        response_payload={
            "status": "error",
            "error": {"code": "not_found", "message": "missing", "details": {}},
        },
    )

    assert snapshot_request_metrics() == [
        {
            "route_name": "unmatched",
            "method": "GET",
            "status_family": "4xx",
            "count": 1,
            "latency_ms_total": 7,
        }
    ]
