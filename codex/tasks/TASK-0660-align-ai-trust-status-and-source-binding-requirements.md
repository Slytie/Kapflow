---
id: TASK-0660
epic: EPIC-142
title: "Align AI trust status and source-binding requirements"
status: TODO
owners: ["capex-architecture", "qa"]
reviewers: ["backend", "security", "capex-sme"]
depends_on: ["TASK-0564", "TASK-0651"]
risk: high
context_packs: ["codex/context/EPIC-142.md"]
patterns: ["SME-RP acceptance conditions", "AI draft boundary", "meaningful SourceRefs"]
---

# TASK-0660 - Align AI Trust Status And Source-Binding Requirements

## Why

AI output must remain a draft or reviewed artifact until promoted through canonical governance. Executive/status views need explicit trust and source-binding labels.

## Scope

Align AI trust status and SourceRef requirements with evidence binding, closure, and executive reporting guardrails.

- Define AI statuses from suggestion through official pointer adoption.
- Require meaningful SourceRefs before AI-assisted evidence can support reviewed state.
- Bind the work to `SME-RP-G009`.

## Out of scope

- LLM prompt or model implementation.
- AI-generated official state.
- CEO/status view implementation.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-142 and `SME-RP-G009`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- AI statuses distinguish suggestion, human reviewed, corrected, rejected, adopted reviewed state, and official pointer adoption.
- AI output cannot satisfy evidence or executive reporting without explicit trust/source labels.
- Source binding depends on resolver-backed meaningful SourceRefs.

## Source row mapping

- Source task ID: `TASK-0637`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G009`
- Source conditions: `TOP-09;11-A2;11-A3;11-A4`
