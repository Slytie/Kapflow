# REPO_HYGIENE.md

This repo keeps source-of-truth artifacts in Git and excludes local machine/runtime noise.

## Ignored paths (why)
- `.DS_Store`, `.idea/`
  - OS/editor metadata; not portable and not part of runtime truth.
- `.tmp/`
  - local runtime scratch DBs and temporary artifact-store bytes from scenario/test runs.
- `.onetruth_artifacts/`
  - local default runtime evidence/blob root for bounded execution slices; not a fixture location or repo source boundary.
- `artifacts/`
  - local inspection outputs and blob-store style byproducts from pilot/test runs.
- `*.db`, `*.db-*`, `*.sqlite*`, `*.sqlite3*`
  - local SQLite runtime/test databases and journal/WAL sidecars.
- `codex_handoff_packet_*.zip`
  - local handoff/export bundles; regenerate outside Git when needed. These are review/handoff snapshots, not release artifacts.
- `node_modules/`, `frontend/node_modules/`, `frontend/dist/`, `frontend/.vite/`, `frontend/coverage/`
  - dependency installs and generated frontend build/test outputs.
- `*.log`
  - transient local logs.
- `.env*`, `.codex.env` (except `.env.example` / `.env.sample`)
  - local secrets/config overlays; must not be committed.
- `.venv/`, `venv/`, `.mypy_cache/`, `.ruff_cache/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`
  - Python virtualenv and cache artifacts.

## Tracked-noise cleanup rule
If any ignored path is already tracked, remove it from the index:

```bash
git rm -r --cached <path>
```

This keeps local files on disk while stopping future commits of non-source noise.

If runtime evidence should become a reusable golden artifact, move it into an explicit `fixtures/` path rather than leaving it under `.onetruth_artifacts/`.

## Bundle classes
- `handoff_source_bundle`
  - working-tree-sensitive internal review/handoff snapshot exported by `scripts/export_clean_source_bundle.py` or `make handoff-source-bundle`; it may include non-ignored untracked source and is not an operator-facing release artifact.
- `release_source_bundle`
  - clean tracked commit snapshot exported by `scripts/export_clean_source_bundle.py --bundle-kind release_source_bundle`, `make release-source-bundle`, or the operator-default alias `make clean-source-bundle`; it requires `HEAD` plus a clean tracked worktree, is the only endorsed share/release source package, and carries `release_provenance.json` alongside `bundle_manifest.json`.
- `runtime_workspace_bundle`
  - run inspection/evidence bundle exported by `scripts/export_run_workspace_bundle.py`; it is derived from canonical runtime projections and is not source/release packaging.
- raw workspace archives or manual ad hoc zips
  - non-release/internal only; they do not carry endorsed provenance and must not be presented as operator distribution artifacts.

## PR validation skeletons
- `cloudbuild.pr.yaml`
  - PR validation only; it runs repo assurance and focused contract tests without production secrets, deployment commands, live OpenAI keys, production DB URLs, or artifact-root mutation.
  - Hosted Cloud Build triggers, branch protections, and required-check settings are operator-managed outside repo source.

## Secret Hygiene Follow-Ups
- Repo-enforceable actions:
  - keep tracked-file secret detection green,
  - run the dedicated `secret_hygiene` workflow,
  - remove tracked secret-bearing files from the Git index immediately.
- Operator-only actions:
  - confirm leaked credentials are revoked,
  - decide whether Git history rewrite is justified,
  - enable hosted GitHub secret scanning push protection or related org/repo settings when available.
- These operator-only actions are not routine Codex code tasks and should be tracked/documented explicitly rather than silently implied by repo changes.
