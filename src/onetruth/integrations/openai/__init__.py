from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "OpenAIConfigError",
    "OpenAIResponseMetadata",
    "OpenAIResponsesError",
    "OpenAIResponsesRuntimeConfig",
    "OpenAIResponsesStage06Classifier",
    "OpenAIResponsesFunctionCallingRunner",
    "ResponsesFunctionCallRecord",
    "ResponsesFunctionCallingResult",
    "ResponsesFunctionToolSpec",
    "ResponsesTurnRecord",
    "STAGE06_ALLOWED_FOLLOW_ON_TASK_KINDS",
    "STAGE06_ALLOWED_OUTCOMES",
    "STAGE06_REVIEW_OUTPUT_SCHEMA",
    "Stage06ReviewClassification",
    "Stage06ReviewClassifier",
    "build_openai_function_calling_runner",
    "build_openai_function_calling_runner_from_env",
    "build_openai_responses_runtime_config_from_env",
    "build_stage06_review_classifier_from_env",
    "parse_stage06_review_output",
    "validate_stage06_review_output",
]

_EXPORT_TO_MODULE = {
    "OpenAIConfigError": ".responses_adapter",
    "OpenAIResponseMetadata": ".responses_adapter",
    "OpenAIResponsesError": ".responses_adapter",
    "OpenAIResponsesRuntimeConfig": ".responses_adapter",
    "OpenAIResponsesStage06Classifier": ".responses_adapter",
    "STAGE06_ALLOWED_FOLLOW_ON_TASK_KINDS": ".responses_adapter",
    "STAGE06_ALLOWED_OUTCOMES": ".responses_adapter",
    "STAGE06_REVIEW_OUTPUT_SCHEMA": ".responses_adapter",
    "Stage06ReviewClassification": ".responses_adapter",
    "Stage06ReviewClassifier": ".responses_adapter",
    "build_openai_responses_runtime_config_from_env": ".responses_adapter",
    "build_stage06_review_classifier_from_env": ".responses_adapter",
    "parse_stage06_review_output": ".responses_adapter",
    "validate_stage06_review_output": ".responses_adapter",
    "OpenAIResponsesFunctionCallingRunner": ".responses_agent_runner",
    "ResponsesFunctionCallRecord": ".responses_agent_runner",
    "ResponsesFunctionCallingResult": ".responses_agent_runner",
    "ResponsesFunctionToolSpec": ".responses_agent_runner",
    "ResponsesTurnRecord": ".responses_agent_runner",
    "build_openai_function_calling_runner": ".responses_agent_runner",
    "build_openai_function_calling_runner_from_env": ".responses_agent_runner",
}


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
