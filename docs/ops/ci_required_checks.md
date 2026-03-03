# CI required checks

Minimum CI checks for Stage 4 should include:

## Source contract checks
Run:
- `make schema-validate`
- `make contract`

This must validate at least:
- workflow contract YAML against `schemas/workflows/workflow_contract.schema.json`
- artifact map YAML against `schemas/workflows/artifact_map.schema.json`
- decision catalog YAML against `schemas/agentic/decision_catalog.schema.json`
- execution profile YAML against `schemas/agentic/execution_profile.schema.json`
- event envelope and event-type registry
- event payload schemas and trace bindings
- artifact metadata schema
- runtime object schemas
- governance vocabulary / permissions alignment
- tool-class registry coverage
- acceptance scenario catalog coverage (`AT-SCH-001` .. `AT-SCH-007`)

## Replay and acceptance checks
Run:
- `make replay`
- `make acceptance`

This must validate at least:
- Schedule Planning golden traces against the event envelope
- required link coverage from the event registry
- payload contracts from `schemas/events/payloads/*.schema.json`
- stable replay oracles for the Schedule Planning corpus
- AT-SCH acceptance evidence expectations

## Security and safety checks
Run:
- `make security`

This must validate at least:
- scope-isolation negative tests
- policy-gate denial before unapproved side effects
- fully-agentive approval-path preservation
- promotion drift scenario coverage
- degraded-mode scenario coverage
- no out-of-plan execution without explicit approval path once runtime exists

## Core semantic checks
Run:
- `make unit`
- `make property`

This must validate at least:
- reducer-level workflow and task semantics
- lease-expiry reopening behavior
- artifact lineage acyclicity
- replay determinism over the trace corpus

## Repo hygiene checks
- docs index points at existing files
- task index matches task files
- current focus references existing task files
- no stale approval vocabulary or actor taxonomy remains (`approval.grant`, `user` actor type, etc.)
