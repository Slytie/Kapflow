# CI Troubleshooting

This note covers common CI issues for the GitHub Actions workflows:
- `main` (`.github/workflows/main.yml`)
- `agent_api` (`.github/workflows/agent_api.yml`)
- `agent_api_live` (`.github/workflows/agent_api_live.yml`)
- `dependency_review` (`.github/workflows/dependency_review.yml`)
- `codeql` (`.github/workflows/codeql.yml`)

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
- one of `make assurance-fast`, `make contract`, `make replay`, `make acceptance`, `make runtime`, or a `make release-confidence-*` target fails.

Checks:
- run the same target locally and fix the first failing assertion.
- for assurance failures, start with `python3.11 scripts/validate_repo.py --domain schema --domain governance --domain metadata --domain release --domain secrets`.
- for trace-only failures, use `python3.11 scripts/validate_repo.py --domain traces`.

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
- `agent_api` never runs live OpenAI tests.
- `agent_api_live` prints that weekly Stage04 real-network coverage remains skipped.

Expected behavior:
- `agent_api` is now mock-only by design; it should run `make PYTHON=python ci-fast-backend` and stop there.
- `agent_api_live` always runs the fast backend baseline first, then runs `tests/integration_openai` with `ONETRUTH_RUN_OPENAI_E2E=1`.
- weekly Stage04 real-network coverage still stays opt-in until `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1`.

### Live OpenAI secret/gate failures
Symptoms:
- `agent_api_live` fails before or during the real OpenAI step.

Checks:
- confirm repository secret `OPENAI_API_KEY` exists; `agent_api_live` now fails closed instead of silently succeeding without it.
- confirm repository variable `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E` is set to `1` only when weekly Stage04 real-network coverage is intended.
- rerun locally with:
  - `ONETRUTH_RUN_OPENAI_E2E=1 OPENAI_API_KEY=... PYTHONPATH=src pytest -q tests/integration_openai`

### Dependency review failures
Symptoms:
- `dependency_review` fails on a pull request.

Checks:
- inspect the dependency delta in the PR and the dependency-review job summary.
- confirm the PR is not introducing vulnerabilities above the configured threshold.
- if a dependency update is intentional, land the safer version or document the hosted GitHub review decision outside repo source.

### CodeQL failures
Symptoms:
- `codeql` fails on `pull_request`, `push`, or schedule.

Checks:
- inspect the CodeQL SARIF summary and job annotations in GitHub Actions.
- confirm the failure is not caused by a transient workflow bootstrap problem by rerunning the workflow once.
- if a real finding is present, treat it as a code/security follow-up rather than downgrading the workflow.

## Local reproduction
Run the same baseline checks CI runs:

```bash
make assurance-fast
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

## Manual workflow runs
### `agent_api` (mock lane)
1. Open GitHub -> Actions -> `agent_api`.
2. Click **Run workflow**.
3. Select the target branch and run.

The workflow runs baseline non-network checks only.

### `agent_api_live` (manual live lane)
1. Open GitHub -> Actions -> `agent_api_live`.
2. Click **Run workflow**.
3. Select the target branch and run.

The workflow runs the same fast backend baseline first, then the gated real OpenAI integration tests.

## Confirm secret exists (without printing it)
In GitHub:
1. Go to Settings -> Secrets and variables -> Actions.
2. Confirm a secret named `OPENAI_API_KEY` exists.
3. Do not print or echo secret values in logs.

In workflow logs:
- `agent_api` should never attempt live-secret usage.
- `agent_api_live` should fail early if the secret is missing, or continue into `tests/integration_openai` when the secret is present.
