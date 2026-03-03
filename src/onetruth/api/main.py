from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs

from onetruth.api.dependencies import (
    ACTOR_ID_HEADER,
    ACTOR_ROLES_HEADER,
    ACTOR_TYPE_HEADER,
    DOMAIN_HEADER,
    TENANT_HEADER,
    parse_page,
    request_context_from_headers,
    resolve_db_url,
    open_connection,
)
from onetruth.api.errors import ApiError, error_payload
from onetruth.api.routes.approvals import list_approvals_endpoint, respond_approval_endpoint
from onetruth.api.routes.board import schedule_planning_board_endpoint
from onetruth.api.routes.human_tasks import (
    claim_human_task_endpoint,
    complete_human_task_endpoint,
    list_human_tasks_endpoint,
)
from onetruth.api.routes.pointers import list_pointers_endpoint
from onetruth.api.routes.workflow_runs import (
    get_workflow_run_detail_endpoint,
    list_workflow_runs_endpoint,
)

ASGIApp = Callable[[dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[None]]


@dataclass(frozen=True)
class MatchedRoute:
    method: str
    name: str
    params: dict[str, str]


def create_app(*, db_url: str | None = None) -> ASGIApp:
    resolved_db_url = resolve_db_url(db_url)

    async def app(scope: dict[str, Any], receive, send) -> None:
        if scope.get("type") != "http":
            await _send_json(
                send,
                status_code=500,
                payload={
                    "status": "error",
                    "error": {
                        "code": "unsupported_scope",
                        "message": "only HTTP scopes are supported",
                        "details": {},
                    },
                },
            )
            return

        method = str(scope.get("method", "")).upper()
        path = str(scope.get("path", ""))
        raw_headers = scope.get("headers", [])
        headers = _decode_headers(raw_headers)
        query = _decode_query(scope.get("query_string", b""))

        matched = _match_route(method, path)
        if matched is None:
            await _send_json(
                send,
                status_code=404,
                payload={
                    "status": "error",
                    "error": {
                        "code": "not_found",
                        "message": "route not found",
                        "details": {"method": method, "path": path},
                    },
                },
            )
            return

        try:
            context = request_context_from_headers(headers)
            body_payload = await _read_json_body(method, receive)
            page = parse_page(query) if method == "GET" else None

            connection = open_connection(resolved_db_url)
            try:
                response_payload = _dispatch_route(
                    matched=matched,
                    connection=connection,
                    context=context,
                    query=query,
                    page=page,
                    payload=body_payload,
                )
            finally:
                connection.close()

            await _send_json(send, status_code=200, payload={"status": "ok", **response_payload})
        except ApiError as exc:
            await _send_json(send, status_code=exc.status_code, payload=error_payload(exc))
        except Exception as exc:
            await _send_json(
                send,
                status_code=500,
                payload={
                    "status": "error",
                    "error": {
                        "code": "internal_error",
                        "message": "unhandled server error",
                        "details": {"exception": exc.__class__.__name__},
                    },
                },
            )

    return app


def _match_route(method: str, path: str) -> MatchedRoute | None:
    if method == "GET" and path == "/api/v1/human-tasks":
        return MatchedRoute(method=method, name="human_tasks.list", params={})
    if method == "POST" and path.endswith("/claim"):
        prefix = "/api/v1/human-tasks/"
        suffix = "/claim"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            human_task_id = path[len(prefix) : -len(suffix)]
            if human_task_id:
                return MatchedRoute(
                    method=method,
                    name="human_tasks.claim",
                    params={"human_task_id": human_task_id},
                )
    if method == "POST" and path.endswith("/complete"):
        prefix = "/api/v1/human-tasks/"
        suffix = "/complete"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            human_task_id = path[len(prefix) : -len(suffix)]
            if human_task_id:
                return MatchedRoute(
                    method=method,
                    name="human_tasks.complete",
                    params={"human_task_id": human_task_id},
                )
    if method == "GET" and path == "/api/v1/approvals":
        return MatchedRoute(method=method, name="approvals.list", params={})
    if method == "POST" and path.endswith("/respond"):
        prefix = "/api/v1/approvals/"
        suffix = "/respond"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            approval_id = path[len(prefix) : -len(suffix)]
            if approval_id:
                return MatchedRoute(
                    method=method,
                    name="approvals.respond",
                    params={"approval_id": approval_id},
                )
    if method == "GET" and path == "/api/v1/workflow-runs":
        return MatchedRoute(method=method, name="workflow_runs.list", params={})
    if method == "GET" and path.startswith("/api/v1/workflow-runs/"):
        workflow_run_id = path[len("/api/v1/workflow-runs/") :]
        if workflow_run_id:
            return MatchedRoute(
                method=method,
                name="workflow_runs.detail",
                params={"workflow_run_id": workflow_run_id},
            )
    if method == "GET" and path == "/api/v1/pointers":
        return MatchedRoute(method=method, name="pointers.list", params={})
    if method == "GET" and path == "/api/v1/board/schedule-planning":
        return MatchedRoute(method=method, name="board.schedule_planning", params={})
    return None


def _dispatch_route(
    *,
    matched: MatchedRoute,
    connection,
    context,
    query: dict[str, str],
    page,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if matched.name == "human_tasks.list":
        assert page is not None
        return list_human_tasks_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )
    if matched.name == "human_tasks.claim":
        return claim_human_task_endpoint(
            connection,
            context=context,
            human_task_id=matched.params["human_task_id"],
            payload=_require_payload(payload),
        )
    if matched.name == "human_tasks.complete":
        return complete_human_task_endpoint(
            connection,
            context=context,
            human_task_id=matched.params["human_task_id"],
            payload=_require_payload(payload),
        )
    if matched.name == "approvals.list":
        assert page is not None
        return list_approvals_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )
    if matched.name == "approvals.respond":
        return respond_approval_endpoint(
            connection,
            context=context,
            approval_id=matched.params["approval_id"],
            payload=_require_payload(payload),
        )
    if matched.name == "workflow_runs.list":
        assert page is not None
        return list_workflow_runs_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )
    if matched.name == "workflow_runs.detail":
        return get_workflow_run_detail_endpoint(
            connection,
            context=context,
            workflow_run_id=matched.params["workflow_run_id"],
        )
    if matched.name == "pointers.list":
        assert page is not None
        return list_pointers_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )
    if matched.name == "board.schedule_planning":
        assert page is not None
        return schedule_planning_board_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )

    raise ApiError(
        status_code=404,
        code="not_found",
        message="route handler not found",
        details={"route": matched.name},
    )


