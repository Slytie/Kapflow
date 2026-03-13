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
  - local handoff/export bundles; regenerate outside Git when needed.
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
