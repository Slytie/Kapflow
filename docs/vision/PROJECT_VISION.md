# Project vision

## Why this exists
Modern operations run on mutable spreadsheets, documents, chats, and ad-hoc approvals. The result is familiar:
- conflicting versions
- missing provenance
- silent state drift
- poor handoffs
- automation that amplifies ambiguity instead of reducing it

This project exists to make messy operational work tractable without making it brittle.

## Core product claim
We want a platform where:
- artifacts are immutable and attributable,
- officialness is explicit rather than implied by "latest",
- workflows remain auditable even when humans and agents collaborate,
- and adaptive methods can evolve without corrupting enterprise truth.

## Creative vision
The creative vision is not "lock everything down."

It is:
- let people and agents invent better methods,
- let workflows remain flexible where the world is genuinely dynamic,
- but anchor that flexibility inside stable laws:
  - one truth system
  - explicit scope
  - append-only narrative
  - explicit approvals
  - bounded automation

## Design stance
We take a process-first stance:
- work is a sequence of transformations over artifacts and decisions,
- dashboards and summaries are compressions of that process,
- and any compression used for governance must remain coherent with the underlying substrate.

## Business wedge
The repo currently uses two workflow families:
- **Payroll** - linear, gated, audit-heavy, approval-driven
- **Schedule Planning** - stable publication plus bounded exception handling for same-day delivery

This pairing is intentional. It prevents the platform from overfitting to one workflow shape.

## Agentic stance
Agents are valuable, but they are not the truth system.
They may:
- propose plans
- draft artifacts
- analyze discrepancies
- suggest method changes

The platform must still:
- validate
- authorize
- execute
- record
- promote

## What success looks like
A future engineer or Codex run should be able to answer:
- what is authoritative here?
- what is generated?
- what is safe to change?
- what must remain pinned for audit?
- how does a flexible method stay inside a stable substrate?

If those answers are not obvious from the repo, the repo is under-specified.
