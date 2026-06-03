from __future__ import annotations

import pytest

from onetruth.application.services.workpage_descriptor_registry import (
    WorkpageDescriptorPack,
    WorkpageDescriptorRegistry,
)
from onetruth.application.services.workpage_descriptor_registry_defaults import (
    DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY,
)
from onetruth.application.services.workpage_descriptors import (
    SCHEDULE_WORKFLOW_ID,
    SCHEDULE_WORKPAGE_KIND,
    WorkpageDescriptor,
    descriptor_for_public_run,
    get_workpage_descriptor,
    require_workpage_descriptor,
)


def test_descriptor_registry_can_be_constructed_without_logistics() -> None:
    registry = WorkpageDescriptorRegistry()

    assert registry.pack_names == ()
    assert registry.descriptors == ()
    assert registry.get_descriptor(SCHEDULE_WORKPAGE_KIND) is None
    with pytest.raises(KeyError, match="unknown workpage kind"):
        registry.require_descriptor(SCHEDULE_WORKPAGE_KIND)


def test_descriptor_registry_resolves_custom_domain_pack_without_logistics() -> None:
    descriptor = _fixture_descriptor()
    registry = WorkpageDescriptorRegistry(
        packs=(
            WorkpageDescriptorPack(
                pack_name="fixture",
                descriptors=(descriptor,),
            ),
        ),
    )

    assert registry.pack_names == ("fixture",)
    assert registry.get_descriptor("fixture-v0") is descriptor
    assert registry.descriptor_for_public_run(
        workpage_kind="fixture-v0",
        workflow_id="fixture.workflow.v1",
    ) is descriptor
    assert registry.descriptor_for_public_run(
        workpage_kind="fixture-v0",
        workflow_id="other.workflow.v1",
    ) is None
    assert registry.get_descriptor(SCHEDULE_WORKPAGE_KIND) is None


def test_default_descriptor_registry_exposes_only_logistics_pack_today() -> None:
    assert DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY.pack_names == ("logistics",)
    assert tuple(
        descriptor.kind
        for descriptor in DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY.descriptors
    ) == (
        "schedule-v0",
        "eod-v0",
        "route-demand-v0",
        "driver-preferences-v0",
    )


def test_descriptor_compatibility_facades_use_default_registry() -> None:
    descriptor = DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY.require_descriptor(SCHEDULE_WORKPAGE_KIND)

    assert get_workpage_descriptor(SCHEDULE_WORKPAGE_KIND) is descriptor
    assert require_workpage_descriptor(SCHEDULE_WORKPAGE_KIND) is descriptor
    assert descriptor_for_public_run(
        workpage_kind=SCHEDULE_WORKPAGE_KIND,
        workflow_id=SCHEDULE_WORKFLOW_ID,
    ) is descriptor
    assert descriptor_for_public_run(
        workpage_kind=SCHEDULE_WORKPAGE_KIND,
        workflow_id="dispatch_reporting.v1",
    ) is None


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
        open_action_id="workpage.fixture-v0.open",
        open_action_label="Open fixture",
        create_action_id=None,
        create_action_label=None,
        submit_action_id="workpage.fixture-v0.submit",
        submit_action_label="Submit fixture",
        preview_action_id=None,
        preview_action_label=None,
        create_relation_kind=None,
        submit_relation_kind="response",
    )
