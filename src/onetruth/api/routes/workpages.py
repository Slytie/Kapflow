from __future__ import annotations

from onetruth.api.dependencies import RequestContext
from onetruth.api.errors import ApiError
from onetruth.application.services.logistics_workpages import (
    DemoWorkpageNotFoundError,
    build_demo_workpage_contract,
)


def demo_workpage_endpoint(
    *,
    context: RequestContext,
    workpage_id: str,
) -> dict[str, object]:
    del context
    try:
        contract = build_demo_workpage_contract(workpage_id)
    except DemoWorkpageNotFoundError as exc:
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={"workpage_id": exc.workpage_id},
        ) from exc
    return {
        "command": "api.workpages.demo",
        **contract,
    }
