from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, replace
from typing import Any, Awaitable, Callable, cast
from urllib.parse import parse_qs, urlparse

from onetruth.api.dependencies import (
    ACTOR_ID_HEADER,
    ACTOR_ROLES_HEADER,
    ACTOR_TYPE_HEADER,
    BOUNDARY_PROFILES,
    DEFAULT_API_BOUNDARY_PROFILE,
    DOMAIN_HEADER,
    BoundaryProfile,
    PrincipalResolver,
    TENANT_HEADER,
    unavailable_principal_resolver,
    parse_page,
    open_connection,
    resolve_db_url,
    trusted_header_principal_resolver,
)
from onetruth.api.errors import ApiError, error_payload
from onetruth.api.request_correlation import (
    REQUEST_ID_HEADER,
    request_id_header,
    resolve_request_id,
)
from onetruth.api.route_registry import RequestBodyPolicy, RouteExecutionContext, match_route

ASGIApp = Callable[[dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[None]]


_CORS_ALLOW_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
_CORS_DEFAULT_ALLOW_HEADERS = ",".join(
    [
        "content-type",
        TENANT_HEADER,
        DOMAIN_HEADER,
        ACTOR_ID_HEADER,
        ACTOR_TYPE_HEADER,
        ACTOR_ROLES_HEADER,
    ]
)
_API_BOUNDARY_PROFILE_ENV = "ONETRUTH_API_BOUNDARY_PROFILE"


@dataclass(frozen=True)
class ApiBoundaryConfig:
    profile: BoundaryProfile
    principal_resolver: PrincipalResolver


def create_app(
    *,
    db_url: str | None = None,
    boundary_profile: BoundaryProfile | str | None = None,
    principal_resolver: PrincipalResolver | None = None,
) -> ASGIApp:
    resolved_db_url = resolve_db_url(db_url)
    boundary = _resolve_boundary_config(
        boundary_profile=boundary_profile,
        principal_resolver=principal_resolver,
    )

    async def app(scope: dict[str, Any], receive, send) -> None:
        if scope.get("type") != "http":
            request_id = resolve_request_id(None)
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
                request_id=request_id,
                boundary_profile=boundary.profile,
            )
            return

        method = str(scope.get("method", "")).upper()
        path = str(scope.get("path", ""))
        raw_headers = scope.get("headers", [])
        headers = _decode_headers(raw_headers)
        request_id = resolve_request_id(headers)
        query = _decode_query(scope.get("query_string", b""))

        if method == "OPTIONS" and path.startswith("/api/v1/"):
            await _send_no_content(
                send,
                status_code=204,
                request_id=request_id,
                boundary_profile=boundary.profile,
                request_headers=headers,
            )
            return

        matched = match_route(method, path)
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
                request_id=request_id,
                boundary_profile=boundary.profile,
                request_headers=headers,
            )
            return

        try:
            context = replace(boundary.principal_resolver(headers), request_id=request_id)
            body_payload = await _read_json_body(
                matched.route.body_policy,
                headers,
                receive,
            )
            page = parse_page(query) if matched.route.needs_page else None

            connection = open_connection(resolved_db_url)
            try:
                response_payload = matched.dispatch(
                    RouteExecutionContext(
                        connection=connection,
                        context=context,
                        query=query,
                        page=page,
                        payload=body_payload,
                        db_url=resolved_db_url,
                    )
                )
            finally:
                connection.close()

            await _send_json(
                send,
                status_code=200,
                payload={"status": "ok", **response_payload},
                request_id=request_id,
                boundary_profile=boundary.profile,
                request_headers=headers,
            )
        except ApiError as exc:
            await _send_json(
                send,
                status_code=exc.status_code,
                payload=error_payload(exc),
                request_id=request_id,
                boundary_profile=boundary.profile,
                request_headers=headers,
            )
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
                request_id=request_id,
                boundary_profile=boundary.profile,
                request_headers=headers,
            )

    return app


def _resolve_boundary_config(
    *,
    boundary_profile: BoundaryProfile | str | None,
    principal_resolver: PrincipalResolver | None,
) -> ApiBoundaryConfig:
    resolved_profile = _resolve_boundary_profile(boundary_profile)
    if principal_resolver is not None:
        return ApiBoundaryConfig(
            profile=resolved_profile,
            principal_resolver=principal_resolver,
        )
    if resolved_profile in {"local_dev", "ci_test"}:
        return ApiBoundaryConfig(
            profile=resolved_profile,
            principal_resolver=trusted_header_principal_resolver,
        )
    return ApiBoundaryConfig(
        profile=resolved_profile,
        principal_resolver=unavailable_principal_resolver,
    )


def _resolve_boundary_profile(
    configured_profile: BoundaryProfile | str | None,
) -> BoundaryProfile:
    raw_profile = configured_profile
    if raw_profile is None:
        raw_profile = os.environ.get(_API_BOUNDARY_PROFILE_ENV)
    if raw_profile is None:
        return DEFAULT_API_BOUNDARY_PROFILE
    normalized = raw_profile.strip().lower()
    if normalized not in BOUNDARY_PROFILES:
        raise ValueError(
            "invalid API boundary profile "
            f"{raw_profile!r}; expected one of {', '.join(BOUNDARY_PROFILES)}"
        )
    return cast(BoundaryProfile, normalized)