def _require_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        raise ApiError(
            status_code=400,
            code="invalid_payload",
            message="request body is required",
            details={},
        )
    return payload


def _decode_headers(raw_headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in raw_headers:
        headers[key.decode("latin-1").lower()] = value.decode("latin-1")
    return headers


def _decode_query(raw_query: bytes) -> dict[str, str]:
    parsed = parse_qs(raw_query.decode("latin-1"), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items() if values}


async def _read_json_body(method: str, receive) -> dict[str, Any] | None:
    if method not in {"POST", "PUT", "PATCH"}:
        return None

    chunks: list[bytes] = []
    more = True
    while more:
        message = await receive()
        message_type = message.get("type")
        if message_type == "http.disconnect":
            break
        if message_type != "http.request":
            continue
        body_chunk = message.get("body", b"")
        if body_chunk:
            chunks.append(body_chunk)
        more = bool(message.get("more_body", False))

    raw_body = b"".join(chunks)
    if not raw_body:
        return None

    try:
        parsed = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiError(
            status_code=400,
            code="invalid_json",
            message=f"invalid JSON body: {exc.msg}",
            details={"pos": exc.pos},
        ) from exc
    if not isinstance(parsed, dict):
        raise ApiError(
            status_code=400,
            code="invalid_payload",
            message="expected JSON object body",
            details={},
        )
    return parsed


async def _send_json(send, *, status_code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


def _build_server_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onetruth-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db-url", default=None)
    parser.description = (
        "Run the thin onetruth runtime HTTP adapter. "
        f"Required request headers: {TENANT_HEADER}, {DOMAIN_HEADER}, {ACTOR_ID_HEADER}, {ACTOR_TYPE_HEADER}, {ACTOR_ROLES_HEADER}."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_server_parser().parse_args(argv)
    try:
        import uvicorn
    except ImportError:
        raise SystemExit(
            "uvicorn is required to run the API server. Install with `python3 -m pip install -e .[api]`."
        )

    uvicorn.run(create_app(db_url=args.db_url), host=args.host, port=args.port)
    return 0


app = create_app()


if __name__ == "__main__":
    raise SystemExit(main())
