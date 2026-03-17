"""Thin HTTP adapter over canonical onetruth runtime handlers and query surfaces."""

from __future__ import annotations

from typing import Any

__all__ = ["app", "create_app"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import main as api_main

        return getattr(api_main, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
