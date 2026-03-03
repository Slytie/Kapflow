from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.helpers.repo_paths import TRACE_DIR


def trace_path(name: str) -> Path:
    path = TRACE_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def load_trace(name: str) -> list[dict[str, Any]]:
    path = trace_path(name)
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def list_trace_names() -> list[str]:
    return sorted(p.name for p in TRACE_DIR.glob("*.jsonl"))
