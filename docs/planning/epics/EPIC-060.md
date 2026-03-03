# EPIC-060 - Approvals + Policy enforcement (server-side)

## Summary
Freeze the single approval model and server-side enforcement points.

## Why this epic exists (risk retired)
Prevents separate business-approval and agent-decision truth systems from emerging.

## Scope
### In scope
- approval object model
- approval kinds
- evidence requirements
- policy enforcement points
- canonical governance vocabulary and actor taxonomy
- projection coherence rules for approval-critical packets

### Out of scope
- mature method-change lifecycle

## Dependencies
- EPIC-050
- EPIC-025
- EPIC-030

## Key decisions / constraints
- there is one approval system for business decisions, execution gates, and future method-change review
- approvals bind to exact evidence refs, actor identity, and allowed response vocabulary
- projections are non-authoritative; if approval-critical packets drift, coherence rules must say whether to block or fail visible
- debug-tenant agent principals may use the same approval path, but may not bypass it

## Recommended pattern cards (read cards first)
- `PATTERN-002`
- `PATTERN-005`
- `PATTERN-008`

Context pack: `codex/context/EPIC-060.md`

## Tasks
- TASK-0012
- TASK-0031
- TASK-0034
