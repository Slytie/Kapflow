# Example Document Corpus

`manifest.yaml` defines the executable document corpus used by:
- runtime scenario seeding,
- frontend snapshot exports,
- sandbox-input fixture preparation,
- approval/review evidence examples.

`seed_sets.json` mirrors stable seed-set IDs for lightweight consumers that only need deterministic set membership.

Rules:
- source files remain under `fixtures/workflows/*/template_pack/*_Example_COMPLETED.*`,
- ingestion must go through canonical artifact ingress (`artifacts ingest` / API upload),
- no second attachment truth system is introduced.

Refresh workflow:
1. update or add source example docs in the workflow template packs,
2. update `manifest.yaml` document and seed-set entries,
3. run scenario/snapshot tests and re-export frontend snapshots if needed.
