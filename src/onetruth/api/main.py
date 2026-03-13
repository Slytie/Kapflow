from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
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
from onetruth.api.routes.approvals import (
    get_approval_endpoint,
    list_approvals_endpoint,
    respond_approval_endpoint,
)
from onetruth.api.routes.artifacts import (
    download_artifact_endpoint,
    get_artifact_endpoint,
    ingest_artifact_endpoint,
    list_approval_artifacts_endpoint,
    list_artifacts_endpoint,
    list_flag_artifacts_endpoint,
    list_human_task_artifacts_endpoint,
    list_workflow_run_artifacts_endpoint,
    upload_approval_artifact_endpoint,
    upload_flag_artifact_endpoint,
    upload_human_task_artifact_endpoint,
    upload_workflow_run_artifact_endpoint,
)
from onetruth.api.routes.board import schedule_planning_board_endpoint
from onetruth.api.routes.logistics_story import (
    logistics_three_workflow_story_endpoint,
)
from onetruth.api.routes.flags import (
    get_flag_endpoint,
    list_flags_endpoint,
    transition_flag_endpoint,
)
from onetruth.api.routes.human_tasks import (
    claim_human_task_endpoint,
    complete_human_task_endpoint,
    confirm_human_task_review_endpoint,
    get_human_task_endpoint,
    get_human_task_subgraph_endpoint,
    list_human_tasks_endpoint,
    run_stage06_agent_review_endpoint,
    run_weekly_stage04_openai_agent_endpoint,
)
from onetruth.api.routes.pointers import list_pointers_endpoint
from onetruth.api.routes.timeline import (
    list_timeline_events_endpoint,
    list_workflow_run_timeline_endpoint,
)
from onetruth.api.routes.templates import (
    download_template_endpoint,
    get_template_endpoint,
    list_templates_endpoint,
)
from onetruth.api.routes.workflow_runs import (
    get_workflow_run_detail_endpoint,
    get_workflow_run_workspace_endpoint,
    list_workflow_runs_endpoint,
)

