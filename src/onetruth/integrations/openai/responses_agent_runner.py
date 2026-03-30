from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from typing import Any, Callable, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from onetruth.integrations.openai.responses_adapter import (
    OpenAIConfigError,
    OpenAIResponsesError,
    OpenAIResponsesRuntimeConfig,
    build_openai_responses_runtime_config_from_env,
)

ResponseTransportResult = tuple[int, dict[str, Any], Optional[str], dict[str, str]]
ResponseTransport = Callable[[dict[str, Any], float], ResponseTransportResult]
FunctionExecutor = Callable[[str, dict[str, Any]], Any]
ModelOutputSerializer = Callable[[str, dict[str, Any], Any], Any]
TurnObserver = Callable[["ResponsesTurnRecord"], None]
ProgressEvaluator = Callable[[str, dict[str, Any], Any], bool]


@dataclass(frozen=True)
class ResponsesFunctionToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]

    def as_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
            "strict": True,
        }


@dataclass(frozen=True)
class ResponsesFunctionCallRecord:
    call_id: str
    name: str
    arguments_json: str
    arguments: dict[str, Any]
    model_output_json: str
    evidence_output_json: str
    progress_made: bool = False

    @property
    def output_json(self) -> str:
        return self.evidence_output_json

    def as_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "name": self.name,
            "arguments_json": self.arguments_json,
            "arguments": self.arguments,
            "model_output_json": self.model_output_json,
            "evidence_output_json": self.evidence_output_json,
            "output_json": self.evidence_output_json,
            "progress_made": self.progress_made,
        }


@dataclass(frozen=True)
class ResponsesTurnRecord:
    turn_index: int
    request_payload: dict[str, Any]
    response_id: str | None
    request_id: str | None
    model: str | None
    usage: dict[str, Any]
    output_text: str | None
    function_calls: tuple[ResponsesFunctionCallRecord, ...]
    progress_made: bool = False
    no_progress_streak: int = 0
    request_attempts: int = 1
    retry_history: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "request_payload": self.request_payload,
            "response_id": self.response_id,
            "request_id": self.request_id,
            "model": self.model,
            "usage": self.usage,
            "output_text": self.output_text,
            "function_calls": [item.as_dict() for item in self.function_calls],
            "progress_made": self.progress_made,
            "no_progress_streak": self.no_progress_streak,
            "request_attempts": self.request_attempts,
            "retry_history": list(self.retry_history),
        }


@dataclass(frozen=True)
class ResponsesFunctionCallingResult:
    turns: tuple[ResponsesTurnRecord, ...]
    final_response_id: str | None
    final_request_id: str | None
    final_output_text: str | None
    total_usage: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "turns": [turn.as_dict() for turn in self.turns],
            "final_response_id": self.final_response_id,
            "final_request_id": self.final_request_id,
            "final_output_text": self.final_output_text,
            "total_usage": dict(self.total_usage),
        }


@dataclass(frozen=True)
class _ParsedFunctionCall:
    call_id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class _RequestOutcome:
    status_code: int
    payload: dict[str, Any]
    request_id: str | None
    attempts: int
    retry_history: tuple[dict[str, Any], ...]


