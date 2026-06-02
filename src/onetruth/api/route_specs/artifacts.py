from __future__ import annotations

from onetruth.api.routes.artifacts import (
    download_artifact_binary_endpoint,
    download_artifact_endpoint,
    get_artifact_endpoint,
    ingest_artifact_endpoint,
    list_artifacts_endpoint,
)
from onetruth.api.route_specs._core import (
    JSON_ARTIFACT_BODY,
    NO_BODY,
    RouteSpec,
    _exact,
    _param,
    _require_page,
    _require_payload,
)

ARTIFACT_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="artifacts.ingest",
        method="POST",
        pattern=_exact("/api/v1/artifacts/ingest"),
        body_policy=JSON_ARTIFACT_BODY,
        needs_page=False,
        dispatch=lambda execution, _params: ingest_artifact_endpoint(
            execution.connection,
            context=execution.context,
            db_url=execution.db_url,
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="artifacts.list",
        method="GET",
        pattern=_exact("/api/v1/artifacts"),
        body_policy=NO_BODY,
        needs_page=True,
        dispatch=lambda execution, _params: list_artifacts_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="artifacts.download.binary",
        method="GET",
        pattern=_param(
            "/api/v1/artifacts/",
            param_name="artifact_version_id",
            suffix="/download.bin",
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: download_artifact_binary_endpoint(
            execution.connection,
            context=execution.context,
            boundary_profile=execution.boundary_profile,
            db_url=execution.db_url,
            artifact_version_id=params["artifact_version_id"],
        ),
    ),
    RouteSpec(
        name="artifacts.download",
        method="GET",
        pattern=_param(
            "/api/v1/artifacts/",
            param_name="artifact_version_id",
            suffix="/download",
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: download_artifact_endpoint(
            execution.connection,
            context=execution.context,
            boundary_profile=execution.boundary_profile,
            db_url=execution.db_url,
            artifact_version_id=params["artifact_version_id"],
        ),
    ),
    RouteSpec(
        name="artifacts.detail",
        method="GET",
        pattern=_param(
            "/api/v1/artifacts/",
            param_name="artifact_version_id",
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: get_artifact_endpoint(
            execution.connection,
            context=execution.context,
            artifact_version_id=params["artifact_version_id"],
        ),
    ),
)
