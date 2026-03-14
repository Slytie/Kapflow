from __future__ import annotations

import secrets
from typing import Mapping

REQUEST_ID_HEADER = "x-request-id"
_REQUEST_ID_MAX_LENGTH = 128


def resolve_request_id(headers: Mapping[str, str] | None) -> str:
    if headers is not None:
        normalized = normalize_request_id(headers.get(REQUEST_ID_HEADER))
        if normalized is not None:
            return normalized
    return generate_request_id()


def normalize_request_id(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > _REQUEST_ID_MAX_LENGTH:
        return None
    try:
        candidate.encode("ascii")
    except UnicodeEncodeError:
        return None
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in candidate):
        return None
    return candidate


def generate_request_id() -> str:
    return f"httpreq_{secrets.token_hex(16)}"


def request_id_header(request_id: str) -> tuple[bytes, bytes]:
    return (
        REQUEST_ID_HEADER.encode("ascii"),
        request_id.encode("ascii"),
    )
