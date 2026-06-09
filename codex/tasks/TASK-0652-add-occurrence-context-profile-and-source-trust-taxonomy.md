---
id: TASK-0652
epic: EPIC-141
title: "Add occurrence context profile and source trust taxonomy"
status: TODO
owners: ["capex-platform", "data-governance"]
reviewers: ["backend", "security", "capex-sme"]
depends_on: ["TASK-0564"]
risk: high
context_packs: ["codex/context/EPIC-141.md"]
patterns: ["SME-RP acceptance conditions", "source occurrence context"]
---

# TASK-0652 - Add Occurrence Context Profile And Source Trust Taxonomy

## Why

SourceRefs need context about where evidence came from and what trust mode applies. This is a general source governance condition for CAPEX real-project work.

## Scope

Add a document occurrence context profile and source/data-source trust taxonomy for planning and later implementation.

- Distinguish observed, referenced, imported, reviewed, and officially adopted material.
- Preserve SourceOccurrence as observed source truth, not reviewed project truth.
- Bind the taxonomy to `SME-RP-G004`.

## Out of scope

- New ingestion runtime implementation.
- External connector activation.
- Raw corpus import.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-141 and `SME-RP-G004`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Source trust modes are general CAPEX evidence-source rules.
- Source occurrence, evidence binding, review, approval, and official adoption remain separate.
- External or imported status cannot overwrite CAPEX state directly.

## Source row mapping

- Source task ID: `TASK-0629`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G004`
- Source conditions: `6-A2;6-A3;13-A3;14-D9`
