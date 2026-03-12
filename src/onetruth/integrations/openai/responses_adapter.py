from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import time
from typing import Any, Callable, Optional, Protocol, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

from onetruth.infrastructure.events.event_store import utc_now_iso

STAGE06_ALLOWED_OUTCOMES = {
    "draft_is_publish_ready",
    "review_requires_more_information",
    "review_requests_changes",
}
STAGE06_ALLOWED_FOLLOW_ON_TASK_KINDS = {
    "final_review",
    "information_request",
    "work_item",
}

STAGE06_REVIEW_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "outcome",
        "rationale_summary",
        "evidence_refs",
        "suggested_follow_on_task_kind",
    ],
    "properties": {
        "outcome": {
            "type": "string",
            "enum": sorted(STAGE06_ALLOWED_OUTCOMES),
        },
        "rationale_summary": {"type": "string"},
        "evidence_refs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "suggested_follow_on_task_kind": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "string",
                    "enum": sorted(STAGE06_ALLOWED_FOLLOW_ON_TASK_KINDS),
                },
            ],
        },
    },
}


class OpenAIConfigError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "openai_not_configured"


class OpenAIResponsesError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}


@dataclass(frozen=True)
class Stage06ReviewClassification:
    outcome: str
    rationale_summary: str
    evidence_refs: list[str]
    suggested_follow_on_task_kind: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "rationale_summary": self.rationale_summary,
            "evidence_refs": self.evidence_refs,
            "suggested_follow_on_task_kind": self.suggested_follow_on_task_kind,
        }


@dataclass(frozen=True)
class OpenAIResponseMetadata:
    response_id: str | None
    request_id: str | None
    model: str
    usage: dict[str, Any]
    attempts: int
    requested_at: str
    completed_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "model": self.model,
            "usage": self.usage,
            "attempts": self.attempts,
            "requested_at": self.requested_at,
            "completed_at": self.completed_at,
        }


@dataclass(frozen=True)
class OpenAIResponsesRuntimeConfig:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float
    max_retries: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }


class Stage06ReviewClassifier(Protocol):
    def classify_stage06_review(
        self,
        *,
        instruction_context: dict[str, Any],
        artifact_context: list[dict[str, Any]],
        document_text: str,
    ) -> tuple[Stage06ReviewClassification, OpenAIResponseMetadata]:
        ...


ResponseTransport = Callable[[dict[str, Any], float], Tuple[int, dict[str, Any], Optional[str]]]


