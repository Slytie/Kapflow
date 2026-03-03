# Golden event traces - Schedule Planning

This folder contains JSONL golden traces that act as executable memory for the Schedule Planning runtime/debug wedge.

Stable scenarios:
- `schedule_happy_path_publish_and_replan.jsonl` - AT-SCH-001 Stage03->Stage07 happy path with publish + additive replan
- `schedule_drift_after_review.jsonl` - AT-SCH-002 promotion drift is detected after review
- `schedule_fully_agentive_whole_flow.jsonl` - AT-SCH-003 fully-agentive end-to-end debug slice
- `schedule_lease_expiry_recovery.jsonl` - AT-SCH-004 lease expiry and recovery without duplicate issue work
- `schedule_degraded_mode_survivability.jsonl` - AT-SCH-005 degraded export/index visibility while truth writes continue
- `schedule_cross_scope_denial.jsonl` - AT-SCH-006 cross-scope tool request denied through canonical execution / policy evidence
- `schedule_policy_gate_enforced.jsonl` - AT-SCH-007 out-of-plan side-effecting tool execution denied until approval/policy gate is satisfied

Legacy alias retained:
- `schedule_planning_publish_and_replan_example.jsonl`

Additional design trace:
- `schedule_conditional_task_spawn_review_loop.jsonl` - illustrates parent task completion spawning explicit child follow-on work; this is not yet mapped to a stable AT-SCH scenario ID

All traces should validate against:
- `schemas/events/envelope.schema.json`
- `schemas/events/event_type_registry.yaml`
- `schemas/events/payloads/*.schema.json`
