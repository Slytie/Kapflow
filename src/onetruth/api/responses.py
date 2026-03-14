from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BinaryResponse:
    body: bytes
    media_type: str
    file_name: str


def sanitize_download_filename(
    file_name: str | None,
    *,
    fallback: str,
) -> str:
    candidate = (file_name or "").strip() or fallback
    return (
        candidate.replace("\r", "")
        .replace("\n", "")
        .replace('"', "")
        .replace("\\", "")
        or fallback
    )