class OpenAIResponsesFunctionCallingRunner:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        transport: ResponseTransport | None = None,
    ) -> None:
        self.api_key = str(api_key)
        self.model = str(model)
        self.base_url = str(base_url).rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = int(max_retries)
        self._transport = transport or self._default_transport

    def run_function_calling_loop(
        self,
        *,
        initial_input: list[dict[str, Any]],
        tools: list[ResponsesFunctionToolSpec],
        execute_function: FunctionExecutor,
        max_turns: int,
        previous_response_id: str | None = None,
        no_progress_limit: int | None = None,
        progress_evaluator: ProgressEvaluator | None = None,
        model_output_serializer: ModelOutputSerializer | None = None,
        on_turn_complete: TurnObserver | None = None,
    ) -> ResponsesFunctionCallingResult:
        if max_turns <= 0:
            raise OpenAIResponsesError(
                code="openai_invalid_request",
                message="max_turns must be > 0",
            )
        if no_progress_limit is not None and no_progress_limit < 0:
            raise OpenAIResponsesError(
                code="openai_invalid_request",
                message="no_progress_limit must be >= 0 when provided",
            )
        tool_names = [tool.name for tool in tools]
        if len(tool_names) != len(set(tool_names)):
            raise OpenAIResponsesError(
                code="openai_invalid_request",
                message="tool names must be unique",
            )
        tool_map = {tool.name: tool for tool in tools}
        pending_input = initial_input
        continuation_response_id = (
            str(previous_response_id).strip()
            if str(previous_response_id or "").strip()
            else None
        )
        turns: list[ResponsesTurnRecord] = []
        usage_totals: dict[str, int] = {}
        no_progress_streak = 0

        for turn_index in range(1, max_turns + 1):
            request_payload: dict[str, Any] = {
                "model": self.model,
                "input": pending_input,
                "tools": [tool.as_openai_tool() for tool in tools],
            }
            if continuation_response_id is not None:
                request_payload["previous_response_id"] = continuation_response_id

            request_outcome = self._request_with_retries(request_payload)
            response_payload = request_outcome.payload
            response_id = _as_optional_str(response_payload.get("id"))
            model = _as_optional_str(response_payload.get("model"))
            usage = response_payload.get("usage") if isinstance(response_payload.get("usage"), dict) else {}
            _accumulate_usage(usage_totals, usage)

            parsed_calls = _extract_function_calls(response_payload)
            output_text = _extract_output_text(response_payload)

            if not parsed_calls:
                turn_record = ResponsesTurnRecord(
                    turn_index=turn_index,
                    request_payload=request_payload,
                    response_id=response_id,
                    request_id=request_outcome.request_id,
                    model=model,
                    usage=usage,
                    output_text=output_text,
                    function_calls=(),
                    progress_made=False,
                    no_progress_streak=no_progress_streak,
                    request_attempts=request_outcome.attempts,
                    retry_history=request_outcome.retry_history,
                )
                turns.append(turn_record)
                if on_turn_complete is not None:
                    on_turn_complete(turn_record)
                return ResponsesFunctionCallingResult(
                    turns=tuple(turns),
                    final_response_id=response_id,
                    final_request_id=request_outcome.request_id,
                    final_output_text=output_text,
                    total_usage=usage_totals,
                )

            executed_calls: list[ResponsesFunctionCallRecord] = []
            next_input: list[dict[str, Any]] = []
            turn_progress_made = False
            for parsed_call in parsed_calls:
                if parsed_call.name not in tool_map:
                    raise OpenAIResponsesError(
                        code="openai_invalid_output",
                        message="response requested an unknown function",
                        details={"function_name": parsed_call.name},
                    )
                arguments = _load_function_arguments(parsed_call.arguments_json)
                output_payload = execute_function(parsed_call.name, arguments)
                model_output_payload = _serialize_model_output(
                    model_output_serializer,
                    parsed_call.name,
                    arguments,
                    output_payload,
                )
                evidence_output_json = _serialize_function_output(output_payload)
                model_output_json = _serialize_function_output(model_output_payload)
                call_progress_made = _evaluate_progress(
                    progress_evaluator,
                    parsed_call.name,
                    arguments,
                    output_payload,
                )
                turn_progress_made = turn_progress_made or call_progress_made
                next_input.append(
                    {
                        "type": "function_call_output",
                        "call_id": parsed_call.call_id,
                        "output": model_output_json,
                    }
                )
                executed_calls.append(
                    ResponsesFunctionCallRecord(
                        call_id=parsed_call.call_id,
                        name=parsed_call.name,
                        arguments_json=parsed_call.arguments_json,
                        arguments=arguments,
                        model_output_json=model_output_json,
                        evidence_output_json=evidence_output_json,
                        progress_made=call_progress_made,
                    )
                )

            no_progress_streak = 0 if turn_progress_made else no_progress_streak + 1
            turn_record = ResponsesTurnRecord(
                turn_index=turn_index,
                request_payload=request_payload,
                response_id=response_id,
                request_id=request_outcome.request_id,
                model=model,
                usage=usage,
                output_text=output_text,
                function_calls=tuple(executed_calls),
                progress_made=turn_progress_made,
                no_progress_streak=no_progress_streak,
                request_attempts=request_outcome.attempts,
                retry_history=request_outcome.retry_history,
            )
            turns.append(turn_record)
            if on_turn_complete is not None:
                on_turn_complete(turn_record)
            if no_progress_limit is not None and no_progress_streak >= no_progress_limit:
                raise OpenAIResponsesError(
                    code="openai_tool_no_progress",
                    message="function-calling loop exhausted no-progress budget",
                    retryable=False,
                    details={
                        "turn_index": turn_index,
                        "no_progress_limit": no_progress_limit,
                        "no_progress_streak": no_progress_streak,
                    },
                )
            if response_id is None:
                raise OpenAIResponsesError(
                    code="openai_invalid_output",
                    message="response with function_call items is missing response id",
                )
            continuation_response_id = response_id
            pending_input = next_input

        raise OpenAIResponsesError(
            code="openai_tool_loop_exhausted",
            message="function-calling loop exhausted max_turns without a final model response",
            retryable=False,
            details={"max_turns": max_turns},
        )

    def _request_with_retries(
        self,
        request_payload: dict[str, Any],
    ) -> _RequestOutcome:
        attempts = 0
        retry_history: list[dict[str, Any]] = []
        while attempts <= self.max_retries:
            attempts += 1
            try:
                status_code, payload, request_id, response_headers = _normalize_transport_result(
                    self._transport(
                        request_payload,
                        self.timeout_seconds,
                    )
                )
            except OpenAIResponsesError as exc:
                if exc.retryable and attempts <= self.max_retries:
                    retry_delay = _retry_delay_seconds(exc, attempts=attempts)
                    retry_history.append(
                        _build_retry_history_entry(
                            attempt=attempts,
                            error=exc,
                            retry_after_seconds=retry_delay,
                            request_id=_as_optional_str(exc.details.get("request_id")),
                        )
                    )
                    time.sleep(retry_delay)
                    continue
                raise _augment_openai_error(
                    exc,
                    attempts=attempts,
                    retry_history=retry_history,
                )

            if status_code >= 400:
                error = _openai_error_from_response(
                    status_code=status_code,
                    response_payload=payload,
                    request_id=request_id,
                    response_headers=response_headers,
                )
                if error.retryable and attempts <= self.max_retries:
                    retry_delay = _retry_delay_seconds(error, attempts=attempts)
                    retry_history.append(
                        _build_retry_history_entry(
                            attempt=attempts,
                            error=error,
                            retry_after_seconds=retry_delay,
                            request_id=request_id,
                        )
                    )
                    time.sleep(retry_delay)
                    continue
                raise _augment_openai_error(
                    error,
                    attempts=attempts,
                    retry_history=retry_history,
                )
            return _RequestOutcome(
                status_code=status_code,
                payload=payload,
                request_id=request_id,
                attempts=attempts,
                retry_history=tuple(retry_history),
            )

        raise OpenAIResponsesError(
            code="openai_no_response",
            message="OpenAI response was unavailable after retry attempts",
            retryable=True,
            details={
                "attempts": attempts,
                "retry_history": retry_history,
            },
        )

    def _default_transport(
        self,
        request_payload: dict[str, Any],
        timeout_seconds: float,
    ) -> ResponseTransportResult:
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
                request_id = _as_optional_str(response.headers.get("x-request-id"))
                return (
                    int(response.status),
                    parsed,
                    request_id,
                    _response_headers_dict(response.headers),
                )
        except urllib_error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            parsed = _safe_json_parse(body_text)
            request_id = _as_optional_str(
                exc.headers.get("x-request-id") if exc.headers else None
            )
            return (
                int(exc.code),
                parsed,
                request_id,
                _response_headers_dict(exc.headers),
            )
        except urllib_error.URLError as exc:
            raise OpenAIResponsesError(
                code="openai_transport_error",
                message="OpenAI transport error",
                retryable=True,
                details={"reason": str(exc.reason)},
            ) from exc


