from __future__ import annotations

from typing import Any

import pytest

from onetruth.integrations.openai import (
    OpenAIConfigError,
    OpenAIResponsesError,
    build_stage06_review_classifier_from_env,
)
from onetruth.integrations.openai.responses_adapter import (
    OpenAIResponsesStage06Classifier,
    parse_stage06_review_output,
    validate_stage06_review_output,
)


def _success_response(
    outcome: str = "draft_is_publish_ready",
    suggested_follow_on_task_kind: str | None = "final_review",
) -> dict[str, Any]:
    return {
        "id": "resp_test_123",
        "model": "gpt-4.1-mini",
        "usage": {"input_tokens": 12, "output_tokens": 8},
        "output_text": (
            "{"
            f'"outcome":"{outcome}",'
            '"rationale_summary":"Looks complete.",'
            '"evidence_refs":["doc:section-1"],'
            f'"suggested_follow_on_task_kind":{_json_nullable(suggested_follow_on_task_kind)}'
            "}"
        ),
    }


def _json_nullable(value: str | None) -> str:
    if value is None:
        return "null"
    return f'"{value}"'


def test_validate_stage06_output_accepts_expected_shape() -> None:
    payload = {
        "outcome": "review_requires_more_information",
        "rationale_summary": "Missing route coverage evidence.",
        "evidence_refs": ["doc:para-2", "doc:table-1"],
        "suggested_follow_on_task_kind": "information_request",
    }
    validated = validate_stage06_review_output(payload)
    assert validated["outcome"] == "review_requires_more_information"


def test_validate_stage06_output_rejects_invalid_outcome() -> None:
    with pytest.raises(OpenAIResponsesError) as exc_info:
        validate_stage06_review_output(
            {
                "outcome": "unknown",
                "rationale_summary": "x",
                "evidence_refs": [],
                "suggested_follow_on_task_kind": None,
            }
        )
    assert exc_info.value.code == "openai_invalid_output"


def test_parse_stage06_output_rejects_non_json() -> None:
    with pytest.raises(OpenAIResponsesError) as exc_info:
        parse_stage06_review_output({"output_text": "not-json"})
    assert exc_info.value.code == "openai_invalid_output"


def test_classifier_retries_transient_429_then_succeeds() -> None:
    attempts = {"count": 0}

    def transport(_: dict[str, Any], __: float) -> tuple[int, dict[str, Any], str | None]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return 429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests"}}, "req_1"
        return 200, _success_response(), "req_2"

    classifier = OpenAIResponsesStage06Classifier(
        api_key="test-key",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=2,
        max_input_chars=1000,
        transport=transport,
    )

    classification, metadata = classifier.classify_stage06_review(
        instruction_context={"workflow_run_id": "wr-1"},
        artifact_context=[],
        document_text="example text",
    )

    assert classification.outcome == "draft_is_publish_ready"
    assert metadata.attempts == 2


def test_classifier_maps_malformed_output_to_error() -> None:
    def transport(_: dict[str, Any], __: float) -> tuple[int, dict[str, Any], str | None]:
        return 200, {"id": "resp_x", "output_text": "{}"}, "req_x"

    classifier = OpenAIResponsesStage06Classifier(
        api_key="test-key",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        max_input_chars=1000,
        transport=transport,
    )

    with pytest.raises(OpenAIResponsesError) as exc_info:
        classifier.classify_stage06_review(
            instruction_context={"workflow_run_id": "wr-1"},
            artifact_context=[],
            document_text="example text",
        )

    assert exc_info.value.code == "openai_invalid_output"


def test_classifier_missing_api_key_from_env_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(OpenAIConfigError):
        build_stage06_review_classifier_from_env()


def test_classifier_env_uses_explicit_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ONETRUTH_OPENAI_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("ONETRUTH_OPENAI_BASE_URL", "https://api.openai.test/v1")
    monkeypatch.setenv("ONETRUTH_OPENAI_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("ONETRUTH_OPENAI_MAX_RETRIES", "1")
    monkeypatch.setenv("ONETRUTH_OPENAI_MAX_INPUT_CHARS", "321")

    classifier = build_stage06_review_classifier_from_env(transport=lambda _p, _t: (200, _success_response(), "req"))
    assert classifier.model == "gpt-4.1-mini"
    assert classifier.base_url == "https://api.openai.test/v1"
    assert classifier.max_retries == 1
    assert classifier.max_input_chars == 321


@pytest.mark.parametrize(
    "env_name,env_value",
    [
        ("ONETRUTH_OPENAI_TIMEOUT_SECONDS", "x"),
        ("ONETRUTH_OPENAI_MAX_RETRIES", "x"),
        ("ONETRUTH_OPENAI_MAX_INPUT_CHARS", "x"),
    ],
)
def test_classifier_env_validation(monkeypatch: pytest.MonkeyPatch, env_name: str, env_value: str) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv(env_name, env_value)
    with pytest.raises(OpenAIConfigError):
        build_stage06_review_classifier_from_env()
