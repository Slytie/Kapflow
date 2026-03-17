# EPIC-100 - Production perimeter + substrate + release-mediated promotion discipline

## Summary
Turn the now-internally-coherent repo into a stable first-user production system with a clearly defined perimeter, deploy topology, operator workflow, and promotion path.

## Why this epic exists
The repo's internal runtime/control semantics are stronger than its outer production perimeter. The next risk is not hidden semantic contradiction; it is production ambiguity around identity, startup posture, deploy substrate, rollback/restore, and operator distribution habits.

## Scope
### In scope
- server-derived viewer/bootstrap/session contract for shared environments
- frontend identity migration away from browser-set production truth
- executable local-dev loopback guard
- production-vs-lab topology and deploy reference for a first-user single-node system
- backup / restore / rollback runbooks and rehearsal basis
- observability baseline and perimeter hardening
- release-mediated promotion guidance

### Out of scope
- generalized multi-node/cloud-native platform migration
- PostgreSQL/object-store migration by default
- reopening the capability lattice or shared-env trust semantics already frozen in earlier tranches
- direct runtime promotion of lab candidates into production

## Dependencies
- EPIC-010
- EPIC-080

## Key decisions / constraints
- Prod and lab may share code and release discipline, but not live DBs, artifact roots, or secrets.
- The first-user production target is allowed to be a single-node system if it is explicit, backed up, restorable, and observable.
- Shared-env identity should be server-derived; browser-set identity remains local-dev/demo only.
- Promotion of workflow/task/process candidates should be release-mediated until explicit version-coexistence support is proven.

## Deliverables
- server-derived viewer/bootstrap/session design and implementation plan
- production-vs-lab topology ADR / runbook
- deploy / rollback / restore / rotate-secret runbooks
- perimeter/observability/GitHub hardening tasks and prompts

## Definition of Done
- a fresh operator can explain what production is, what lab is, how a release reaches prod, and how identity/bootstrap work in shared environments without relying on browser configuration or raw workspace sharing.

## Current Repo Status (2026-03-17 implementation pass)
- Backend `shared_env` principal resolution is credible and the frontend now boots through a server-derived viewer session contract instead of treating browser headers as production identity.
- The supported `onetruth-api` `local_dev` startup path now enforces loopback-only binds by default and requires an explicit unsafe override for controlled non-loopback test scenarios.
- Production and lab topology are now explicit as separate single-node environments over the current `SQLite + local filesystem artifacts` substrate, deployed from `release_source_bundle`.
- Release-bundle discipline is strong, but backup/restore/rollback rehearsal and proof are still the next operator-facing gap.
- Structured boundary logs exist, but metrics/health/readiness and GitHub perimeter hardening remain the next operator-facing gaps.

## Tasks
- TASK-0110
- TASK-0111
- TASK-0112
- TASK-0113
- TASK-0114
- TASK-0115
- TASK-0116
