"""Thin HTTP adapter over canonical onetruth runtime handlers and query surfaces."""

from .main import app, create_app

__all__ = ["app", "create_app"]
