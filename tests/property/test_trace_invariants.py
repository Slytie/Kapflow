from __future__ import annotations

from tests.helpers.reference_model import canonicalize_state, reduce_events
from tests.helpers.trace_loader import list_trace_names, load_trace



def test_replay_state_is_deterministic_across_all_schedule_traces() -> None:
    for trace_name in list_trace_names():
        events = load_trace(trace_name)
        assert canonicalize_state(reduce_events(events)) == canonicalize_state(reduce_events(events))



def test_artifact_supersedes_chain_is_acyclic() -> None:
    all_versions: dict[str, str | None] = {}
    for trace_name in list_trace_names():
        state = reduce_events(load_trace(trace_name))
        for artifact_version_id, artifact in state["artifact_versions"].items():
            all_versions[artifact_version_id] = artifact.get("supersedes_artifact_version_id")

    for start in sorted(all_versions):
        seen: set[str] = set()
        current = start
        while current is not None:
            assert current not in seen, f"cycle detected at {current}"
            seen.add(current)
            current = all_versions.get(current)
