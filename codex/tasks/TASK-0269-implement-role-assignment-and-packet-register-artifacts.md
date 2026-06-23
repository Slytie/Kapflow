---
id: TASK-0269
epic: EPIC-141
title: "Implement role assignment and packet register artifacts"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0268"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `INGEST-004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
AI suggests roles/packets, human reviews.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-141.md`
- `codex/context/EPIC-141.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: role correction; packet split/merge tests
- Acceptance gate: `AT-ROLE-001; AT-PACKET-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: role assignments; packet register; review states
- Review focus covered: AI draft not official; role not file identity
- Refactor focus covered: shared row state enum
- Docs requirement covered: packet workpage docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `INGEST-004`
- Source phase: `P5/P7 Corpus baseline`
- Source priority: `P0`
- Source area: `workflow/generated artifacts`
- Original depends_on: `INGEST-003`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Completion evidence
- Added `docs/planning/capex_source_ingest/ROLE_PACKET_REGISTER_CONTRACT.yaml` as the planning-only role/packet artifact contract for `INGEST-004`.
- Added `onetruth.capex_platform.role_packet_register` for deterministic `capex.role_assignment_register.v1` and `capex.packet_register.v1` payloads from sanitized SourceOccurrence refs.
- Added unit and contract coverage for role correction, packet split/merge, unknown refs, duplicate refs, raw material rejection, and the non-official baseline boundary.
- CAPEX runtime/product activation, raw corpus import, public routes, reviewed baseline creation, and official pointer creation remain blocked.
