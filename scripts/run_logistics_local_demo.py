#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from onetruth.application.services.logistics_local_demo import (
    DEFAULT_PLANNING_WEEK_ID,
    DEFAULT_SERVICE_DATE_ID,
    seed_weekly_first_logistics_local_demo,
)
from onetruth.infrastructure.db.session import DEFAULT_DB_URL, open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed the weekly-first local logistics demo and print stable URLs.",
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help="SQLite database URL used for canonical runtime state.",
    )
    parser.add_argument(
        "--planning-week-id",
        default=DEFAULT_PLANNING_WEEK_ID,
        help="PlanningWeekID for the current weekly planning demo run.",
    )
    parser.add_argument(
        "--service-date-id",
        default=DEFAULT_SERVICE_DATE_ID,
        help="ServiceDateID for the current reporting run and later live-dispatch prepare step.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional file path where summary JSON should be written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    connection = open_sqlite_connection(str(args.db_url))
    try:
        create_sqlite_substrate(connection)
        seeded = seed_weekly_first_logistics_local_demo(
            connection,
            db_url=str(args.db_url),
            planning_week_id=str(args.planning_week_id),
            service_date_id=str(args.service_date_id),
        )
    finally:
        connection.close()

    result = {
        "status": "ok",
        "command": "logistics-local-demo.seed",
        **seeded,
    }
    if args.output_json:
        output_path = Path(str(args.output_json)).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result["output_json_path"] = str(output_path)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
