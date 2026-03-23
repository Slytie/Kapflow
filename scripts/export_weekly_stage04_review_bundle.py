#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from onetruth.application.services.weekly_stage04_review_bundle import (
    export_weekly_stage04_review_bundle,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export an SME-facing review ZIP for a completed weekly Stage04 pilot run.",
    )
    parser.add_argument(
        "--run-root",
        required=True,
        help="Pilot run directory that contains pilot_summary.json and per-pilot outputs.",
    )
    parser.add_argument(
        "--pilot-id",
        required=True,
        help="Pilot ID to export from the run root.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output ZIP path.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit bundle summary as JSON to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = export_weekly_stage04_review_bundle(
        run_root=Path(str(args.run_root)),
        pilot_id=str(args.pilot_id),
        output_path=Path(str(args.output)),
    )
    if args.json_output:
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            "\n".join(
                [
                    "Weekly Stage04 review bundle export complete.",
                    f"Pilot ID: {result['pilot_id']}",
                    f"Workflow run ID: {result['workflow_run_id']}",
                    f"Output ZIP: {result['output_path']}",
                ]
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
