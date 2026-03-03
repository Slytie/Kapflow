from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRACE_DIR = REPO_ROOT / "fixtures" / "workflows" / "schedule_planning" / "golden_event_traces"
