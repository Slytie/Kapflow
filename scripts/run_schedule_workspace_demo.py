#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from onetruth.application.services.realistic_schedule_planning_pilot import (
    PILOT_STAGE06_NEEDS_INFORMATION,
    PILOT_STAGE06_PUBLISH_READY,
    PILOT_STAGE07_ISSUE_REPLAN,
    run_realistic_schedule_planning_pilot_suite,
)
from onetruth.infrastructure.db.session import DEFAULT_DB_URL, open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate

SCENARIO_TO_PILOT = {
    "stage06_publish_ready": PILOT_STAGE06_PUBLISH_READY,
    "stage06_needs_information": PILOT_STAGE06_NEEDS_INFORMATION,
    "stage07_major_replan": PILOT_STAGE07_ISSUE_REPLAN,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed one realistic workflow-run workspace demo scenario.",
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help="SQLite database URL used for canonical runtime state.",
    )
    parser.add_argument(
        "--scenario",
        required=True,
        choices=sorted(SCENARIO_TO_PILOT),
        help="Workspace demo scenario to seed.",
    )
    parser.add_argument(
        "--pilot-key",
        default="workspace-demo",
        help="Stable key used for deterministic canonical IDs.",
    )
    parser.add_argument(
        "--output-root",
        default="artifacts/workspace_demos",
        help="Root directory for generated inspection artifacts.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional file path where summary JSON should be written.",
    )
    parser.add_argument(
        "--openai-mode",
        default="mock",
        choices=["mock", "real"],
        help="Use deterministic mock Stage06 classifier or real OpenAI path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pilot_id = SCENARIO_TO_PILOT[str(args.scenario)]

    connection = open_sqlite_connection(args.db_url)
    try:
        create_sqlite_substrate(connection)
        summary = run_realistic_schedule_planning_pilot_suite(
            connection,
            db_url=str(args.db_url),
            pilot_key=str(args.pilot_key),
            output_root=Path(str(args.output_root)).expanduser(),
            pilot_ids=[pilot_id],
            openai_mode=str(args.openai_mode),
        )
    finally:
        connection.close()

    run_info = summary["pilot_runs"][0]
    workflow_run_id = str(run_info["workflow_run_id"])
    openai_enabled = bool(args.openai_mode == "real")
    openai_api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    result = {
        "status": "ok",
        "command": "workspace-demo.run",
        "scenario": str(args.scenario),
        "workflow_run_id": workflow_run_id,
        "recommended_ui_url": f"/runs/{workflow_run_id}/workspace",
        "fallback_board_url": f"/board?workflow_run_id={workflow_run_id}",
        "openai_mode": str(args.openai_mode),
        "openai_review_enabled": openai_enabled,
        "openai_api_key_present": openai_api_key_present,
        "reused_existing_run": bool(run_info.get("reused_existing", False)),
        "inspection_packet_path": str(run_info["inspection_packet_path"]),
        "inspection_markdown_path": str(run_info["inspection_markdown_path"]),
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
