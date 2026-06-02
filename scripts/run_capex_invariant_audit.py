#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from onetruth.application.services.capex_invariant_audit import (
    capex_invariant_audit_exit_code,
    run_capex_invariant_audit,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the CAPEX platform-readiness invariant audit.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root to audit. Defaults to this script's repo.",
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Directory where audit JSON and Markdown reports are written.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the machine-readable manifest to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    manifest = run_capex_invariant_audit(
        repo_root=Path(args.repo_root),
        output_root=Path(args.output_root),
    )
    if args.json:
        sys.stdout.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    else:
        report_paths = manifest.get("report_paths") or {}
        sys.stdout.write(
            "CAPEX invariant audit {status}: {json_path}\n".format(
                status=manifest["status"],
                json_path=report_paths.get("json", args.output_root),
            )
        )
    return capex_invariant_audit_exit_code(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
