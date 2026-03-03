# TEST_STRATEGY.md - Test-driven development for Stage 4 (Codex-friendly)

This document turns our research-backed TDD guidance into **repo-native rules** and a **test portfolio** that locks in the platform invariants.

> Key idea: for a durable, multi-tenant, human-in-the-loop orchestration platform, **tests are the primary mechanism for preventing regressions** in:
> - durability (retries, idempotency, replay determinism)
> - auditability (complete timeline + strong linking)
> - tenant isolation / authorization
> - automation safety (policy-gated tools, sandbox containment)
>
> See research: `docs/research/full/test-driven-development-for-multi-tenant-hitl-orchestration-platform.md`.

## Non-negotiable testing rules (Stage 4)

### T1) Workflow logic must be testable as a deterministic reducer
Model core workflow/case logic as a deterministic state transition function:

\[
s_{t+1} = f(s_t, e_t)
\]

- Tests MUST cover illegal transitions (fail closed).
- Any introduced non-determinism in `f` is considered a **release-blocking defect**.

### T2) Idempotency is a first-class contract
For any operation that can retry (API mutation, worker processing, tool execution request):
- Require an idempotency key.
- Tests MUST prove "retry does not duplicate effects."

### T3) Tenant + domain isolation must have CI-blocking negative tests
- Cross-tenant reads/writes must fail and be logged.
- Cross-domain reads/writes must fail unless explicitly tenant-global.
- Isolation tests must cover background consumers/exporters, not only API endpoints.

### T4) Audit truth is not "best effort"
- Authoritative TimelineEvents must be emitted with state transitions (commit-path).
- Export/index/search pipelines may lag/fail (fail-open), but this must be visible and testable (degraded mode).

### T5) Agent/tool safety requires adversarial regression tests
Even in MVP:
- No tool execution with side effects without policy + approval.
- Tool outputs are treated as untrusted data (not instructions).
- Add regression tests for prompt/tool injection patterns and for redaction failures.

### T6) The primary vertical slice must support a fully-agentive debug path
For the primary Schedule Planning slice:
- every in-scope stage must be exercisable by agent-owned work,
- approvals must still travel through the canonical approval model,
- tests must prove that agentive execution does **not** create agent-only authoritative state.

## Test portfolio (what we build)

We follow the test pyramid, but extend it with replay, idempotency, and agent-security suites.

### Unit tests (fast)
**Goal:** lock down core invariants as pure logic.
- Workflow reducer / state-machine transitions (`s' = f(s,e)`).
- Validators (artifact metadata, event envelope).
- Policy decision wrappers (allow/deny/require-approval).

### Contract tests (CDC)
**Goal:** prevent breaking changes between independently deployable components.
- Event envelope schema compatibility.
- Tool-plane execute API envelope compatibility.
- Policy decision API contract.

### Integration tests (real dependencies)
**Goal:** catch serialization/storage/idempotency bugs that mocks hide.
- DB + unique constraints for idempotency.
- Object store metadata + artifact version writes.
- Queue/workers: retry semantics, deadletters, lease recovery.

### Property-based tests (invariant exploration)
**Goal:** find edge cases beyond hand-written examples.
- Lineage graph is acyclic.
- Replay determinism on random event histories.
- Idempotency equivalence classes.

### Replay tests (history compatibility)
**Goal:** prevent upgrades from breaking historical run interpretation.
- Store "golden" event histories.
- Replay and assert resulting state and critical derived fields are stable.

> Note: Stage 4 product posture does **not** promise full deterministic replay for all effects, but we still require replay determinism for *workflow state logic*.

### End-to-end acceptance tests (minimal, high value)
**Goal:** prove the vertical slice.
- Schedule Planning happy path (Stage03-Stage07).
- Schedule Planning major replan + additive delta semantics.
- Schedule Planning fully-agentive whole-flow run.
- Red-team negatives: drift-after-review, degraded audit export, cross-scope access attempts.
- Payroll remains a secondary linear-approval reference corpus.

### Scheduled adversarial / failure-mode tests
**Goal:** confidence under turbulence.
- Worker crashes, retries, partitions, clock skew (as hypothesis-driven experiments).
- Sandbox "deny network / deny file / deny syscall" fixtures.
- Prompt/tool injection corpus regression suite.


## Current repo harness (now implemented)
The repo now includes an initial executable TDD harness:
- `tests/helpers/reference_model.py` - small, non-authoritative replay reducer for trace oracles
- `tests/helpers/scenario_catalog.py` - stable `AT-SCH-001` .. `AT-SCH-007` mapping
- `tests/contract/` - validator and scenario-catalog checks
- `tests/replay/` - replay and final-state oracles
- `tests/acceptance/` - acceptance evidence checks
- `tests/security/` - cross-scope and policy-gate negatives

Use `docs/planning/TDD_IMPLEMENTATION_PLAN.md` for the repo-native working order and commands.

## CI gates (high-level)

### Pre-merge (fast)
- Unit tests
- Schema validation (events/artifacts/policy/workflow packs)
- Contract tests (where applicable)
- "Replay smoke": small set of golden histories for changed workflow logic

### Post-merge (slower)
- Integration tests with real deps
- Isolation test suite (cross-tenant + cross-domain)
- Acceptance suite (Schedule Planning vertical slice)

### Nightly / scheduled
- Full replay suite
- Adversarial agent-security corpus
- Sandbox containment suite
- Failure-mode/chaos experiments (targeted)
- Payroll reference corpus checks

## How Codex tasks should use this
Every task brief in `codex/tasks/` must include:
- **Test-first plan:** which tests fail first and why
- **Verification commands:** what must pass locally/CI
- **Oracle:** what artifacts/events prove success (e.g., golden trace)
