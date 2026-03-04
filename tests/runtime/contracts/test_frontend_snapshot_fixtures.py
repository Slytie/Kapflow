from __future__ import annotations

from tests.runtime.helpers.frontend_snapshots import (
    build_frontend_snapshots_payloads,
    load_frontend_snapshots,
)


def test_frontend_snapshot_fixtures_match_scenario_backed_exports() -> None:
    generated = build_frontend_snapshots_payloads()
    committed = load_frontend_snapshots()
    assert committed == generated
