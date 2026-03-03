# Schedule Planning fixtures

This directory contains:
- the schedule-planning artifact template pack (EMPTY + COMPLETED examples)
- golden event traces and synthetic examples that act as the first behavioral corpus for Stage 4

Use the `*_Example_COMPLETED.*` files as the seed artifact inputs for future runtime scenario tests.
Use the `*_Template_EMPTY.*` files as the blank authored forms.

## Stable trace scenarios
- `schedule_happy_path_publish_and_replan.jsonl` - AT-SCH-001 happy path publish + additive replan
- `schedule_drift_after_review.jsonl` - AT-SCH-002 drift after review is visible
- `schedule_fully_agentive_whole_flow.jsonl` - AT-SCH-003 fully-agentive whole-flow debug slice
- `schedule_lease_expiry_recovery.jsonl` - AT-SCH-004 exception-task lease expiry and recovery
- `schedule_degraded_mode_survivability.jsonl` - AT-SCH-005 degraded-mode survivability
- `schedule_cross_scope_denial.jsonl` - AT-SCH-006 cross-scope negative
- `schedule_policy_gate_enforced.jsonl` - AT-SCH-007 sandbox/policy gate enforced

## Rules
- Do not commit real employee, routing, or customer data.
- Templates are allowed; completed examples must be synthetic.
- Availability uses coded leave types only; do not encode medical detail.
- If a workflow-semantic change lands, update the relevant trace and the matching test oracle in `tests/helpers/scenario_catalog.py`.
