# Weekly schedule planning examples

These examples are normalized from the real artifacts provided:
- recurring Amazon weekly/horizon route-update emails,
- the current scheduling spreadsheet,
- the EOS / dispatch workbook.

They are illustrative examples for pack design, not new sources of truth.

Added schedule-control bridge examples in this slice:
- route-slot requirements (`planning.route_slot_requirements.workbook`),
- driver capabilities (`planning.driver_capabilities.workbook`),
- Stage04 input bundle (`planning.input_bundle.doc`),
- Stage04 candidate delta (`planning.candidate_schedule_delta.workbook`),
- Stage04 validation summary (`planning.validation_summary.doc`).

Default realistic Stage04 hard-case contract:
- `route_slot_requirements_overcapacity_preference_example.yaml`
- `driver_capabilities_overcapacity_preference_example.yaml`
- `approved_availability_overcapacity_preference_example.yaml`
- `actual_hours_snapshot_overcapacity_preference_example.yaml`
- `stage04_input_bundle_overcapacity_preference_example.yaml`

That realistic weekly pilot contract is pinned to `PW-2026-W12` and is intentionally over-capacity on every day so future planner iterations can optimize preference, continuity, seniority, and reliability tradeoffs without changing artifact kinds.
