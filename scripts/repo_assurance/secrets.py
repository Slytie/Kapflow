from __future__ import annotations

import re
import subprocess
from pathlib import Path

from scripts.repo_assurance.core import AssuranceState, ROOT

OPENAI_KEY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI project API key", re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
)


def run_secrets_domain(state: AssuranceState) -> None:
    validate_secret_hygiene(state)


def iter_tracked_files(state: AssuranceState) -> list[Path]:
    collector = state.collector
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=False,
        )
    except Exception as exc:
        collector.fail(f"unable to enumerate tracked files for secret scan: {exc}")
        return []

    tracked: list[Path] = []
    for raw in completed.stdout.split(b"\x00"):
        if not raw:
            continue
        relative = Path(raw.decode("utf-8", errors="strict"))
        path = ROOT / relative
        if path.is_file():
            tracked.append(path)
    return tracked


def validate_secret_hygiene(state: AssuranceState) -> None:
    collector = state.collector
    text_files_scanned = 0
    for path in iter_tracked_files(state):
        relative = path.relative_to(ROOT)
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text_files_scanned += 1
        for label, pattern in OPENAI_KEY_PATTERNS:
            for match in pattern.finditer(contents):
                line_number = contents.count("\n", 0, match.start()) + 1
                collector.fail(
                    f"possible {label} detected in tracked file {relative}:{line_number}"
                )
    collector.ok(
        f"secret hygiene scan passed across {text_files_scanned} tracked text files"
    )