class OpenAIResponsesStage06Classifier:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        max_input_chars: int,
        transport: ResponseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_input_chars = max_input_chars
        self._transport = transport or self._default_transport

    def classify_stage06_review(
        self,
        *,
        instruction_context: dict[str, Any],
        artifact_context: list[dict[str, Any]],
        document_text: str,
    ) -> tuple[Stage06ReviewClassification, OpenAIResponseMetadata]:
        bounded_document_text = document_text[: self.max_input_chars]
        requested_at = utc_now_iso()
        request_payload = self._build_request_payload(
            instruction_context=instruction_context,
            artifact_context=artifact_context,
            document_text=bounded_document_text,
        )

        response_payload: dict[str, Any] | None = None
        request_id: str | None = None
        attempts = 0
        while attempts <= self.max_retries:
            attempts += 1
            try:
                status_code, payload, request_id = self._transport(
                    request_payload,
                    self.timeout_seconds,
                )
            except OpenAIResponsesError as exc:
                if exc.retryable and attempts <= self.max_retries:
                    time.sleep(min(0.2 * attempts, 1.0))
                    continue
                raise

            if status_code >= 400:
                error = _openai_error_from_response(
                    status_code=status_code,
                    response_payload=payload,
                    request_id=request_id,
                )
                if error.retryable and attempts <= self.max_retries:
                    time.sleep(min(0.2 * attempts, 1.0))
                    continue
                raise error

            response_payload = payload
            break

        if response_payload is None:
            raise OpenAIResponsesError(
                code="openai_no_response",
                message="OpenAI response was unavailable after retry attempts",
                retryable=True,
            )

        output = parse_stage06_review_output(response_payload)
        completed_at = utc_now_iso()
        metadata = OpenAIResponseMetadata(
            response_id=_as_optional_str(response_payload.get("id")),
            request_id=request_id,
            model=_as_optional_str(response_payload.get("model")) or self.model,
            usage=response_payload.get("usage") if isinstance(response_payload.get("usage"), dict) else {},
            attempts=attempts,
            requested_at=requested_at,
            completed_at=completed_at,
        )
        return output, metadata

    def _build_request_payload(
        self,
        *,
        instruction_context: dict[str, Any],
        artifact_context: list[dict[str, Any]],
        document_text: str,
    ) -> dict[str, Any]:
        system_prompt = (
            "You are a bounded Stage06 review classifier. "
            "Return only strict JSON matching the schema. "
            "Do not add keys or narrative outside JSON."
        )
        user_payload = {
            "task_context": instruction_context,
            "artifact_context": artifact_context,
            "instructions": {
                "goal": "Classify Stage06 review outcome.",
                "allowed_outcomes": sorted(STAGE06_ALLOWED_OUTCOMES),
                "allowed_follow_on_task_kinds": sorted(STAGE06_ALLOWED_FOLLOW_ON_TASK_KINDS),
                "notes": [
                    "Prefer review_requires_more_information when evidence is incomplete.",
                    "Use concise rationale_summary.",
                    "evidence_refs should point to concrete cues from the provided document content.",
                ],
            },
            "document_excerpt": document_text,
        }

        return {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": json.dumps(user_payload, separators=(",", ":"))}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "stage06_review_outcome",
                    "schema": STAGE06_REVIEW_OUTPUT_SCHEMA,
                    "strict": True,
                }
            },
        }

    def _default_transport(
        self,
        request_payload: dict[str, Any],
        timeout_seconds: float,
    ) -> tuple[int, dict[str, Any], str | None]:
        body = json.dumps(request_payload, separators=(",", ":")).encode("utf-8")
        request = urllib_request.Request(
            url=f"{self.base_url}/responses",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                parsed = json.loads(response_body) if response_body else {}
                return int(response.status), parsed, _as_optional_str(response.headers.get("x-request-id"))
        except urllib_error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            parsed = _safe_json_parse(body_text)
            return int(exc.code), parsed, _as_optional_str(exc.headers.get("x-request-id") if exc.headers else None)
        except urllib_error.URLError as exc:
            raise OpenAIResponsesError(
                code="openai_transport_error",
                message="OpenAI transport error",
                retryable=True,
                details={"reason": str(exc.reason)},
            ) from exc


def parse_stage06_review_output(response_payload: dict[str, Any]) -> Stage06ReviewClassification:
    text = _extract_output_text(response_payload)
    parsed_json = _safe_json_object_from_output_text(text)
    validated = validate_stage06_review_output(parsed_json)
    return Stage06ReviewClassification(
        outcome=validated["outcome"],
        rationale_summary=validated["rationale_summary"],
        evidence_refs=validated["evidence_refs"],
        suggested_follow_on_task_kind=validated["suggested_follow_on_task_kind"],
    )


def validate_stage06_review_output(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="structured output must be an object",
        )

    expected_keys = {
        "outcome",
        "rationale_summary",
        "evidence_refs",
        "suggested_follow_on_task_kind",
    }
    actual_keys = set(payload.keys())
    if actual_keys != expected_keys:
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="structured output keys do not match expected schema",
            details={
                "expected_keys": sorted(expected_keys),
                "actual_keys": sorted(actual_keys),
            },
        )

    outcome = payload.get("outcome")
    if outcome not in STAGE06_ALLOWED_OUTCOMES:
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="outcome is not allowed",
            details={"outcome": outcome, "allowed": sorted(STAGE06_ALLOWED_OUTCOMES)},
        )

    rationale_summary = payload.get("rationale_summary")
    if not isinstance(rationale_summary, str) or not rationale_summary.strip():
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="rationale_summary must be a non-empty string",
        )

    evidence_refs = payload.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not all(isinstance(item, str) for item in evidence_refs):
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="evidence_refs must be an array of strings",
        )

    suggested = payload.get("suggested_follow_on_task_kind")
    if suggested is not None and suggested not in STAGE06_ALLOWED_FOLLOW_ON_TASK_KINDS:
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="suggested_follow_on_task_kind is not allowed",
            details={
                "suggested_follow_on_task_kind": suggested,
                "allowed": sorted(STAGE06_ALLOWED_FOLLOW_ON_TASK_KINDS),
            },
        )

    return {
        "outcome": str(outcome),
        "rationale_summary": rationale_summary.strip(),
        "evidence_refs": [item.strip() for item in evidence_refs],
        "suggested_follow_on_task_kind": suggested,
    }


