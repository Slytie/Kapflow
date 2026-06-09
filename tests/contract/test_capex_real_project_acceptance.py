from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REGISTER_DIR = ROOT / "docs/planning/capex_real_project_acceptance"
REGISTER_PATH = REGISTER_DIR / "SME_RP_ACCEPTANCE_REGISTER.yaml"
SIGN_OFF_PATH = REGISTER_DIR / "SME_RP_APPROVAL_WITH_CONDITIONS_SIGN_OFF.md"
SCOPE_CONTRACT_PATH = ROOT / "docs/architecture/CAPEX_SCOPE_HIERARCHY_CONTRACT.md"
TASK_DIR = ROOT / "codex/tasks"
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)


def _load_register() -> dict:
    return yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))


def _task_frontmatter(path: Path) -> dict:
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    assert match is not None, f"{path} is missing task frontmatter"
    return yaml.safe_load(match.group("body"))


def _task_file(task_id: str) -> Path:
    matches = sorted(TASK_DIR.glob(f"{task_id}-*.md"))
    assert len(matches) == 1, f"Expected exactly one task file for {task_id}"
    return matches[0]


def _assert_no_legacy_gate_prefix(paths: list[Path]) -> None:
    legacy_gate_prefix = "SME-K12" + "-G"
    offenders = [
        str(path.relative_to(ROOT))
        for path in paths
        if legacy_gate_prefix in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_sme_rp_register_uses_generalized_gate_namespace() -> None:
    register = _load_register()
    gate_ids = [gate["gate_id"] for gate in register["acceptance_gates"]]
    legacy_annex_dir = ROOT / "docs/planning" / ("capex_sme" + "_k12_annexes")

    assert REGISTER_DIR.exists()
    assert not legacy_annex_dir.exists()
    assert register["namespace"] == "SME-RP"
    assert gate_ids == [f"SME-RP-G{index:03d}" for index in range(1, 14)]
    assert register["source_provenance"]["source_namespace"] == "SME-K12"
    assert register["source_provenance"]["repo_namespace"] == "SME-RP"

    paths_to_scan = [
        *REGISTER_DIR.glob("*"),
        *TASK_DIR.glob("TASK-06*.md"),
        *(ROOT / "docs/planning/epics").glob("EPIC-1*.md"),
        *(ROOT / "codex/context").glob("EPIC-1*.md"),
        SCOPE_CONTRACT_PATH,
        ROOT / "docs/status/CURRENT_FOCUS.md",
        ROOT / "docs/status/DECISIONS_SINCE_LAST.md",
    ]
    _assert_no_legacy_gate_prefix(paths_to_scan)


def test_sme_rp_task_remap_is_complete_and_collision_free() -> None:
    register = _load_register()
    remap = register["task_remap"]
    repo_task_ids = [row["repo_task_id"] for row in remap]
    source_task_ids = [row["source_task_id"] for row in remap]

    assert repo_task_ids == [f"TASK-{index:04d}" for index in range(648, 665)]
    assert source_task_ids == [f"TASK-{index:04d}" for index in range(625, 642)]
    assert len(repo_task_ids) == len(set(repo_task_ids)) == 17
    assert len(source_task_ids) == len(set(source_task_ids)) == 17

    all_task_ids: dict[str, Path] = {}
    for path in TASK_DIR.glob("TASK-*.md"):
        frontmatter = _task_frontmatter(path)
        task_id = frontmatter["id"]
        assert task_id not in all_task_ids, (
            f"{task_id} appears in both {all_task_ids[task_id]} and {path}"
        )
        all_task_ids[task_id] = path

    for row in remap:
        path = _task_file(row["repo_task_id"])
        frontmatter = _task_frontmatter(path)
        text = path.read_text(encoding="utf-8")

        assert all_task_ids[row["repo_task_id"]] == path
        assert frontmatter["epic"] == row["target_epic"]
        assert f"Source task ID: `{row['source_task_id']}`" in text
        assert "Source namespace: `SME-K12`" in text
        assert "Repo namespace: `SME-RP`" in text
        for gate_ref in row["gate_refs"]:
            assert gate_ref in text


def test_k12_cases_are_fixture_case_ids_not_acceptance_namespace() -> None:
    register = _load_register()
    fixture_case_ids = [case["fixture_case_id"] for case in register["fixture_cases"]]
    gate_ids = [gate["gate_id"] for gate in register["acceptance_gates"]]
    annex_c_text = (
        REGISTER_DIR / "ANNEX_C_REAL_PROJECT_BINDING_ACCEPTANCE_CATALOGUE.md"
    ).read_text(encoding="utf-8")

    assert fixture_case_ids == [f"K12-T{index}" for index in range(1, 11)]
    assert not any(gate_id.startswith("K12") for gate_id in gate_ids)
    assert "Real-Project Binding Acceptance Catalogue" in annex_c_text
    assert "fixture-case IDs" in annex_c_text
    assert "top-level acceptance namespace" in annex_c_text


def test_target_epic_notes_reference_sme_rp_addendum_tasks() -> None:
    required_by_epic = {
        "EPIC-136": ["TASK-0648", "TASK-0664", "SME-RP real-project acceptance addendum"],
        "EPIC-140": ["TASK-0649", "TASK-0650", "SME-RP real-project acceptance addendum"],
        "EPIC-141": ["TASK-0652", "SME-RP real-project acceptance addendum"],
        "EPIC-142": ["TASK-0651", "TASK-0658", "TASK-0660"],
        "EPIC-143": ["TASK-0654", "TASK-0655", "TASK-0656", "TASK-0657"],
        "EPIC-144": ["TASK-0653", "Workpages may surface"],
        "EPIC-145": ["CAPEX real-project fixture governance", "New acceptance gates"],
        "EPIC-146": ["TASK-0661", "K12-T1..T10"],
        "EPIC-147": ["fixture tiers", "generalized SME-RP gates"],
        "EPIC-149": ["TASK-0662", "SME-RP-G013"],
        "EPIC-151": ["TASK-0659", "TASK-0663", "SME-RP-G011"],
    }

    for epic_id, required_snippets in required_by_epic.items():
        text = (ROOT / f"docs/planning/epics/{epic_id}.md").read_text(
            encoding="utf-8"
        )
        assert "SME-RP" in text
        for snippet in required_snippets:
            assert snippet in text


def test_approval_with_conditions_posture_is_closeout_grade() -> None:
    register = _load_register()
    posture = register["approval_posture"]
    sign_off_text = SIGN_OFF_PATH.read_text(encoding="utf-8")
    readme_text = (REGISTER_DIR / "README.md").read_text(encoding="utf-8")

    assert posture["gate_id"] == "SME-RP-G001"
    assert posture["approval_kind"] == "approval_with_conditions"
    assert posture["conditional"] is True
    assert posture["module_specific"] is True
    assert posture["non_activation"] is True
    assert posture["blocking_scope"] == "affected_module_only"
    assert posture["affected_module_only"] is True
    assert posture["wording_ref"] == (
        "docs/planning/capex_real_project_acceptance/"
        "SME_RP_APPROVAL_WITH_CONDITIONS_SIGN_OFF.md"
    )
    assert set(posture["cannot_be_used_for"]) >= {
        "implementation_approval",
        "capex_runtime_activation",
        "product_activation",
        "public_route_activation",
        "migration_approval",
        "raw_corpus_import",
    }

    normalized = re.sub(r"\s+", " ", sign_off_text)
    normalized_lower = normalized.lower()
    for required in (
        "SME-RP acceptance is conditional and module-specific",
        "not implementation approval",
        "not CAPEX runtime activation",
        "affected module only",
    ):
        assert required in normalized
    assert "non-activation" in normalized_lower
    assert "SME_RP_APPROVAL_WITH_CONDITIONS_SIGN_OFF.md" in readme_text


def test_capex_scope_hierarchy_contract_preserves_boundaries() -> None:
    text = SCOPE_CONTRACT_PATH.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", text)
    hierarchy = re.findall(r"^\d+\. `([^`]+)`$", text, flags=re.MULTILINE)

    assert hierarchy == [
        "project",
        "module_workstream",
        "package",
        "discipline",
        "source_occurrence",
        "artifact",
        "task",
        "approval",
        "flag",
        "external_binding",
    ]
    for required in (
        "Scope rows never cross tenant, domain, or project boundaries.",
        "Parent and child scope refs must stay inside the same `project_id`.",
        "`capex_projects.project_id` remains the durable project root.",
        "`workflow_run_id` is execution identity only; it is not project identity and is not scope identity.",
        "One closed scope cannot imply overall closure.",
    ):
        assert required in normalized
    assert "`K12-T1` is the motivating fixture case" in normalized
    assert "`K12-T1` is a fixture-case ID only" in normalized
    assert "not a product namespace, gate namespace, or runtime scope kind" in normalized
