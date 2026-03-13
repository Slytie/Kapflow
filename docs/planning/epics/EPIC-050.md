# EPIC-050 - Human task queue (assignment, claim lease, SLA timer)

## Summary
Freeze the human-task model used for work routing and approval preparation.

## Why this epic exists (risk retired)
Prevents stuck or silently owned work and keeps human/agent intervention inside the same truth substrate.

## Scope
### In scope
- task kinds
- assignment / claim / lease
- escalation
- relationship to approvals and execution sessions
- end-to-end agent-owned work as a mode of the same task system

### Out of scope
- advanced workforce management UI

## Dependencies
- EPIC-010
- EPIC-020

## Recommended pattern cards (read cards first)
- `PATTERN-002`
- `PATTERN-007`
- `PATTERN-008`
- `PATTERN-009`

Context pack: `codex/context/EPIC-050.md`

Also see `docs/patterns/PATTERN_INDEX.yaml` for the full tagged library.

## Tasks
- TASK-0010
- TASK-0035
- TASK-0077

## Current Repo Status (2026-03-13)
- `TASK-0077` freezes the capability lattice in architecture docs and contract coverage, separating routing, claim, completion, specialized execute, upload, approval response, and flag-transition semantics before later write-boundary hardening.
