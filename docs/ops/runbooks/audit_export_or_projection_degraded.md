# Audit export or projection degraded

## Trigger
- alert on outbox backlog, projection render failures, or coherence failures

## Immediate checks
1. confirm authoritative timeline writes are healthy
2. confirm artifact writes and approvals are healthy
3. identify affected derived sinks or renderers
4. inspect recent `audit.degraded_mode.changed` and `projection.coherence_failed` events

## Safe operator actions
- pause non-critical export consumers if needed
- rebuild derived views from authoritative events after the root issue is fixed
- do not treat missing dashboards as missing truth unless timeline persistence also failed

## Escalate when
- timeline persistence is impaired
- approvals cannot be recorded
- pointer promotions cannot be recorded
