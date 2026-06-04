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


def test_route_registry_preserves_exact_global_route_order() -> None:
    assert [route.name for route in ROUTES] == [
        "ops.health",
        "ops.readiness",
        "ops.metrics",
        "viewer.bootstrap",
        "operator.home",
        "human_tasks.list",
        "human_tasks.detail",
        "human_tasks.subgraph",
        "human_tasks.artifacts.list",
        "human_tasks.artifacts.upload",
        "human_tasks.claim",
        "human_tasks.complete",
        "human_tasks.confirm_review",
        "human_tasks.stage06_agent_review",
        "human_tasks.weekly_stage04_openai_agent",
        "approvals.list",
        "approvals.detail",
        "approvals.artifacts.list",
        "approvals.artifacts.upload",
        "approvals.respond",
        "flags.list",
        "flags.detail",
        "flags.artifacts.list",
        "flags.artifacts.upload",
        "flags.transition",
        "capex.projects.list",
        "capex.projects.create",
        "capex.projects.memberships.list",
        "capex.projects.memberships.grant",
        "capex.projects.workflow_runs.create",
        "capex.projects.detail",
        "workflow_runs.list",
        "workflow_runs.artifacts.list",
        "workflow_runs.artifacts.upload",
        "workflow_runs.timeline",
        "workflow_runs.workspace",
        "workflow_runs.prepare_live_dispatch_day",
        "workflow_runs.detail",
        "pointers.list",
        "templates.list",
        "templates.download.binary",
        "templates.download",
        "templates.detail",
        "artifacts.ingest",
        "artifacts.list",
        "artifacts.download.binary",
        "artifacts.download",
        "artifacts.detail",
        "timeline_events.list",
        "board.schedule_planning",
        "stories.logistics_three_workflow",
        "workpages.workflow_run.artifact.preview",
        "workpages.workflow_run.route_demand.artifact.save_and_run",
        "workpages.workflow_run.schedule.sick_no_show",
        "workpages.workflow_run.schedule.route_demand_coverage_candidates",
        "workpages.workflow_run.schedule.route_demand_coverage",
        "workpages.workflow_run.schedule.previous_week_reality",
        "workpages.workflow_run.artifact.detail",
        "workpages.workflow_run.artifact.submit",
        "workpages.workflow_run.detail",
        "workpages.workflow_run.eod_drafts.create",
        "workpages.workflow_run.route_demand.next_week.create",
        "workpages.workflow_run.eod_intake.ensure",
        "workpages.workflow_run.driver_preferences.snapshots.create",
        "workpages.workflow_run.driver_preferences.availability_exceptions.add",
    ]


