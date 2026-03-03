# EPICS.md - Stage 4 work breakdown

Current runtime/debug priority: **Schedule Planning**. Payroll remains the secondary reference workflow.

## Epic list (recommended order)

| Epic ID | Title | Primary artifacts | Depends on |
|---|---|---|---|
| EPIC-000 | Payroll workflow contract v1 (freeze) | S4-A01, S4-A07 | - |
| EPIC-005 | Schedule Planning workflow contract v1 + operating model (freeze) | S4-A08 | EPIC-000 |
| EPIC-015 | One truth system + authority model + vision preservation | S4-A09 | EPIC-000, EPIC-005 |
| EPIC-025 | Canonical execution overlay + generated derivative policy | S4-A10, S4-A11 | EPIC-015 |
| EPIC-010 | Scope model + AuthZ + Isolation harness | S4-A01, S4-A02, S4-A07 | EPIC-015 |
| EPIC-020 | Authoritative TimelineEvent + Outbox + Degraded mode | S4-A04 | EPIC-010, EPIC-015 |
| EPIC-030 | Artifact store + Promotion pointers + Drift visibility | S4-A03 | EPIC-020, EPIC-015 |
| EPIC-040 | Orchestrator core (runs pinned, WAIT, bounded exception handling) | S4-A01 | EPIC-020, EPIC-025, EPIC-030 |
| EPIC-050 | Human task queue (assignment, claim lease, SLA timer) | S4-A02 | EPIC-010, EPIC-020 |
| EPIC-060 | Approvals + Policy enforcement (server-side) | S4-A01 | EPIC-050, EPIC-025, EPIC-030 |
| EPIC-070 | Automation sandbox baseline (tool execution gating) | S4-A01 | EPIC-060, EPIC-025 |
| EPIC-080 | Ops readiness (CI/CD, dashboards, runbooks, generated checks) | S4-A05, S4-A06 | EPIC-020, EPIC-025 |
| EPIC-090 | Acceptance suite + golden traces (happy path + negatives) | S4-A07 | EPIC-000..080 |

## Update rules
- Keep epic files in `docs/planning/epics/`
- Keep task briefs in `codex/tasks/`
- If an epic changes the authority chain, update `AUTHORITY_MODEL.md`
- If an epic defers something subtle, record it in `MERGER_BACKLOG.md`
- Keep epic-specific pattern guidance and context-pack links current when architecture references change
