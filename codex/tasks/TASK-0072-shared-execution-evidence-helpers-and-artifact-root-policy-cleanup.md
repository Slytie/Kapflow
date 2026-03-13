---
id: TASK-0072
epic: EPIC-070
title: "Shared execution-evidence helpers and artifact-root policy cleanup"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0066", "TASK-0069", "TASK-0071"]
risk: medium
context_packs: ["EPIC-070"]
patterns: ["PATTERN-005", "PATTERN-003"]
---

## Context
The repo now has two bounded OpenAI execution paths (legacy Stage06 and weekly Stage04). They both persist execution evidence, and the helper logic had started to drift across the two services.

## Objective
Consolidate shared execution-evidence helpers into one repo-native service and clarify the local/dev/test artifact-root policy without changing business semantics.

## Non-goals
- No business-semantics changes.
- No Stage06 compiled-control migration in this task.
- No large new abstraction framework.

## Source Files Changed
- `src/onetruth/application/services/execution_evidence.py`
- `src/onetruth/application/services/stage06_openai_sandbox.py`
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `docs/planning/EXECUTION_SESSION_RUNTIME_MODEL.md`
- `docs/planning/WEEKLY_STAGE04_OPENAI_AGENT_RUNTIME.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0072-shared-execution-evidence-helpers-and-artifact-root-policy-cleanup.md`

## Verification Run
- `PYTHONPATH=src pytest -q tests/runtime/test_execution_session_runtime.py`
- `PYTHONPATH=src pytest -q tests/runtime/test_weekly_stage04_execution_runtime.py`
- `PYTHONPATH=src pytest -q tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `PYTHONPATH=src pytest -q tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `python3 -m compileall -q src tests scripts`

## Acceptance Criteria Coverage
- Duplicated helper logic for stable execution IDs, artifact-root resolution, and prepared evidence persistence now lives in `execution_evidence.py`.
- Stage06 and weekly Stage04 continue to write canonical execution evidence with the same bounded artifact/linkage style.
- Artifact-root policy is documented clearly for local/dev/test usage: `ONETRUTH_ARTIFACT_ROOT` is the isolation knob, and the default live root is local-only evidence rather than fixture/source authority.
- Targeted Stage06 and weekly Stage04 tests cover the shared storage-root behavior via canonical artifact `storage_uri` assertions.

## Completion Notes (2026-03-13)
- Kept the helper surface intentionally small: shared ID generation, artifact-root resolution, and persistence moved into `execution_evidence.py`; task-specific policy and payload logic stayed in Stage06/Stage04 services.
- Preserved canonical evidence kinds, metadata, links, and lifecycle behavior; this task only removed duplication and aligned the local evidence-root posture.
- Weekly Stage04 and Stage06 now prove the configured artifact root through API-level evidence path assertions, reducing the chance of future drift.
