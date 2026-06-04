from __future__ import annotations

from typing import Any

from onetruth.application.services.logistics_workpages import (
    latest_compatible_eod_draft_artifact,
    latest_schedule_draft_artifact,
)
from onetruth.application.services.workpage_action_registry import (
    ApprovalWorkpageActionRule,
    HumanTaskWorkpageActionRule,
    WorkpageActionPack,
    WorkpageActionRegistry,
)
from onetruth.application.services.workpage_action_registry_defaults import (
    DEFAULT_WORKPAGE_ACTION_REGISTRY,
)
from onetruth.application.services.logistics_workpage_descriptors import (
    logistics_workpage_descriptor_registry,
)
from onetruth.application.services.workpage_descriptors import (
    EOD_WORKPAGE_KIND,
    SCHEDULE_WORKPAGE_KIND,
)


WEEKLY_SCHEDULE_WORKFLOW_ID = "weekly_schedule_planning.v1"
DISPATCH_REPORTING_WORKFLOW_ID = "dispatch_reporting.v1"


def build_logistics_workpage_projection(
    workflow_run: dict[str, Any],
    artifact_versions: list[dict[str, Any]],
) -> dict[str, Any]:
    del workflow_run
    return {
        "latest_schedule_draft": latest_schedule_draft_artifact(artifact_versions),
        "latest_eod_draft": latest_compatible_eod_draft_artifact(artifact_versions),
    }


LOGISTICS_WORKPAGE_ACTION_PACK = WorkpageActionPack(
    pack_name="logistics",
    projection_builder=build_logistics_workpage_projection,
    human_task_rules=(
        HumanTaskWorkpageActionRule(
            workflow_id=WEEKLY_SCHEDULE_WORKFLOW_ID,
            surfaces=frozenset(
                {
                    ("Stage04", "work_item"),
                    ("Stage05", "information_request"),
                    ("Stage05", "final_review"),
                }
            ),
            workpage_kind=SCHEDULE_WORKPAGE_KIND,
            latest_artifact_projection_key="latest_schedule_draft",
            unavailable_reason="schedule_draft_unavailable",
            action_mode="open_latest_artifact",
        ),
        HumanTaskWorkpageActionRule(
            workflow_id=DISPATCH_REPORTING_WORKFLOW_ID,
            surfaces=frozenset({("Stage04", "final_packet_review")}),
            workpage_kind=EOD_WORKPAGE_KIND,
            latest_artifact_projection_key="latest_eod_draft",
            unavailable_reason="eod_draft_unavailable",
            action_mode="open_or_create_artifact",
        ),
    ),
    approval_rules=(
        ApprovalWorkpageActionRule(
            workflow_id=WEEKLY_SCHEDULE_WORKFLOW_ID,
            scope_refs=frozenset({"Stage06"}),
            workpage_kind=SCHEDULE_WORKPAGE_KIND,
            latest_artifact_projection_key="latest_schedule_draft",
            unavailable_reason="schedule_draft_unavailable",
            action_mode="open_latest_artifact",
        ),
        ApprovalWorkpageActionRule(
            workflow_id=DISPATCH_REPORTING_WORKFLOW_ID,
            scope_refs=frozenset({"Stage04"}),
            workpage_kind=EOD_WORKPAGE_KIND,
            latest_artifact_projection_key="latest_eod_draft",
            unavailable_reason="eod_draft_unavailable",
            action_mode="open_or_create_artifact",
        ),
    ),
)


LOGISTICS_WORKPAGE_ACTION_WORKFLOW_IDS = frozenset(
    {WEEKLY_SCHEDULE_WORKFLOW_ID, DISPATCH_REPORTING_WORKFLOW_ID}
)


def logistics_workpage_action_registry() -> WorkpageActionRegistry:
    return WorkpageActionRegistry(
        (LOGISTICS_WORKPAGE_ACTION_PACK,),
        descriptor_registry=logistics_workpage_descriptor_registry(),
    )


def logistics_workpage_action_registry_for_workflow(
    workflow_id: str,
) -> WorkpageActionRegistry:
    if workflow_id in LOGISTICS_WORKPAGE_ACTION_WORKFLOW_IDS:
        return logistics_workpage_action_registry()
    return DEFAULT_WORKPAGE_ACTION_REGISTRY
