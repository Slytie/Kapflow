from __future__ import annotations

import json
from typing import Any

import pytest

from onetruth.integrations.openai import (
    OpenAIResponsesError,
    OpenAIResponsesFunctionCallingRunner,
    ResponsesFunctionToolSpec,
)


def test_function_calling_loop_supports_multiple_calls_in_single_turn() -> None:
    requests: list[dict[str, Any]] = []
    responses: list[tuple[int, dict[str, Any], str | None]] = [
        (
            200,
            {
                "id": "resp_1",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_alpha",
                        "name": "tool_alpha",
                        "arguments": '{"x":1}',
                    },
                    {
                        "type": "function_call",
                        "call_id": "call_beta",
                        "name": "tool_beta",
                        "arguments": '{"y":"z"}',
                    },
                ],
            },
            "req_1",
        ),
        (
            200,
            {
                "id": "resp_2",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 7, "output_tokens": 3},
                "output_text": '{"summary":"done"}',
            },
            "req_2",
        ),
    ]

    def transport(payload: dict[str, Any], timeout_seconds: float) -> tuple[int, dict[str, Any], str | None]:
        assert timeout_seconds == 5.0
        requests.append(payload)
        return responses.pop(0)

    def execute_function(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"tool": name, "arguments": arguments}

    runner = OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )
    result = runner.run_function_calling_loop(
        initial_input=[{"role": "user", "content": [{"type": "input_text", "text": "run"}]}],
        tools=[
            ResponsesFunctionToolSpec(
                name="tool_alpha",
                description="alpha",
                parameters_schema={"type": "object", "additionalProperties": False, "properties": {"x": {"type": "integer"}}, "required": ["x"]},
            ),
            ResponsesFunctionToolSpec(
                name="tool_beta",
                description="beta",
                parameters_schema={"type": "object", "additionalProperties": False, "properties": {"y": {"type": "string"}}, "required": ["y"]},
            ),
        ],
        execute_function=execute_function,
        max_turns=5,
    )

    assert result.final_response_id == "resp_2"
    assert result.final_request_id == "req_2"
    assert result.final_output_text == '{"summary":"done"}'
    assert result.total_usage["input_tokens"] == 17
    assert result.total_usage["output_tokens"] == 8
    assert len(result.turns) == 2
    assert len(result.turns[0].function_calls) == 2
    assert result.turns[0].function_calls[0].call_id == "call_alpha"
    assert result.turns[0].function_calls[1].call_id == "call_beta"

    second_request = requests[1]
    assert second_request["previous_response_id"] == "resp_1"
    assert {item["call_id"] for item in second_request["input"]} == {"call_alpha", "call_beta"}
    assert all(item["type"] == "function_call_output" for item in second_request["input"])


def test_function_calling_loop_allows_final_response_without_function_calls() -> None:
    def transport(_: dict[str, Any], __: float) -> tuple[int, dict[str, Any], str | None]:
        return (
            200,
            {
                "id": "resp_final",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 3, "output_tokens": 2},
                "output_text": '{"summary":"no_tools_needed"}',
            },
            "req_final",
        )

    runner = OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )
    result = runner.run_function_calling_loop(
        initial_input=[{"role": "user", "content": [{"type": "input_text", "text": "run"}]}],
        tools=[],
        execute_function=lambda _name, _arguments: {},
        max_turns=3,
    )
    assert result.final_response_id == "resp_final"
    assert result.final_output_text == '{"summary":"no_tools_needed"}'
    assert len(result.turns) == 1
    assert result.turns[0].function_calls == ()


def test_function_calling_loop_accepts_initial_previous_response_id() -> None:
    requests: list[dict[str, Any]] = []

    def transport(payload: dict[str, Any], __: float) -> tuple[int, dict[str, Any], str | None]:
        requests.append(payload)
        return (
            200,
            {
                "id": "resp_final",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 3, "output_tokens": 2},
                "output_text": '{"summary":"continued"}',
            },
            "req_final",
        )

    runner = OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )
    result = runner.run_function_calling_loop(
        initial_input=[{"role": "user", "content": [{"type": "input_text", "text": "continue"}]}],
        tools=[],
        execute_function=lambda _name, _arguments: {},
        max_turns=2,
        previous_response_id="resp_previous_turn",
    )

    assert result.final_response_id == "resp_final"
    assert requests[0]["previous_response_id"] == "resp_previous_turn"


