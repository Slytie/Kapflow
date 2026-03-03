from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import CommandError
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, Any]


def api_error_from_command(exc: CommandError) -> ApiError:
    code = exc.code
    status_code = 400

    if code.endswith("_not_found") or code.startswith("cross_"):
        status_code = 404
    elif code.startswith("invalid_"):
        status_code = 400
    elif code.startswith("duplicate_"):
        status_code = 409
    elif code.endswith("_conflict") or code.endswith("_mismatch"):
        status_code = 409
    elif code in {
        "task_not_claimable",
        "task_not_completable",
        "task_run_not_claimable",
        "task_run_not_completable",
        "approval_not_respondable",
        "approval_not_approved",
        "approval_required_for_promotion",
        "pointer_already_current",
        "pointer_conflict",
    }:
        status_code = 409

    return ApiError(
        status_code=status_code,
        code=code,
        message=exc.message,
        details=exc.details,
    )


def api_error_from_duplicate_idempotency(exc: DuplicateIdempotencyKeyError) -> ApiError:
    return ApiError(
        status_code=409,
        code="duplicate_idempotency_key",
        message=str(exc),
        details={
            "idempotency_key": exc.idempotency_key,
            "existing_event_id": exc.existing_event_id,
        },
    )


def error_payload(error: ApiError) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        },
    }
