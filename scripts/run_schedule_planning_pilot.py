#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from onetruth.application.services.realistic_schedule_planning_pilot import (
    ALL_PILOT_IDS,
    run_realistic_schedule_planning_pilot_suite,
)
from onetruth.infrastructure.db.session import DEFAULT_DB_URL, open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run realistic Schedule Planning pilot scenarios and export inspection packets.",
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help="SQLite database URL used for canonical runtime state.",
    )
    parser.add_argument(
        "--pilot-key",
        default="default",
        help="Stable pilot key used to derive deterministic run/object IDs.",
    )
    parser.add_argument(
        "--output-root",
        default="artifacts/pilot_runs",
        help="Directory where pilot inspection packets and summary files are written.",
    )
    parser.add_argument(
        "--artifact-root",
        default=None,
        help="Optional artifact blob storage root (defaults from DB path).",
    )
    parser.add_argument(
        "--manifest-path",
        default=None,
        help="Optional corpus manifest override path.",
    )
    parser.add_argument(
        "--openai-mode",
        default="mock",
        choices=["mock", "real"],
        help="Use deterministic mock classifier or real OpenAI classifier for Stage06 pilot steps.",
    )
    parser.add_argument(
        "--pilot",
        dest="pilots",
        action="append",
        choices=[*ALL_PILOT_IDS, "all"],
        help="Pilot scenario to run. Can be repeated. Defaults to all scenarios.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit summary as JSON to stdout.",
    )
    return parser


def _selected_pilots(raw: list[str] | None) -> tuple[str, ...]:
    if raw is None or not raw:
        return ALL_PILOT_IDS
    if "all" in raw:
        return ALL_PILOT_IDS
    return tuple(raw)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    pilots = _selected_pilots(args.pilots)
    output_root = Path(args.output_root).expanduser()
    artifact_root = Path(args.artifact_root).expanduser() if args.artifact_root else None
    manifest_path = Path(args.manifest_path).expanduser() if args.manifest_path else None

    connection = open_sqlite_connection(args.db_url)
    try:
        create_sqlite_substrate(connection)
        summary = run_realistic_schedule_planning_pilot_suite(
            connection,
            db_url=args.db_url,
            pilot_key=str(args.pilot_key),
            output_root=output_root,
            artifact_root=artifact_root,
            pilot_ids=pilots,
            openai_mode=str(args.openai_mode),
            manifest_path=manifest_path,
        )
    finally:
        connection.close()

    if args.json_output:
        sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            "\n".join(
                [
                    "Schedule Planning pilot run complete.",
                    f"Pilot key: {summary['pilot_key']}",
                    f"Summary JSON: {summary['summary_json_path']}",
                    f"Summary Markdown: {summary['summary_markdown_path']}",
                ]
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
