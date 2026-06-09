---
id: TASK-0657
epic: EPIC-143
title: "Classify workflow extensions as MVP-lite or post-MVP"
status: TODO
owners: ["capex-product", "capex-architecture"]
reviewers: ["engineering-pm", "capex-sme"]
depends_on: ["TASK-0566"]
risk: medium
context_packs: ["codex/context/EPIC-143.md"]
patterns: ["SME-RP acceptance conditions", "MVP scope control"]
---

# TASK-0657 - Classify Workflow Extensions As MVP-Lite Or Post-MVP

## Why

Real-project SME feedback adds important workflow families, but not every family belongs in MVP. The repo needs an explicit classification to avoid silent scope creep.

## Scope

Classify shutdown/schedule, supplier claim/warranty, lessons learned, and related workflow extensions as MVP-lite, conditional, or post-MVP reserved.

- Preserve hooks for later without activating reserved modules.
- Bind classification to `SME-RP-G012`.
- Keep MVP scope focused on accepted early workflow families.

## Out of scope

- Runtime implementation of reserved workflows.
- Full supplier claim/warranty management.
- Lessons learned / after-handover performance library.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-143 and `SME-RP-G012`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Workflow extension classification is explicit and reviewable.
- MVP-lite and post-MVP modules do not become activation blockers for unrelated platform work.
- The classification keeps commercial, technical, handover, and effectiveness state separate.

## Source row mapping

- Source task ID: `TASK-0634`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G012`
- Source conditions: `8-A4;8-A7;8-A8;14-D1`
