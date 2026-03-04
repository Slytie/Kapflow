#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.runtime.helpers.frontend_snapshots import (  # noqa: E402
    FRONTEND_SNAPSHOT_DIR,
    SNAPSHOT_FILES,
    build_frontend_snapshots_payloads,
    export_frontend_snapshots,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export backend-owned frontend snapshot fixtures from scenario-backed runtime states."
    )
    parser.add_argument(
        "--output-dir",
        default=str(FRONTEND_SNAPSHOT_DIR),
        help="Directory where snapshot JSON files are written.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if generated snapshots differ from files on disk.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_dir = Path(args.output_dir).resolve()

    if args.check:
        generated = build_frontend_snapshots_payloads()
        for snapshot_key, file_name in SNAPSHOT_FILES.items():
            path = output_dir / file_name
            if not path.exists():
                print(f"missing snapshot file: {path}", file=sys.stderr)
                return 1
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != generated[snapshot_key]:
                print(
                    f"snapshot mismatch: {snapshot_key} ({path})",
                    file=sys.stderr,
                )
                return 1
        print(f"snapshot fixtures are up to date in {output_dir}")
        return 0

    written = export_frontend_snapshots(output_dir)
    print(
        json.dumps(
            {
                "status": "ok",
                "output_dir": str(output_dir),
                "written_files": [str(path) for path in written],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
