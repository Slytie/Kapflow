from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
CODEOWNERS_PATH = REPO_ROOT / ".github/CODEOWNERS"
EXPECTED_PATTERNS = {
    "/.github/",
    "/schemas/",
    "/docs/architecture/",
    "/docs/workflows/",
    "/src/",
    "/scripts/",
    "/tests/",
    "/frontend/",
    "*",
}
OWNER_RE = re.compile(r"^@[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?$")


@dataclass(frozen=True)
class CodeownersEntry:
    pattern: str
    owners: tuple[str, ...]


def _parse_codeowners() -> list[CodeownersEntry]:
    entries: list[CodeownersEntry] = []
    for raw_line in CODEOWNERS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        pattern, owners = parts[0], tuple(parts[1:])
        entries.append(CodeownersEntry(pattern=pattern, owners=owners))
    return entries


def test_codeowners_uses_expected_root_patterns_and_real_owner() -> None:
    assert CODEOWNERS_PATH.exists()
    entries = _parse_codeowners()
    assert entries
    assert {entry.pattern for entry in entries} == EXPECTED_PATTERNS
    for entry in entries:
        assert entry.owners == ("@tylerclark",)


def test_codeowners_patterns_are_root_anchored_literals_that_exist() -> None:
    for entry in _parse_codeowners():
        if entry.pattern == "*":
            continue
        assert entry.pattern.startswith("/")
        assert not any(token in entry.pattern for token in ("*", "?", "[", "]"))
        relative_path = entry.pattern.lstrip("/").rstrip("/")
        assert relative_path
        assert (REPO_ROOT / relative_path).exists(), entry.pattern


def test_codeowners_owner_tokens_are_valid_github_targets() -> None:
    for entry in _parse_codeowners():
        for owner in entry.owners:
            assert OWNER_RE.match(owner), owner
