from __future__ import annotations

from onetruth.application.services.weekly_stage04_openai_agent import (
    _compact_stage04_build_result,
    _compact_validation_summary,
    _stage04_tool_specs,
)


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


def test_stage04_compact_outputs_keep_contract_change_counts_only() -> None:
    contract_change_summary = {
        "new_agreement_required_count": 5,
        "new_agreement_driver_day_count": 4,
        "new_agreement_driver_ids": ["DRV-01", "DRV-02", "DRV-03"],
        "new_agreement_by_service_date": {
            "2026-03-22": 2,
            "2026-03-23": 2,
        },
    }

    validation_summary = _compact_validation_summary(
        {
            "summary": {
                **contract_change_summary,
            }
        }
    )
    assert validation_summary is not None
    assert validation_summary["summary"]["contract_change_summary"] == {
        "new_agreement_required_count": 5,
        "new_agreement_driver_day_count": 4,
        "new_agreement_driver_count": 3,
        "new_agreement_service_date_count": 2,
    }

    build_result = _compact_stage04_build_result(
        {
            "contract_change_summary": contract_change_summary,
        }
    )
    assert build_result is not None
    assert build_result["contract_change_summary"] == {
        "new_agreement_required_count": 5,
        "new_agreement_driver_day_count": 4,
        "new_agreement_driver_count": 3,
        "new_agreement_service_date_count": 2,
    }
