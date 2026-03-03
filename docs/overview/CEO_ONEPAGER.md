# CEO One-Pager - Stage 4 Vertical Slice MVP

## What we are building
An enterprise, multi-tenant operations orchestration platform where spreadsheets and documents are first-class immutable artifacts and operational workflows execute with durable semantics, approvals, and a complete audit timeline.

## Why this matters
Today the same business process can have:
- multiple "latest" files
- unclear approval history
- poor handoffs
- dashboards that are more persuasive than the underlying evidence

Stage 4 is designed to prove that we can support both human work and agentic assistance without splitting into multiple truth systems.

## What Stage 4 ships
- one implemented reference wedge: Payroll
- one dynamic pressure-test workflow pack: Schedule Planning (contract + fixtures; not implemented runtime in Stage 4)
- one explicit authority model
- one repo-native execution overlay per workflow
- one policy for generated derivatives like runbook packs and CompanyOS IR
- minimum safety, ops, and audit scaffolding

## What Stage 4 does not attempt
- broad workflow library
- full deterministic replay
- free-form method self-modification at runtime

## How to know it succeeded
- a fresh engineer or Codex run can tell what is authoritative
- generated artifacts do not drift silently from repo-native source
- Payroll can be implemented without semantic ambiguity
- Schedule Planning remains representable without breaking the same core laws
