# Governance vocabulary

This repo has one shared vocabulary for approval responses, approval outcomes, actor taxonomy, and the permission actions that govern approvals.

The machine-readable source is:
- `schemas/policy/governance_vocabulary.yaml`

## 1) Actor taxonomy
Canonical actor types are:
- `human` - an interactive user principal acting manually
- `agent` - an agent principal acting through the same canonical workflow/task/approval path
- `service` - a service or worker identity operating under policy and scope controls
- `system` - platform-owned housekeeping or migration-safe system activity

Do not use `user` as a peer actor type. Use `human` instead.

## 2) Approval vocabulary
The repo distinguishes three related but different layers.

### Response verbs
These are the interactive choices offered to a reviewer:
- `approve`
- `reject`
- `request_changes`
- `cancel`
- `expire`

### Recorded outcomes
These are the canonical outcomes written onto the timeline:
- `approved`
- `rejected`
- `changes_requested`
- `canceled`
- `expired`

### Mapping
- `approve -> approved`
- `reject -> rejected`
- `request_changes -> changes_requested`
- `cancel -> canceled`
- `expire -> expired`

This distinction matters because a UI may offer response verbs while the timeline records the resulting outcome.

## 3) Canonical approval permission actions
Approval permissions are expressed with exactly two canonical actions:
- `approval.request`
- `approval.respond`

Do not use `approval.grant`.

`approval.respond` is the capability to emit a canonical `approval.responded` event with one of the approved outcome values.

## 4) Debug-tenant rule for agent principals
The Stage 4 fully-agentive Schedule Planning objective allows designated agent principals to act through the same canonical task and approval pathways in debug tenants.

That means:
- actor type may be `agent`
- the same approval object model still applies
- the same permission actions still apply
- the same event vocabulary still applies

It does **not** authorize a second agent-only decision or state system.
