from __future__ import annotations

from onetruth.api.route_registry import (
    JSON_ARTIFACT_BODY,
    JSON_COMMAND_BODY,
    NO_BODY,
    ROUTES,
    match_route,
)


def test_route_registry_route_names_are_unique() -> None:
    route_names = [route.name for route in ROUTES]
    assert len(route_names) == len(set(route_names))


def test_route_registry_matches_representative_exact_and_parameterized_routes() -> None:
    exact_match = match_route("GET", "/api/v1/workflow-runs")
    assert exact_match is not None
    assert exact_match.route.name == "workflow_runs.list"
    assert exact_match.params == {}

    detail_match = match_route("GET", "/api/v1/artifacts/art-001")
    assert detail_match is not None
    assert detail_match.route.name == "artifacts.detail"
    assert detail_match.params == {"artifact_version_id": "art-001"}

    story_match = match_route("GET", "/api/v1/stories/logistics-three-workflow")
    assert story_match is not None
    assert story_match.route.name == "stories.logistics_three_workflow"


def test_route_registry_preserves_suffix_precedence_over_detail_routes() -> None:
    template_download = match_route(
        "GET",
        "/api/v1/templates/schedule.stage05.draft_schedule.workbook.empty.v1/download",
    )
    assert template_download is not None
    assert template_download.route.name == "templates.download"

    workflow_timeline = match_route("GET", "/api/v1/workflow-runs/wr-001/timeline")
    assert workflow_timeline is not None
    assert workflow_timeline.route.name == "workflow_runs.timeline"

    workflow_workspace = match_route("GET", "/api/v1/workflow-runs/wr-001/workspace")
    assert workflow_workspace is not None
    assert workflow_workspace.route.name == "workflow_runs.workspace"

    human_task_subgraph = match_route("GET", "/api/v1/human-tasks/ht-001/subgraph")
    assert human_task_subgraph is not None
    assert human_task_subgraph.route.name == "human_tasks.subgraph"

    human_task_claim = match_route("POST", "/api/v1/human-tasks/ht-001/claim")
    assert human_task_claim is not None
    assert human_task_claim.route.name == "human_tasks.claim"


def test_route_registry_exposes_representative_metadata() -> None:
    routes_by_name = {route.name: route for route in ROUTES}

    assert routes_by_name["workflow_runs.list"].needs_page is True
    assert routes_by_name["workflow_runs.list"].body_policy == NO_BODY

    assert routes_by_name["human_tasks.claim"].needs_page is False
    assert routes_by_name["human_tasks.claim"].body_policy == JSON_COMMAND_BODY

    assert routes_by_name["workflow_runs.workspace"].needs_page is False
    assert routes_by_name["workflow_runs.workspace"].body_policy == NO_BODY

    assert routes_by_name["artifacts.ingest"].body_policy == JSON_ARTIFACT_BODY


def test_route_registry_preserves_current_permissive_vs_strict_slash_behavior() -> None:
    strict_detail = match_route("GET", "/api/v1/human-tasks/ht-001/extra")
    assert strict_detail is None

    permissive_claim = match_route("POST", "/api/v1/human-tasks/ht-001/extra/claim")
    assert permissive_claim is not None
    assert permissive_claim.route.name == "human_tasks.claim"
    assert permissive_claim.params == {"human_task_id": "ht-001/extra"}

    permissive_timeline = match_route("GET", "/api/v1/workflow-runs/wr-001/extra/timeline")
    assert permissive_timeline is not None
    assert permissive_timeline.route.name == "workflow_runs.timeline"
    assert permissive_timeline.params == {"workflow_run_id": "wr-001/extra"}

    strict_workspace = match_route("GET", "/api/v1/workflow-runs/wr-001/extra/workspace")
    assert strict_workspace is None
