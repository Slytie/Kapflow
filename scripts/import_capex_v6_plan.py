#!/usr/bin/env python3
"""Import the CAPEX v6 master planning package into repo-native backlog docs.

The importer is planning-only. It reads the external CAPEX v6 master ZIP,
generates task/epic/context docs plus conversion maps, and never extracts or
copies the raw K12/K3/blind project corpora into the repository.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK_START = 233
TASK_COUNT = 374
TASK_END = TASK_START + TASK_COUNT - 1
IMPORT_DATE = "2026-06-01"
EXPECTED_MASTER_SHA256 = (
    "ea06571a2e4667487cac3ee870dd91a5489b4ed52edbff2cd96e4c0473d54b95"
)
INITIAL_DONE_SOURCE_TASKS = {"MP-PR000", "MP-PR001"}
CAPEX_TASK_ROW = re.compile(r"^\| TASK-0(2[3-9]\d|[3-5]\d\d|60[0-6]) \| EPIC-1(3[6-9]|4\d|5[0-2]) \| ")
CAPEX_EPIC_ROW = re.compile(r"^\| EPIC-1(3[6-9]|4\d|5[0-2]) \| ")

V5_CARRY_FORWARD_RECONCILIATION: dict[str, tuple[str, ...]] = {
    "V5-TASK-001": ("TASK-0447", "TASK-0565", "TASK-0305"),
    "V5-TASK-002": ("TASK-0392", "TASK-0373"),
    "V5-TASK-003": ("TASK-0565",),
    "V5-TASK-004": ("TASK-0305", "TASK-0565"),
    "V5-TASK-005": ("TASK-0257", "TASK-0561"),
    "V5-TASK-006": ("TASK-0235", "TASK-0562"),
    "V5-TASK-007": ("TASK-0564", "TASK-0428"),
    "V5-TASK-008": ("TASK-0582",),
    "V5-TASK-009": ("TASK-0583", "TASK-0584"),
    "V5-TASK-010": ("TASK-0566",),
}

V5_GATE_TO_TASK: dict[str, str] = {
    "V5-GATE-001": "V5-TASK-005",
    "V5-GATE-002": "V5-TASK-006",
    "V5-GATE-003": "V5-TASK-001",
    "V5-GATE-004": "V5-TASK-002",
    "V5-GATE-005": "V5-TASK-003",
    "V5-GATE-006": "V5-TASK-004",
    "V5-GATE-007": "V5-TASK-007",
    "V5-GATE-008": "V5-TASK-008",
    "V5-GATE-009": "V5-TASK-009",
    "V5-GATE-010": "V5-TASK-010",
}

V5_RISK_RECONCILIATION: dict[str, tuple[str, ...]] = {
    "V5-RISK-001": ("TASK-0447", "TASK-0565", "TASK-0305"),
    "V5-RISK-002": ("TASK-0257", "TASK-0561"),
    "V5-RISK-003": ("TASK-0235", "TASK-0562"),
    "V5-RISK-004": ("TASK-0565",),
    "V5-RISK-005": ("TASK-0305", "TASK-0565"),
    "V5-RISK-006": ("TASK-0566",),
    "V5-RISK-007": ("TASK-0582", "TASK-0583", "TASK-0584"),
}

ASCII_TRANSLATION = str.maketrans(
    {
        0x2013: "-",
        0x2014: "-",
        0x2192: "->",
        0x2190: "<-",
        0x2264: "<=",
        0x2265: ">=",
        0x2260: "!=",
        0x201C: '"',
        0x201D: '"',
        0x2018: "'",
        0x2019: "'",
    }
)


@dataclass(frozen=True)
class EpicDefinition:
    epic_id: str
    title: str
    summary: str
    primary_artifacts: str
    depends_on: str


EPICS: tuple[EpicDefinition, ...] = (
    EpicDefinition(
        "EPIC-136",
        "CAPEX intake, provenance, and source freeze",
        "Own the v6 intake record, source-package provenance, task conversion, and source-freeze gates.",
        "CAPEX intake, conversion map, gate/risk/decision map",
        "EPIC-080",
    ),
    EpicDefinition(
        "EPIC-137",
        "CAPEX activation blockers and platform readiness",
        "Close P0 platform blockers before any CAPEX runtime activation claim.",
        "storage safety, transaction safety, invariant audit, readiness closeouts",
        "EPIC-136, EPIC-080, EPIC-100",
    ),
    EpicDefinition(
        "EPIC-138",
        "CAPEX production/lab separation and deploy readiness",
        "Keep CAPEX pilot, lab, and production-like activation behind explicit environment and restore gates.",
        "deploy gates, backup/restore evidence, branch rules",
        "EPIC-137, EPIC-100",
    ),
    EpicDefinition(
        "EPIC-139",
        "CAPEX domain-boundary cleanup",
        "Separate logistics-specific behavior from shared platform semantics before CAPEX surfaces are introduced.",
        "domain manifests, approval side-effect cleanup, workpage descriptor registry",
        "EPIC-137",
    ),
    EpicDefinition(
        "EPIC-140",
        "CAPEX project access and membership",
        "Define project anchors, membership, roles, and project-scoped APIs without crossing tenant/domain boundaries.",
        "project schema decisions, authorization helpers, project dashboard scope",
        "EPIC-137, EPIC-139",
    ),
    EpicDefinition(
        "EPIC-141",
        "CAPEX source occurrence and evidence",
        "Build the content identity, source occurrence, extraction, and evidence-binding foundations.",
        "source occurrence register, extraction state, evidence refs",
        "EPIC-140",
    ),
    EpicDefinition(
        "EPIC-142",
        "CAPEX artifact promotion and governance",
        "Constrain generated artifacts, pointer promotion, closure, stale reopen, and waiver behavior.",
        "artifact envelopes, promotion validators, closure and waiver models",
        "EPIC-141",
    ),
    EpicDefinition(
        "EPIC-143",
        "CAPEX workflow catalog",
        "Define CAPEX workflow slices for intake, baseline, lifecycle, commitments, assumptions, interfaces, snapshots, and risk.",
        "workflow contracts, operating models, acceptance matrices",
        "EPIC-140, EPIC-142",
    ),
    EpicDefinition(
        "EPIC-144",
        "CAPEX workpages and projections",
        "Plan CAPEX workpage projections, command envelopes, read APIs, and stale-command protections.",
        "workpage contracts, projections, projection consistency tests",
        "EPIC-142, EPIC-143",
    ),
    EpicDefinition(
        "EPIC-145",
        "CAPEX K12/K3 fixture governance",
        "Govern K12/K3 fixture roles, quarantine, redaction, expected outputs, and release checks without raw corpus commits.",
        "fixture manifests, redaction policy, K12/K3 expected outputs",
        "EPIC-141",
    ),
    EpicDefinition(
        "EPIC-146",
        "CAPEX three-project validation",
        "Use the three approved ZIP fixture roles for validation planning without importing raw corpora.",
        "three-project governance, validation protocol, fixture tiering",
        "EPIC-145",
    ),
    EpicDefinition(
        "EPIC-147",
        "CAPEX blind/lab evaluation",
        "Define blind validation and lab-eval protocols that prevent overfitting and preserve lab non-authority.",
        "blind baseline protocol, eval matrix, no-overfitting checkpoint",
        "EPIC-146, EPIC-110",
    ),
    EpicDefinition(
        "EPIC-148",
        "CAPEX off-repo full-corpus runs",
        "Plan capacity, restore, leak-scan, and full-corpus runbooks while keeping raw corpora off-repo.",
        "off-repo runbook, capacity and restore evidence, quarantine rules",
        "EPIC-145, EPIC-138",
    ),
    EpicDefinition(
        "EPIC-149",
        "CAPEX QA/TDD and semantic tests",
        "Define CAPEX invariant tests, fixture tests, eval harnesses, and CI markers.",
        "test catalog, semantic suites, TDD metrics",
        "EPIC-141, EPIC-142, EPIC-143, EPIC-144",
    ),
    EpicDefinition(
        "EPIC-150",
        "CAPEX release governance",
        "Add release, branch, review, migration, activation, and docs-authority governance for CAPEX work.",
        "branch manifests, release gates, code review policy",
        "EPIC-137, EPIC-149",
    ),
    EpicDefinition(
        "EPIC-151",
        "CAPEX transparency and snapshots",
        "Define executive snapshots, risk signals, external bindings, freshness, and audit export contracts.",
        "snapshot schemas, risk signal contracts, external observation queues",
        "EPIC-142, EPIC-144",
    ),
    EpicDefinition(
        "EPIC-152",
        "CAPEX production preflight",
        "Verify P0 blockers, three-project evidence, raw-data quarantine, restore, release, and go/no-go readiness.",
        "production preflight memo, gate evidence, go/no-go record",
        "EPIC-137, EPIC-146, EPIC-148, EPIC-150",
    ),
)


def to_ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.translate(ASCII_TRANSLATION))
    return normalized.encode("ascii", "ignore").decode("ascii")


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", to_ascii(str(value))).strip()


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_zip_member(zip_file: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in zip_file.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {suffix} in master ZIP, found {len(matches)}")
    return matches[0]


def read_master_csv(master_zip: Path, suffix: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(master_zip) as archive:
        name = find_zip_member(archive, suffix)
        text = archive.read(name).decode("utf-8-sig")
    return [
        {key: clean_text(value) for key, value in row.items()}
        for row in csv.DictReader(text.splitlines())
    ]


def package_stats(zip_path: Path) -> dict[str, object]:
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
    extensions = Counter()
    for info in infos:
        if info.is_dir():
            continue
        extensions[Path(info.filename).suffix.lower() or "<none>"] += 1
    return {
        "basename": to_ascii(zip_path.name),
        "sha256": sha256_file(zip_path),
        "entries": len(infos),
        "files": sum(1 for info in infos if not info.is_dir()),
        "size_bytes": zip_path.stat().st_size,
        "uncompressed_bytes": sum(info.file_size for info in infos),
        "top_extensions": dict(extensions.most_common(8)),
    }


def assign_epic(row: dict[str, str]) -> str:
    source_id = row["task_id"]
    area = row["area"].lower()
    if source_id.startswith("PP-TASK") or "production-preflight" in area:
        return "EPIC-152"
    if source_id in {"TP-TASK-001", "TP-TASK-002", "TP-TASK-003", "TP-TASK-009"}:
        return "EPIC-146"
    if source_id == "TP-TASK-007":
        return "EPIC-148"
    if source_id.startswith("TP-TASK"):
        return "EPIC-147"
    if source_id.startswith("SD-TASK") or source_id in {"MP-PR000", "V5-TASK-008", "V5-TASK-009"}:
        return "EPIC-136"
    if source_id.startswith("MP-PR"):
        number = int(re.search(r"(\d+)$", source_id).group(1))  # type: ignore[union-attr]
        if 1 <= number <= 7:
            return "EPIC-137"
        if 8 <= number <= 11 or 21 <= number <= 23:
            return "EPIC-138"
        if 12 <= number <= 20:
            return "EPIC-139"
    if source_id.startswith("DEPLOY") or source_id.startswith("SAFE-C"):
        return "EPIC-138"
    if source_id.startswith("SAFE-D") or source_id in {"INGEST-010", "TEST-003"}:
        return "EPIC-148"
    if source_id == "NU-CB-P0-001":
        return "EPIC-139"
    if source_id in {"NU-CB-P0-002", "V5-TASK-006"}:
        return "EPIC-137"
    if source_id.startswith("CLEAN") or source_id in {"RF-001", "RF-002", "V5-TASK-005"}:
        return "EPIC-139"
    if source_id.startswith("PROJ") or source_id.startswith("ARCH-W1") or source_id in {"NU-CB-P0-003", "RF-003"}:
        return "EPIC-140"
    if source_id.startswith("INGEST") or source_id.startswith("ARCH-W2") or source_id.startswith("ARCH-W3") or source_id in {"NU-CB-P0-004", "V5-TASK-007", "RF-004", "RF-005", "RF-006"}:
        return "EPIC-141"
    if source_id in {"ART-002", "WFLOW-008", "NU-CB-P1-009"} or source_id.startswith("ARCH-W8"):
        return "EPIC-151"
    if source_id == "ART-007":
        return "EPIC-144"
    if source_id.startswith("ART") or source_id.startswith("ARCH-W4") or source_id in {"NU-CB-P0-005", "NU-CB-P1-010", "RF-007", "RF-008", "V5-TASK-001", "V5-TASK-002", "V5-TASK-004"}:
        return "EPIC-142"
    if source_id.startswith("WFLOW") or source_id in {"NU-CB-P0-006", "NU-CB-P1-011", "V5-TASK-003", "V5-TASK-010"}:
        return "EPIC-143"
    if source_id.startswith("WP") or source_id.startswith("ARCH-W5") or source_id in {"NU-CB-P0-007", "RF-009"}:
        return "EPIC-144"
    if source_id.startswith("K12") or source_id.startswith("SPB2") or source_id.startswith("ARCH-W6") or source_id.startswith("SAFE-B") or source_id in {"SAFE-001", "RF-010"}:
        return "EPIC-145"
    if source_id.startswith("ARCH-W75") or source_id.startswith("TEST") or source_id.startswith("QD") or source_id == "NU-CB-P0-008":
        return "EPIC-149"
    if source_id.startswith("ARCH-W7") or source_id.startswith("DOC") or source_id in {"RF-011", "RF-012", "SAFE-002"}:
        return "EPIC-150"
    if "snapshot" in area or "external" in area:
        return "EPIC-151"
    return "EPIC-136"


def owner_reviewers(row: dict[str, str]) -> tuple[list[str], list[str]]:
    area = row["area"].lower()
    if "frontend" in area or "workpage" in area:
        return ["frontend"], ["platform", "qa"]
    if "security" in area or "governance" in area:
        return ["platform", "security"], ["architect", "qa"]
    if "docs" in area or "documentation" in area or "process" in area:
        return ["architect"], ["platform", "qa"]
    if "testing" in area or "quality" in area or "tdd" in area:
        return ["qa"], ["platform", "architect"]
    if "production" in area or "deployment" in area or "ops" in area or "capacity" in area:
        return ["platform", "sre"], ["security", "qa"]
    return ["platform"], ["architect", "qa"]


def task_risk(row: dict[str, str]) -> str:
    if "P0" in row["priority"]:
        return "high"
    area = row["area"].lower()
    if "security" in area or "approval" in area or "pointer" in area:
        return "high"
    return "medium"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", clean_text(value).lower()).strip("-")
    return (slug or "task")[:96].rstrip("-")


def expand_range_token(token: str, known_ids: set[str]) -> list[str]:
    if ".." not in token:
        return []
    start, end = token.split("..", 1)
    start_match = re.match(r"^(.*?)(\d+)$", start.strip())
    end_match = re.match(r"^(.*?)(\d+)$", end.strip())
    if not start_match or not end_match:
        return []
    prefix, start_number = start_match.groups()
    end_prefix, end_number = end_match.groups()
    if end_prefix and end_prefix != prefix and not prefix.endswith(end_prefix):
        return []
    width = max(len(start_number), len(end_number))
    return [
        candidate
        for candidate in (
            f"{prefix}{number:0{width}d}"
            for number in range(int(start_number), int(end_number) + 1)
        )
        if candidate in known_ids
    ]


def converted_dependencies(depends_on: str, source_to_task: dict[str, str]) -> tuple[list[str], str]:
    text = depends_on.strip()
    if not text or text.lower() in {"none", "n/a", "na"}:
        return [], ""
    known_ids = set(source_to_task)
    found: set[str] = set()
    matched: list[str] = []
    for shorthand in re.finditer(r"\bPR(\d{3})(?:\.\.|-)(?:PR)?(\d{3})\b", text):
        for number in range(int(shorthand.group(1)), int(shorthand.group(2)) + 1):
            source_id = f"MP-PR{number:03d}"
            if source_id in source_to_task:
                found.add(source_id)
        matched.append(shorthand.group(0))
    for range_token in re.findall(r"[A-Z0-9][A-Z0-9_-]*\d+\.\.[A-Z0-9_-]*\d+", text):
        expanded = expand_range_token(range_token, known_ids)
        if expanded:
            found.update(expanded)
            matched.append(range_token)
    normalized = re.sub(r"[^A-Za-z0-9_-]+", " ", text)
    for token in normalized.split():
        if token in source_to_task:
            found.add(token)
            matched.append(token)
        elif re.fullmatch(r"PR\d{3}", token):
            source_id = f"MP-{token}"
            if source_id in source_to_task:
                found.add(source_id)
                matched.append(token)
    converted = sorted(
        (source_to_task[source_id] for source_id in found),
        key=lambda task_id: int(task_id.split("-")[1]),
    )
    unresolved = text
    for fragment in sorted(set(matched), key=len, reverse=True):
        unresolved = unresolved.replace(fragment, "").strip()
    for source_id in sorted(found, key=len, reverse=True):
        unresolved = unresolved.replace(source_id, "").strip()
    unresolved = re.sub(r"\s+", " ", unresolved).strip(" ;,.")
    return converted, unresolved


def build_task_records(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    if len(rows) != TASK_COUNT:
        raise RuntimeError(f"expected {TASK_COUNT} source task rows, found {len(rows)}")
    source_to_task = {
        row["task_id"]: f"TASK-{TASK_START + index:04d}"
        for index, row in enumerate(rows)
    }
    records: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        repo_task_id = f"TASK-{TASK_START + index:04d}"
        epic_id = assign_epic(row)
        depends, unresolved = converted_dependencies(row["depends_on"], source_to_task)
        owners, reviewers = owner_reviewers(row)
        records.append(
            {
                "source": row,
                "repo_task_id": repo_task_id,
                "epic_id": epic_id,
                "depends_on": depends,
                "unresolved_depends_on": unresolved,
                "owners": owners,
                "reviewers": reviewers,
                "risk": task_risk(row),
                "filename": f"{repo_task_id}-{slugify(row['title'])}.md",
            }
        )
    return records


def task_status(source_id: str) -> str:
    if (
        source_id in INITIAL_DONE_SOURCE_TASKS
        or source_id in V5_CARRY_FORWARD_RECONCILIATION
    ):
        return "DONE"
    return "TODO"


def source_lineage(source_id: str) -> str:
    if source_id in V5_CARRY_FORWARD_RECONCILIATION:
        return "v5_carried_forward"
    return "capex_v6"


def active_disposition(source_id: str) -> str:
    if source_id in V5_CARRY_FORWARD_RECONCILIATION:
        return "historical_alias"
    return "active_task"


def canonical_task_refs(source_id: str) -> tuple[str, ...]:
    return V5_CARRY_FORWARD_RECONCILIATION.get(source_id, ())


def source_metadata_frontmatter(source_id: str) -> str:
    refs = canonical_task_refs(source_id)
    if not refs:
        return ""
    return (
        f"source_lineage: {source_lineage(source_id)}\n"
        f"active_disposition: {active_disposition(source_id)}\n"
        f"canonical_task_refs: {json.dumps(list(refs))}\n"
    )


def record_metadata(source_id: str) -> dict[str, str]:
    canonical_refs: tuple[str, ...] = ()
    if source_id in V5_GATE_TO_TASK:
        canonical_refs = canonical_task_refs(V5_GATE_TO_TASK[source_id])
    elif source_id in V5_RISK_RECONCILIATION:
        canonical_refs = V5_RISK_RECONCILIATION[source_id]

    is_v5_reference = source_id.startswith("V5-")
    return {
        "source_lineage": "v5_carried_forward" if is_v5_reference else "capex_v6",
        "active_disposition": "historical_reference" if is_v5_reference else "reference",
        "canonical_task_refs": ";".join(canonical_refs),
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_ascii(text), encoding="utf-8")


def parse_frontmatter_fields(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def task_body(record: dict[str, object]) -> str:
    row = record["source"]  # type: ignore[assignment]
    assert isinstance(row, dict)
    task_id = str(record["repo_task_id"])
    epic_id = str(record["epic_id"])
    source_task_id = row["task_id"]
    status = task_status(source_task_id)
    context_pack = f"codex/context/{epic_id}.md"
    source_metadata = source_metadata_frontmatter(source_task_id)
    dependency_note = ""
    if record["unresolved_depends_on"]:
        dependency_note = f"- Source-only dependency notes: `{record['unresolved_depends_on']}`\n"
    closeout = ""
    if row["task_id"] == "MP-PR000":
        closeout = """