def _decode_headers(raw_headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in raw_headers:
        headers[key.decode("latin-1").lower()] = value.decode("latin-1")
    return headers


def _decode_query(raw_query: bytes) -> dict[str, str]:
    parsed = parse_qs(raw_query.decode("latin-1"), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items() if values}


def _normalized_content_type(raw_content_type: str | None) -> str | None:
    if raw_content_type is None:
        return None
    media_type = raw_content_type.split(";", 1)[0].strip().lower()
    return media_type or None


def _validate_request_content_type(
    body_policy: RequestBodyPolicy,
    request_headers: dict[str, str],
) -> None:
    assert body_policy.required_content_type is not None
    raw_content_type = request_headers.get("content-type")
    normalized = _normalized_content_type(raw_content_type)
    if normalized == body_policy.required_content_type:
        return
    raise ApiError(
        status_code=415,
        code="unsupported_media_type",
        message="expected Content-Type application/json",
        details={
            "expected_content_type": body_policy.required_content_type,
            "received_content_type": raw_content_type,
        },
    )


async def _read_json_body(
    body_policy: RequestBodyPolicy,
    request_headers: dict[str, str],
    receive,
) -> dict[str, Any] | None:
    if body_policy.kind == "none":
        return None

    chunks: list[bytes] = []
    body_started = False
    total_bytes = 0
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
            if not body_started:
                body_started = True
                _validate_request_content_type(body_policy, request_headers)
            total_bytes += len(body_chunk)
            if (
                body_policy.max_bytes is not None
                and total_bytes > body_policy.max_bytes
            ):
                raise ApiError(
                    status_code=413,
                    code="payload_too_large",
                    message="request body exceeds maximum size",
                    details={"max_bytes": body_policy.max_bytes},
                )
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


def _cors_headers(
    *,
    boundary_profile: BoundaryProfile,
    request_headers: dict[str, str] | None,
) -> list[tuple[bytes, bytes]]:
    if boundary_profile != "local_dev" or request_headers is None:
        return []
    requested_origin = request_headers.get("origin")
    if not requested_origin or not _is_loopback_origin(requested_origin):
        return []
    allow_headers = (
        request_headers.get("access-control-request-headers")
        or _CORS_DEFAULT_ALLOW_HEADERS
    )
    return [
        (
            b"access-control-allow-origin",
            requested_origin.encode("latin-1"),
        ),
        (b"access-control-allow-methods", _CORS_ALLOW_METHODS.encode("latin-1")),
        (b"access-control-allow-headers", allow_headers.encode("latin-1")),
        (
            b"access-control-expose-headers",
            REQUEST_ID_HEADER.encode("latin-1"),
        ),
        (b"access-control-max-age", b"600"),
        (b"vary", b"origin, access-control-request-headers"),
    ]


def _is_loopback_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"}:
        return False
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


async def _send_json(
    send,
    *,
    status_code: int,
    payload: dict[str, Any],
    request_id: str,
    boundary_profile: BoundaryProfile,
    request_headers: dict[str, str] | None = None,
) -> None:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    response_headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        request_id_header(request_id),
    ]
    response_headers.extend(
        _cors_headers(
            boundary_profile=boundary_profile,
            request_headers=request_headers,
        )
    )
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": response_headers,
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})


async def _send_no_content(
    send,
    *,
    status_code: int,
    request_id: str,
    boundary_profile: BoundaryProfile,
    request_headers: dict[str, str] | None = None,
) -> None:
    response_headers = [
        (b"content-length", b"0"),
        request_id_header(request_id),
    ]
    response_headers.extend(
        _cors_headers(
            boundary_profile=boundary_profile,
            request_headers=request_headers,
        )
    )
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": response_headers,
        }
    )
    await send({"type": "http.response.body", "body": b"", "more_body": False})


def _build_server_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onetruth-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db-url", default=None)
    parser.add_argument(
        "--api-boundary-profile",
        choices=BOUNDARY_PROFILES,
        default=None,
        help=(
            "API trust boundary profile. Defaults to env "
            f"{_API_BOUNDARY_PROFILE_ENV} or {DEFAULT_API_BOUNDARY_PROFILE}."
        ),
    )
    parser.description = (
        "Run the thin onetruth runtime HTTP adapter. "
        "Trusted request headers "
        f"({TENANT_HEADER}, {DOMAIN_HEADER}, {ACTOR_ID_HEADER}, {ACTOR_TYPE_HEADER}, {ACTOR_ROLES_HEADER}) "
        "are allowed only in local_dev and ci_test. "
        f"Default profile: {DEFAULT_API_BOUNDARY_PROFILE}."
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

    uvicorn.run(
        create_app(
            db_url=args.db_url,
            boundary_profile=args.api_boundary_profile,
        ),
        host=args.host,
        port=args.port,
    )
    return 0


app = create_app()


if __name__ == "__main__":
    raise SystemExit(main())
