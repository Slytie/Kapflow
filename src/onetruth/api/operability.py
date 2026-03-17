from __future__ import annotations

import json
from typing import Any

from onetruth.api.boundary_logging import snapshot_request_metrics
from onetruth.infrastructure.artifacts.storage import probe_storage_root
from onetruth.infrastructure.db.session import (
    open_read_only_sqlite_connection,
    probe_sqlite_database,
)


def build_readiness_snapshot(*, db_url: str) -> dict[str, Any]:
    db_probe = probe_sqlite_database(db_url)
    storage_probe = probe_storage_root(db_url)
    degraded_snapshot = _load_degraded_snapshot(db_url) if db_probe.ready else _unavailable_degraded_snapshot()

    return {
        "ready": db_probe.ready and storage_probe.ready,
        "db": {
            "kind": "sqlite",
            "ready": db_probe.ready,
            "exists": db_probe.exists,
            "is_file": db_probe.is_file,
            "error_code": db_probe.error_code,
        },
        "artifact_storage": {
            "ready": storage_probe.ready,
            "exists": storage_probe.exists,
            "is_directory": storage_probe.is_directory,
            "writable": storage_probe.writable,
            "error_code": storage_probe.error_code,
        },
        "warnings": {
            "degradation_visibility_available": degraded_snapshot["available"],
            "active_degraded_components": degraded_snapshot[
                "active_degraded_components"
            ],
            "projection_coherence_failed_total": degraded_snapshot[
                "projection_coherence_failed_total"
            ],
        },
    }


def build_metrics_snapshot(*, db_url: str) -> dict[str, Any]:
    readiness = build_readiness_snapshot(db_url=db_url)
    warnings = readiness["warnings"]
    return {
        "request_counters": snapshot_request_metrics(),
        "readiness": readiness,
        "active_degraded_components": warnings["active_degraded_components"],
        "projection_coherence_failed_total": warnings[
            "projection_coherence_failed_total"
        ],
    }


def _load_degraded_snapshot(db_url: str) -> dict[str, Any]:
    components: dict[str, str] = {}
    projection_coherence_failed_total = 0

    try:
        connection = open_read_only_sqlite_connection(db_url)
    except OSError:
        return _unavailable_degraded_snapshot()

    try:
        rows = connection.execute(
            """
            SELECT event_type, payload
            FROM timeline_events
            WHERE event_type IN (
                'audit.degraded_mode.changed',
                'projection.coherence_failed'
            )
            ORDER BY sequence_no ASC
            """
        ).fetchall()
    except Exception:
        connection.close()
        return _unavailable_degraded_snapshot()

    connection.close()

    for row in rows:
        event_type = str(row["event_type"])
        payload = _parse_payload(row["payload"])
        if event_type == "audit.degraded_mode.changed":
            component = str(payload.get("component") or "").strip()
            to_state = str(payload.get("to_state") or "").strip()
            if component and to_state:
                components[component] = to_state
            continue
        if event_type == "projection.coherence_failed":
            projection_coherence_failed_total += 1

    active_degraded_components = [
        {"component": component, "state": state}
        for component, state in sorted(components.items())
        if state != "normal"
    ]
    return {
        "available": True,
        "active_degraded_components": active_degraded_components,
        "projection_coherence_failed_total": projection_coherence_failed_total,
    }


def _parse_payload(raw_payload: object) -> dict[str, Any]:
    if not isinstance(raw_payload, str):
        return {}
    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _unavailable_degraded_snapshot() -> dict[str, Any]:
    return {
        "available": False,
        "active_degraded_components": [],
        "projection_coherence_failed_total": None,
    }
