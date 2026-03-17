from __future__ import annotations

from onetruth.api.dependencies import BoundaryProfile, RequestContext


def get_viewer_session_endpoint(
    *,
    context: RequestContext,
    boundary_profile: BoundaryProfile,
) -> dict[str, object]:
    request_context_mode = (
        "server_derived" if boundary_profile == "shared_env" else "trusted_headers"
    )
    actor_switching_allowed = boundary_profile in {"local_dev", "ci_test"}
    return {
        "command": "api.viewer.bootstrap",
        "viewer_session": {
            "tenant_id": context.tenant_id,
            "domain_id": context.domain_id,
            "actor_id": context.actor_id,
            "actor_type": context.actor_type,
            "actor_roles": list(context.actor_roles),
            "boundary_profile": boundary_profile,
            "request_context_mode": request_context_mode,
            "actor_switching_allowed": actor_switching_allowed,
        },
    }
