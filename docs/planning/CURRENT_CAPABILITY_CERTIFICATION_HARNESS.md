# CURRENT_CAPABILITY_CERTIFICATION_HARNESS.md

## Purpose
This harness certifies the currently implemented demo/scenario surface as a repeatable release-confidence gate:

`seed -> canonical run -> derived workspace/export artifacts -> invariant checks -> certification manifest`

It does not add new runtime semantics. It orchestrates existing entrypoints and verifies invariant expectations.

## Entrypoint
- `scripts/run_current_capability_certification.py`

Default certified scenarios:
1. `stage06_publish_ready` (workspace demo + export bundle)
2. `stage07_major_replan` (workspace demo + export bundle)
3. `logistics_weekly_to_live_golden_slice` (weekly->live handoff activation slice)

## Run
```bash
PYTHONPATH=src python3 scripts/run_current_capability_certification.py \
  --db-url sqlite:///.tmp/current-capability-certification.db \
  --certification-key release-candidate \
  --output-root artifacts/certification/current_capability \
  --openai-mode mock \
  --json
```

Run one scenario only:
```bash
PYTHONPATH=src python3 scripts/run_current_capability_certification.py \
  --db-url sqlite:///.tmp/current-capability-certification.db \
  --certification-key release-candidate \
  --output-root artifacts/certification/current_capability \
  --scenario stage07_major_replan
```

## Outputs
For a key `K`, output is written under:
- `artifacts/certification/current_capability/K/`

Primary files:
- `certification_manifest.json` (machine-readable gate artifact)
- `certification_manifest.md` (human summary)
- `<scenario_id>/...` scenario-local artifacts and bundles

Per scenario manifest fields include:
- canonical command/entrypoint records (`entrypoint_commands`)
- run IDs and edge execution IDs (`run_ids`, `edge_execution_ids`)
- output bundle path (`output_bundle_path`)
- invariant result rows (`invariants`)
- invariant summary (`invariant_summary`)

## Gate semantics
- Exit code `0`: all selected scenarios passed invariants.
- Exit code `1`: at least one scenario failed or one scenario command errored.

When failed, inspect:
1. `certification_manifest.json` scenario `status` and `error` fields.
2. scenario-local bundle paths for evidence and run IDs.
