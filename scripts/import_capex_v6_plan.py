#!/usr/bin/env python3
"""Import the CAPEX v6 master planning package into repo-native backlog docs.

This is a planning-only importer. It reads the external CAPEX v6 master ZIP and
generates task/epic/context docs plus conversion maps. It never extracts or
copies the raw K12/K3/blind project corpora into the repository.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
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
        "CAPEX v6 intake, provenance, and delivery controls",
        "Import the CAPEX v6 master as planning truth, preserve provenance, and define the delivery control layer before runtime work begins.",
        "CAPEX intake, conversion map, delivery cadence, product goal, source freeze",
        "EPIC-015, EPIC-080",
    ),
    EpicDefinition(
        "EPIC-137",
        "CAPEX activation blockers and platform readiness",
        "Retire platform P0/P1 blockers that must be solved before CAPEX runtime activation can safely begin.",
        "platform readiness tasks, generated-artifact helpers, invariant harnesses",
        "EPIC-015, EPIC-030, EPIC-040, EPIC-080",
    ),
    EpicDefinition(
        "EPIC-138",
        "CAPEX production, lab, release, and deployment hardening",
        "Keep production/lab separation, release-bundle cleanliness, rollback, restore, and deployment gates explicit.",
        "release pipeline, lab pilot auth, backup/restore, deployment gates",
        "EPIC-100, EPIC-110, EPIC-137",
    ),
    EpicDefinition(
        "EPIC-139",
        "CAPEX domain cleanup and shared-platform extraction",
        "Separate logistics-specific behavior from shared substrate seams before CAPEX reuses approvals, workpages, and command scopes.",
        "approval side-effect extraction, domain descriptor registry, logistics hardening",
        "EPIC-135, EPIC-137",
    ),
    EpicDefinition(
        "EPIC-140",
        "CAPEX project access, membership, and scoped APIs",
        "Add the project anchor, membership model, and project-scoped API posture required for multi-project CAPEX operation.",
        "project schema, membership, scoped query/API helpers",
        "EPIC-010, EPIC-137",
    ),
    EpicDefinition(
        "EPIC-141",
        "CAPEX corpus ingest, source occurrence, evidence, and search",
        "Create the source occurrence, extraction, evidence, and search foundation without treating raw documents as repo truth.",
        "ingest architecture, source occurrence, SourceRef resolver, extraction/search evidence",
        "EPIC-030, EPIC-040, EPIC-140",
    ),
    EpicDefinition(
        "EPIC-142",
        "CAPEX generated artifacts, promotion, closure, and stale governance",
        "Define generated artifact envelopes, promotion policy, approval response neutrality, closure snapshots, waivers, and stale/reopen behavior.",
        "artifact envelope, pointer policy, closure/waiver state, stale command rules",
        "EPIC-030, EPIC-060, EPIC-139, EPIC-141",
    ),
    EpicDefinition(
        "EPIC-143",
        "CAPEX workflow family and handoff manifests",
        "Introduce CAPEX workflow contracts and handoff manifests while staying on the canonical workflow/task/event substrate.",
        "CAPEX workflow catalog, handoff manifest, router and lifecycle workflows",
        "EPIC-040, EPIC-050, EPIC-142",
    ),
    EpicDefinition(
        "EPIC-144",
        "CAPEX workpages, projections, and stale command guards",
        "Add CAPEX project workpages over backend-owned projections and command envelopes without creating UI-local truth.",
        "workpage families, projection snapshots, stale-command harnesses",
        "EPIC-120, EPIC-143, EPIC-142",
    ),
    EpicDefinition(
        "EPIC-145",
        "CAPEX K12/K3 fixture governance and data quarantine",
        "Establish sanitized fixture governance, raw-data quarantine, sensitivity/redaction manifests, and K12/K3 release rules.",
        "fixture compiler, sensitivity/redaction manifests, K12/K3 quarantine policy",
        "EPIC-141, EPIC-149",
    ),
    EpicDefinition(
        "EPIC-146",
        "CAPEX three-project oracle fixtures and expected-output manifests",
        "Build the K12/K3 expected-output and oracle manifest layer used by the three-project test ladder.",
        "three-project fixture runbook, expected-output manifests, oracle catalog",
        "EPIC-145",
    ),
    EpicDefinition(
        "EPIC-147",
        "CAPEX cross-project invariants, blind validation, and agent lab evaluation",
        "Freeze blind-validation rules, cross-project invariant scorecards, agent-lab eval tiers, and no-overfitting checkpoints.",
        "blind freeze protocol, invariant scorecard, agent-lab eval matrix",
        "EPIC-110, EPIC-146",
    ),
    EpicDefinition(
        "EPIC-148",
        "CAPEX off-repo full-corpus, capacity, backup, and restore readiness",
        "Prove full-project, off-repo corpus processing and restore/capacity realism before any controlled pilot.",
        "full-corpus runbook, capacity benchmark, backup/restore rehearsal",
        "EPIC-138, EPIC-141, EPIC-147",
    ),
    EpicDefinition(
        "EPIC-149",
        "CAPEX QA, semantic tests, and TDD overlay",
        "Add the CAPEX semantic test catalog, quality gates, TDD metrics, and review checkpoints across implementation phases.",
        "semantic tests, phase quality gates, CODEOWNERS/review checks",
        "EPIC-080, EPIC-145",
    ),
    EpicDefinition(
        "EPIC-150",
        "CAPEX release governance, documentation, and repo hygiene",
        "Create the CAPEX release/documentation/refactor governance layer and keep branch, docs, and review policy explicit.",
        "release manifests, docs authority, semantic MR evidence, refactor register",
        "EPIC-138, EPIC-149",
    ),
    EpicDefinition(
        "EPIC-151",
        "CAPEX snapshots, CEO transparency, external boundary, and interface burden",
        "Model reviewed snapshots, external-system boundaries, CEO transparency, and interface-burden constraints.",
        "snapshot contracts, external bindings, transparency views, interface policy",
        "EPIC-142, EPIC-143, EPIC-144",
    ),
    EpicDefinition(
        "EPIC-152",
        "CAPEX production preflight go/no-go",
        "Run the final production preflight evidence review without confusing deployed code with activated truth mutation.",
        "production preflight checklist, evidence package, go/no-go memo",
        "EPIC-136..EPIC-151",
    ),
)

EPIC_BY_ID = {epic.epic_id: epic for epic in EPICS}


def slugify(value: str, limit: int = 88) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    value = re.sub(r"-+", "-", value)
    return (value[:limit].rstrip("-") or "capex-task")


def clean_text(value: str) -> str:
    return unicodedata.normalize("NFKD", value.translate(ASCII_TRANSLATION)).encode("ascii", "ignore").decode()


def md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


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


def master_package_stats(master_zip: Path) -> dict[str, object]:
    with zipfile.ZipFile(master_zip) as archive:
        infos = archive.infolist()
    extensions = Counter()
    for info in infos:
        if info.is_dir():
            continue
        suffix = Path(info.filename).suffix.lower() or "<none>"
        extensions[suffix] += 1
    return {
        "entries": len(infos),
        "files": sum(1 for info in infos if not info.is_dir()),
        "uncompressed_bytes": sum(info.file_size for info in infos),
        "extensions": dict(sorted(extensions.items())),
    }


def project_zip_stats(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
    extensions = Counter()
    for info in infos:
        if info.is_dir():
            continue
        suffix = Path(info.filename).suffix.lower() or "<none>"
        extensions[suffix] += 1
    return {
        "label": ascii_label(path.name),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "entries": len(infos),
        "files": sum(1 for info in infos if not info.is_dir()),
        "directories": sum(1 for info in infos if info.is_dir()),
        "uncompressed_bytes": sum(info.file_size for info in infos),
        "top_extensions": dict(extensions.most_common(8)),
    }


def ascii_label(value: str) -> str:
    label = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    label = re.sub(r"\s+", " ", label).strip()
    return label


def assign_epic(row: dict[str, str]) -> str:
    source_id = row["task_id"]
    area = row["area"].lower()

    if source_id.startswith("PP-TASK"):
        return "EPIC-152"
    if source_id in {"TP-TASK-001", "TP-TASK-002", "TP-TASK-003", "TP-TASK-009"}:
        return "EPIC-146"
    if source_id == "TP-TASK-007":
        return "EPIC-148"
    if source_id.startswith("TP-TASK"):
        return "EPIC-147"
    if source_id.startswith("SD-TASK") or source_id in {
        "MP-PR000",
        "V5-TASK-008",
        "V5-TASK-009",
    }:
        return "EPIC-136"
    if source_id.startswith("MP-PR"):
        number_match = re.search(r"(\d+)$", source_id)
        if not number_match:
            raise RuntimeError(f"could not parse MP planning task number from {source_id}")
        number = int(number_match.group(1))
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
    if source_id in {"NU-CB-P0-001"}:
        return "EPIC-139"
    if source_id in {"NU-CB-P0-002", "V5-TASK-006"}:
        return "EPIC-137"
    if source_id.startswith("CLEAN") or source_id in {
        "RF-001",
        "RF-002",
        "V5-TASK-005",
    }:
        return "EPIC-139"
    if source_id.startswith("PROJ") or source_id.startswith("ARCH-W1") or source_id in {
        "NU-CB-P0-003",
        "RF-003",
    }:
        return "EPIC-140"
    if source_id.startswith("INGEST") or source_id.startswith("ARCH-W2") or source_id.startswith("ARCH-W3") or source_id in {
        "NU-CB-P0-004",
        "V5-TASK-006",
        "V5-TASK-007",
        "RF-004",
        "RF-005",
        "RF-006",
    }:
        return "EPIC-141"
    if source_id in {"ART-002", "WFLOW-008", "NU-CB-P1-009"} or source_id.startswith("ARCH-W8"):
        return "EPIC-151"
    if source_id == "ART-007":
        return "EPIC-144"
    if source_id.startswith("ART") or source_id.startswith("ARCH-W4") or source_id in {
        "NU-CB-P0-005",
        "NU-CB-P1-010",
        "RF-007",
        "RF-008",
        "V5-TASK-001",
        "V5-TASK-002",
        "V5-TASK-004",
    }:
        return "EPIC-142"
    if source_id.startswith("WFLOW") or source_id in {
        "NU-CB-P0-006",
        "NU-CB-P1-011",
        "V5-TASK-003",
        "V5-TASK-010",
    }:
        return "EPIC-143"
    if source_id.startswith("WP") or source_id.startswith("ARCH-W5") or source_id in {
        "ART-007",
        "NU-CB-P0-007",
        "RF-009",
    }:
        return "EPIC-144"
    if source_id.startswith("K12") or source_id.startswith("SPB2") or source_id.startswith("ARCH-W6") or source_id.startswith("SAFE-B") or source_id in {
        "SAFE-001",
        "RF-010",
    }:
        return "EPIC-145"
    if source_id.startswith("ARCH-W75") or source_id.startswith("TEST") or source_id.startswith("QD") or source_id == "NU-CB-P0-008":
        return "EPIC-149"
    if source_id.startswith("ARCH-W7") or source_id.startswith("DOC") or source_id in {
        "RF-011",
        "RF-012",
        "SAFE-002",
    }:
        return "EPIC-150"
    if "production-preflight" in area:
        return "EPIC-152"
    if "snapshot" in area or "external" in area:
        return "EPIC-151"
    return "EPIC-136"


def owner_reviewers(row: dict[str, str]) -> tuple[list[str], list[str]]:
    area = row["area"].lower()
    if "frontend" in area or "workpage" in area:
        return ["frontend"], ["platform", "qa"]
    if "security" in area or "data_governance" in area or "governance" in area:
        return ["platform", "security"], ["architect", "qa"]
    if "docs" in area or "documentation" in area or "process" in area:
        return ["architect"], ["platform", "qa"]
    if "testing" in area or "quality" in area or "tdd" in area:
        return ["qa"], ["platform", "architect"]
    if "production" in area or "deployment" in area or "ops" in area or "capacity" in area:
        return ["platform", "sre"], ["security", "qa"]
    return ["platform"], ["architect", "qa"]


def task_risk(row: dict[str, str]) -> str:
    priority = row["priority"]
    area = row["area"].lower()
    if "P0" in priority:
        return "high"
    if "security" in area or "approval" in area or "pointer" in area:
        return "high"
    return "medium"


def expand_range_token(token: str, known_ids: set[str]) -> list[str]:
    if ".." not in token:
        return []
    start, end = token.split("..", 1)
    start = start.strip()
    end = end.strip()
    start_match = re.match(r"^(.*?)(\d+)$", start)
    end_match = re.match(r"^(.*?)(\d+)$", end)
    if not start_match or not end_match:
        return []
    prefix, start_number = start_match.groups()
    end_prefix, end_number = end_match.groups()
    if end_prefix and end_prefix != prefix and not prefix.endswith(end_prefix):
        return []
    width = max(len(start_number), len(end_number))
    expanded = [
        f"{prefix}{number:0{width}d}"
        for number in range(int(start_number), int(end_number) + 1)
    ]
    return [source_id for source_id in expanded if source_id in known_ids]


def converted_dependencies(depends_on: str, source_to_task: dict[str, str]) -> tuple[list[str], str]:
    text = depends_on.strip()
    if not text or text.lower() in {"none", "n/a", "na"}:
        return [], ""
    known_ids = set(source_to_task)
    found: set[str] = set()
    matched_fragments: list[str] = []
    for shorthand_match in re.finditer(r"\bPR(\d{3})(?:\.\.|-)(?:PR)?(\d{3})\b", text):
        start_number = int(shorthand_match.group(1))
        end_number = int(shorthand_match.group(2))
        for number in range(start_number, end_number + 1):
            source_id = f"MP-PR{number:03d}"
            if source_id in source_to_task:
                found.add(source_id)
        matched_fragments.append(shorthand_match.group(0))
    for range_match in re.findall(r"[A-Z0-9][A-Z0-9_-]*\d+\.\.[A-Z0-9_-]*\d+", text):
        expanded = expand_range_token(range_match, known_ids)
        if expanded:
            found.update(expanded)
            matched_fragments.append(range_match)
    normalized = re.sub(r"[^A-Za-z0-9_-]+", " ", text)
    for token in normalized.split():
        if token in source_to_task:
            found.add(token)
            matched_fragments.append(token)
        elif re.fullmatch(r"PR\d{3}", token):
            source_id = f"MP-{token}"
            if source_id in source_to_task:
                found.add(source_id)
                matched_fragments.append(token)
    converted = sorted((source_to_task[source_id] for source_id in found), key=lambda value: int(value.split("-")[1]))
    unresolved = text
    for fragment in sorted(set(matched_fragments), key=len, reverse=True):
        unresolved = unresolved.replace(fragment, "").strip()
    for source_id in sorted(found, key=len, reverse=True):
        unresolved = unresolved.replace(source_id, "").strip()
    unresolved = re.sub(r"\s+", " ", unresolved).strip(" ;,.")
    return converted, unresolved


def build_task_records(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    if len(rows) != TASK_COUNT:
        raise RuntimeError(f"expected {TASK_COUNT} task rows, found {len(rows)}")
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    repo_task_id = str(record["repo_task_id"])
    epic_id = str(record["epic_id"])
    depends_on = record["depends_on"]
    owners = record["owners"]
    reviewers = record["reviewers"]
    risk = str(record["risk"])
    context_pack = f"codex/context/{epic_id}.md"
    title = row["title"]
    source_id = row["task_id"]
    original_dep = row["depends_on"] or "none"
    unresolved = str(record["unresolved_depends_on"])
    dependency_note = (
        f"- Converted repo dependencies: {', '.join(depends_on)}\n"
        if depends_on
        else "- Converted repo dependencies: none\n"
    )
    if unresolved and unresolved.lower() not in {"none", "n/a", "na"}:
        dependency_note += f"- Source dependency notes still to satisfy: {unresolved}\n"

    return f"""---
