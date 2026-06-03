from __future__ import annotations

from onetruth.application.services.workpage_action_registry import (
    ApprovalWorkpageActionRule,
    HumanTaskWorkpageActionRule,
    WorkpageActionPack,
    WorkpageActionRegistry,
)


def test_registry_merges_projection_builders_and_projects_human_task_rule() -> None:
    registry = WorkpageActionRegistry(
        (
            WorkpageActionPack(
                pack_name="fixture",
                projection_builder=lambda *, workflow_run, artifact_versions: {
                    "latest_schedule_draft": artifact_versions[0]
                },
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
    artifact = {"artifact_version_id": "av-schedule-001"}

    projection = registry.build_projection(
        workflow_run={"workflow_id": "weekly_schedule_planning.v1", "workflow_run_id": "wr-001"},
        artifact_versions=[artifact],
    )
    actions = registry.project_human_task_actions(
        task={
            "workflow_run_id": "wr-001",
            "human_task_id": "ht-001",
            "stage_id": "Stage04",
            "task_kind": "work_item",
        },
        workflow_run={"workflow_id": "weekly_schedule_planning.v1"},
        workpage_projection=projection,
    )

    assert registry.pack_names == ("fixture",)
    assert actions == [
        {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "label": "Open schedule draft",
            "presentation": "open_route",
            "state": "available",
            "route": "/runs/wr-001/workpages/schedule-v0/artifacts/av-schedule-001",
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
                "action_id": "workpage.schedule-v0.open_latest_draft",
                "workpage_kind": "schedule-v0",
                "workflow_run_id": "wr-001",
                "artifact_version_id": "av-schedule-001",
                "subject": {
                    "subject_kind": "human_task",
                    "subject_id": "ht-001",
                },
            },
            "disabled_reason": None,
        }
    ]


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
