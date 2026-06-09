---
id: TASK-0664
epic: EPIC-136
title: "Add module-specific SME readiness rule"
status: TODO
owners: ["capex-product", "capex-architecture"]
reviewers: ["engineering-pm", "capex-sme"]
depends_on: ["TASK-0648"]
risk: high
context_packs: ["codex/context/EPIC-136.md"]
patterns: ["SME-RP acceptance conditions", "module-specific readiness"]
---

# TASK-0664 - Add Module-Specific SME Readiness Rule

## Why

The SME-RP conditions should block the affected module, not all platform foundation work. This prevents both false activation and unnecessary platform freeze.

## Scope

Add the module-specific SME readiness rule to CAPEX planning and gate language.

- Business definitions block only modules that depend on those definitions.
- Disabled safety-hardening and independent platform work may continue.
- Bind the rule to `SME-RP-G002` and `SME-RP-G012`.

## Out of scope

- Runtime activation.
- Waiving any specific SME-RP gate.
- Changing platform invariants.
- Raw corpus import.

## Verification

- Contract tests prove the SME-RP register records module-specific readiness.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- The readiness rule is explicit in repo-native planning memory.
- Affected business modules remain blocked until their required definitions are accepted or waived.
- Independent platform hardening is not blocked merely by unresolved business thresholds.

## Source row mapping

- Source task ID: `TASK-0641`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G002;SME-RP-G012`
- Source conditions: `2-A1;2-A2;14-D8;14-D9;14-D10`