def build_stage06_review_classifier_from_env(
    *,
    transport: ResponseTransport | None = None,
) -> OpenAIResponsesStage06Classifier:
    runtime = build_openai_responses_runtime_config_from_env()
    max_input_chars_raw = os.environ.get("ONETRUTH_OPENAI_MAX_INPUT_CHARS", "12000")
    try:
        max_input_chars = int(max_input_chars_raw)
    except ValueError as exc:
        raise OpenAIConfigError("ONETRUTH_OPENAI_MAX_INPUT_CHARS must be an integer") from exc

    if max_input_chars <= 0:
        raise OpenAIConfigError("ONETRUTH_OPENAI_MAX_INPUT_CHARS must be > 0")

    return OpenAIResponsesStage06Classifier(
        api_key=runtime.api_key,
        model=runtime.model,
        base_url=runtime.base_url,
        timeout_seconds=runtime.timeout_seconds,
        max_retries=runtime.max_retries,
        max_input_chars=max_input_chars,
        transport=transport,
    )


def build_openai_responses_runtime_config_from_env(
    *,
    default_model: str = "gpt-4.1-mini",
) -> OpenAIResponsesRuntimeConfig:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIConfigError("OPENAI_API_KEY is required for Stage06 OpenAI sandbox classification")

    model = os.environ.get("ONETRUTH_OPENAI_MODEL", default_model).strip() or default_model
    base_url = os.environ.get("ONETRUTH_OPENAI_BASE_URL", "https://api.openai.com/v1").strip() or "https://api.openai.com/v1"
    timeout_raw = os.environ.get("ONETRUTH_OPENAI_TIMEOUT_SECONDS", "30")
    retries_raw = os.environ.get("ONETRUTH_OPENAI_MAX_RETRIES", "2")

    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise OpenAIConfigError("ONETRUTH_OPENAI_TIMEOUT_SECONDS must be numeric") from exc
    try:
        max_retries = int(retries_raw)
    except ValueError as exc:
        raise OpenAIConfigError("ONETRUTH_OPENAI_MAX_RETRIES must be an integer") from exc

    if timeout_seconds <= 0:
        raise OpenAIConfigError("ONETRUTH_OPENAI_TIMEOUT_SECONDS must be > 0")
    if max_retries < 0:
        raise OpenAIConfigError("ONETRUTH_OPENAI_MAX_RETRIES must be >= 0")

    return OpenAIResponsesRuntimeConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


def _extract_output_text(response_payload: dict[str, Any]) -> str:
    direct_text = response_payload.get("output_text")
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text

    output = response_payload.get("output")
    if isinstance(output, list):
        for block in output:
            if not isinstance(block, dict):
                continue
            content = block.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    return text

    raise OpenAIResponsesError(
        code="openai_invalid_output",
        message="response did not contain structured output text",
    )


def _safe_json_object_from_output_text(output_text: str) -> dict[str, Any]:
    candidate = output_text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="structured output is not valid JSON",
            details={"error": str(exc)},
        ) from exc
    if not isinstance(parsed, dict):
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="structured output must decode to an object",
        )
    return parsed


def _openai_error_from_response(
    *,
    status_code: int,
    response_payload: dict[str, Any],
    request_id: str | None,
) -> OpenAIResponsesError:
    error_obj = response_payload.get("error") if isinstance(response_payload, dict) else None
    if not isinstance(error_obj, dict):
        error_obj = {}

    code = _as_optional_str(error_obj.get("code")) or f"openai_http_{status_code}"
    message = _as_optional_str(error_obj.get("message")) or "OpenAI request failed"
    retryable = status_code in {429, 500, 502, 503, 504}

    return OpenAIResponsesError(
        code=code,
        message=message,
        status_code=status_code,
        retryable=retryable,
        details={"request_id": request_id, "status_code": status_code},
    )


def _safe_json_parse(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
