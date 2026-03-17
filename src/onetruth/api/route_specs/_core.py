from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Callable, Literal

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.errors import ApiError
from onetruth.api.responses import BinaryResponse

RequestBodyKind = Literal["none", "json"]
RouteResult = dict[str, Any] | BinaryResponse
RouteDispatcher = Callable[["RouteExecutionContext", dict[str, str]], RouteResult]


@dataclass(frozen=True)
class RequestBodyPolicy:
    kind: RequestBodyKind
    required_content_type: str | None = None
    max_bytes: int | None = None


NO_BODY = RequestBodyPolicy(kind="none")
JSON_COMMAND_BODY = RequestBodyPolicy(
    kind="json",
    required_content_type="application/json",
    max_bytes=256 * 1024,
)
JSON_ARTIFACT_BODY = RequestBodyPolicy(
    kind="json",
    required_content_type="application/json",
    max_bytes=2 * 1024 * 1024,
)


@dataclass(frozen=True)
class RoutePattern:
    exact_path: str | None = None
    prefix: str | None = None
    suffix: str = ""
    param_name: str | None = None
    allow_slash: bool = False

    def match(self, path: str) -> dict[str, str] | None:
        if self.exact_path is not None:
            if path == self.exact_path:
                return {}
            return None

        assert self.prefix is not None
        assert self.param_name is not None

        if not path.startswith(self.prefix):
            return None
        if self.suffix:
            if not path.endswith(self.suffix):
                return None
            if len(path) <= len(self.prefix) + len(self.suffix):
                return None
            value = path[len(self.prefix) : -len(self.suffix)]
        else:
            value = path[len(self.prefix) :]
            if not value:
                return None

        if not value:
            return None
        if not self.allow_slash and "/" in value:
            return None
        return {self.param_name: value}


@dataclass(frozen=True)
class RouteSpec:
    name: str
    method: str
    pattern: RoutePattern
    body_policy: RequestBodyPolicy
    needs_page: bool
    dispatch: RouteDispatcher


@dataclass(frozen=True)
class RouteMatch:
    route: RouteSpec
    params: dict[str, str]

    def dispatch(self, execution: "RouteExecutionContext") -> RouteResult:
        return self.route.dispatch(execution, self.params)


@dataclass(frozen=True)
class RouteExecutionContext:
    connection: sqlite3.Connection
    context: RequestContext
    query: dict[str, str]
    page: Page | None
    payload: dict[str, Any] | None
    db_url: str


def _exact(path: str) -> RoutePattern:
    return RoutePattern(exact_path=path)


def _param(
    prefix: str,
    *,
    param_name: str,
    suffix: str = "",
    allow_slash: bool = False,
) -> RoutePattern:
    return RoutePattern(
        prefix=prefix,
        suffix=suffix,
        param_name=param_name,
        allow_slash=allow_slash,
    )


def _require_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        raise ApiError(
            status_code=400,
            code="invalid_payload",
            message="request body is required",
            details={},
        )
    return payload


def _require_page(page: Page | None) -> Page:
    assert page is not None
    return page
