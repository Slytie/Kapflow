from __future__ import annotations

from onetruth.application.services.workpage_action_registry import (
    ApprovalWorkpageActionRule,
    HumanTaskWorkpageActionRule,
    WorkpageActionPack,
    WorkpageActionRegistry,
)
from onetruth.application.services.workpage_action_registry_defaults import (
    DEFAULT_WORKPAGE_ACTION_REGISTRY,
)
from onetruth.application.services.logistics_workpage_action_registry import (
    logistics_workpage_action_registry_for_workflow,
)
from onetruth.application.services.workpage_descriptor_registry import (
    WorkpageDescriptorPack,
    WorkpageDescriptorRegistry,
)
from onetruth.application.services.workpage_descriptors import WorkpageDescriptor


def test_default_action_registry_is_platform_neutral() -> None:
    assert DEFAULT_WORKPAGE_ACTION_REGISTRY.pack_names == ()
    assert DEFAULT_WORKPAGE_ACTION_REGISTRY.build_projection(
        workflow_run={
            "workflow_id": "capex.project_intake.v1",
            "workflow_run_id": "wr-capex-001",
        },
        artifact_versions=[],
    ) == {
        "workflow_id": "capex.project_intake.v1",
        "workflow_run_id": "wr-capex-001",
    }
    assert DEFAULT_WORKPAGE_ACTION_REGISTRY.project_human_task_actions(
        task={
            "workflow_run_id": "wr-capex-001",
            "human_task_id": "ht-capex-001",
            "stage_id": "Stage04",
            "task_kind": "work_item",
        },
        workflow_run={"workflow_id": "capex.project_intake.v1"},
        workpage_projection={},
    ) == []
    assert not DEFAULT_WORKPAGE_ACTION_REGISTRY.supports_human_task_subject(
        workflow_id="capex.project_intake.v1",
        workpage_kind="schedule-v0",
        stage_id="Stage04",
        task_kind="work_item",
    )


def test_logistics_action_registry_is_explicitly_selected_by_workflow() -> None:
    assert logistics_workpage_action_registry_for_workflow(
        "weekly_schedule_planning.v1"
    ).pack_names == ("logistics",)
    assert logistics_workpage_action_registry_for_workflow(
        "dispatch_reporting.v1"
    ).pack_names == ("logistics",)
    assert (
        logistics_workpage_action_registry_for_workflow(
            "capex.project_intake.v1"
        ).pack_names
        == ()
    )


def test_registry_merges_projection_builders_and_projects_human_task_rule() -> None:
    descriptor_registry = WorkpageDescriptorRegistry(
        packs=(
            WorkpageDescriptorPack(
                pack_name="fixture",
                descriptors=(_fixture_descriptor(),),
            ),
        )
    )
    registry = WorkpageActionRegistry(
        (
            WorkpageActionPack(
                pack_name="fixture",
                projection_builder=lambda *, workflow_run, artifact_versions: {
                    "latest_fixture_artifact": artifact_versions[0]
                },
                human_task_rules=(
                    HumanTaskWorkpageActionRule(
                        workflow_id="fixture.workflow.v1",
                        surfaces=frozenset({("Stage04", "work_item")}),
                        workpage_kind="fixture-v0",
                        latest_artifact_projection_key="latest_fixture_artifact",
                        unavailable_reason="fixture_artifact_unavailable",
                        action_mode="open_latest_artifact",
                    ),
                ),
            ),
        ),
        descriptor_registry=descriptor_registry,
    )
    artifact = {"artifact_version_id": "av-fixture-001"}

    projection = registry.build_projection(
        workflow_run={"workflow_id": "fixture.workflow.v1", "workflow_run_id": "wr-001"},
        artifact_versions=[artifact],
    )
    actions = registry.project_human_task_actions(
        task={
            "workflow_run_id": "wr-001",
            "human_task_id": "ht-001",
            "stage_id": "Stage04",
            "task_kind": "work_item",
        },
        workflow_run={"workflow_id": "fixture.workflow.v1"},
        workpage_projection=projection,
    )

    assert registry.pack_names == ("fixture",)
    assert actions == [
        {
            "action_id": "workpage.fixture-v0.open_latest",
            "workpage_kind": "fixture-v0",
            "label": "Open fixture artifact",
            "presentation": "open_route",
            "state": "available",
            "route": "/fixture/wr-001/av-fixture-001",
            "create_path": None,
            "subject_context": {
                "subject_kind": "human_task",
                "subject_id": "ht-001",
                "workflow_run_id": "wr-001",
            },
            "link_policy": {
                "create_relation_kind": None,
                "submit_relation_kind": "response",
            },
            "action_ref": {
                "action_id": "workpage.fixture-v0.open_latest",
                "workpage_kind": "fixture-v0",
                "workflow_run_id": "wr-001",
                "artifact_version_id": "av-fixture-001",
                "subject": {
                    "subject_kind": "human_task",
                    "subject_id": "ht-001",
                },
            },
            "disabled_reason": None,
        }
    ]