ASGIApp = Callable[[dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[None]]


@dataclass(frozen=True)
class MatchedRoute:
    method: str
    name: str
    params: dict[str, str]


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
                boundary_profile=boundary.profile,
            )
            return

        method = str(scope.get("method", "")).upper()
        path = str(scope.get("path", ""))
        raw_headers = scope.get("headers", [])
        headers = _decode_headers(raw_headers)
        query = _decode_query(scope.get("query_string", b""))

        if method == "OPTIONS" and path.startswith("/api/v1/"):
            await _send_no_content(
                send,
                status_code=204,
                boundary_profile=boundary.profile,
                request_headers=headers,
            )
            return

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
                boundary_profile=boundary.profile,
                request_headers=headers,
            )
            return

        try:
            context = boundary.principal_resolver(headers)
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
                    db_url=resolved_db_url,
                )
            finally:
                connection.close()

            await _send_json(
                send,
                status_code=200,
                payload={"status": "ok", **response_payload},
                boundary_profile=boundary.profile,
                request_headers=headers,
            )
        except ApiError as exc:
            await _send_json(
                send,
                status_code=exc.status_code,
                payload=error_payload(exc),
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


def _match_route(method: str, path: str) -> MatchedRoute | None:
    if method == "GET" and path == "/api/v1/human-tasks":
        return MatchedRoute(method=method, name="human_tasks.list", params={})
    if method == "GET" and path.startswith("/api/v1/human-tasks/"):
        prefix = "/api/v1/human-tasks/"
        human_task_id = path[len(prefix) :]
        if human_task_id and "/" not in human_task_id:
            return MatchedRoute(
                method=method,
                name="human_tasks.detail",
                params={"human_task_id": human_task_id},
            )
    if method == "GET" and path.endswith("/subgraph"):
        prefix = "/api/v1/human-tasks/"
        suffix = "/subgraph"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            human_task_id = path[len(prefix) : -len(suffix)]
            if human_task_id and "/" not in human_task_id:
                return MatchedRoute(
                    method=method,
                    name="human_tasks.subgraph",
                    params={"human_task_id": human_task_id},
                )
    if method == "GET" and path.endswith("/artifacts"):
        prefix = "/api/v1/human-tasks/"
        suffix = "/artifacts"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            human_task_id = path[len(prefix) : -len(suffix)]
            if human_task_id and "/" not in human_task_id:
                return MatchedRoute(
                    method=method,
                    name="human_tasks.artifacts.list",
                    params={"human_task_id": human_task_id},
                )
    if method == "POST" and path.endswith("/artifacts/upload"):
        prefix = "/api/v1/human-tasks/"
        suffix = "/artifacts/upload"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            human_task_id = path[len(prefix) : -len(suffix)]
            if human_task_id and "/" not in human_task_id:
                return MatchedRoute(
                    method=method,
                    name="human_tasks.artifacts.upload",
                    params={"human_task_id": human_task_id},
                )
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
    if method == "POST" and path.endswith("/confirm-review"):
        prefix = "/api/v1/human-tasks/"
        suffix = "/confirm-review"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            human_task_id = path[len(prefix) : -len(suffix)]
            if human_task_id:
                return MatchedRoute(
                    method=method,
                    name="human_tasks.confirm_review",
                    params={"human_task_id": human_task_id},
                )
    if method == "POST" and path.endswith("/stage06-agent-review"):
        prefix = "/api/v1/human-tasks/"
        suffix = "/stage06-agent-review"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            human_task_id = path[len(prefix) : -len(suffix)]
            if human_task_id:
                return MatchedRoute(
                    method=method,
                    name="human_tasks.stage06_agent_review",
                    params={"human_task_id": human_task_id},
                )
    if method == "POST" and path.endswith("/weekly-stage04-openai-agent"):
        prefix = "/api/v1/human-tasks/"
        suffix = "/weekly-stage04-openai-agent"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            human_task_id = path[len(prefix) : -len(suffix)]
            if human_task_id:
                return MatchedRoute(
                    method=method,
                    name="human_tasks.weekly_stage04_openai_agent",
                    params={"human_task_id": human_task_id},
                )
    if method == "GET" and path == "/api/v1/approvals":
        return MatchedRoute(method=method, name="approvals.list", params={})
    if method == "GET" and path.startswith("/api/v1/approvals/"):
        prefix = "/api/v1/approvals/"
        approval_id = path[len(prefix) :]
        if approval_id and "/" not in approval_id:
            return MatchedRoute(
                method=method,
                name="approvals.detail",
                params={"approval_id": approval_id},
            )
    if method == "GET" and path.endswith("/artifacts"):
        prefix = "/api/v1/approvals/"
        suffix = "/artifacts"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            approval_id = path[len(prefix) : -len(suffix)]
            if approval_id and "/" not in approval_id:
                return MatchedRoute(
                    method=method,
                    name="approvals.artifacts.list",
                    params={"approval_id": approval_id},
                )
    if method == "POST" and path.endswith("/artifacts/upload"):
        prefix = "/api/v1/approvals/"
        suffix = "/artifacts/upload"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            approval_id = path[len(prefix) : -len(suffix)]
            if approval_id and "/" not in approval_id:
                return MatchedRoute(
                    method=method,
                    name="approvals.artifacts.upload",
                    params={"approval_id": approval_id},
                )
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

    if method == "GET" and path == "/api/v1/flags":
        return MatchedRoute(method=method, name="flags.list", params={})
    if method == "GET" and path.startswith("/api/v1/flags/"):
        prefix = "/api/v1/flags/"
        flag_id = path[len(prefix) :]
        if flag_id and "/" not in flag_id:
            return MatchedRoute(
                method=method,
                name="flags.detail",
                params={"flag_id": flag_id},
            )
    if method == "GET" and path.endswith("/artifacts"):
        prefix = "/api/v1/flags/"
        suffix = "/artifacts"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            flag_id = path[len(prefix) : -len(suffix)]
            if flag_id and "/" not in flag_id:
                return MatchedRoute(
                    method=method,
                    name="flags.artifacts.list",
                    params={"flag_id": flag_id},
                )
    if method == "POST" and path.endswith("/artifacts/upload"):
        prefix = "/api/v1/flags/"
        suffix = "/artifacts/upload"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            flag_id = path[len(prefix) : -len(suffix)]
            if flag_id and "/" not in flag_id:
                return MatchedRoute(
                    method=method,
                    name="flags.artifacts.upload",
                    params={"flag_id": flag_id},
                )
    if method == "POST" and path.endswith("/transition"):
        prefix = "/api/v1/flags/"
        suffix = "/transition"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            flag_id = path[len(prefix) : -len(suffix)]
            if flag_id:
                return MatchedRoute(
                    method=method,
                    name="flags.transition",
                    params={"flag_id": flag_id},
                )

    if method == "GET" and path == "/api/v1/workflow-runs":
        return MatchedRoute(method=method, name="workflow_runs.list", params={})
    if method == "GET" and path.endswith("/artifacts"):
        prefix = "/api/v1/workflow-runs/"
        suffix = "/artifacts"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            workflow_run_id = path[len(prefix) : -len(suffix)]
            if workflow_run_id and "/" not in workflow_run_id:
                return MatchedRoute(
                    method=method,
                    name="workflow_runs.artifacts.list",
                    params={"workflow_run_id": workflow_run_id},
                )
    if method == "POST" and path.endswith("/artifacts/upload"):
        prefix = "/api/v1/workflow-runs/"
        suffix = "/artifacts/upload"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            workflow_run_id = path[len(prefix) : -len(suffix)]
            if workflow_run_id and "/" not in workflow_run_id:
                return MatchedRoute(
                    method=method,
                    name="workflow_runs.artifacts.upload",
                    params={"workflow_run_id": workflow_run_id},
                )
    if method == "GET" and path.endswith("/timeline"):
        prefix = "/api/v1/workflow-runs/"
        suffix = "/timeline"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            workflow_run_id = path[len(prefix) : -len(suffix)]
            if workflow_run_id:
                return MatchedRoute(
                    method=method,
                    name="workflow_runs.timeline",
                    params={"workflow_run_id": workflow_run_id},
                )
    if method == "GET" and path.endswith("/workspace"):
        prefix = "/api/v1/workflow-runs/"
        suffix = "/workspace"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            workflow_run_id = path[len(prefix) : -len(suffix)]
            if workflow_run_id and "/" not in workflow_run_id:
                return MatchedRoute(
                    method=method,
                    name="workflow_runs.workspace",
                    params={"workflow_run_id": workflow_run_id},
                )
    if method == "GET" and path.startswith("/api/v1/workflow-runs/"):
        workflow_run_id = path[len("/api/v1/workflow-runs/") :]
        if workflow_run_id and "/" not in workflow_run_id:
            return MatchedRoute(
                method=method,
                name="workflow_runs.detail",
                params={"workflow_run_id": workflow_run_id},
            )
    if method == "GET" and path == "/api/v1/pointers":
        return MatchedRoute(method=method, name="pointers.list", params={})
    if method == "GET" and path == "/api/v1/templates":
        return MatchedRoute(method=method, name="templates.list", params={})
    if method == "GET" and path.endswith("/download"):
        prefix = "/api/v1/templates/"
        suffix = "/download"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            template_id = path[len(prefix) : -len(suffix)]
            if template_id and "/" not in template_id:
                return MatchedRoute(
                    method=method,
                    name="templates.download",
                    params={"template_id": template_id},
                )
    if method == "GET" and path.startswith("/api/v1/templates/"):
        prefix = "/api/v1/templates/"
        template_id = path[len(prefix) :]
        if template_id and "/" not in template_id:
            return MatchedRoute(
                method=method,
                name="templates.detail",
                params={"template_id": template_id},
            )
    if method == "POST" and path == "/api/v1/artifacts/ingest":
        return MatchedRoute(method=method, name="artifacts.ingest", params={})
    if method == "GET" and path == "/api/v1/artifacts":
        return MatchedRoute(method=method, name="artifacts.list", params={})
    if method == "GET" and path.endswith("/download"):
        prefix = "/api/v1/artifacts/"
        suffix = "/download"
        if path.startswith(prefix) and len(path) > len(prefix) + len(suffix):
            artifact_version_id = path[len(prefix) : -len(suffix)]
            if artifact_version_id and "/" not in artifact_version_id:
                return MatchedRoute(
                    method=method,
                    name="artifacts.download",
                    params={"artifact_version_id": artifact_version_id},
                )
    if method == "GET" and path.startswith("/api/v1/artifacts/"):
        prefix = "/api/v1/artifacts/"
        artifact_version_id = path[len(prefix) :]
        if artifact_version_id and "/" not in artifact_version_id:
            return MatchedRoute(
                method=method,
                name="artifacts.detail",
                params={"artifact_version_id": artifact_version_id},
            )
    if method == "GET" and path == "/api/v1/timeline-events":
        return MatchedRoute(method=method, name="timeline_events.list", params={})
    if method == "GET" and path == "/api/v1/board/schedule-planning":
        return MatchedRoute(method=method, name="board.schedule_planning", params={})
    if method == "GET" and path == "/api/v1/stories/logistics-three-workflow":
        return MatchedRoute(method=method, name="stories.logistics_three_workflow", params={})
    return None


def _dispatch_route(
    *,
    matched: MatchedRoute,
    connection,
    context,
    query: dict[str, str],
    page,
    payload: dict[str, Any] | None,
    db_url: str,
) -> dict[str, Any]:
    if matched.name == "human_tasks.list":
        assert page is not None
        return list_human_tasks_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )
    if matched.name == "human_tasks.detail":
        return get_human_task_endpoint(
            connection,
            context=context,
            human_task_id=matched.params["human_task_id"],
        )
    if matched.name == "human_tasks.subgraph":
        return get_human_task_subgraph_endpoint(
            connection,
            context=context,
            human_task_id=matched.params["human_task_id"],
        )
    if matched.name == "human_tasks.artifacts.list":
        assert page is not None
        return list_human_task_artifacts_endpoint(
            connection,
            context=context,
            human_task_id=matched.params["human_task_id"],
            page=page,
        )
    if matched.name == "human_tasks.artifacts.upload":
        return upload_human_task_artifact_endpoint(
            connection,
            context=context,
            db_url=db_url,
            human_task_id=matched.params["human_task_id"],
            payload=_require_payload(payload),
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
    if matched.name == "human_tasks.confirm_review":
        return confirm_human_task_review_endpoint(
            connection,
            context=context,
            db_url=db_url,
            human_task_id=matched.params["human_task_id"],
            payload=_require_payload(payload),
        )
    if matched.name == "human_tasks.stage06_agent_review":
        return run_stage06_agent_review_endpoint(
            connection,
            context=context,
            human_task_id=matched.params["human_task_id"],
            payload=_require_payload(payload),
        )
    if matched.name == "human_tasks.weekly_stage04_openai_agent":
        return run_weekly_stage04_openai_agent_endpoint(
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
    if matched.name == "approvals.detail":
        return get_approval_endpoint(
            connection,
            context=context,
            approval_id=matched.params["approval_id"],
        )
    if matched.name == "approvals.artifacts.list":
        assert page is not None
        return list_approval_artifacts_endpoint(
            connection,
            context=context,
            approval_id=matched.params["approval_id"],
            page=page,
        )
    if matched.name == "approvals.artifacts.upload":
        return upload_approval_artifact_endpoint(
            connection,
            context=context,
            db_url=db_url,
            approval_id=matched.params["approval_id"],
            payload=_require_payload(payload),
        )
    if matched.name == "approvals.respond":
        return respond_approval_endpoint(
            connection,
            context=context,
            approval_id=matched.params["approval_id"],
            payload=_require_payload(payload),
        )
    if matched.name == "flags.list":
        assert page is not None
        return list_flags_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )
    if matched.name == "flags.detail":
        return get_flag_endpoint(
            connection,
            context=context,
            flag_id=matched.params["flag_id"],
        )
    if matched.name == "flags.artifacts.list":
        assert page is not None
        return list_flag_artifacts_endpoint(
            connection,
            context=context,
            flag_id=matched.params["flag_id"],
            page=page,
        )
    if matched.name == "flags.artifacts.upload":
        return upload_flag_artifact_endpoint(
            connection,
            context=context,
            db_url=db_url,
            flag_id=matched.params["flag_id"],
            payload=_require_payload(payload),
        )
    if matched.name == "flags.transition":
        return transition_flag_endpoint(
            connection,
            context=context,
            flag_id=matched.params["flag_id"],
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
    if matched.name == "workflow_runs.timeline":
        assert page is not None
        return list_workflow_run_timeline_endpoint(
            connection,
            context=context,
            workflow_run_id=matched.params["workflow_run_id"],
            query=query,
            page=page,
        )
    if matched.name == "workflow_runs.workspace":
        return get_workflow_run_workspace_endpoint(
            connection,
            context=context,
            workflow_run_id=matched.params["workflow_run_id"],
            query=query,
        )
    if matched.name == "workflow_runs.artifacts.list":
        assert page is not None
        return list_workflow_run_artifacts_endpoint(
            connection,
            context=context,
            workflow_run_id=matched.params["workflow_run_id"],
            page=page,
        )
    if matched.name == "workflow_runs.artifacts.upload":
        return upload_workflow_run_artifact_endpoint(
            connection,
            context=context,
            db_url=db_url,
            workflow_run_id=matched.params["workflow_run_id"],
            payload=_require_payload(payload),
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
    if matched.name == "templates.list":
        assert page is not None
        return list_templates_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )
    if matched.name == "templates.detail":
        return get_template_endpoint(
            connection,
            context=context,
            template_id=matched.params["template_id"],
        )
    if matched.name == "templates.download":
        return download_template_endpoint(
            connection,
            context=context,
            template_id=matched.params["template_id"],
        )
    if matched.name == "artifacts.ingest":
        return ingest_artifact_endpoint(
            connection,
            context=context,
            db_url=db_url,
            payload=_require_payload(payload),
        )
    if matched.name == "artifacts.list":
        assert page is not None
        return list_artifacts_endpoint(
            connection,
            context=context,
            query=query,
            page=page,
        )
    if matched.name == "artifacts.detail":
        return get_artifact_endpoint(
            connection,
            context=context,
            artifact_version_id=matched.params["artifact_version_id"],
        )
    if matched.name == "artifacts.download":
        return download_artifact_endpoint(
            connection,
            context=context,
            artifact_version_id=matched.params["artifact_version_id"],
        )
    if matched.name == "timeline_events.list":
        assert page is not None
        return list_timeline_events_endpoint(
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
    if matched.name == "stories.logistics_three_workflow":
        assert page is not None
        return logistics_three_workflow_story_endpoint(
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
    boundary_profile: BoundaryProfile,
    request_headers: dict[str, str] | None = None,
) -> None:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    response_headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
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
    boundary_profile: BoundaryProfile,
    request_headers: dict[str, str] | None = None,
) -> None:
    response_headers = [(b"content-length", b"0")]
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
