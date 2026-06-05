from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from onetruth.capex_platform.domain_runtime.manifest import (
    DomainManifest,
    DomainReadiness,
)


@dataclass(frozen=True)
class DomainCompositionReport:
    domain_count: int
    workflow_count: int
    workpage_count: int
    side_effect_count: int
    ready_domain_ids: tuple[str, ...] = field(default_factory=tuple)
    incubation_domain_ids: tuple[str, ...] = field(default_factory=tuple)
    disabled_domain_ids: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    activation_allowed: bool = False
    composition_report_version: str = "domain_runtime.composition_report.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "composition_report_version": self.composition_report_version,
            "domain_count": self.domain_count,
            "workflow_count": self.workflow_count,
            "workpage_count": self.workpage_count,
            "side_effect_count": self.side_effect_count,
            "ready_domain_ids": list(self.ready_domain_ids),
            "incubation_domain_ids": list(self.incubation_domain_ids),
            "disabled_domain_ids": list(self.disabled_domain_ids),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "activation_allowed": self.activation_allowed,
        }


class DomainRuntimeRegistry:
    def __init__(self, manifests: tuple[DomainManifest, ...] = ()) -> None:
        self._manifests_by_domain_id = _index_manifests(manifests)

    @property
    def domain_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._manifests_by_domain_id))

    @property
    def ready_domain_ids(self) -> tuple[str, ...]:
        return self.by_readiness("ready")

    @property
    def incubation_domain_ids(self) -> tuple[str, ...]:
        return self.by_readiness("incubation")

    @property
    def disabled_domain_ids(self) -> tuple[str, ...]:
        return self.by_readiness("disabled")

    def with_manifest(self, manifest: DomainManifest) -> DomainRuntimeRegistry:
        return DomainRuntimeRegistry(
            tuple(self._manifests_by_domain_id.values()) + (manifest,)
        )

    def get_domain(self, domain_id: str) -> DomainManifest | None:
        return self._manifests_by_domain_id.get(domain_id)

    def require_domain(self, domain_id: str) -> DomainManifest:
        manifest = self.get_domain(domain_id)
        if manifest is None:
            raise KeyError(f"domain manifest not registered: {domain_id}")
        return manifest

    def by_readiness(self, readiness: DomainReadiness) -> tuple[str, ...]:
        return tuple(
            sorted(
                domain_id
                for domain_id, manifest in self._manifests_by_domain_id.items()
                if manifest.readiness == readiness
            )
        )

    def compose(self) -> DomainCompositionReport:
        manifests = tuple(self._manifests_by_domain_id.values())
        warnings: list[str] = []
        for manifest in sorted(manifests, key=lambda item: item.domain_id):
            if manifest.readiness == "ready" and not manifest.workflows:
                warnings.append(f"{manifest.domain_id}: ready domain has no workflows")
            if manifest.readiness == "disabled" and manifest.side_effects:
                warnings.append(f"{manifest.domain_id}: disabled domain inventories side effects")
        return DomainCompositionReport(
            domain_count=len(manifests),
            workflow_count=sum(len(manifest.workflows) for manifest in manifests),
            workpage_count=sum(len(manifest.workpages) for manifest in manifests),
            side_effect_count=sum(len(manifest.side_effects) for manifest in manifests),
            ready_domain_ids=self.ready_domain_ids,
            incubation_domain_ids=self.incubation_domain_ids,
            disabled_domain_ids=self.disabled_domain_ids,
            warnings=tuple(warnings),
            errors=(),
            activation_allowed=False,
        )


def _index_manifests(
    manifests: tuple[DomainManifest, ...],
) -> dict[str, DomainManifest]:
    indexed: dict[str, DomainManifest] = {}
    duplicates: set[str] = set()
    for manifest in manifests:
        if manifest.domain_id in indexed:
            duplicates.add(manifest.domain_id)
        indexed[manifest.domain_id] = manifest
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate domain manifests: {duplicate_list}")
    return indexed