def test_function_calling_loop_raises_when_max_turns_exhausted() -> None:
    attempts = {"count": 0}

    def transport(_: dict[str, Any], __: float) -> tuple[int, dict[str, Any], str | None]:
        attempts["count"] += 1
        return (
            200,
            {
                "id": f"resp_{attempts['count']}",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": f"call_{attempts['count']}",
                        "name": "tool_alpha",
                        "arguments": "{}",
                    }
                ],
            },
            f"req_{attempts['count']}",
        )

    runner = OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )
    with pytest.raises(OpenAIResponsesError, match="exhausted max_turns"):
        runner.run_function_calling_loop(
            initial_input=[{"role": "user", "content": [{"type": "input_text", "text": "run"}]}],
            tools=[
                ResponsesFunctionToolSpec(
                    name="tool_alpha",
                    description="alpha",
                    parameters_schema={"type": "object", "additionalProperties": False, "properties": {}, "required": []},
                )
            ],
            execute_function=lambda _name, _arguments: {"ok": True},
            max_turns=1,
        )


def test_function_calling_loop_enforces_no_progress_limit_and_notifies_turn_observer() -> None:
    observed_turns: list[dict[str, Any]] = []
    attempts = {"count": 0}

    def transport(_: dict[str, Any], __: float) -> tuple[int, dict[str, Any], str | None]:
        attempts["count"] += 1
        return (
            200,
            {
                "id": f"resp_{attempts['count']}",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": f"call_{attempts['count']}",
                        "name": "inspect_only",
                        "arguments": "{}",
                    }
                ],
            },
            f"req_{attempts['count']}",
        )

    runner = OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )

    with pytest.raises(OpenAIResponsesError, match="no-progress budget"):
        runner.run_function_calling_loop(
            initial_input=[{"role": "user", "content": [{"type": "input_text", "text": "run"}]}],
            tools=[
                ResponsesFunctionToolSpec(
                    name="inspect_only",
                    description="inspect",
                    parameters_schema={"type": "object", "additionalProperties": False, "properties": {}, "required": []},
                )
            ],
            execute_function=lambda _name, _arguments: {"progress_made": False, "snapshot": "still reviewing"},
            max_turns=5,
            no_progress_limit=2,
            on_turn_complete=lambda turn: observed_turns.append(turn.as_dict()),
        )

    assert [turn["turn_index"] for turn in observed_turns] == [1, 2]
    assert [turn["progress_made"] for turn in observed_turns] == [False, False]
    assert [turn["no_progress_streak"] for turn in observed_turns] == [1, 2]


def test_function_calling_loop_uses_compact_model_output_but_keeps_full_evidence() -> None:
    requests: list[dict[str, Any]] = []
    responses: list[tuple[int, dict[str, Any], str | None]] = [
        (
            200,
            {
                "id": "resp_1",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_apply",
                        "name": "tool_alpha",
                        "arguments": "{}",
                    }
                ],
            },
            "req_1",
        ),
        (
            200,
            {
                "id": "resp_2",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 4, "output_tokens": 2},
                "output_text": '{"summary":"done"}',
            },
            "req_2",
        ),
    ]

    def transport(payload: dict[str, Any], _timeout_seconds: float) -> tuple[int, dict[str, Any], str | None]:
        requests.append(payload)
        return responses.pop(0)

    runner = OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )
    result = runner.run_function_calling_loop(
        initial_input=[{"role": "user", "content": [{"type": "input_text", "text": "run"}]}],
        tools=[
            ResponsesFunctionToolSpec(
                name="tool_alpha",
                description="alpha",
                parameters_schema={"type": "object", "additionalProperties": False, "properties": {}, "required": []},
            )
        ],
        execute_function=lambda _name, _arguments: {
            "progress_made": True,
            "route_allocations": [{"route_slot_id": "slot-1"}],
            "tradeoffs": ["slot-1 -> driver-1"],
        },
        model_output_serializer=lambda _name, _arguments, output: {
            "progress_made": bool(output.get("progress_made")),
            "route_allocation_count": len(output.get("route_allocations") or []),
            "tradeoffs": list(output.get("tradeoffs") or [])[:1],
        },
        max_turns=4,
    )

    first_call = result.turns[0].function_calls[0]
    assert json.loads(first_call.model_output_json) == {
        "progress_made": True,
        "route_allocation_count": 1,
        "tradeoffs": ["slot-1 -> driver-1"],
    }
    assert json.loads(first_call.evidence_output_json) == {
        "progress_made": True,
        "route_allocations": [{"route_slot_id": "slot-1"}],
        "tradeoffs": ["slot-1 -> driver-1"],
    }

    second_request = requests[1]
    assert json.loads(second_request["input"][0]["output"]) == {
        "progress_made": True,
        "route_allocation_count": 1,
        "tradeoffs": ["slot-1 -> driver-1"],
    }