id: {repo_task_id}
epic: {epic_id}
title: {yaml_quote(title)}
status: TODO
owners: {json.dumps(owners)}
reviewers: {json.dumps(reviewers)}
depends_on: {json.dumps(depends_on)}
risk: {risk}
context_packs:
  - {yaml_quote(context_pack)}
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `{source_id}` so future work can be executed from repo-native backlog memory without loading the full master package.

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

## Source files to change
- Repo-native source files required by the source scope and the `{epic_id}` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
{row["primary_outputs"] or "Record any generated or downstream artifacts in the task implementation notes."}

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
- Source task ID: `{source_id}`
- Source phase: `{row["phase"] or "not specified"}`
- Source priority: `{row["priority"] or "not specified"}`
- Source area: `{row["area"] or "not specified"}`
- Original depends_on: `{original_dep}`
{dependency_note}- Recommended source branch: `{row["recommended_branch"] or "not specified"}`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
"""


def conversion_map_rows(records: list[dict[str, object]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        row = record["source"]
        assert isinstance(row, dict)
        rows.append(
            {
                "source_task_id": row["task_id"],
                "repo_task_id": str(record["repo_task_id"]),
                "epic_id": str(record["epic_id"]),
                "status": "TODO",
                "source_priority": row["priority"],
                "source_phase": row["phase"],
                "source_area": row["area"],
                "original_depends_on": row["depends_on"],
                "converted_depends_on": ";".join(record["depends_on"]),  # type: ignore[arg-type]
                "unresolved_dependency_notes": str(record["unresolved_depends_on"]),
                "acceptance_gate": row["acceptance_gate"],
                "source_title": row["title"],
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def gate_risk_decision_rows(master_zip: Path) -> list[dict[str, str]]:
    gate_rows = read_master_csv(master_zip, "MASTER_Acceptance_Gates.csv")
    risk_rows = read_master_csv(master_zip, "MASTER_Risk_Register.csv")
    decision_rows = read_master_csv(master_zip, "MASTER_Open_Decisions_Register.csv")
    output: list[dict[str, str]] = []
    for row in gate_rows:
        output.append(
            {
                "record_type": "gate",
                "record_id": row["gate_id"],
                "title_or_name": row["gate_name"],
                "category": row["category"],
                "phase_or_owner": row["phase"],
                "priority_or_severity": row["priority"],
                "depends_on_or_blocking": row["depends_on"],
                "source_or_evidence": row["required_evidence"],
                "notes": row["pass_condition"],
            }
        )
    for row in risk_rows:
        title = row["title"] or row["risk"][:96]
        output.append(
            {
                "record_type": "risk",
                "record_id": row["risk_id"],
                "title_or_name": title,
                "category": row["category"],
                "phase_or_owner": row["owner_area"],
                "priority_or_severity": row["severity"],
                "depends_on_or_blocking": row["impact"],
                "source_or_evidence": row["source"],
                "notes": row["mitigation"],
            }
        )
    for row in decision_rows:
        output.append(
            {
                "record_type": "decision",
                "record_id": row["decision_id"],
                "title_or_name": row["decision"],
                "category": "open-decision",
                "phase_or_owner": row["owner_area"],
                "priority_or_severity": row["status"],
                "depends_on_or_blocking": row["blocking"],
                "source_or_evidence": row["source"],
                "notes": row["decision"],
            }
        )
    return output


def intake_doc(
    master_zip: Path,
    task_rows: list[dict[str, str]],
    gate_rows: list[dict[str, str]],
    risk_rows: list[dict[str, str]],
    decision_rows: list[dict[str, str]],
    dependency_rows: list[dict[str, str]],
    catalog_rows: list[dict[str, str]],
    traceability_rows: list[dict[str, str]],
    project_stats: list[dict[str, object]],
) -> str:
    stats = master_package_stats(master_zip)
    master_sha = sha256_file(master_zip)
    if master_sha != EXPECTED_MASTER_SHA256:
        raise RuntimeError(f"master ZIP SHA mismatch: {master_sha}")

    project_lines = []
    for project in project_stats:
        ext_summary = ", ".join(
            f"{suffix}:{count}" for suffix, count in project["top_extensions"].items()  # type: ignore[union-attr]
        )
        project_lines.append(
            "| {role} | `{label}` | `{sha256}` | {files} | {entries} | {size_bytes} | {uncompressed_bytes} | {exts} |".format(
                role=project["role"],
                label=project["label"],
                sha256=project["sha256"],
                files=project["files"],
                entries=project["entries"],
                size_bytes=project["size_bytes"],
                uncompressed_bytes=project["uncompressed_bytes"],
                exts=md_escape(ext_summary),
            )
        )

    return f"""# CAPEX Master Plan v6 Intake

