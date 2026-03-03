# EPIC-005 - Schedule Planning workflow contract v1 + operating model (freeze)

## Summary
Turn Schedule Planning research and same-day delivery assumptions into a pinned repo-native workflow family and the current primary runtime/debug wedge.

## Why this epic exists (risk retired)
Prevents the platform from becoming payroll-shaped only and proves the same substrate can support bounded exception-heavy operations, including a fully-agentive debug path.

## Scope
### In scope
- contract pack
- operating model
- fixtures
- alignment with decision catalog and execution profile
- fully-agentive debug-slice specification for Stage 4 acceptance

### Out of scope
- routing engine implementation
- customer notification flows
- labor-law optimization

## Dependencies
- EPIC-000

## Key decisions / constraints
- base publication and intraday deltas are distinct official artifact streams
- downstream execution overlay may refine but not broaden the workflow contract
- fully-agentive debugging must not create a second agent-only truth path

## Deliverables
- `docs/workflows/schedule_planning/v1/*`
- fixture pack
- dataset keys and permissions updates
- Schedule Planning acceptance criteria for the fully-agentive debug slice

## Definition of Done
- Schedule Planning is specific enough that implementation work does not require domain rediscovery
- the primary Stage 4 debug objective is explicit and testable

## Tasks
- TASK-0016
- TASK-0017
- TASK-0018
- TASK-0033
