from __future__ import annotations

from onetruth.api.boundary_logging import (
    _serialize_log_payload,
    extract_mutation_log_fields,
)


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
