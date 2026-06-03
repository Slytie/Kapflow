from __future__ import annotations

from dataclasses import dataclass, field

from onetruth.application.services.workpage_descriptors import WorkpageDescriptor


@dataclass(frozen=True)
class WorkpageDescriptorPack:
    pack_name: str
    descriptors: tuple[WorkpageDescriptor, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkpageDescriptorRegistry:
    packs: tuple[WorkpageDescriptorPack, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        pack_names = [pack.pack_name for pack in self.packs]
        duplicate_packs = sorted(
            pack_name
            for pack_name in set(pack_names)
            if pack_names.count(pack_name) > 1
        )
        if duplicate_packs:
            raise ValueError(f"duplicate workpage descriptor packs: {', '.join(duplicate_packs)}")

        descriptor_kinds = [descriptor.kind for descriptor in self.descriptors]
        duplicate_kinds = sorted(
            kind
            for kind in set(descriptor_kinds)
            if descriptor_kinds.count(kind) > 1
        )
        if duplicate_kinds:
            raise ValueError(f"duplicate workpage descriptors: {', '.join(duplicate_kinds)}")

    @property
    def pack_names(self) -> tuple[str, ...]:
        return tuple(pack.pack_name for pack in self.packs)

    @property
    def descriptors(self) -> tuple[WorkpageDescriptor, ...]:
        descriptors: list[WorkpageDescriptor] = []
        for pack in self.packs:
            descriptors.extend(pack.descriptors)
        return tuple(descriptors)

    def with_pack(self, pack: WorkpageDescriptorPack) -> WorkpageDescriptorRegistry:
        return WorkpageDescriptorRegistry((*self.packs, pack))

    def get_descriptor(self, workpage_kind: str) -> WorkpageDescriptor | None:
        for descriptor in self.descriptors:
            if descriptor.kind == workpage_kind:
                return descriptor
        return None

    def require_descriptor(self, workpage_kind: str) -> WorkpageDescriptor:
        descriptor = self.get_descriptor(workpage_kind)
        if descriptor is None:
            raise KeyError(f"unknown workpage kind: {workpage_kind}")
        return descriptor

    def descriptor_for_public_run(
        self,
        *,
        workpage_kind: str,
        workflow_id: str,
    ) -> WorkpageDescriptor | None:
        descriptor = self.get_descriptor(workpage_kind)
        if (
            descriptor is None
            or not descriptor.run_enabled
            or not descriptor.supports_workflow(workflow_id)
        ):
            return None
        return descriptor
