from __future__ import annotations

from onetruth.api.operability import build_metrics_snapshot, build_readiness_snapshot
from onetruth.api.responses import JsonResponse


def health_endpoint() -> dict[str, object]:
    return {
        "command": "api.ops.health",
        "health": {"live": True},
    }


def readiness_endpoint(*, db_url: str) -> JsonResponse:
    readiness = build_readiness_snapshot(db_url=db_url)
    ready = bool(readiness["ready"])
    return JsonResponse(
        status_code=200 if ready else 503,
        payload={
            "status": "ok" if ready else "not_ready",
            "command": "api.ops.readiness",
            "readiness": readiness,
        },
    )


def metrics_endpoint(*, db_url: str) -> dict[str, object]:
    return {
        "command": "api.ops.metrics",
        "metrics": build_metrics_snapshot(db_url=db_url),
    }
