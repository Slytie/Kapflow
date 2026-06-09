---
id: TASK-0663
epic: EPIC-151
title: "Define external system mode taxonomy"
status: TODO
owners: ["capex-architecture", "data-governance"]
reviewers: ["backend", "security", "capex-sme"]
depends_on: ["TASK-0547", "TASK-0550"]
risk: high
context_packs: ["codex/context/EPIC-151.md"]
patterns: ["SME-RP acceptance conditions", "external observation boundary"]
---

# TASK-0663 - Define External System Mode Taxonomy

## Why

External systems may be observed or referenced, but they must not silently overwrite CAPEX official state. The taxonomy belongs to executive transparency and external observation requirements.

## Scope

Define external system modes: observed, referenced, imported, human-reviewed, and officially adopted.

- Bind external observation to SourceRef, evidence, review, and pointer semantics.
- Prevent external values from directly becoming CAPEX official state.
- Bind the work to `SME-RP-G011`.

## Out of scope

- External connector implementation.
- ERP/DMS replacement.
- Automatic external-to-official synchronization.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-151 and `SME-RP-G011`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- External data modes are explicit and signed off before connector work activates.
- Observed, referenced, imported, reviewed, and officially adopted states remain distinct.
- External data cannot mutate official pointers or closure state without canonical review/adoption.

## Source row mapping

- Source task ID: `TASK-0640`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G011`
- Source conditions: `13-A3;14-D9`