def test_route_registry_matches_representative_exact_and_parameterized_routes() -> None:
    ops_match = match_route("GET", "/api/v1/ops/readiness")
    assert ops_match is not None
    assert ops_match.route.name == "ops.readiness"
    assert ops_match.params == {}

    exact_match = match_route("GET", "/api/v1/workflow-runs")
    assert exact_match is not None
    assert exact_match.route.name == "workflow_runs.list"
    assert exact_match.params == {}

    capex_project_match = match_route("GET", "/api/v1/capex/projects/cp-001")
    assert capex_project_match is not None
    assert capex_project_match.route.name == "capex.projects.detail"
    assert capex_project_match.params == {"project_id": "cp-001"}

    capex_membership_match = match_route(
        "POST",
        "/api/v1/capex/projects/cp-001/memberships",
    )
    assert capex_membership_match is not None
    assert capex_membership_match.route.name == "capex.projects.memberships.grant"
    assert capex_membership_match.params == {"project_id": "cp-001"}

    detail_match = match_route("GET", "/api/v1/artifacts/art-001")
    assert detail_match is not None
    assert detail_match.route.name == "artifacts.detail"
    assert detail_match.params == {"artifact_version_id": "art-001"}

    story_match = match_route("GET", "/api/v1/stories/logistics-three-workflow")
    assert story_match is not None
    assert story_match.route.name == "stories.logistics_three_workflow"

    operator_home_match = match_route("GET", "/api/v1/operator/home")
    assert operator_home_match is not None
    assert operator_home_match.route.name == "operator.home"
    assert operator_home_match.params == {}

    workflow_run_workpage_match = match_route(
        "GET",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0",
    )
    assert workflow_run_workpage_match is not None
    assert workflow_run_workpage_match.route.name == "workpages.workflow_run.detail"
    assert workflow_run_workpage_match.params == {
        "workflow_run_workpage": "wr-001/schedule-v0"
    }

    workflow_run_artifact_match = match_route(
        "GET",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001",
    )
    assert workflow_run_artifact_match is not None
    assert workflow_run_artifact_match.route.name == "workpages.workflow_run.artifact.detail"
    assert workflow_run_artifact_match.params == {
        "workflow_run_artifact": "wr-001/schedule-v0/artifacts/av-001"
    }

    workflow_run_previous_week_reality_match = match_route(
        "GET",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/reality/previous-week",
    )
    assert workflow_run_previous_week_reality_match is not None
    assert (
        workflow_run_previous_week_reality_match.route.name
        == "workpages.workflow_run.schedule.previous_week_reality"
    )
    assert workflow_run_previous_week_reality_match.params == {
        "workflow_run_schedule_previous_week_reality": (
            "wr-001/schedule-v0/artifacts/av-001"
        )
    }

    workflow_run_artifact_preview_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/preview",
    )
    assert workflow_run_artifact_preview_match is not None
    assert (
        workflow_run_artifact_preview_match.route.name
        == "workpages.workflow_run.artifact.preview"
    )
    assert workflow_run_artifact_preview_match.params == {
        "workflow_run_artifact_preview": "wr-001/schedule-v0/artifacts/av-001"
    }

    workflow_run_artifact_submit_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/submit",
    )
    assert workflow_run_artifact_submit_match is not None
    assert workflow_run_artifact_submit_match.route.name == "workpages.workflow_run.artifact.submit"
    assert workflow_run_artifact_submit_match.params == {
        "workflow_run_artifact_submit": "wr-001/schedule-v0/artifacts/av-001"
    }

    workflow_run_route_demand_save_and_run_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/route-demand-v0/artifacts/av-001/save-and-run",
    )
    assert workflow_run_route_demand_save_and_run_match is not None
    assert (
        workflow_run_route_demand_save_and_run_match.route.name
        == "workpages.workflow_run.route_demand.artifact.save_and_run"
    )
    assert workflow_run_route_demand_save_and_run_match.params == {
        "workflow_run_artifact_save_and_run": "wr-001/route-demand-v0/artifacts/av-001"
    }

    workflow_run_schedule_sick_no_show_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/sick-no-show",
    )
    assert workflow_run_schedule_sick_no_show_match is not None
    assert (
        workflow_run_schedule_sick_no_show_match.route.name
        == "workpages.workflow_run.schedule.sick_no_show"
    )
    assert workflow_run_schedule_sick_no_show_match.params == {
        "workflow_run_schedule_sick_no_show": "wr-001/schedule-v0/artifacts/av-001"
    }

    workflow_run_schedule_route_demand_coverage_candidates_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/route-demand-coverage-candidates",
    )
    assert workflow_run_schedule_route_demand_coverage_candidates_match is not None
    assert (
        workflow_run_schedule_route_demand_coverage_candidates_match.route.name
        == "workpages.workflow_run.schedule.route_demand_coverage_candidates"
    )
    assert workflow_run_schedule_route_demand_coverage_candidates_match.params == {
        "workflow_run_schedule_route_demand_coverage_candidates": (
            "wr-001/schedule-v0/artifacts/av-001"
        )
    }

    workflow_run_schedule_route_demand_coverage_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/route-demand-coverage",
    )
    assert workflow_run_schedule_route_demand_coverage_match is not None
    assert (
        workflow_run_schedule_route_demand_coverage_match.route.name
        == "workpages.workflow_run.schedule.route_demand_coverage"
    )
    assert workflow_run_schedule_route_demand_coverage_match.params == {
        "workflow_run_schedule_route_demand_coverage": (
            "wr-001/schedule-v0/artifacts/av-001"
        )
    }

    workflow_run_eod_draft_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/eod-v0/drafts",
    )
    assert workflow_run_eod_draft_match is not None
    assert workflow_run_eod_draft_match.route.name == "workpages.workflow_run.eod_drafts.create"
    assert workflow_run_eod_draft_match.params == {"workflow_run_id": "wr-001"}

    workflow_run_route_demand_next_week_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/route-demand-v0/next-week",
    )
    assert workflow_run_route_demand_next_week_match is not None
    assert (
        workflow_run_route_demand_next_week_match.route.name
        == "workpages.workflow_run.route_demand.next_week.create"
    )
    assert workflow_run_route_demand_next_week_match.params == {"workflow_run_id": "wr-001"}

    workflow_run_eod_intake_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/eod-v0/intake-task",
    )
    assert workflow_run_eod_intake_match is not None
    assert workflow_run_eod_intake_match.route.name == "workpages.workflow_run.eod_intake.ensure"
    assert workflow_run_eod_intake_match.params == {"workflow_run_id": "wr-001"}

    workflow_run_driver_preferences_snapshot_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/driver-preferences-v0/snapshots",
    )
    assert workflow_run_driver_preferences_snapshot_match is not None
    assert (
        workflow_run_driver_preferences_snapshot_match.route.name
        == "workpages.workflow_run.driver_preferences.snapshots.create"
    )
    assert workflow_run_driver_preferences_snapshot_match.params == {
        "workflow_run_id": "wr-001"
    }

    workflow_run_driver_availability_exception_match = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/driver-preferences-v0/availability-exceptions",
    )
    assert workflow_run_driver_availability_exception_match is not None
    assert (
        workflow_run_driver_availability_exception_match.route.name
        == "workpages.workflow_run.driver_preferences.availability_exceptions.add"
    )
    assert workflow_run_driver_availability_exception_match.params == {
        "workflow_run_id": "wr-001"
    }

    assert match_route("GET", "/api/v1/workpages/demo/schedule-v0") is None
    assert match_route("GET", "/api/v1/workpages/demo/eod-v0") is None
    assert match_route("GET", "/api/v1/workpages/artifacts/av-001") is None
    assert match_route("POST", "/api/v1/workpages/artifacts/av-001/preview") is None
    assert match_route("POST", "/api/v1/workpages/artifacts/av-001/submit") is None
    assert match_route("POST", "/api/v1/workpages/demo/eod-v0/drafts") is None


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

    template_binary_download = match_route(
        "GET",
        "/api/v1/templates/schedule.stage05.draft_schedule.workbook.empty.v1/download.bin",
    )
    assert template_binary_download is not None
    assert template_binary_download.route.name == "templates.download.binary"

    artifact_binary_download = match_route(
        "GET",
        "/api/v1/artifacts/art-001/download.bin",
    )
    assert artifact_binary_download is not None
    assert artifact_binary_download.route.name == "artifacts.download.binary"

    schedule_sick_no_show = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/sick-no-show",
    )
    assert schedule_sick_no_show is not None
    assert schedule_sick_no_show.route.name == "workpages.workflow_run.schedule.sick_no_show"

    schedule_route_demand_coverage_candidates = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/route-demand-coverage-candidates",
    )
    assert schedule_route_demand_coverage_candidates is not None
    assert (
        schedule_route_demand_coverage_candidates.route.name
        == "workpages.workflow_run.schedule.route_demand_coverage_candidates"
    )

    schedule_route_demand_coverage = match_route(
        "POST",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/route-demand-coverage",
    )
    assert schedule_route_demand_coverage is not None
    assert (
        schedule_route_demand_coverage.route.name
        == "workpages.workflow_run.schedule.route_demand_coverage"
    )

    schedule_previous_week_reality = match_route(
        "GET",
        "/api/v1/workpages/workflow-runs/wr-001/schedule-v0/artifacts/av-001/reality/previous-week",
    )
    assert schedule_previous_week_reality is not None
    assert (
        schedule_previous_week_reality.route.name
        == "workpages.workflow_run.schedule.previous_week_reality"
    )


