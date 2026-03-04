from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkspaceGraphNode:
    node_id: str
    label: str
    kind: str
    status: str
    reason: str | None
    blocking_subject_ids: tuple[str, ...]
    primary_subject_id: str | None
    updated_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "kind": self.kind,
            "status": self.status,
            "reason": self.reason,
            "blocking_subject_ids": list(self.blocking_subject_ids),
            "primary_subject_id": self.primary_subject_id,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class WorkspaceGraphEdge:
    from_node: str
    to_node: str
    kind: str
    label: str | None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "from": self.from_node,
            "to": self.to_node,
            "kind": self.kind,
        }
        if self.label is not None:
            payload["label"] = self.label
        return payload


@dataclass(frozen=True)
class WorkspaceGraphProjection:
    nodes: tuple[WorkspaceGraphNode, ...]
    edges: tuple[WorkspaceGraphEdge, ...]
    summary: dict[str, Any]
    latest_event_sequence: int | None
    warnings: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
            "summary": self.summary,
            "latest_event_sequence": self.latest_event_sequence,
            "warnings": list(self.warnings),
        }