## Completion evidence
- CAPEX v6 intake, conversion map, gate/risk/decision map, epics, context packs, and task files were imported as planning-only repo artifacts.
- Current-code blocker mappings were recorded in the intake document.
- No runtime/API/schema/DB/workpage or activation behavior changed for this task.
"""
    elif row["task_id"] == "MP-PR001":
        closeout = """
## Completion evidence
- Release/source-bundle hygiene now excludes `node_modules/` paths repo-wide.
- Cloud Build PR validation skeleton was added as a no-secret, no-deploy validation lane.
- Tracked `node_modules` residue was removed from repo truth before this task was closed.
"""
    elif source_task_id in V5_CARRY_FORWARD_RECONCILIATION:
        refs = ", ".join(f"`{ref}`" for ref in canonical_task_refs(source_task_id))
        closeout = f"""
## Reconciliation closeout evidence
- This source row is carried forward from v5 inside the CAPEX v6 package and is closed as a historical alias, not as independent active backlog.
- Canonical active work remains on {refs}; this closeout does not mark those target tasks complete unless their own task files record completion.
- CAPEX v6 remains the active planning baseline; v5 and earlier packages remain superseded history.
"""
    return f"""---
id: {task_id}
epic: {epic_id}
title: {yaml_quote(row["title"])}
status: {status}
{source_metadata}owners: {json.dumps(record["owners"])}
reviewers: {json.dumps(record["reviewers"])}
depends_on: {json.dumps(record["depends_on"])}
risk: {record["risk"]}
context_packs:
  - {yaml_quote(context_pack)}
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `{row["task_id"]}` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
{row["scope"] or "Carry out the source task scope recorded in the CAPEX v6 conversion map."}

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/{epic_id}.md`
- `{context_pack}`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: {row["required_tests"] or "none specified in v6 source row"}
- Acceptance gate: `{row["acceptance_gate"] or "none"}`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: {row["primary_outputs"] or row["acceptance_gate"] or "task source scope completed"}
- Review focus covered: {row["code_review_focus"] or "normal code/document review"}
- Refactor focus covered: {row["refactor_focus"] or "none specified"}
- Docs requirement covered: {row["docs_required"] or "none specified"}
- Rollback/recovery posture recorded: {row["rollback_or_recovery"] or "documented if production-facing"}

## Source row mapping
- Source task ID: `{row["task_id"]}`
- Source phase: `{row["phase"] or "not specified"}`
- Source priority: `{row["priority"] or "not specified"}`
- Source area: `{row["area"] or "not specified"}`
- Original depends_on: `{row["depends_on"] or "none"}`
{dependency_note}- Recommended source branch: `{row["recommended_branch"] or "not specified"}`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
{closeout}"""


def conversion_rows(records: list[dict[str, object]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        row = record["source"]
        assert isinstance(row, dict)
        rows.append(
            {
                "source_task_id": row["task_id"],
                "repo_task_id": str(record["repo_task_id"]),
                "epic_id": str(record["epic_id"]),
                "status": task_status(row["task_id"]),
                "source_priority": row["priority"],
                "source_phase": row["phase"],
                "source_area": row["area"],
                "original_depends_on": row["depends_on"],
                "converted_depends_on": ";".join(record["depends_on"]),  # type: ignore[arg-type]
                "unresolved_dependency_notes": str(record["unresolved_depends_on"]),
                "acceptance_gate": row["acceptance_gate"],
                "source_title": row["title"],
                "source_lineage": source_lineage(row["task_id"]),
                "active_disposition": active_disposition(row["task_id"]),
                "canonical_task_refs": ";".join(canonical_task_refs(row["task_id"])),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def gate_risk_decision_rows(
    gates: list[dict[str, str]],
    risks: list[dict[str, str]],
    decisions: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for gate in gates:
        rows.append(
            {
                "record_type": "gate",
                "source_id": gate.get("gate_id", ""),
                "name": gate.get("gate_name", ""),
                "category": gate.get("category", ""),
                "phase": gate.get("phase", ""),
                "depends_on": gate.get("depends_on", ""),
                "status_or_priority": gate.get("priority", ""),
                "summary": gate.get("pass_condition", ""),
                "evidence_or_owner": gate.get("required_evidence", ""),
                **record_metadata(gate.get("gate_id", "")),
            }
        )
    for risk in risks:
        rows.append(
            {
                "record_type": "risk",
                "source_id": risk.get("risk_id", ""),
                "name": risk.get("risk_title", risk.get("title", "")),
                "category": risk.get("category", risk.get("area", "")),
                "phase": risk.get("phase", ""),
                "depends_on": risk.get("related_gate_or_task", risk.get("depends_on", "")),
                "status_or_priority": risk.get("severity", risk.get("priority", "")),
                "summary": risk.get("risk_statement", risk.get("description", "")),
                "evidence_or_owner": risk.get("mitigation", risk.get("owner", "")),
                **record_metadata(risk.get("risk_id", "")),
            }
        )
    for decision in decisions:
        rows.append(
            {
                "record_type": "decision",
                "source_id": decision.get("decision_id", ""),
                "name": decision.get("decision_title", decision.get("title", "")),
                "category": decision.get("category", decision.get("area", "")),
                "phase": decision.get("phase", ""),
                "depends_on": decision.get("depends_on", ""),
                "status_or_priority": decision.get("status", decision.get("priority", "")),
                "summary": decision.get("question", decision.get("summary", "")),
                "evidence_or_owner": decision.get("owner", decision.get("needed_by", "")),
                **record_metadata(decision.get("decision_id", "")),
            }
        )
    return rows


def format_exts(stats: dict[str, object]) -> str:
    return ", ".join(f"{key}:{value}" for key, value in stats["top_extensions"].items())  # type: ignore[union-attr]


def intake_doc(
    master_stats: dict[str, object],
    task_rows: list[dict[str, str]],
    gate_rows: list[dict[str, str]],
    risk_rows: list[dict[str, str]],
    decision_rows: list[dict[str, str]],
    project_stats: list[tuple[str, dict[str, object]]],
) -> str:
    project_lines = [
        f"| {label} | `{stats['basename']}` | `{stats['sha256']}` | {stats['entries']} | {stats['files']} | {stats['size_bytes']} | {stats['uncompressed_bytes']} | {format_exts(stats)} |"
        for label, stats in project_stats
    ]
    return f"""# CAPEX Master v6 Intake

## Source package
- Active package: `CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip`
- SHA256: `{master_stats["sha256"]}`
- Entries/files: {master_stats["entries"]} entries / {master_stats["files"]} files
- Uncompressed bytes: {master_stats["uncompressed_bytes"]}
- Top extensions: {format_exts(master_stats)}
- Source-package role: active CAPEX planning baseline; v5 and earlier packages are superseded history.
- Runtime/API/schema/DB/workpage changes in this import: none.

## Imported planning counts
| Source table | Imported count | Repo handling |
|---|---:|---|
| MASTER_Task_Backlog.csv | {len(task_rows)} | `TASK-0233` through `TASK-0606` |
| MASTER_Acceptance_Gates.csv | {len(gate_rows)} | reference map only |
| MASTER_Risk_Register.csv | {len(risk_rows)} | reference map only |
| MASTER_Open_Decisions_Register.csv | {len(decision_rows)} | reference map only |

## v5 carry-forward reconciliation
- CAPEX v6 is the active planning baseline; v5 and earlier source packages remain superseded history.
- `V5-TASK-*` rows embedded in the v6 task table are preserved as source-provenance rows only, not active backlog.
- Reconciled v5 rows are marked `DONE` with `source_lineage=v5_carried_forward`, `active_disposition=historical_alias`, and `canonical_task_refs` pointing at the v6/native task refs that own the remaining work.
- `V5-GATE-*`, `V5-RISK-*`, and `V5-OD-*` entries in the gate/risk/decision map are marked `historical_reference`.

## Raw-data boundary
- Raw K12, K3, and blind-validation corpora are not committed to the repo.
- Approved repo records are ZIP basenames, hashes, aggregate counts, fixture-role labels, quarantine policy, and derived planning tasks.
- Do not commit extracted documents, screenshots, raw filenames from inside project archives, embedded text, or OCR/search output from the raw corpora.

## Three project ZIP provenance
| Fixture role | ZIP basename | SHA256 | Entries | Files | Size bytes | Uncompressed bytes | Top extensions |
|---|---|---|---:|---:|---:|---:|---|
{chr(10).join(project_lines) if project_lines else "| Not supplied | n/a | n/a | 0 | 0 | 0 | 0 | n/a |"}

## TASK-0233 closeout evidence
- Imported CAPEX v6 planning source row count: {len(task_rows)} tasks, {len(gate_rows)} gates, {len(risk_rows)} risks, {len(decision_rows)} open decisions.
- Current-code blocker mappings recorded for approval domain coupling, artifact auth-before-read, CAPEX project access, and source occurrence/evidence.
- Verification basis: CAPEX conversion check, repo validation, schema validation, focused planning/import checks, and `git diff --check`.

## TASK-0234 closeout evidence
- Release/source-bundle hygiene excludes `node_modules/` directories repo-wide.
- Cloud Build PR validation skeleton is no-secret/no-deploy by contract.
- Tracked `node_modules` residue is removed from repo truth.

## Current-code blocker mappings
| Blocker | CAPEX task refs | Current repo surface |
|---|---|---|
| Approval response domain coupling | `TASK-0257`, `TASK-0561` | `src/onetruth/application/handlers/approvals.py` |
| Artifact auth-before-read and storage confinement | `TASK-0235`, `TASK-0562` | `src/onetruth/api/routes/artifacts.py`, `src/onetruth/application/handlers/artifacts.py`, `src/onetruth/infrastructure/artifacts/storage.py` |
| Transaction composition safety | `TASK-0236` | `src/onetruth/application/handlers/schedule_control.py`, `src/onetruth/application/handlers/logistics_handoff.py` |
| CAPEX project membership runtime | `TASK-0261`..`TASK-0263`, `TASK-0385`, `TASK-0386`, `TASK-0563` | future CAPEX project scope runtime |
| Source occurrence / SourceRef | `TASK-0268`, `TASK-0391`, `TASK-0407`, `TASK-0428`, `TASK-0564` | future source occurrence and evidence resolver |

## Verification commands
- `python3 scripts/import_capex_v6_plan.py check --master-zip <CAPEX_v6_master_zip>`
- `python3 scripts/validate_repo.py`
- `make schema-validate`
- `git diff --check`
"""


def epic_doc(epic: EpicDefinition, records: list[dict[str, object]]) -> str:
    active_records = [
        record
        for record in records
        if str(record["source"]["task_id"]) not in V5_CARRY_FORWARD_RECONCILIATION  # type: ignore[index]
    ]
    historical_records = [
        record
        for record in records
        if str(record["source"]["task_id"]) in V5_CARRY_FORWARD_RECONCILIATION  # type: ignore[index]
    ]
    task_lines = [
        f"- `{record['repo_task_id']}` (`{record['source']['task_id']}`) - {record['source']['title']}"  # type: ignore[index]
        for record in active_records
    ]
    historical_lines = [
        f"- `{record['repo_task_id']}` (`{record['source']['task_id']}`) -> {', '.join(canonical_task_refs(str(record['source']['task_id'])))} - {record['source']['title']}"  # type: ignore[index]
        for record in historical_records
    ]
    families = Counter(str(record["source"]["task_id"]).split("-")[0] for record in records)  # type: ignore[index]
    family_text = ", ".join(f"{key}:{value}" for key, value in sorted(families.items()))
    return f"""# {epic.epic_id} - {epic.title}

## Summary
{epic.summary}

This epic was imported from CAPEX v6 on `{IMPORT_DATE}` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog unless an individual task records completed repo evidence.

## In scope
- Source task families/counts: {family_text or "none"}.
- Preserve CAPEX v6 source-row intent while translating work into repo-native tasks and context packs.
- Keep official claims inside the canonical workflow/task/approval/event/artifact/pointer substrate.

## Out of scope
- Raw K12, K3, or blind-validation corpus commits.
- Direct production activation or live truth mutation from this planning import.
- Treating generated material, agent output, or Workflow Lab evidence as source authority.

## Dependencies
- {epic.depends_on}

Context pack:
- `codex/context/{epic.epic_id}.md`

## Source references
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`