def test_route_registry_exposes_representative_metadata() -> None:
    routes_by_name = {route.name: route for route in ROUTES}

    assert routes_by_name["ops.health"].needs_page is False
    assert routes_by_name["ops.health"].body_policy == NO_BODY
    assert routes_by_name["ops.health"].requires_request_context is False
    assert routes_by_name["ops.health"].needs_db_connection is False

    assert routes_by_name["operator.home"].needs_page is False
    assert routes_by_name["operator.home"].body_policy == NO_BODY
    assert routes_by_name["operator.home"].requires_request_context is True
    assert routes_by_name["operator.home"].needs_db_connection is True

    assert routes_by_name["workflow_runs.list"].needs_page is True
    assert routes_by_name["workflow_runs.list"].body_policy == NO_BODY

    assert routes_by_name["human_tasks.claim"].needs_page is False
    assert routes_by_name["human_tasks.claim"].body_policy == JSON_COMMAND_BODY

    assert routes_by_name["workflow_runs.workspace"].needs_page is False
    assert routes_by_name["workflow_runs.workspace"].body_policy == NO_BODY

    assert routes_by_name["artifacts.ingest"].body_policy == JSON_ARTIFACT_BODY

    assert routes_by_name["workpages.workflow_run.artifact.detail"].needs_page is False
    assert routes_by_name["workpages.workflow_run.artifact.detail"].body_policy == NO_BODY
    assert routes_by_name["workpages.workflow_run.artifact.detail"].requires_request_context is True
    assert routes_by_name["workpages.workflow_run.artifact.detail"].needs_db_connection is True

    assert routes_by_name["workpages.workflow_run.artifact.preview"].needs_page is False
    assert routes_by_name["workpages.workflow_run.artifact.preview"].body_policy == JSON_COMMAND_BODY
    assert (
        routes_by_name["workpages.workflow_run.artifact.preview"].requires_request_context
        is True
    )
    assert routes_by_name["workpages.workflow_run.artifact.preview"].needs_db_connection is True

    assert routes_by_name["workpages.workflow_run.artifact.submit"].needs_page is False
    assert routes_by_name["workpages.workflow_run.artifact.submit"].body_policy == JSON_COMMAND_BODY
    assert (
        routes_by_name["workpages.workflow_run.artifact.submit"].requires_request_context
        is True
    )
    assert routes_by_name["workpages.workflow_run.artifact.submit"].needs_db_connection is True

    assert (
        routes_by_name["workpages.workflow_run.schedule.route_demand_coverage_candidates"].needs_page
        is False
    )
    assert (
        routes_by_name["workpages.workflow_run.schedule.route_demand_coverage_candidates"].body_policy
        == JSON_COMMAND_BODY
    )
    assert (
        routes_by_name["workpages.workflow_run.schedule.route_demand_coverage_candidates"].requires_request_context
        is True
    )
    assert (
        routes_by_name["workpages.workflow_run.schedule.route_demand_coverage_candidates"].needs_db_connection
        is True
    )

    assert (
        routes_by_name["workpages.workflow_run.schedule.previous_week_reality"].needs_page
        is False
    )
    assert (
        routes_by_name["workpages.workflow_run.schedule.previous_week_reality"].body_policy
        == NO_BODY
    )
    assert (
        routes_by_name["workpages.workflow_run.schedule.previous_week_reality"].requires_request_context
        is True
    )
    assert (
        routes_by_name["workpages.workflow_run.schedule.previous_week_reality"].needs_db_connection
        is True
    )

    assert routes_by_name["workpages.workflow_run.schedule.route_demand_coverage"].needs_page is False
    assert (
        routes_by_name["workpages.workflow_run.schedule.route_demand_coverage"].body_policy
        == JSON_COMMAND_BODY
    )
    assert (
        routes_by_name["workpages.workflow_run.schedule.route_demand_coverage"].requires_request_context
        is True
    )
    assert (
        routes_by_name["workpages.workflow_run.schedule.route_demand_coverage"].needs_db_connection
        is True
    )

    assert routes_by_name["workpages.workflow_run.detail"].needs_page is False
    assert routes_by_name["workpages.workflow_run.detail"].body_policy == NO_BODY
    assert routes_by_name["workpages.workflow_run.detail"].requires_request_context is True
    assert routes_by_name["workpages.workflow_run.detail"].needs_db_connection is True

    assert (
        routes_by_name["workpages.workflow_run.driver_preferences.snapshots.create"].needs_page
        is False
    )
    assert (
        routes_by_name["workpages.workflow_run.driver_preferences.snapshots.create"].body_policy
        == JSON_COMMAND_BODY
    )
    assert (
        routes_by_name[
            "workpages.workflow_run.driver_preferences.snapshots.create"
        ].requires_request_context
        is True
    )
    assert (
        routes_by_name["workpages.workflow_run.driver_preferences.snapshots.create"]
        .needs_db_connection
        is True
    )

    assert routes_by_name["workpages.workflow_run.eod_drafts.create"].needs_page is False
    assert routes_by_name["workpages.workflow_run.eod_drafts.create"].body_policy == JSON_COMMAND_BODY
    assert (
        routes_by_name["workpages.workflow_run.eod_drafts.create"].requires_request_context
        is True
    )
    assert routes_by_name["workpages.workflow_run.eod_drafts.create"].needs_db_connection is True

    assert "workpages.eod_drafts.create" not in routes_by_name
    assert "workpages.artifact.detail" not in routes_by_name
    assert "workpages.artifact.preview" not in routes_by_name
    assert "workpages.artifact.submit" not in routes_by_name
    assert "workpages.demo.detail" not in routes_by_name


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
