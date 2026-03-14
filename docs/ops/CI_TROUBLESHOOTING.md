# CI Troubleshooting

This note covers common CI issues for the GitHub Actions workflows:
- `main` (`.github/workflows/main.yml`)
- `agent_api` (`.github/workflows/agent_api.yml`)

## Common failures

### Python dependency install failures
Symptoms:
- `pip install` fails before tests start.
- missing module errors during `make`/`pytest` steps.

Checks:
- `requirements.txt` is only a compatibility shim; local and CI installs should use `python3.11 -m pip install -e ".[api,dev]"`.
- confirm `pyproject.toml` editable extras install cleanly in a fresh Python `3.11` environment.
- confirm test/runtime dependencies are available under the same interpreter that `make` uses.

### Make target failures
Symptoms:
- one of `make schema-validate`, `make contract`, `make replay`, `make acceptance`, `make runtime`, or a `make release-confidence-*` target fails.

Checks:
- run the same target locally and fix the first failing assertion.
- for trace/schema failures, start with `python3 scripts/validate_repo.py --schemas-only` or `--traces-only`.

### Release-confidence slice failures
Symptoms:
- one `release-confidence / <slice>` matrix check fails in `main`.

Checks:
- rerun just that slice locally:
  - `make release-confidence-validation`
  - `make release-confidence-demo-export`
  - `make release-confidence-projection-coherence`
  - `make release-confidence-logistics-weekly-live`
  - `make release-confidence-certification-manifest`
- if `certification-manifest` fails, inspect the emitted `certification_manifest.json` referenced in command output.

### Frontend job failures
Symptoms:
- `npm ci`, `npm run typecheck`, `npm run test:run`, or `npm run build` fails in `frontend`.

Checks:
- run from repo root:
  - `cd frontend && npm ci`
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run test:run`
  - `cd frontend && npm run build`
- ensure `frontend/package-lock.json` is in sync with `frontend/package.json`.

### OpenAI integration step skipped
Symptoms:
- `agent_api` prints that OpenAI integration tests were skipped.

Expected behavior:
- skip is expected when `OPENAI_API_KEY` secret is not configured.
- skip is also expected if no `tests/integration_openai` directory exists.

## Local reproduction
Run the same baseline checks CI runs:

```bash
make schema-validate
make contract
make replay
make acceptance
make runtime
pytest -q
```

Run the release-confidence gate locally:

```bash
make release-confidence
```

Run OpenAI integration tests locally (only when key is set):

```bash
ONETRUTH_RUN_OPENAI_E2E=1 OPENAI_API_KEY=... PYTHONPATH=src pytest -q tests/integration_openai
```

## Manual `agent_api` workflow run
1. Open GitHub -> Actions -> `agent_api`.
2. Click **Run workflow**.
3. Select the target branch and run.

The workflow always runs baseline non-network checks first, then conditionally runs OpenAI integration tests.

## Confirm secret exists (without printing it)
In GitHub:
1. Go to Settings -> Secrets and variables -> Actions.
2. Confirm a secret named `OPENAI_API_KEY` exists.
3. Do not print or echo secret values in logs.

In workflow logs:
- look for the gating message:
  - present: OpenAI integration tests execute.
  - missing: workflow prints skip message and exits successfully.