def build_openai_function_calling_runner_from_env(
    *,
    transport: ResponseTransport | None = None,
) -> OpenAIResponsesFunctionCallingRunner:
    config = build_openai_responses_runtime_config_from_env()
    return build_openai_function_calling_runner(config=config, transport=transport)


def build_openai_function_calling_runner(
    *,
    config: OpenAIResponsesRuntimeConfig,
    transport: ResponseTransport | None = None,
) -> OpenAIResponsesFunctionCallingRunner:
    if not str(config.api_key).strip():
        raise OpenAIConfigError("OPENAI_API_KEY is required")
    return OpenAIResponsesFunctionCallingRunner(
        api_key=config.api_key,
        model=config.model,
        base_url=config.base_url,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        transport=transport,
    )


def _load_function_arguments(arguments_json: str) -> dict[str, Any]:
    try:
        decoded = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="function_call arguments are not valid JSON",
            details={"arguments": arguments_json},
        ) from exc
    if not isinstance(decoded, dict):
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="function_call arguments must decode to an object",
            details={"arguments": arguments_json},
        )
    return decoded


def _serialize_model_output(
    model_output_serializer: ModelOutputSerializer | None,
    function_name: str,
    arguments: dict[str, Any],
    output_payload: Any,
) -> Any:
    if model_output_serializer is None:
        return output_payload
    return model_output_serializer(function_name, arguments, output_payload)


def _serialize_function_output(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise OpenAIResponsesError(
            code="openai_invalid_request",
            message="tool output must be JSON-serializable or string",
            details={"type": value.__class__.__name__},
        ) from exc


def _extract_function_calls(response_payload: dict[str, Any]) -> list[_ParsedFunctionCall]:
    output = response_payload.get("output")
    if not isinstance(output, list):
        return []
    calls: list[_ParsedFunctionCall] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "") != "function_call":
            continue
        call_id = _as_optional_str(item.get("call_id"))
        name = _as_optional_str(item.get("name"))
        arguments_json = item.get("arguments")
        if call_id is None or name is None or not isinstance(arguments_json, str):
            raise OpenAIResponsesError(
                code="openai_invalid_output",
                message="function_call item is missing call_id/name/arguments",
            )
        calls.append(
            _ParsedFunctionCall(
                call_id=call_id,
                name=name,
                arguments_json=arguments_json,
            )
        )
    return calls


