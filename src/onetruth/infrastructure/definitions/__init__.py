from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ControlCompileError",
    "DefinitionCompileError",
    "compile_control_layer",
    "compile_workflow_family",
    "derive_execution_session_payload",
    "resolve_stage_execution_spec",
    "validate_activation_request",
]

_EXPORT_TO_MODULE = {
    "ControlCompileError": ".control_layer",
    "compile_control_layer": ".control_layer",
    "derive_execution_session_payload": ".control_layer",
    "resolve_stage_execution_spec": ".control_layer",
    "validate_activation_request": ".control_layer",
    "DefinitionCompileError": ".family_compiler",
    "compile_workflow_family": ".family_compiler",
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
