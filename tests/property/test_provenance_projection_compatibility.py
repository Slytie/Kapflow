from __future__ import annotations

from itertools import permutations

from onetruth.infrastructure.repositories.artifact_provenance import (
    project_legacy_lineage_from_edge_rows,
)


def test_projection_is_deterministic_for_edge_row_order() -> None:
    edge_rows = [
        {
            "output_artifact_version_id": "av-out",
            "input_artifact_version_id": "av-parent-b",
            "edge_type": "derives_from",
            "edge_order": 2,
        },
        {
            "output_artifact_version_id": "av-out",
            "input_artifact_version_id": "av-parent-a",
            "edge_type": "derives_from",
            "edge_order": 1,
        },
        {
            "output_artifact_version_id": "av-out",
            "input_artifact_version_id": "av-superseded-a",
            "edge_type": "supersedes",
            "edge_order": 1,
        },
        {
            "output_artifact_version_id": "av-out",
            "input_artifact_version_id": "av-reviewed",
            "edge_type": "reviewed_against",
            "edge_order": 1,
        },
    ]

    expected = {
        "parent_artifact_version_id": "av-parent-a",
        "supersedes_artifact_version_id": "av-superseded-a",
    }
    for permutation in permutations(edge_rows):
        assert project_legacy_lineage_from_edge_rows(list(permutation)) == expected

