#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from onetruth.application.services.current_capability_certification import (
    CANONICAL_SCENARIO_ORDER,
    certification_exit_code,
    run_current_capability_certification,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run current-capability certification scenarios and emit a machine-readable manifest.",
    )
    parser.add_argument(
        "--db-url",
        default="sqlite:///.tmp/current-capability-certification.db",
        help="SQLite database URL used for canonical runtime state.",
    )
    parser.add_argument(
        "--certification-key",
        default="current-capability",
        help="Stable key used to derive output folders and deterministic IDs.",
    )
    parser.add_argument(
        "--output-root",
        default="artifacts/certification/current_capability",
        help="Root directory where certification artifacts are written.",
    )
    parser.add_argument(
        "--manifest-path",
        default=None,
        help="Optional explicit manifest path override.",
    )
    parser.add_argument(
        "--openai-mode",
        default="mock",
        choices=["mock", "real"],
        help="Use deterministic mock Stage06 classifier or real OpenAI path.",
    )
    parser.add_argument(
        "--scenario",
        dest="scenarios",
        action="append",
        choices=[*CANONICAL_SCENARIO_ORDER, "all"],
        help="Scenario to certify. Can be repeated. Defaults to all scenarios.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit full manifest JSON to stdout.",
    )
    return parser


def _selected_scenarios(raw: list[str] | None) -> tuple[str, ...] | None:
    if raw is None or not raw:
        return None
    if "all" in raw:
        return None
    return tuple(raw)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    selected = _selected_scenarios(args.scenarios)
    output_root = Path(str(args.output_root)).expanduser()
    manifest_path = (
        Path(str(args.manifest_path)).expanduser()
        if args.manifest_path
        else None
    )

    manifest = run_current_capability_certification(
        db_url=str(args.db_url),
        certification_key=str(args.certification_key),
        output_root=output_root,
        openai_mode=str(args.openai_mode),
        selected_scenarios=selected,
        manifest_path=manifest_path,
    )

    if args.json_output:
        sys.stdout.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            "\n".join(
                [
                    "Current capability certification complete.",
                    f"Status: {manifest['status']}",
                    f"Manifest JSON: {manifest['manifest_path']}",
                    f"Manifest Markdown: {manifest['manifest_markdown_path']}",
                    f"Scenarios: {manifest['scenario_count']} (passed={manifest['passed_scenarios']}, failed={manifest['failed_scenarios']})",
                ]
            )
            + "\n"
        )
    return certification_exit_code(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
