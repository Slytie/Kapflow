# EPIC-010 - Scope model + AuthZ + Isolation harness

## Summary
Freeze scope and authorization rules that apply equally to canonical stores, generated artifacts, and derived stores.

## Why this epic exists
A one-truth system still fails if scope leaks through projections, caches, or generated packets.

## Scope
### In scope
- tenant/domain rules
- isolation harness plan
- derived-store and generated-output isolation requirements

### Out of scope
- full ReBAC or generalized policy-language implementation

## Dependencies
- EPIC-015

## Deliverables
- `docs/architecture/scope_model.md`
- permissions vocabulary updates
- negative-test guidance

## Tasks
- TASK-0002
