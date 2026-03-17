from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from scripts.repo_assurance.core import AssuranceState, ROOT, load_json
from scripts.repo_assurance.schema_governance import build_indexes, load_event_map


def run_traces_domain(state: AssuranceState) -> None:
    indexes = build_indexes(state)
    event_map = load_event_map(state, indexes)
    collector = state.collector
    envelope_schema = load_json(ROOT / "schemas/events/envelope.schema.json")
    envelope_validator = Draft202012Validator(envelope_schema)
    payload_validators = {
        event_id: Draft202012Validator(load_json(ROOT / info["payload_schema"]))
        for event_id, info in event_map.items()
    }
    trace_files = sorted(
        (ROOT / "fixtures/workflows/schedule_planning/golden_event_traces").glob("*.jsonl")
    )
    for trace in trace_files:
        seen_ids: set[str] = set()
        lines = trace.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                collector.fail(f"{trace.relative_to(ROOT)}:{index} invalid JSON: {exc}")
                continue
            envelope_errors = sorted(
                envelope_validator.iter_errors(obj), key=lambda error: list(error.path)
            )
            for error in envelope_errors:
                collector.fail(
                    f"{trace.relative_to(ROOT)}:{index} envelope error: {error.message}"
                )
            event_id = obj.get("event_id")
            if event_id:
                if event_id in seen_ids:
                    collector.fail(
                        f"{trace.relative_to(ROOT)} duplicate event_id: {event_id}"
                    )
                seen_ids.add(event_id)
            event_type = obj.get("event_type")
            if event_type not in event_map:
                collector.fail(
                    f"{trace.relative_to(ROOT)}:{index} unknown event type: {event_type}"
                )
                continue
            required_types = set(event_map[event_type]["required_links"])
            actual_types = {link["type"] for link in obj.get("links", [])}
            missing = required_types - actual_types
            if missing:
                collector.fail(
                    f"{trace.relative_to(ROOT)}:{index} missing required link types for "
                    f"{event_type}: {sorted(missing)}"
                )
            payload_validator = payload_validators[event_type]
            payload_errors = sorted(
                payload_validator.iter_errors(obj.get("payload", {})),
                key=lambda error: list(error.path),
            )
            for error in payload_errors:
                collector.fail(
                    f"{trace.relative_to(ROOT)}:{index} payload error for "
                    f"{event_type}: {error.message}"
                )
        collector.ok(f"trace validated: {trace.relative_to(ROOT)}")