def _fixture_descriptor() -> WorkpageDescriptor:
    return WorkpageDescriptor(
        kind="fixture-v0",
        workflow_id="fixture.workflow.v1",
        run_enabled=True,
        artifact_enabled=True,
        submit_enabled=True,
        artifact_kinds=frozenset({"fixture.artifact"}),
        editable_artifact_kinds=frozenset({"fixture.artifact"}),
        frontend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: (
            f"/fixture/{workflow_run_id}/{artifact_version_id}"
        ),
        backend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: (
            f"/api/fixture/{workflow_run_id}/{artifact_version_id}"
        ),
        backend_artifact_submit_path_builder=None,
        backend_artifact_preview_path_builder=None,
        create_path_builder=None,
        open_action_id="workpage.fixture-v0.open_latest",
        open_action_label="Open fixture artifact",
        create_action_id=None,
        create_action_label=None,
        submit_action_id="workpage.fixture-v0.submit",
        submit_action_label="Submit fixture",
        preview_action_id=None,
        preview_action_label=None,
        create_relation_kind=None,
        submit_relation_kind="response",
    )


def test_registry_returns_no_action_for_unregistered_surface() -> None:
    registry = WorkpageActionRegistry(
        (
            WorkpageActionPack(
                pack_name="fixture",
                human_task_rules=(
                    HumanTaskWorkpageActionRule(
                        workflow_id="weekly_schedule_planning.v1",
                        surfaces=frozenset({("Stage04", "work_item")}),
                        workpage_kind="schedule-v0",
                        latest_artifact_projection_key="latest_schedule_draft",
                        unavailable_reason="schedule_draft_unavailable",
                        action_mode="open_latest_artifact",
                    ),
                ),
            ),
        )
    )

    assert registry.project_human_task_actions(
        task={
            "workflow_run_id": "wr-001",
            "human_task_id": "ht-001",
            "stage_id": "Stage99",
            "task_kind": "work_item",
        },
        workflow_run={"workflow_id": "weekly_schedule_planning.v1"},
        workpage_projection={},
    ) == []


def test_registry_support_checks_cover_human_task_and_approval_subjects() -> None:
    registry = WorkpageActionRegistry(
        (
            WorkpageActionPack(
                pack_name="fixture",
                human_task_rules=(
                    HumanTaskWorkpageActionRule(
                        workflow_id="weekly_schedule_planning.v1",
                        surfaces=frozenset({("Stage04", "work_item")}),
                        workpage_kind="schedule-v0",
                        latest_artifact_projection_key="latest_schedule_draft",
                        unavailable_reason="schedule_draft_unavailable",
                        action_mode="open_latest_artifact",
                    ),
                ),
                approval_rules=(
                    ApprovalWorkpageActionRule(
                        workflow_id="weekly_schedule_planning.v1",
                        scope_refs=frozenset({"Stage06"}),
                        workpage_kind="schedule-v0",
                        latest_artifact_projection_key="latest_schedule_draft",
                        unavailable_reason="schedule_draft_unavailable",
                        action_mode="open_latest_artifact",
                    ),
                ),
            ),
        )
    )

    assert registry.supports_human_task_subject(
        workflow_id="weekly_schedule_planning.v1",
        workpage_kind="schedule-v0",
        stage_id="Stage04",
        task_kind="work_item",
    )
    assert not registry.supports_human_task_subject(
        workflow_id="weekly_schedule_planning.v1",
        workpage_kind="schedule-v0",
        stage_id="Stage99",
        task_kind="work_item",
    )
    assert registry.supports_approval_subject(
        workflow_id="weekly_schedule_planning.v1",
        workpage_kind="schedule-v0",
        scope_kind="stage",
        scope_ref="Stage06",
    )
    assert not registry.supports_approval_subject(
        workflow_id="weekly_schedule_planning.v1",
        workpage_kind="schedule-v0",
        scope_kind="workflow",
        scope_ref="Stage06",
    )
