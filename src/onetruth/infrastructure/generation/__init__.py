"""Generation helpers for non-authoritative derived artifacts."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "GENERATOR_VERSION",
    "GenerationError",
    "check_workflow_prototype",
    "generate_workflow_prototype",
]

_EXPORT_TO_MODULE = {
    "GENERATOR_VERSION": ".prototype",
    "GenerationError": ".prototype",
    "check_workflow_prototype": ".prototype",
    "generate_workflow_prototype": ".prototype",
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
