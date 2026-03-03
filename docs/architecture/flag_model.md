# Flag model

Flags are *first-class case items* used to surface exceptions, anomalies, or required human attention **without** silently mutating official artifacts.

They exist to satisfy three Stage-4 needs:

1) Make operational anomalies explicit and attributable (who/what/when).
2) Prevent exceptions from being "hidden" inside spreadsheets, comments, or dashboards.
3) Provide a durable bridge between automated checks and human resolution.

## 1) Formal objects

### Flag (runtime object)
A `Flag` is a scoped object:

- **scope:** `(tenant_id, domain_id)`
- **workflow binding:** `workflow_id` + `partition_key`
- **identity:** `flag_id` (stable)
- **classification:** `kind`, `severity`
- **lifecycle:** `state` (open → triage → resolved/closed/waived)

Schema: `schemas/runtime/flag.schema.json`.

### Flag events (timeline)
Flags are **append-only** via the canonical timeline:

- `flag.created` — creates a new flag.
- `flag.state_changed` — transitions state (including “closed”).

The current flag state is a *derived view* from the flag’s event history.

The flag model intentionally does **not** require a second “flag timeline”.

## 2) Lifecycle and invariants

### Allowed states
Recommended MVP states:

- `open` — created and awaiting attention
- `triage` — actively being investigated
- `blocked` — cannot progress without external input/decision
- `resolved` — addressed; may still require closure approval in some domains
- `closed` — completed and no longer active
- `waived` — explicitly accepted risk / exception with rationale

### Invariants (must hold)
- A flag belongs to exactly one `(tenant_id, domain_id, workflow_id, partition_key)` binding.
- A flag’s state history is reconstructable from timeline events.
- Creating or changing a flag **must** emit a timeline event with:
  - `links[]` including `workflow_run` and `flag`
  - optional evidence links (artifact versions, approvals, task runs)
- Flag payloads must not contain secrets/PII. Use references to immutable artifacts as evidence.

## 3) Relationship to human tasks and approvals
Flags do not replace tasks or approvals:

- A flag may **create** a human task (“investigate undercoverage”).
- A task may **resolve** a flag, but the closure still requires:
  - `flag.state_changed` emitted on the timeline
- Some flag closures may require an approval (e.g., “waive SLA window”), but that is an `approval.requested` / `approval.responded` pair linked to the flag.

## 4) Stable vs variable parts
Stable (platform-level):
- object fields and lifecycle rules
- required timeline events and link discipline
- scope enforcement rules

Variable (tenant/customer/domain):
- the vocabulary for `kind` values (e.g., `missing_punch`, `undercoverage`)
- which flag kinds require approvals to close/waive
- severity mapping thresholds and escalation rules

