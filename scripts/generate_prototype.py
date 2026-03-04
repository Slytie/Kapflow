#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from onetruth.infrastructure.generation.prototype import (  # noqa: E402
    DEFAULT_WORKFLOW_ID,
    GenerationError,
    check_workflow_prototype,
    generate_workflow_prototype,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root is not None
        else None
    )

    try:
        if args.check:
            payload = check_workflow_prototype(
                repo_root=repo_root,
                workflow_id=args.workflow_id,
                output_root=output_root,
            )
            payload["status"] = "ok"
            payload["command"] = "generate-prototype.check"
        else:
            payload = generate_workflow_prototype(
                repo_root=repo_root,
                workflow_id=args.workflow_id,
                output_root=output_root,
            )
            payload["status"] = "ok"
            payload["command"] = "generate-prototype.run"
    except GenerationError as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "command": "generate-prototype.check" if args.check else "generate-prototype.run",
                    "error": str(exc),
                }
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
