from __future__ import annotations

from onetruth.application.services.weekly_stage04_openai_agent import _stage04_tool_specs


def test_stage04_tool_schemas_are_strict_openai_compatible() -> None:
    specs = _stage04_tool_specs(
        {
            "runtime_bindings": {
                "tool_execution": {
                    "allowed_tool_classes": [
                        "artifact.read",
                        "validation",
                        "spreadsheet.transform",
                        "flag.raise",
                        "projection.render",
                    ]
                }
            }
        }
    )

    assert {spec.name for spec in specs} == {
        "get_stage04_context",
        "preview_stage04_next_iteration",
        "apply_stage04_next_iteration",
        "get_stage04_validation_summary",
        "get_stage04_iteration_analysis",
        "finalize_weekly_stage04_draft_outputs",
    }

    for spec in specs:
        schema = spec.parameters_schema
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert set(schema.get("required") or []) == set((schema.get("properties") or {}).keys())

    iteration_analysis = next(spec for spec in specs if spec.name == "get_stage04_iteration_analysis")
    iteration_index = iteration_analysis.parameters_schema["properties"]["iteration_index"]

    assert iteration_analysis.parameters_schema["required"] == ["iteration_index"]
    assert iteration_index["anyOf"] == [
        {"type": "integer", "minimum": 1},
        {"type": "null"},
    ]
