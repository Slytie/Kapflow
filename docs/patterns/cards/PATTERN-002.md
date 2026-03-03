---
pattern_id: PATTERN-002
title: "Flowable \u2014 BPMN/CMMN/DMN engine patterns for human tasks, jobs/timers,\
  \ and definition versioning"
source_notes: docs/patterns/sources/converted/Flowable_Engine_Architecture_Pattern_Extraction.md
tags:
- bpmn
- cmmn
- dmn
- human-tasks
- claim
- timers
- jobs
- definition-versioning
- optimistic-locking
applies_to_epics:
- EPIC-040
- EPIC-050
- EPIC-060
- EPIC-090
use_when:
- 'Defining **human task semantics**: candidate groups, claim, completion, deadlines/escalations.'
- Designing **timer/job execution** (durable waits, retries, deadletter).
- 'Designing **safe evolution**: how workflow definition versions relate to running
  instances.'
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-002 — Flowable — BPMN/CMMN/DMN engine patterns for human tasks, jobs/timers, and definition versioning

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Defining **human task semantics**: candidate groups, claim, completion, deadlines/escalations.
- Designing **timer/job execution** (durable waits, retries, deadletter).
- Designing **safe evolution**: how workflow definition versions relate to running instances.

## Key patterns to borrow

- **Command + interceptor pipeline for all state transitions**
- Why it works: makes every mutation explicit, composable, and easy to wrap with tx/retry/logging/security.
- Where: `CommandExecutorImpl.execute`, interceptor chain creation in `AbstractEngineConfiguration.initCommandInterceptors`. (`CommandExecutorImpl.java:27-38`, `AbstractEngineConfiguration.java:568-618`)
- Adaptation: model every registry update, run creation, promotion, and run completion as commands; install interceptors for tenancy, budgets, and audit.
- **CommandContext + close listeners (structured side effects)**
- Why: guarantees ordering: “do domain work → run close listeners → flush → commit/rollback”.
- Where: `CommandContext.close()` calls close listeners then flushes sessions; tx close listener commits/rollbacks. (`CommandContext.java:56-106`, `TransactionCommandContextCloseListener.java:28-71`)
- Adaptation: use close listeners to (a) write lineage edges, (b) emit outbox events, (c) update derived materializations—only if tx succeeded.
- **Agenda-driven micro-step execution**
- Why: clean small-step semantics; easy to interpose async boundaries; avoids deep recursion in process traversal.
- Where: `CommandInvoker.execute()` loops over `agenda.getNextOperation()`; `DefaultFlowableEngineAgenda` pre-registers operations. (`CommandInvoker.java:64-92`, `DefaultFlowableEngineAgenda.java:43-92`)
- Adaptation: implement your pipeline engine as an agenda of operations: `EvaluateEligibility`, `StartRun`, `CompleteRun`, `SpawnChild`, etc.
- **Explicit token/execution tree as runtime state**
- Why: concurrency and nested scopes become first-class; durable waiting is just “token at node + persisted state”.

## Pitfalls / what *not* to copy

- Why mismatch: your orchestration should be **artifact.promoted-driven**, not “wall-clock assumptions”.
- Where: `AcquireTimerJobsRunnable` loops and waits. (`AcquireTimerJobsRunnable.java:92-176`, `AcquireTimerJobsRunnable.java:237-264`)
- Adaptation: prefer event subscriptions + after-commit hints; keep timers only for SLA/escalation backstops.
- Why mismatch: your artifacts are immutable; variables are mutable state.
- Where: BPMN behaviors frequently `execution.setVariable(...)` (e.g., DMN task sets results). (`DmnActivityBehavior.java:142-164`)
- Adaptation: variables should store only immutable *artifact IDs/version IDs*, not the spreadsheet content.
- Why mismatch: durable orchestration must survive restarts.
- Where: `AbstractAgenda` has `futureOperations` and special handling for futures. (`AbstractAgenda.java:31-90`)
- Adaptation: disallow non-durable waits; represent waits only via persisted jobs/subscriptions.
- Why mismatch: you require explicit guardrails (max depth/spawn budget, cycle detection).
- Evidence status: **Unknown from code inspected** as a built-in engine feature; I did not find a first-class “cycle detection” or “spawn budget” mechanism in the inspected components. I searched for keywords like “cycle”, “spawn budget”, “max depth” in the job acquisition/config and core agenda layers and did not see such a mechanism. (Guardrails that *do* exist are mostly job acquisition rate limits: `AcquireJobsRunnableConfiguration`, `DefaultAsyncJobExecutor`.)
- --

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/Flowable_Engine_Architecture_Pattern_Extraction.md`
