# Scope model (tenant + domain)

## Scope tuple
Every object and action is scoped by:
- `tenant_id` (required)
- `domain_id` (required for domain-scoped objects)

## Domain model (MVP)
For MVP, treat `domain_id` as an internal operational partition such as station, region, program, or business unit.
Do not overload a single `domain_id` with multiple orthogonal axes without explicit modeling.

## Rules
- All list/query endpoints must require a scope filter and enforce it.
- Background consumers, exporters, indexers, projections, and generated artifacts must enforce scope on read and write.
- Cross-tenant access is forbidden.
- Cross-domain access is forbidden unless explicitly modeled as a tenant-global object.

## Derived-store consequence
WorkGraph, dashboards, approval packets, generated IR caches, and search indices are not exempt from the scope model. Derived material can leak just as easily as canonical storage.

## Evidence required
- CI must include negative tests for cross-tenant and cross-domain access attempts.
- Any denial must be logged.
- Generated or compiled artifacts must record the scope they were produced under.
