# runtime/ - Runtime command-boundary smoke tests

These tests drive the real runtime CLI boundary (`python -m onetruth.cli`) end-to-end.

Current coverage:
- initialize a fresh runtime database via `init-db`,
- append canonical timeline envelopes,
- list timeline envelopes with ordering and filtering checks,
- enforce raw event-store idempotency behavior for duplicate `events append` `idempotency_key` values (explicit failure, no silent duplicate append),
- create/list/show workflow/task rows through CLI lifecycle commands,
- assert canonical command-boundary retry replay behavior through scoped command receipts (`idempotent_replay` + stable `receipt`),
- request/respond approvals and assert transactional `approval.*` event emission,
- create immutable artifact versions and assert transactional `artifact.version.created` emission,
- promote pointers with explicit conflict/race handling and assert transactional `artifact.pointer.promoted` emission,
- assert cross-linkage coherence across workflow/task/artifact/approval/pointer operations.
- execute Stage06 scenario fixtures step-by-step through CLI under `tests/runtime/scenarios/`,
- assert completion-driven Stage06 child-task spawning lineage + idempotency behavior,
- assert board/query read-surface JSON contracts under `tests/runtime/contracts/`,
- assert thin HTTP adapter contracts/mutations/scope-denial behavior under `tests/runtime/api/`.
