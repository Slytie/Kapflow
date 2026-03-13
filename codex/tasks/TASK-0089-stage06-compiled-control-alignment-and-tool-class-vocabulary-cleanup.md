---
id: TASK-0089
epic: EPIC-070
title: "Stage06 compiled-control alignment and tool-class vocabulary cleanup"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0052", "TASK-0061", "TASK-0069"]
risk: medium
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-025.md"]
patterns: ["PATTERN-005", "PATTERN-003"]
---

## Objective
Align the bounded Stage06 OpenAI sandbox with the compiled-control execution-metadata posture used by newer agent runtimes, remove Stage06's hardcoded execution-spec/tool-class dependency where authored or registry-backed metadata can provide it, and clarify the distinction between authored allowed tool classes and engine-specific runtime tool-class strings.

## Non-goals
- no new Stage06 business capabilities,
- no broadening of Stage06 autonomy beyond the existing single-call bounded review sandbox,
- no re-promotion of legacy `schedule_planning.v1` as the primary agentic scheduling surface,
- no workflow-pack redesign or generalized multi-agent framework work.

## Source Files Changed
- `src/onetruth/infrastructure/definitions/control_layer.py`
- `src/onetruth/application/services/stage06_openai_sandbox.py`
- `schemas/agentic/tool_class_registry.yaml`
- `docs/planning/EXECUTION_SESSION_RUNTIME_MODEL.md`
- `tests/unit/test_reference_stage_runtime_alignment.py`
- `tests/runtime/test_execution_session_runtime.py`
- `tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0089-stage06-compiled-control-alignment-and-tool-class-vocabulary-cleanup.md`

## Verification Run
- `PYTHONPATH=src pytest -q tests/unit/test_reference_stage_runtime_alignment.py` - passed (`.. [100%]`)
- `PYTHONPATH=src pytest -q tests/runtime/test_execution_session_runtime.py` - passed
- `PYTHONPATH=src pytest -q tests/runtime/api/test_stage06_openai_review_sandbox_api.py` - passed (`... [100%]`)
- `python scripts/validate_repo.py` - could not run in this environment (`python` was not installed)
- `python3 scripts/validate_repo.py` - first rerun failed because `TASK-0073` had not been written yet; reran after creating this task file and passed (`1365 check(s) passed`)

## Acceptance Criteria Coverage
- Stage06 no longer hardcodes its execution-spec identifier; pinned execution semantics are derived from authored Stage06 execution-profile control plus a registry-backed runtime tool binding.
- The engine-specific Stage06 runtime tool-class string is explicitly modeled as a runtime binding and kept distinct from authored `allowed_tool_classes` capability vocabulary.
- Runtime binding validation now fails closed if a Stage06 runtime binding claims authored tool classes not allowed by the Stage06 execution profile.
- The bounded Stage06 sandbox remains a single-call review classifier path with no business-semantics or autonomy expansion.

## Completion Notes
- Added a small control-layer helper for reference-only stage runtimes so legacy Stage06 can pin richer execution semantics without introducing a second authored workflow-definition system.
- Kept the Stage06 sandbox's actual bounded runtime budget (`max_tool_calls=1`) while explicitly recording the underlying authored Stage06 execution profile and runtime tool binding relationship in pinned execution evidence.
- Added focused unit/runtime/api coverage for the authored-vs-runtime tool-class split and Stage06 compiled-control alignment.
- `git diff --check` passed after the cleanup/doc updates.
- Backlog sync note: this task was formerly duplicated as `TASK-0073` before the truth-alignment planning sync. The Stage04 iterative agent-loop task keeps canonical ownership of `TASK-0073`.
