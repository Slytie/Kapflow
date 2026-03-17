# SRE_SIGNOFF.md - SRE gate checklist (Stage 4)

## Dashboards
- [ ] event persistence health
- [ ] outbox backlog / degraded-mode signals
- [ ] projection coherence failures
- [ ] task queue depth / stuck task signals
- [ ] generated-artifact freshness failures

## Alerts
- [ ] degraded mode visible and alertable
- [ ] stuck workflow/task alerts
- [ ] projection coherence failure alerts
- [ ] source-to-generated drift alerts when generation exists

## Runbooks
- [ ] audit export or projection degraded runbook exists
- [ ] stuck workflow or task runbook exists
- [ ] backup / restore runbook exists
- [ ] backup / restore rehearsal evidence exists
- [ ] rollback / deploy runbook exists
- [ ] generated artifact drift runbook exists
