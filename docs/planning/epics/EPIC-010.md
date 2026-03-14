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

## Status
- `TASK-0002`, `TASK-0078`, and `TASK-0101` are complete.
- The API trust boundary now has explicit `local_dev`, `ci_test`, and `shared_env` profiles; `shared_env` fails closed by default, trusted-header CORS is limited to loopback local-dev origins, and a configured bearer-JWT resolver can now provide attested principals in `shared_env` without trusting `x-onetruth-*` headers.

## Tasks
- TASK-0002
- TASK-0078
- TASK-0101
