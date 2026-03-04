from __future__ import annotations

from typing import Any

from tests.runtime.helpers.frontend_snapshots import (
    build_frontend_snapshots_payloads,
    load_frontend_snapshots,
)


def test_frontend_snapshot_fixtures_match_scenario_backed_exports() -> None:
    generated = build_frontend_snapshots_payloads()
    committed = load_frontend_snapshots()
    assert committed == generated


def test_frontend_snapshot_payloads_do_not_contain_local_absolute_paths() -> None:
    generated = build_frontend_snapshots_payloads()
    committed = load_frontend_snapshots()
    for payload in [*generated.values(), *committed.values()]:
        for text in _iter_strings(payload):
            assert "/Users/" not in text
            assert "C:/Users/" not in text
            assert "C:\\Users\\" not in text


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(_iter_strings(child))
        return strings
    if isinstance(value, list):
        strings: list[str] = []
        for child in value:
            strings.extend(_iter_strings(child))
        return strings
    if isinstance(value, str):
        return [value]
    return []
