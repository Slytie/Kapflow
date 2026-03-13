from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.queries import query_pointers


def list_pointers_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    rows = query_pointers(
        connection,
        context=context,
        pointer_id=query.get("pointer_id"),
        pointer_key=query.get("pointer_key"),
        workflow_run_id=query.get("workflow_run_id"),
        dataset_key=query.get("dataset_key"),
        partition_kind=query.get("partition_kind"),
        partition_key=query.get("partition_key"),
        stream_key=query.get("stream_key"),
        registry_kind=query.get("registry_kind"),
        scope_kind=query.get("scope_kind"),
        scope_ref=query.get("scope_ref"),
        artifact_kind=query.get("artifact_kind"),
        page=page,
    )
    return {
        "command": "api.pointers.list",
        "pointers": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }
