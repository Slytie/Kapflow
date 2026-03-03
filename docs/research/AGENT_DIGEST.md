# Agent Digest — Research Library

This is a curated map of the research documents in `docs/research/full/`.

## How to use (Codex / fresh session)
- **Default:** read this digest only.
- **Escalate:** open a full doc when you need deeper detail to justify a design choice.
- **Do not invent rules:** if something impacts invariants, audit, isolation, authority, or sandboxing, update the relevant authoritative docs under `docs/architecture/`, `docs/workflows/`, or `schemas/`.

## External pattern library

We also maintain an LLM-friendly architecture pattern library under `docs/patterns/`:

- `docs/patterns/PATTERN_INDEX.yaml` — index of external patterns, tagged and mapped to epics.
- `docs/patterns/cards/` — short pattern cards (default read path).
- `docs/patterns/sources/converted/` — full extraction notes (open only when needed).

**Rule:** do not load full source notes unless the task directly touches that subsystem; prefer cards first.

## Quick index

| ID | Topic | Full doc | When to read | Most relevant areas |
|---|---|---|---|---|
| R01 | Architecture + planning formats (ADRs, viewpoints, PRR) | `full/best-practices-for-software-architecture-and-planning-formats-for-complex-softwa.md` | When writing or refreshing architecture docs, ADRs, or readiness checks | `docs/adr/`, EPIC-080 |
| R02 | Research-backed implementation plan for this product class | `full/research-backed-implementation-plan-for-a-human-first-enterprise-process-orchest.md` | When validating stage gates, sign-offs, and delivery workflow | EPIC-080, EPIC-090 |
| R03 | Logistics-specific multi-tenant HITL agentic workflow architecture | `full/architecture-best-practices-for-a-multi-tenant-human-in-the-loop-agentic-workflo.md` | When deciding low-latency loops, ops metrics, and tenancy controls | EPIC-010, EPIC-050, EPIC-080 |
| R04 | HITL orchestration architecture checklist | `full/architecture-best-practices-checklist-for-a-human-in-the-loop-business-process-o.md` | Use as a pre-flight review checklist across epics | all epics; especially EPIC-010, EPIC-020, EPIC-070 |
| R05 | Artifact versioning + spreadsheet-first orchestration | `full/artifact-versioning-and-safe-spreadsheet-oriented-orchestration-for-an-mvp.md` | When implementing artifact store, promotions, or lineage | EPIC-030, TASK-0030 |
| R06 | Reasoning models + tool-use integration patterns | `full/best-practices-for-integrating-reasoning-models-with-tool-use-into-a-new-applica.md` | When designing tool router, model gateway, safety budgets | EPIC-060, EPIC-070 |
| R07 | Agent-ready payroll task instruction system | `full/agent-ready-payroll-task-instruction-system-for-a-same-day-logistics-payroll-mvp.md` | When shaping payroll task cards, approvals, and segregation of duties | Payroll workflow, EPIC-050, EPIC-060 |
| R08 | End-to-end delivery workflow for enterprise HITL BPM/case platforms | `full/end-to-end-delivery-workflow-for-an-enterprise-human-in-the-loop-bpm-and-adaptiv.md` | When checking whether delivery artifacts or sign-off gates are missing | EPIC-080, EPIC-090 |
| R09 | Codex / LLM-friendly repo research report | `full/deep-research-llm-friendly-repo.md` | When evolving repo scaffolding for stateless agents | `AGENTS.md`, `codex/`, `docs/status/` |
| R10 | Test-driven development for durable orchestration | `full/test-driven-development-for-multi-tenant-hitl-orchestration-platform.md` | When defining test strategy, CI gates, and durable-state validation | `docs/planning/TEST_STRATEGY.md`, EPIC-080, EPIC-090 |

## Summaries

### R01 — Architecture + planning formats
**Why it matters:** architecture is a set of decisions plus evidence, and lightweight governance reduces late-stage surprises.

**Apply here:**
- Keep ADRs in `docs/adr/`.
- Keep authority docs short and stable; move deep rationale into ADRs or research notes.
- Use readiness-review thinking for EPIC-080.

### R02 — Research-backed implementation plan
**Why it matters:** staged delivery with explicit gates is the safest path when durability, isolation, auditability, and automation safety are the hardest-to-fix failures.

**Apply here:**
- Treat epic completion as a gate, not merely progress.
- Ensure each gate has acceptance tests, measurable ops signals, and security review hooks.

### R03 — Logistics-specific HITL workflow architecture
**Why it matters:** same-day logistics has fast loops and high exception rates; designs that assume batch-only flows or no timers/escalations fail operationally.

**Apply here:**
- Keep claim leases and at least one SLA timer in human-task semantics.
- Keep stuck-work and stale-run signals visible in ops guidance.

### R04 — HITL orchestration architecture checklist
**Why it matters:** provides a broad checklist spanning artifact-centricity, multi-tenant isolation, audit content, and LLM risk classes.

**Apply here:**
- Use it as a design-review checklist.
- If an item cannot be satisfied in MVP, record it as a deferred risk with a compensating control.

### R05 — Artifact versioning + spreadsheet-first orchestration
**Why it matters:** strengthens the posture that artifacts are state-bearing objects, not just attachments, and that promotions and lineage must be precise.

**Apply here:**
- Keep dataset keys enumerated.
- Promotions must record the exact artifact version promoted and surface drift.
- Lineage should minimally link inputs used to outputs produced per run.

### R06 — Reasoning models + tool-use integration patterns
**Why it matters:** models propose; systems execute under policy. Tool execution needs budgets, allowlists, and consistent constraints.

**Apply here:**
- Keep server-side policy gating explicit.
- Keep the sandbox baseline concrete even if automation scope is initially small.

### R07 — Agent-ready payroll instruction system
**Why it matters:** provides payroll-specific task-card framing with segregation of duties, strong provenance, and idempotent tool execution.

**Apply here:**
- Use it to shape payroll task evidence and approval discipline.
- Keep preparer / approver separation visible in workflow design.

### R08 — End-to-end delivery workflow for enterprise HITL platforms
**Why it matters:** reinforces gate-based delivery and highlights common failure modes around durability, isolation, auditability, and automation safety.

**Apply here:**
- Use it to sanity-check stage gates and delivery artifacts.

### R09 — Codex / LLM-friendly repo research report
**Why it matters:** formalizes the repo-as-externalized-memory pattern.

**Apply here:**
- Keep `AGENTS.md` short and stable.
- Keep `docs/status/CURRENT_FOCUS.md` current and trustworthy.
- Prefer pattern cards and context packs over long essays for routine tasks.

### R10 — Test-driven development for durable orchestration
**Why it matters:** tests are the main mechanism that prevents regressions in durability semantics, tenant isolation, audit correctness, and automation safety.

**Apply here:**
- Treat workflow logic as a deterministic reducer when possible.
- Make idempotency and dedupe explicit test targets at each retry boundary.
- Add replay, adversarial, and containment suites as the implementation appears.
