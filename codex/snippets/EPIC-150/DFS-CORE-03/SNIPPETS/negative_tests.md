# DFS-CORE-03 Negative Tests

## Blocking tests

```text
T1 — AI proposal cannot self-review.
T2 — Proposal import cannot smuggle reviewed/official state.
T3 — Bulk accept requires PM role; AI/service accounts are denied.
T4 — Bulk accept requires fresh projection snapshot.
T5 — Bulk accept creates review decisions, not baseline rows directly.
T7 — Same digest never collapses source occurrences.
T13 — Missing selected_items cannot mean all rows.
T14 — Concurrent bulk accept is idempotent.
T15 — Proposal lineage survives supersession/withdrawal.
T19 — Metadata-only proposal run sends no raw text, full paths, URIs, or credentials.
T20 — Backend rejects stale snapshot/source occurrence versions.
```

## Key invariant assertions

```text
No AI proposal row can directly create ReviewedCorpusBaseline.
No folder path is project truth.
No digest equality merges SourceOccurrence rows.
No local deletion removes evidence custody.
No reviewed baseline row is official without a separate officialization workflow.
No PM bulk action executes without explicit selected_items.
No raw project data is sent to ML under metadata_only policy.
```