def _extract_output_text(response_payload: dict[str, Any]) -> str | None:
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
    return None


def _openai_error_from_response(
    *,
    status_code: int,
    response_payload: dict[str, Any],
    request_id: str | None,
    response_headers: dict[str, str] | None = None,
) -> OpenAIResponsesError:
    error_obj = response_payload.get("error") if isinstance(response_payload, dict) else None
    if not isinstance(error_obj, dict):
        error_obj = {}

    code = _as_optional_str(error_obj.get("code")) or f"openai_http_{status_code}"
    message = _as_optional_str(error_obj.get("message")) or "OpenAI request failed"
    retryable = status_code in {429, 500, 502, 503, 504}
    retry_after_seconds = _retry_after_seconds(
        headers=response_headers,
        message=message,
    )

    return OpenAIResponsesError(
        code=code,
        message=message,
        status_code=status_code,
        retryable=retryable,
        details={
            "request_id": request_id,
            "status_code": status_code,
            "retry_after_seconds": retry_after_seconds,
        },
    )


def _safe_json_parse(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _accumulate_usage(accumulator: dict[str, int], usage: dict[str, Any]) -> None:
    for key, value in usage.items():
        if not isinstance(value, int):
            continue
        accumulator[key] = int(accumulator.get(key, 0)) + value


def _evaluate_progress(
    progress_evaluator: ProgressEvaluator | None,
    function_name: str,
    arguments: dict[str, Any],
    output_payload: Any,
) -> bool:
    if progress_evaluator is not None:
        return bool(progress_evaluator(function_name, arguments, output_payload))
    if isinstance(output_payload, dict):
        return bool(output_payload.get("progress_made"))
    return False


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_transport_result(
    result: Any,
) -> tuple[int, dict[str, Any], str | None, dict[str, str]]:
    if len(result) == 3:
        status_code, payload, request_id = result
        return status_code, payload, request_id, {}
    status_code, payload, request_id, response_headers = result
    return status_code, payload, request_id, {
        str(key).lower(): str(value)
        for key, value in dict(response_headers or {}).items()
        if str(key).strip()
    }


def _response_headers_dict(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    items = getattr(headers, "items", None)
    if callable(items):
        return {
            str(key).lower(): str(value)
            for key, value in items()
            if str(key).strip()
        }
    return {}


def _retry_after_seconds(
    *,
    headers: dict[str, str] | None,
    message: str | None,
) -> float | None:
    if isinstance(headers, dict):
        raw_retry_after = headers.get("retry-after")
        if raw_retry_after is not None:
            parsed_header = _parse_retry_after_value(raw_retry_after)
            if parsed_header is not None:
                return parsed_header
    if isinstance(message, str):
        match = re.search(r"retry after\s+([0-9]+(?:\.[0-9]+)?)s", message, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def _parse_retry_after_value(raw_retry_after: Any) -> float | None:
    try:
        seconds = float(str(raw_retry_after).strip())
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return seconds


def _retry_delay_seconds(error: OpenAIResponsesError, *, attempts: int) -> float:
    retry_after = error.details.get("retry_after_seconds")
    try:
        retry_after_seconds = float(retry_after)
    except (TypeError, ValueError):
        retry_after_seconds = None
    if retry_after_seconds is not None and retry_after_seconds >= 0:
        return min(retry_after_seconds, 15.0)
    return min(float(2 ** max(attempts - 1, 0)), 15.0)


def _build_retry_history_entry(
    *,
    attempt: int,
    error: OpenAIResponsesError,
    retry_after_seconds: float,
    request_id: str | None,
) -> dict[str, Any]:
    return {
        "attempt": int(attempt),
        "error_code": error.code,
        "error_message": str(error),
        "status_code": error.status_code,
        "request_id": request_id,
        "retry_after_seconds": float(retry_after_seconds),
    }


def _augment_openai_error(
    error: OpenAIResponsesError,
    *,
    attempts: int,
    retry_history: list[dict[str, Any]],
) -> OpenAIResponsesError:
    details = dict(error.details)
    details["attempts"] = int(attempts)
    details["retry_history"] = [dict(item) for item in retry_history]
    return OpenAIResponsesError(
        code=error.code,
        message=str(error),
        status_code=error.status_code,
        retryable=error.retryable,
        details=details,
    )