Imported on `{IMPORT_DATE}` as repo-native planning backlog memory.

## Source package
- Active package: `CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip`
- SHA256: `{master_sha}`
- ZIP entries observed: {stats["entries"]}
- ZIP files observed: {stats["files"]}
- ZIP uncompressed bytes observed: {stats["uncompressed_bytes"]}
- Supersedes: v5 and earlier CAPEX master planning packages for future conversion work.

## Validation row counts
| Register | Rows |
|---|---:|
| Task backlog | {len(task_rows)} |
| Acceptance gates | {len(gate_rows)} |
| Risk register | {len(risk_rows)} |
| Dependency register | {len(dependency_rows)} |
| Catalog | {len(catalog_rows)} |
| Open decisions | {len(decision_rows)} |
| Traceability | {len(traceability_rows)} |

The v6 package reported zero CSV parse failures, zero JSON parse failures, zero duplicate ID failures, zero semantic coverage failures, and zero raw project filename hits.

## Repo integration status
- Converted source task rows: `{TASK_COUNT}`.
- Repo task range: `TASK-{TASK_START:04d}` through `TASK-{TASK_END:04d}`.
- Repo epic range: `EPIC-136` through `EPIC-152`.
- Runtime/API/schema/DB/workpage changes in this import: none.
- All converted tasks start as `TODO`.
- CAPEX production-like activation remains blocked by the imported P0, three-project, data-governance, capacity/restore, release, and production-preflight gates.