## Task stack
{chr(10).join(task_lines)}

## Historical/reconciled aliases
{chr(10).join(historical_lines) if historical_lines else "- None."}

## Acceptance criteria
- Every listed task preserves its v6 source row, acceptance gate, dependency notes, and raw-data boundary.
- Implementation tasks update authoritative repo source before generated derivatives.
- CAPEX remains gated until the relevant acceptance gates and production-preflight evidence are closed or explicitly waived.
"""


def context_doc(epic: EpicDefinition, records: list[dict[str, object]]) -> str:
    source_ids = [str(record["source"]["task_id"]) for record in records]  # type: ignore[index]
    source_ranges = ", ".join(source_ids[:8])
    if len(source_ids) > 8:
        source_ranges += f", ... ({len(source_ids)} tasks total)"
    historical_rows = [
        f"- `{record['source']['task_id']}` is a reconciled v5 historical alias for {', '.join(canonical_task_refs(str(record['source']['task_id'])))}."  # type: ignore[index]
        for record in records
        if str(record["source"]["task_id"]) in V5_CARRY_FORWARD_RECONCILIATION  # type: ignore[index]
    ]
    return f"""# {epic.epic_id} Context Pack - {epic.title}

Purpose:
- Rehydrate the CAPEX v6 task tranche for `{epic.epic_id}` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
{source_ranges or "No source rows assigned."}

