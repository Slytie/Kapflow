# EPIC-149 Context Pack - CAPEX QA/TDD and semantic tests

Purpose:
- Rehydrate the CAPEX v6 task tranche for `EPIC-149` without opening the full master package.
- Keep future work inside the existing one-truth runtime, approval, artifact, pointer, and event model.

## Imported source rows
TEST-001, TEST-002, TEST-004, QD-001, QD-002, QD-003, QD-004, QD-005, ... plus SME-RP source row `TASK-0639` remapped to repo `TASK-0662` (71 tasks total)

## Current closeout notes
- `TASK-0568` is closed as of 2026-06-09: the repo now has a `capex_semantic` pytest marker, `docs/planning/CAPEX_CB2_SEMANTIC_TEST_BACKLOG.yaml`, `make capex-semantic-tests`, a visible GitHub Actions lane, and real-owner CODEOWNERS coverage. This is quality-gate evidence only, not CAPEX activation.

## SME-RP addendum rows
- `TASK-0662` adds generalized subject-matter negative-test obligations under `SME-RP-G013`.
- `K12-T1..T10` are the first binding cases for these tests, not a top-level acceptance namespace.

## Load first
- `docs/planning/epics/EPIC-149.md`
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/capex_real_project_acceptance/SME_RP_ACCEPTANCE_REGISTER.yaml`
- `docs/architecture/invariants.md`
- `docs/status/CURRENT_FOCUS.md`

## Non-negotiable invariants
- One truth system: official claims come only from immutable objects, append-only events, and audited pointers.
- Tenant, domain, and future CAPEX project boundaries must not be crossed in reads, writes, exports, projections, or generated material.
- Raw K12/K3/blind corpus files stay off-repo; only sanitized fixtures, manifests, hashes, and aggregate evidence may be committed.
- Generated artifacts, Workflow Lab reports, and AI output are not source authority.
- Production/lab activation is release-mediated and remains blocked until the relevant gates close or receive explicit waivers.

## Preferred implementation posture
- Start with the source task's required tests or evidence.
- Update repo-native authoritative source before downstream generated artifacts.
- Keep implementation PRs small enough to review against the source row and acceptance gate.
- Preserve logistics weekly/live current focus unless a CAPEX task explicitly changes shared semantics.

## Stop line
- Do not import raw project corpus content.
- Do not activate CAPEX runtime/product behavior merely because a planning task exists.