## Project corpus provenance
Only aggregate ZIP-level metadata is recorded here. The project corpora remain outside the repo and must be mounted read-only only through an approved off-repo runbook.

| Assumed role | ZIP label | SHA256 | Files | Entries | ZIP bytes | Uncompressed bytes | Top extensions |
|---|---|---|---:|---:|---:|---:|---|
{chr(10).join(project_lines)}

## Raw-data boundary
- Do not commit extracted project files, internal project paths, raw document text, screenshots, prompts, completions, or logs containing raw project content.
- Commit only sanitized fixtures, manifests, hashes, aggregate reports, and policy/evidence records approved by the relevant CAPEX fixture-governance task.
- Blind-validation outputs must not be inspected or tuned against before the freeze and baseline protocol tasks have completed.
- Workflow Lab outputs remain non-authoritative and cannot promote pointers, approve claims, close technical state, or mutate production truth.

## Generated companion artifacts
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/epics/EPIC-136.md` through `docs/planning/epics/EPIC-152.md`
- `codex/context/EPIC-136.md` through `codex/context/EPIC-152.md`
- `codex/tasks/TASK-{TASK_START:04d}-*.md` through `codex/tasks/TASK-{TASK_END:04d}-*.md`
"""


def epic_doc(epic: EpicDefinition, records: list[dict[str, object]]) -> str:
    task_lines = [
        f"- `{record['repo_task_id']}` (`{record['source']['task_id']}`) - {record['source']['title']}"  # type: ignore[index]
        for record in records
    ]
    source_families = Counter(str(record["source"]["task_id"]).split("-")[0] for record in records)  # type: ignore[index]
    families = ", ".join(f"{family}:{count}" for family, count in sorted(source_families.items()))
    return f"""# {epic.epic_id} - {epic.title}

## Summary
{epic.summary}

This epic was imported from CAPEX v6 on `{IMPORT_DATE}` as planning backlog only. It does not activate CAPEX runtime behavior by itself.

## Status
Imported as TODO backlog. Implementation must proceed through small reviewed tasks and the normal repo verification loop.

## In scope
- Source task families/counts: {families or "none"}.
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
    return f"""# {epic.epic_id} Context Pack - {epic.title}

Purpose:
- Rehydrate the CAPEX v6 task tranche for `{epic.epic_id}` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
{source_ranges or "No source rows assigned."}

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
- No production-like CAPEX activation from planning docs alone.
- No raw corpus extraction into repo, CI logs, screenshots, prompts, or generated packs.
- No CAPEX-specific shortcut around canonical approval, artifact pointer, task, event, or policy seams.
"""


def update_epics_index(epic_records: dict[str, list[dict[str, object]]]) -> None:
    path = ROOT / "docs/planning/EPICS.md"
    text = path.read_text(encoding="utf-8")
    marker = "| EPIC-136 | CAPEX v6 intake, provenance, and delivery controls |"
    if marker in text:
        return
    rows = []
    for epic in EPICS:
        rows.append(
            f"| {epic.epic_id} | {md_escape(epic.title)} | {md_escape(epic.primary_artifacts)} | {md_escape(epic.depends_on)} |"
        )
    insert_after = "| EPIC-135 | Unified schedule replan popup and dynamic scheduling activation |"
    lines = text.splitlines()
    output: list[str] = []
    inserted = False
    for line in lines:
        output.append(line)
        if line.startswith(insert_after):
            output.extend(rows)
            inserted = True
    if not inserted:
        raise RuntimeError("could not find EPIC-135 row in EPICS.md")
    note = (
        "\nStatus note (2026-06-01): CAPEX v6 is imported as a gated planning backlog "
        "in EPIC-136 through EPIC-152 and TASK-0233 through TASK-0606. This import "
        "does not supersede the current logistics weekly/live implementation focus and "
        "does not activate CAPEX runtime truth mutation.\n"
    )
    text = "\n".join(output) + "\n"
    text = text.replace("\n## Update rules", note + "\n## Update rules")
    path.write_text(text, encoding="utf-8")


def update_task_index(records: list[dict[str, object]]) -> None:
    path = ROOT / "docs/planning/TASK_INDEX.md"
    text = path.read_text(encoding="utf-8")
    retained_lines = []
    for line in text.rstrip().splitlines():
        match = re.match(r"\| TASK-(\d{4}) \|", line)
        if match and TASK_START <= int(match.group(1)) <= TASK_END:
            continue
        retained_lines.append(line)
    rows = []
    for record in records:
        row = record["source"]
        assert isinstance(row, dict)
        rows.append(
            f"| {record['repo_task_id']} | {record['epic_id']} | TODO | {record['risk']} | {md_escape(row['title'])} |"
        )
    text = "\n".join(retained_lines).rstrip() + "\n" + "\n".join(rows) + "\n"
    path.write_text(text, encoding="utf-8")


def update_current_focus() -> None:
    path = ROOT / "docs/status/CURRENT_FOCUS.md"
    text = path.read_text(encoding="utf-8")
    marker = "## CAPEX v6 planning import"
    if marker in text:
        return
    block = f"""
## CAPEX v6 planning import
Imported on `{IMPORT_DATE}` as gated backlog memory only:
- source package: `CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip`
- repo-native task range: `TASK-{TASK_START:04d}` through `TASK-{TASK_END:04d}`
- repo-native epic range: `EPIC-136` through `EPIC-152`
- all converted tasks start as `TODO`
- no runtime behavior, API, schema, DB, workpage, or production activation changed in the import
- raw K12, K3, and blind-validation project ZIPs remain off-repo; only hashes, aggregate ZIP metadata, sanitized fixtures, and approved evidence may enter repo truth

The current logistics weekly/live implementation focus remains intact. CAPEX work should be selected deliberately from the imported backlog and must respect the production/lab, raw-data, and one-truth gates recorded in `docs/planning/CAPEX_MASTER_V6_INTAKE.md`.

"""
    text = text.replace("\n## Current implemented baseline", "\n" + block + "## Current implemented baseline")
    path.write_text(text, encoding="utf-8")


def update_decisions() -> None:
    path = ROOT / "docs/status/DECISIONS_SINCE_LAST.md"
    text = path.read_text(encoding="utf-8")
    marker = "## 2026-06-01 (CAPEX v6 planning import and gated backlog conversion)"
    if marker in text:
        return
    block = f"""
## 2026-06-01 (CAPEX v6 planning import and gated backlog conversion)
- Source decision: `CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip` is the active CAPEX planning baseline; v5 and earlier packages are superseded for future conversion work.
- Backlog decision: all {TASK_COUNT} v6 source task rows are converted to repo-native TODO tasks `TASK-{TASK_START:04d}` through `TASK-{TASK_END:04d}` and grouped under `EPIC-136` through `EPIC-152`.
- Boundary decision: this import is planning-only and does not change runtime behavior, schemas, APIs, DB state, workpages, or production/lab activation.
- Data-governance decision: the K12, K3, and blind-validation project ZIPs remain off-repo; repo truth may include only ZIP-level hashes/aggregate metadata, sanitized fixtures, manifests, and approved evidence.
- Activation decision: CAPEX production-like activation remains blocked until P0, three-project, raw-data governance, capacity/restore, release, and production-preflight gates close or receive explicit waivers.

"""
    text = text.replace(
        "Record any decisions made since the last session so a fresh Codex run can rehydrate quickly.\n",
        "Record any decisions made since the last session so a fresh Codex run can rehydrate quickly.\n" + block,
    )
    path.write_text(text, encoding="utf-8")


def generate(args: argparse.Namespace) -> None:
    master_zip = Path(args.master_zip).expanduser().resolve()
    if not master_zip.exists():
        raise RuntimeError(f"master ZIP not found: {master_zip}")

    task_rows = read_master_csv(master_zip, "MASTER_Task_Backlog.csv")
    gate_rows = read_master_csv(master_zip, "MASTER_Acceptance_Gates.csv")
    risk_rows = read_master_csv(master_zip, "MASTER_Risk_Register.csv")
    decision_rows = read_master_csv(master_zip, "MASTER_Open_Decisions_Register.csv")
    dependency_rows = read_master_csv(master_zip, "MASTER_Dependency_Register.csv")
    catalog_rows = read_master_csv(master_zip, "MASTER_CAPEX_Schema_Workflow_Workpage_Catalog.csv")
    traceability_rows = read_master_csv(master_zip, "MASTER_Traceability_Register.csv")

    records = build_task_records(task_rows)
    epic_records: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        epic_records[str(record["epic_id"])].append(record)

    project_inputs = [
        ("K12 primary MVP fixture candidate", args.k12_zip),
        ("K3 shadow/regression fixture candidate", args.k3_zip),
        ("Blind/third-validation holdout candidate", args.blind_zip),
    ]
    project_stats: list[dict[str, object]] = []
    for role, raw_path in project_inputs:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"project ZIP not found for {role}: {path}")
        stats = project_zip_stats(path)
        stats["role"] = role
        project_stats.append(stats)

    write_text(
        ROOT / "docs/planning/CAPEX_MASTER_V6_INTAKE.md",
        intake_doc(
            master_zip,
            task_rows,
            gate_rows,
            risk_rows,
            decision_rows,
            dependency_rows,
            catalog_rows,
            traceability_rows,
            project_stats,
        ),
    )
    write_csv(ROOT / "docs/planning/CAPEX_V6_CONVERSION_MAP.csv", conversion_map_rows(records))
    write_csv(ROOT / "docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv", gate_risk_decision_rows(master_zip))

    for epic in EPICS:
        records_for_epic = epic_records.get(epic.epic_id, [])
        write_text(ROOT / f"docs/planning/epics/{epic.epic_id}.md", epic_doc(epic, records_for_epic))
        write_text(ROOT / f"codex/context/{epic.epic_id}.md", context_doc(epic, records_for_epic))

    for record in records:
        write_text(ROOT / f"codex/tasks/{record['filename']}", task_body(record))

    update_epics_index(epic_records)
    update_task_index(records)
    update_current_focus()
    update_decisions()


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
        errors.append("conversion map repo task IDs are not the expected contiguous TASK-0233..TASK-0606 range")
    if len(set(row.get("source_task_id", "") for row in rows)) != len(rows):
        errors.append("conversion map contains duplicate source task IDs")
    if len(set(actual_ids)) != len(actual_ids):
        errors.append("conversion map contains duplicate repo task IDs")

    task_index = (ROOT / "docs/planning/TASK_INDEX.md").read_text(encoding="utf-8")
    epics_index = (ROOT / "docs/planning/EPICS.md").read_text(encoding="utf-8")
    for row in rows:
        task_id = row["repo_task_id"]
        epic_id = row["epic_id"]
        status = row.get("status", "")
        if status not in {"TODO", "DONE", "BLOCKED"}:
            errors.append(f"conversion map has invalid status for {task_id}: {status}")
            continue
        matches = list((ROOT / "codex/tasks").glob(f"{task_id}-*.md"))
        if len(matches) != 1:
            errors.append(f"expected one task file for {task_id}, found {len(matches)}")
            continue
        text = matches[0].read_text(encoding="utf-8")
        frontmatter = parse_frontmatter_fields(text)
        if frontmatter.get("id") != task_id:
            errors.append(f"task file {matches[0]} missing id front matter")
        if frontmatter.get("epic") != epic_id:
            errors.append(f"task file {matches[0]} missing epic front matter")
        if frontmatter.get("status") != status:
            errors.append(f"task file {matches[0]} status does not match conversion map")
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
    else:
        errors.append("missing CAPEX_V6_GATE_RISK_DECISION_MAP.csv")

    if intake_path.exists():
        intake = intake_path.read_text(encoding="utf-8")
        if EXPECTED_MASTER_SHA256 not in intake:
            errors.append("intake missing expected master SHA256")
        for phrase in ["Runtime/API/schema/DB/workpage changes in this import: none", "Raw-data boundary"]:
            if phrase not in intake:
                errors.append(f"intake missing boundary phrase: {phrase}")
    else:
        errors.append("missing CAPEX_MASTER_V6_INTAKE.md")

    if args.master_zip:
        master_rows = read_master_csv(Path(args.master_zip).expanduser().resolve(), "MASTER_Task_Backlog.csv")
        if [row["source_task_id"] for row in rows] != [row["task_id"] for row in master_rows]:
            errors.append("conversion source task order does not match master ZIP task order")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"CAPEX v6 conversion check passed: {TASK_COUNT} tasks, {len(EPICS)} epics")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--master-zip", required=True)
    generate_parser.add_argument("--k12-zip", required=True)
    generate_parser.add_argument("--k3-zip", required=True)
    generate_parser.add_argument("--blind-zip", required=True)
    generate_parser.set_defaults(func=generate)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--master-zip")
    check_parser.set_defaults(func=check)

    args = parser.parse_args()
    result = args.func(args)
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
