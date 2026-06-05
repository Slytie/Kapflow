from __future__ import annotations

import ast
from pathlib import Path

import pytest

from onetruth.capex_platform.domain_runtime import (
    DomainManifest,
    DomainRuntimeRegistry,
    DomainWorkflowRef,
    DomainWorkpageRef,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAPEX_PLATFORM_DIR = REPO_ROOT / "src" / "onetruth" / "capex_platform"


def _manifest(
    domain_id: str,
    readiness: str,
    *,
    workflows: tuple[DomainWorkflowRef, ...] = (),
    workpages: tuple[DomainWorkpageRef, ...] = (),
) -> DomainManifest:
    return DomainManifest(
        schema_version="domain_manifest.v1",
        domain_id=domain_id,
        display_name=domain_id.title(),
        readiness=readiness,  # type: ignore[arg-type]
        workflows=workflows,
        workpages=workpages,
    )


def _workflow(workflow_id: str = "alpha.v1") -> DomainWorkflowRef:
    return DomainWorkflowRef(
        workflow_id=workflow_id,
        module_id=workflow_id.split(".")[0],
        pack_path=f"docs/workflows/{workflow_id}",
        partition_kind="PartitionID",
        family_status="first_slice",
        readiness="ready",
    )


def _workpage(kind: str = "alpha-v0") -> DomainWorkpageRef:
    return DomainWorkpageRef(
        kind=kind,
        workflow_id="alpha.v1",
        descriptor_pack_ref="example.alpha.DESCRIPTOR_PACK",
        action_pack_ref=None,
        run_enabled=True,
        artifact_enabled=True,
        submit_enabled=False,
    )


def test_empty_registry_composes_deterministically_with_activation_blocked() -> None:
    report = DomainRuntimeRegistry().compose()

    assert report.to_dict() == {
        "composition_report_version": "domain_runtime.composition_report.v1",
        "domain_count": 0,
        "workflow_count": 0,
        "workpage_count": 0,
        "side_effect_count": 0,
        "ready_domain_ids": [],
        "incubation_domain_ids": [],
        "disabled_domain_ids": [],
        "warnings": [],
        "errors": [],
        "activation_allowed": False,
    }


def test_duplicate_domain_ids_fail_closed() -> None:
    with pytest.raises(ValueError, match="duplicate domain manifests: logistics"):
        DomainRuntimeRegistry(
            (
                _manifest("logistics", "ready"),
                _manifest("logistics", "incubation"),
            )
        )


def test_ready_incubation_disabled_grouping_and_counts_are_deterministic() -> None:
    registry = DomainRuntimeRegistry(
        (
            _manifest("zeta", "disabled"),
            _manifest("alpha", "ready", workflows=(_workflow(),), workpages=(_workpage(),)),
            _manifest("beta", "incubation"),
        )
    )

    report = registry.compose()

    assert registry.domain_ids == ("alpha", "beta", "zeta")
    assert report.ready_domain_ids == ("alpha",)
    assert report.incubation_domain_ids == ("beta",)
    assert report.disabled_domain_ids == ("zeta",)
    assert report.domain_count == 3
    assert report.workflow_count == 1
    assert report.workpage_count == 1
    assert report.side_effect_count == 0
    assert report.activation_allowed is False


def test_capex_platform_domain_runtime_has_no_domain_or_logistics_imports() -> None:
    forbidden_prefixes = (
        "onetruth.domains",
        "onetruth.domain",
        "onetruth.application.services.logistics",
        "docs.domains",
    )
    violations: list[str] = []

    for path in sorted(CAPEX_PLATFORM_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden_prefixes):
                        violations.append(f"{path.relative_to(REPO_ROOT)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(forbidden_prefixes):
                    violations.append(f"{path.relative_to(REPO_ROOT)} imports {node.module}")

        text = path.read_text(encoding="utf-8")
        if "docs/domains/" in text or "logistics_" in text:
            violations.append(f"{path.relative_to(REPO_ROOT)} contains domain-specific string")

    assert violations == []
