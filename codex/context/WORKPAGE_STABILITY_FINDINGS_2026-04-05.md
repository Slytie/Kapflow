# Workpage stability findings - 2026-04-05

This note records the concrete findings that motivated EPIC-132 and EPIC-133.

These findings are historical evidence from 2026-04-05. They are not automatically the live repo truth. `TASK-0211` must reconcile them against the current checkout before classifying any item as still open.

## Historical repo-state findings
### 1. The uploaded repo snapshot was dirty relative to `HEAD`
The 2026-04-05 working tree contained modified workpage/backend/frontend/doc files on top of the last commit.

High-signal modified files in that snapshot included:
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/application/services/workpage_descriptors.py`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/pages/DispatchReportWorkpagePage.tsx`
- several docs/fixture files

Interpretation at the time:
- the repo was not in a finished closeout state,
- some cleanup had been started but not fully landed.

### 2. The dirty delta introduced a shared write-path regression
The 2026-04-05 working tree removed `from uuid import uuid4` from:
- `src/onetruth/application/handlers/workpages.py`

but still called `uuid4()` inside `_create_workbook_artifact_version(...)`.

Effect at the time:
- several public write paths returned `500` with `NameError`.

### 3. Clean `HEAD` still had at least one committed reliability/test-truth gap
Representative failing test at clean `HEAD` in the 2026-04-05 analysis:
- `tests/runtime/api/test_workpages_artifact_eod_contract.py::test_canonical_eod_draft_create_replays_idempotently_without_duplicate_artifacts`

Observed problem at the time:
- the test asserted whole-run artifact count instead of the semantic EOD draft artifact family.

### 4. Frontend verification depended on environment truth
The 2026-04-05 environment review found meaningful frontend coverage, but reproducible execution depended on:
- Node 20,
- clean install from the committed lockfile,
- not treating packaged local `node_modules` as source truth.

## Architectural debts that remained live in the 2026-04-05 review
### 1. Client-side lineage/history reconstruction
`frontend/src/lib/repositories/workpagesRepository.ts` listed workflow-run artifacts and filtered by kind client-side for core history rails.

### 2. Client-owned workflow intent
Frontend create/submit calls still sent raw `subject_link` payloads.

### 3. Demo-shell dual mutation path
`frontend/src/components/workpages/InlineLogisticsWorkpages.tsx` still owned create/submit/history orchestration for inline demo workpages.

### 4. Large concentration files
Approximate sizes observed:
- `src/onetruth/application/handlers/workpages.py` ~2240 lines
- `src/onetruth/application/services/logistics_workpages.py` ~4370 lines
- `frontend/src/components/workpages/InlineLogisticsWorkpages.tsx` ~938 lines
- `frontend/src/pages/LogisticsScheduleWorkpagePage.tsx` ~1028 lines

## Consequence for planning
These findings support a strict order:
1. **EPIC-132 first** - settle correctness, repo truth, and reproducible verification.
2. **EPIC-133 second** - reduce accidental complexity and future fragility.

## Live reconciliation reminder
When using this note after 2026-04-05:
- verify the live checkout first,
- classify which findings are already resolved,
- classify which findings are still open in supported environments,
- and defer the still-real client-owned/decomposition debts to EPIC-133 unless they block settlement directly.