## Historical/reconciled aliases
{chr(10).join(historical_rows) if historical_rows else "- None."}

## Load first
- `docs/planning/epics/{epic.epic_id}.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## Non-negotiable invariants
- One truth system: official claims come only from immutable objects, append-only events, and audited pointers.
- Tenant, domain, and future CAPEX project boundaries must not be crossed in reads, writes, exports, projections, or generated material.
- Raw K12/K3/blind corpus files stay off-repo; only sanitized fixtures, manifests, hashes, and aggregate evidence may be committed.
- Generated artifacts, Workflow Lab reports, and AI output are not source authority.
- Production/lab activation is release-mediated and remains blocked until the relevant gates close or receive explicit waivers.

## Preferred implementation posture
- Start with the source task's required tests or evidence.
- Update repo-native authoritative source before downstream generated artifacts.
- Keep implementation PRs small enough to review against the source row and acceptance gate.
- Preserve logistics weekly/live current focus unless a CAPEX task explicitly changes shared semantics.

## Stop line
- Do not import raw project corpus content.
- Do not activate CAPEX runtime/product behavior merely because a planning task exists.
"""


def rewrite_task_index(records: list[dict[str, object]]) -> None:
    path = ROOT / "docs/planning/TASK_INDEX.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not CAPEX_TASK_ROW.match(line)]
    rows = []
    for record in records:
        row = record["source"]
        assert isinstance(row, dict)
        rows.append(
            f"| {record['repo_task_id']} | {record['epic_id']} | {task_status(row['task_id'])} | {record['risk']} | {row['title']} |"
        )
    if kept and kept[-1] != "":
        kept.append("")
    kept.extend(rows)
    write_text(path, "\n".join(kept) + "\n")


def rewrite_epics_index() -> None:
    path = ROOT / "docs/planning/EPICS.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not CAPEX_EPIC_ROW.match(line)]
    insert_at = next((index for index, line in enumerate(kept) if line == "## Update rules"), len(kept))
    rows = [
        f"| {epic.epic_id} | {epic.title} | {epic.primary_artifacts} | {epic.depends_on} |"
        for epic in EPICS
    ]
    if insert_at > 0 and kept[insert_at - 1] != "":
        rows = [""] + rows
    kept[insert_at:insert_at] = rows
    write_text(path, "\n".join(kept) + "\n")


def append_once(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    suffix = "" if text.endswith("\n") else "\n"
    write_text(path, text + suffix + "\n" + block.strip() + "\n")


def generate(args: argparse.Namespace) -> int:
    master_zip = Path(args.master_zip).expanduser().resolve()
    task_rows = read_master_csv(master_zip, "MASTER_Task_Backlog.csv")
    gate_rows = read_master_csv(master_zip, "MASTER_Acceptance_Gates.csv")
    risk_rows = read_master_csv(master_zip, "MASTER_Risk_Register.csv")
    decision_rows = read_master_csv(master_zip, "MASTER_Open_Decisions_Register.csv")
    records = build_task_records(task_rows)
    master_stats = package_stats(master_zip)
    if master_stats["sha256"] != EXPECTED_MASTER_SHA256:
        raise RuntimeError("master ZIP SHA256 does not match the expected v6 package")

    project_stats: list[tuple[str, dict[str, object]]] = []
    for label, raw_path in (
        ("K12 primary MVP fixture candidate", args.k12_zip),
        ("K3 shadow/regression fixture candidate", args.k3_zip),
        ("Blind/third-validation holdout candidate", args.blind_zip),
    ):
        if raw_path:
            project_stats.append((label, package_stats(Path(raw_path).expanduser().resolve())))

    write_text(
        ROOT / "docs/planning/CAPEX_MASTER_V6_INTAKE.md",
        intake_doc(master_stats, task_rows, gate_rows, risk_rows, decision_rows, project_stats),
    )
    write_csv(ROOT / "docs/planning/CAPEX_V6_CONVERSION_MAP.csv", conversion_rows(records))
    write_csv(
        ROOT / "docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv",
        gate_risk_decision_rows(gate_rows, risk_rows, decision_rows),
    )
    for epic in EPICS:
        epic_records = [record for record in records if record["epic_id"] == epic.epic_id]
        write_text(ROOT / f"docs/planning/epics/{epic.epic_id}.md", epic_doc(epic, epic_records))
        write_text(ROOT / f"codex/context/{epic.epic_id}.md", context_doc(epic, epic_records))
    for record in records:
        write_text(ROOT / f"codex/tasks/{record['filename']}", task_body(record))

    rewrite_task_index(records)
    rewrite_epics_index()
    append_once(
        ROOT / "docs/status/CURRENT_FOCUS.md",
        "CAPEX v6 imported planning backlog",
        """
## CAPEX v6 imported planning backlog
- CAPEX v6 is imported as gated planning backlog only: `TASK-0233` through `TASK-0606`, with `TASK-0233` and `TASK-0234` completed as prerequisite planning/platform hygiene.
- CAPEX runtime activation remains blocked until imported P0, three-project, data-governance, capacity/restore, release, and production-preflight gates close or receive explicit waivers.
- Logistics weekly/live/workpages remain the current implementation focus unless a CAPEX task explicitly changes shared platform semantics.
""",
    )
    append_once(
        ROOT / "docs/status/DECISIONS_SINCE_LAST.md",
        "CAPEX v6 planning import",
        """
## 2026-06-01 (CAPEX v6 planning import)
- Source decision: `CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip` is the active CAPEX planning baseline; v5 and earlier packages are superseded history.
- Boundary decision: raw K12/K3/blind project corpora remain off-repo; only ZIP basenames, hashes, aggregate counts, fixture-role labels, and repo-native planning artifacts may be committed.
- Activation decision: imported CAPEX tasks do not activate runtime behavior until the relevant gates close or are explicitly waived.
""",
    )
    print(f"Imported CAPEX v6 planning backlog: {len(records)} tasks, {len(EPICS)} epics")
    return 0


def check(args: argparse.Namespace) -> int:
    errors: list[str] = []
    conversion_path = ROOT / "docs/planning/CAPEX_V6_CONVERSION_MAP.csv"
    gate_map_path = ROOT / "docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv"
    intake_path = ROOT / "docs/planning/CAPEX_MASTER_V6_INTAKE.md"
    if not conversion_path.exists():
        errors.append("missing CAPEX_V6_CONVERSION_MAP.csv")
        rows: list[dict[str, str]] = []
    else:
        rows = list(csv.DictReader(conversion_path.read_text(encoding="utf-8").splitlines()))

    if len(rows) != TASK_COUNT:
        errors.append(f"expected {TASK_COUNT} conversion rows, found {len(rows)}")
    expected_ids = [f"TASK-{number:04d}" for number in range(TASK_START, TASK_END + 1)]
    actual_ids = [row.get("repo_task_id", "") for row in rows]
    if actual_ids != expected_ids:
        errors.append("conversion map repo task IDs are not contiguous TASK-0233..TASK-0606")
    if len(set(row.get("source_task_id", "") for row in rows)) != len(rows):
        errors.append("conversion map contains duplicate source task IDs")
    if len(set(actual_ids)) != len(actual_ids):
        errors.append("conversion map contains duplicate repo task IDs")

    task_index = (ROOT / "docs/planning/TASK_INDEX.md").read_text(encoding="utf-8")
    epics_index = (ROOT / "docs/planning/EPICS.md").read_text(encoding="utf-8")
    for row in rows:
        task_id = row.get("repo_task_id", "")
        epic_id = row.get("epic_id", "")
        source_id = row.get("source_task_id", "")
        status = row.get("status", "")
        if status not in {"TODO", "DONE", "BLOCKED"}:
            errors.append(f"conversion map has invalid status for {task_id}: {status}")
            continue
        if source_id in V5_CARRY_FORWARD_RECONCILIATION:
            expected_refs = ";".join(canonical_task_refs(source_id))
            if status != "DONE":
                errors.append(f"{source_id} must be DONE as a reconciled historical alias")
            if row.get("source_lineage") != "v5_carried_forward":
                errors.append(f"{source_id} missing v5_carried_forward lineage")
            if row.get("active_disposition") != "historical_alias":
                errors.append(f"{source_id} missing historical_alias disposition")
            if row.get("canonical_task_refs") != expected_refs:
                errors.append(f"{source_id} canonical task refs mismatch")
        matches = list((ROOT / "codex/tasks").glob(f"{task_id}-*.md"))
        if len(matches) != 1:
            errors.append(f"expected one task file for {task_id}, found {len(matches)}")
            continue
        frontmatter = parse_frontmatter_fields(matches[0].read_text(encoding="utf-8"))
        if frontmatter.get("id") != task_id:
            errors.append(f"task file {matches[0]} missing id front matter")
        if frontmatter.get("epic") != epic_id:
            errors.append(f"task file {matches[0]} missing epic front matter")
        if frontmatter.get("status") != status:
            errors.append(f"task file {matches[0]} status does not match conversion map")
        if source_id in V5_CARRY_FORWARD_RECONCILIATION:
            if frontmatter.get("source_lineage") != "v5_carried_forward":
                errors.append(f"task file {matches[0]} missing v5 lineage")
            if frontmatter.get("active_disposition") != "historical_alias":
                errors.append(f"task file {matches[0]} missing historical alias disposition")
        if f"| {task_id} | {epic_id} | {status} |" not in task_index:
            errors.append(f"TASK_INDEX.md status row missing for {task_id}")

    for epic in EPICS:
        if not (ROOT / f"docs/planning/epics/{epic.epic_id}.md").exists():
            errors.append(f"missing planning epic {epic.epic_id}")
        if not (ROOT / f"codex/context/{epic.epic_id}.md").exists():
            errors.append(f"missing context pack {epic.epic_id}")
        if f"| {epic.epic_id} |" not in epics_index:
            errors.append(f"EPICS.md missing row for {epic.epic_id}")

    if gate_map_path.exists():
        gate_rows = list(csv.DictReader(gate_map_path.read_text(encoding="utf-8").splitlines()))
        counts = Counter(row["record_type"] for row in gate_rows)
        if counts != {"gate": 270, "risk": 222, "decision": 23}:
            errors.append(f"unexpected gate/risk/decision counts: {dict(counts)}")
        for row in gate_rows:
            source_id = row.get("source_id", "")
            if not source_id.startswith("V5-"):
                continue
            expected = record_metadata(source_id)
            if row.get("source_lineage") != expected["source_lineage"]:
                errors.append(f"{source_id} missing v5 reference lineage")
            if row.get("active_disposition") != expected["active_disposition"]:
                errors.append(f"{source_id} missing historical reference disposition")
    else:
        errors.append("missing CAPEX_V6_GATE_RISK_DECISION_MAP.csv")

    if intake_path.exists():
        intake = intake_path.read_text(encoding="utf-8")
        for phrase in (
            EXPECTED_MASTER_SHA256,
            "Runtime/API/schema/DB/workpage changes in this import: none",
            "Raw-data boundary",
        ):
            if phrase not in intake:
                errors.append(f"intake missing required phrase: {phrase}")
    else:
        errors.append("missing CAPEX_MASTER_V6_INTAKE.md")

    if args.master_zip:
        master_rows = read_master_csv(Path(args.master_zip).expanduser().resolve(), "MASTER_Task_Backlog.csv")
        if [row["source_task_id"] for row in rows] != [row["task_id"] for row in master_rows]:
            errors.append("conversion source task order does not match master ZIP task order")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"CAPEX v6 conversion check passed: {TASK_COUNT} tasks, {len(EPICS)} epics")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--master-zip", required=True)
    generate_parser.add_argument("--k12-zip")
    generate_parser.add_argument("--k3-zip")
    generate_parser.add_argument("--blind-zip")
    generate_parser.set_defaults(func=generate)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--master-zip")
    check_parser.set_defaults(func=check)

    args = parser.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
