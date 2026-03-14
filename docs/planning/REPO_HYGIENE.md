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
- `frontend/node_modules/`, `frontend/dist/`, `frontend/.vite/`, `frontend/coverage/`
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
  - working-tree-sensitive review/handoff snapshot exported by `scripts/export_clean_source_bundle.py` (and `make clean-source-bundle` by alias); may include non-ignored untracked source.
- `release_source_bundle`
  - clean tracked commit snapshot exported by `scripts/export_clean_source_bundle.py --bundle-kind release_source_bundle`; it requires `HEAD` plus a clean tracked worktree and is the lightweight provenance-oriented source package.
- `runtime_workspace_bundle`
  - run inspection/evidence bundle exported by `scripts/export_run_workspace_bundle.py`; it is derived from canonical runtime projections and is not source/release packaging.

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