def test_function_calling_loop_honors_retry_after_without_duplicate_tool_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, Any]] = []
    sleep_calls: list[float] = []
    execute_calls: list[str] = []
    responses: list[
        tuple[int, dict[str, Any], str | None]
        | tuple[int, dict[str, Any], str | None, dict[str, str]]
    ] = [
        (
            429,
            {"error": {"code": "rate_limit_exceeded", "message": "Too many requests"}},
            "req_retry_1",
            {"retry-after": "7.5"},
        ),
        (
            200,
            {
                "id": "resp_after_retry",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 11, "output_tokens": 5},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_after_retry",
                        "name": "tool_alpha",
                        "arguments": "{}",
                    }
                ],
            },
            "req_retry_2",
        ),
        (
            200,
            {
                "id": "resp_done",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 4, "output_tokens": 2},
                "output_text": '{"summary":"done"}',
            },
            "req_retry_3",
        ),
    ]

    def transport(payload: dict[str, Any], _timeout_seconds: float):
        requests.append(payload)
        return responses.pop(0)

    monkeypatch.setattr("time.sleep", lambda seconds: sleep_calls.append(seconds))

    runner = OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=2,
        transport=transport,
    )
    result = runner.run_function_calling_loop(
        initial_input=[{"role": "user", "content": [{"type": "input_text", "text": "run"}]}],
        tools=[
            ResponsesFunctionToolSpec(
                name="tool_alpha",
                description="alpha",
                parameters_schema={"type": "object", "additionalProperties": False, "properties": {}, "required": []},
            )
        ],
        execute_function=lambda name, _arguments: execute_calls.append(name) or {"progress_made": True},
        max_turns=4,
    )

    assert sleep_calls == [7.5]
    assert execute_calls == ["tool_alpha"]
    assert len(result.turns) == 2
    assert result.turns[0].request_attempts == 2
    assert list(result.turns[0].retry_history) == [
        {
            "attempt": 1,
            "error_code": "rate_limit_exceeded",
            "error_message": "Too many requests",
            "status_code": 429,
            "request_id": "req_retry_1",
            "retry_after_seconds": 7.5,
        }
    ]
    assert requests[0]["input"][0]["content"][0]["text"] == "run"
    assert requests[2]["previous_response_id"] == "resp_after_retry"


def test_function_calling_loop_uses_message_retry_after_on_exhausted_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleep_calls: list[float] = []
    attempts = {"count": 0}

    def transport(_: dict[str, Any], __: float) -> tuple[int, dict[str, Any], str | None]:
        attempts["count"] += 1
        return (
            429,
            {
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Limit 500000, Used 451054, Requested 110432, retry after 7.378s",
                }
            },
            f"req_limit_{attempts['count']}",
        )

    monkeypatch.setattr("time.sleep", lambda seconds: sleep_calls.append(seconds))

    runner = OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=1,
        transport=transport,
    )

    with pytest.raises(OpenAIResponsesError) as exc_info:
        runner.run_function_calling_loop(
            initial_input=[{"role": "user", "content": [{"type": "input_text", "text": "run"}]}],
            tools=[],
            execute_function=lambda _name, _arguments: {},
            max_turns=1,
        )

    assert sleep_calls == [7.378]
    assert exc_info.value.code == "rate_limit_exceeded"
    assert exc_info.value.details["attempts"] == 2
    assert exc_info.value.details["retry_history"] == [
        {
            "attempt": 1,
            "error_code": "rate_limit_exceeded",
            "error_message": "Limit 500000, Used 451054, Requested 110432, retry after 7.378s",
            "status_code": 429,
            "request_id": "req_limit_1",
            "retry_after_seconds": 7.378,
        }
    ]
