# ADR-005 - Approval response domain hooks

## Status
Accepted

## Decision
The generic `approval.respond` command owns only the canonical approval transition and the `approval.responded` timeline event.

Domain-specific consequences of an approval response must be implemented as explicit approval-response hooks registered through `src/onetruth/application/services/approval_response_hooks.py`.

The current registered logistics hooks are:
- `logistics.weekly_publish_approval`
- `logistics.dispatch_reporting_finalize_approval`

These hooks may create artifacts, promote pointers, or invoke handoff commands only by using the existing one-truth runtime substrate inside the command transaction. They must not create a second approval truth system, hidden queue, or out-of-band official state.

## Why
Weekly schedule publish and dispatch-reporting finalize behavior were previously embedded in the generic approval handler. That made `approval.respond` carry logistics knowledge directly, which would not scale to CAPEX or other domains.

The approval model already says approvals authorize recorded actions; they do not themselves define business-domain mutation semantics. A hook registry preserves that model while keeping today’s logistics behavior synchronous, auditable, and fail-closed.

## Consequences
- `src/onetruth/application/handlers/approvals.py` must not import logistics handoff/build modules, publish/finalize constants, artifact-version effect helpers, or pointer-promotion effect helpers.
- Domain hooks are invoked after the generic `approval.responded` event is appended and before the command transaction commits.
- Hook effects must use canonical command/effect helpers, event idempotency keys derived from the approval-response receipt, and tenant/domain scoped workflow truth.
- A hook failure rolls back the approval response and its domain effects together.
- Future domains add hooks through the registry rather than editing the generic approval handler.
- Runtime activation, production deployment, and CAPEX-specific behavior remain separately gated.
