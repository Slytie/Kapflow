from __future__ import annotations

from onetruth.application.services.workpage_descriptor_registry import (
    WorkpageDescriptorPack,
    WorkpageDescriptorRegistry,
)
from onetruth.application.services.workpage_descriptors import (
    DISPATCH_REPORTING_WORKFLOW_ID,
    DRIVER_PREFERENCES_ARTIFACT_KIND,
    DRIVER_PREFERENCES_WORKPAGE_KIND,
    EOD_DRAFT_ARTIFACT_KIND,
    EOD_WORKPAGE_KIND,
    ROUTE_DEMAND_ARTIFACT_KIND,
    ROUTE_DEMAND_WORKPAGE_KIND,
    SCHEDULE_DRAFT_ARTIFACT_KIND,
    SCHEDULE_PUBLISHED_ARTIFACT_KIND,
    SCHEDULE_WORKPAGE_KIND,
    WEEKLY_SCHEDULE_WORKFLOW_ID,
    WorkpageDescriptor,
    canonical_driver_preferences_artifact_path,
    canonical_driver_preferences_artifact_route,
    canonical_driver_preferences_artifact_submit_path,
    canonical_driver_preferences_snapshot_create_path,
    canonical_eod_artifact_path,
    canonical_eod_artifact_route,
    canonical_eod_artifact_submit_path,
    canonical_eod_draft_create_path,
    canonical_route_demand_artifact_path,
    canonical_route_demand_artifact_route,
    canonical_route_demand_artifact_submit_path,
    canonical_route_demand_next_week_create_path,
    canonical_schedule_artifact_path,
    canonical_schedule_artifact_preview_path,
    canonical_schedule_artifact_route,
    canonical_schedule_artifact_submit_path,
)


_LOGISTICS_DESCRIPTORS: tuple[WorkpageDescriptor, ...] = (
    WorkpageDescriptor(
        kind=SCHEDULE_WORKPAGE_KIND,
        workflow_id=WEEKLY_SCHEDULE_WORKFLOW_ID,
        run_enabled=True,
        artifact_enabled=True,
        submit_enabled=True,
        artifact_kinds=frozenset(
            {
                SCHEDULE_DRAFT_ARTIFACT_KIND,
                SCHEDULE_PUBLISHED_ARTIFACT_KIND,
            }
        ),
        editable_artifact_kinds=frozenset({SCHEDULE_DRAFT_ARTIFACT_KIND}),
        frontend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: canonical_schedule_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: canonical_schedule_artifact_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_submit_path_builder=lambda workflow_run_id, artifact_version_id: canonical_schedule_artifact_submit_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_preview_path_builder=lambda workflow_run_id, artifact_version_id: canonical_schedule_artifact_preview_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        create_path_builder=None,
        open_action_id="workpage.schedule-v0.open_latest_draft",
        open_action_label="Open schedule draft",
        create_action_id=None,
        create_action_label=None,
        submit_action_id="workpage.schedule-v0.save_draft",
        submit_action_label="Save draft",
        preview_action_id="workpage.schedule-v0.preview_recalc",
        preview_action_label="Preview recalculation",
        create_relation_kind=None,
        submit_relation_kind="response",
    ),
    WorkpageDescriptor(
        kind=EOD_WORKPAGE_KIND,
        workflow_id=DISPATCH_REPORTING_WORKFLOW_ID,
        run_enabled=True,
        artifact_enabled=True,
        submit_enabled=True,
        artifact_kinds=frozenset({EOD_DRAFT_ARTIFACT_KIND}),
        editable_artifact_kinds=frozenset({EOD_DRAFT_ARTIFACT_KIND}),
        frontend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: canonical_eod_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: canonical_eod_artifact_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_submit_path_builder=lambda workflow_run_id, artifact_version_id: canonical_eod_artifact_submit_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_preview_path_builder=None,
        create_path_builder=lambda workflow_run_id: canonical_eod_draft_create_path(
            workflow_run_id=workflow_run_id
        ),
        open_action_id="workpage.eod-v0.open_latest_draft",
        open_action_label="Open EOD draft",
        create_action_id="workpage.eod-v0.create_draft",
        create_action_label="Create EOD draft",
        submit_action_id="workpage.eod-v0.submit_draft",
        submit_action_label="Submit draft",
        preview_action_id=None,
        preview_action_label=None,
        create_relation_kind="draft",
        submit_relation_kind="response",
    ),
    WorkpageDescriptor(
        kind=ROUTE_DEMAND_WORKPAGE_KIND,
        workflow_id=WEEKLY_SCHEDULE_WORKFLOW_ID,
        run_enabled=True,
        artifact_enabled=True,
        submit_enabled=True,
        artifact_kinds=frozenset({ROUTE_DEMAND_ARTIFACT_KIND}),
        editable_artifact_kinds=frozenset({ROUTE_DEMAND_ARTIFACT_KIND}),
        frontend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: canonical_route_demand_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: canonical_route_demand_artifact_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_submit_path_builder=lambda workflow_run_id, artifact_version_id: canonical_route_demand_artifact_submit_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_preview_path_builder=None,
        create_path_builder=lambda workflow_run_id: canonical_route_demand_next_week_create_path(
            workflow_run_id=workflow_run_id
        ),
        open_action_id="workpage.route-demand-v0.open_latest",
        open_action_label="Open route demand",
        create_action_id="workpage.route-demand-v0.add_next_week",
        create_action_label="Add a week",
        submit_action_id="workpage.route-demand-v0.save",
        submit_action_label="Save route demand",
        preview_action_id=None,
        preview_action_label=None,
        create_relation_kind="response",
        submit_relation_kind="response",
    ),
    WorkpageDescriptor(
        kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
        workflow_id=WEEKLY_SCHEDULE_WORKFLOW_ID,
        run_enabled=True,
        artifact_enabled=True,
        submit_enabled=True,
        artifact_kinds=frozenset({DRIVER_PREFERENCES_ARTIFACT_KIND}),
        editable_artifact_kinds=frozenset({DRIVER_PREFERENCES_ARTIFACT_KIND}),
        frontend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: canonical_driver_preferences_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_route_builder=lambda workflow_run_id, artifact_version_id: canonical_driver_preferences_artifact_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_submit_path_builder=lambda workflow_run_id, artifact_version_id: canonical_driver_preferences_artifact_submit_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
        backend_artifact_preview_path_builder=None,
        create_path_builder=lambda workflow_run_id: canonical_driver_preferences_snapshot_create_path(
            workflow_run_id=workflow_run_id
        ),
        open_action_id="workpage.driver-preferences-v0.open_latest",
        open_action_label="Open driver preferences",
        create_action_id="workpage.driver-preferences-v0.create_snapshot",
        create_action_label="Create preferences snapshot",
        submit_action_id="workpage.driver-preferences-v0.save",
        submit_action_label="Save driver preferences",
        preview_action_id=None,
        preview_action_label=None,
        create_relation_kind="response",
        submit_relation_kind="response",
    ),
)

LOGISTICS_WORKPAGE_DESCRIPTOR_PACK = WorkpageDescriptorPack(
    pack_name="logistics",
    descriptors=_LOGISTICS_DESCRIPTORS,
)


def logistics_workpage_descriptor_registry() -> WorkpageDescriptorRegistry:
    return WorkpageDescriptorRegistry(packs=(LOGISTICS_WORKPAGE_DESCRIPTOR_PACK,))


LOGISTICS_WORKPAGE_WORKFLOW_IDS = frozenset(
    {WEEKLY_SCHEDULE_WORKFLOW_ID, DISPATCH_REPORTING_WORKFLOW_ID}
)
