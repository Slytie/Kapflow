# OPENAI_API_E2E_SANDBOX_SPIKE.md

## Purpose
This spike exists to validate one real model-assisted workflow hop before hardening broader execution-session/tool orchestration. We need concrete evidence on request shape, schema adherence, failure mapping, and canonical evidence persistence when a real OpenAI call is in the loop.

## First use case
Primary and only use case in this spike:
- Stage06 review outcome classification for `review_packet` human tasks.

Input scope:
- canonical Stage06 review-ready example documents (artifact-backed via existing ingress path),
- linked task/workflow metadata,
- bounded instruction context.

Structured output schema (strict):
- `outcome`: `draft_is_publish_ready | review_requires_more_information | review_requests_changes`
- `rationale_summary`: string
- `evidence_refs`: string[]
- `suggested_follow_on_task_kind`: `null | final_review | information_request | work_item`

## Why Responses API
New work uses the OpenAI Responses API so this path aligns with the current OpenAI surface and avoids adding legacy/deprecated API shape debt.

## Why structured outputs
Structured outputs keep the path bounded and testable:
- no free-form decision payloads,
- explicit contract validation before canonical workflow mutation,
- deterministic mapping into existing Stage06 completion outcomes.

## Data flow (bounded sandbox)
1. Resolve Stage06 `review_packet` task + workflow scope from canonical runtime rows.
2. Resolve input artifact refs from canonical artifact versions (example corpus seeded through existing harness).
3. Read bounded document text from artifact storage URI.
4. Call OpenAI Responses API with strict schema.
5. Validate and normalize structured output.
6. Persist model evidence/result metadata as canonical artifact version.
7. Complete task through existing `tasks.complete` handler using returned `outcome`.
8. Follow-on task truth is emitted only by existing canonical spawn logic.

No drag, no autonomous loops, no side-channel state.

## Canonical persistence
Persisted canonically:
- evidence artifact version containing structured model output + run metadata,
- links to input artifact version ids/content digests,
- canonical completion/spawn events produced by existing handlers.

Not authoritative:
- transient logs,
- local in-memory model transcript state.

## Gating model
Real-network e2e tests are opt-in only.

Required gate:
- `ONETRUTH_RUN_OPENAI_E2E=1`

If gate is on but required config is missing, tests fail clearly.
If gate is off, real-network tests are skipped.

This keeps default local/PR fast suites deterministic and network-free.

## Environment variables
Required for real run:
- `OPENAI_API_KEY`

Optional:
- `ONETRUTH_OPENAI_MODEL` (default from adapter)
- `ONETRUTH_OPENAI_BASE_URL` (default `https://api.openai.com/v1`)
- `ONETRUTH_OPENAI_TIMEOUT_SECONDS`
- `ONETRUTH_OPENAI_MAX_RETRIES`
- `ONETRUTH_ARTIFACT_ROOT` (where evidence json files are materialized before canonical artifact registration)

## Failure handling
Mapped as explicit categories:
- missing/invalid config,
- upstream HTTP/auth/rate-limit/transient failures,
- malformed/non-schema model output,
- canonical persistence/transition failures.

Error payloads remain explicit and machine-readable; no silent fallback to non-canonical behavior.

## Cost and rate-limit precautions
- narrow single-use-case scope,
- bounded input excerpt size,
- minimal retry policy with capped attempts,
- gated execution only (manual/nightly),
- no background loops.

## Retry policy
- retry only transient upstream classes (e.g., timeout/429/5xx),
- capped retries with short backoff,
- no infinite retries,
- no hidden semantic retries after canonical mutation commit.

## Redaction / sensitivity assumptions
This spike uses repo example corpus fixtures intended for development/testing.
No production customer sensitive data is introduced by this spike.
If corpus sensitivity changes later, a redaction/classification policy must be added before expanding scope.

## Safe re-run procedure
1. Seed scenario fixture corpus through existing harness.
2. Run bounded sandbox endpoint for Stage06 task.
3. Inspect resulting evidence artifact + canonical events.
4. Re-run with new idempotency key for a fresh attempt.

Do not mutate canonical rows outside handlers to “repair” model outcomes.

## Decisions this spike should inform next
- execution-session/tool event shape needed for broader agent hardening,
- required metadata fields for audit and replay fidelity,
- provider-failure mapping and retry semantics,
- whether polling/read surfaces need dedicated agent-evidence projections,
- what to keep strict vs. configurable before generalized execution architecture.
