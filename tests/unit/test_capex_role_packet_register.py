from __future__ import annotations

import pytest

from onetruth.capex_platform.role_packet_register import (
    PACKET_REGISTER_SCHEMA_VERSION,
    ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION,
    ROLE_PACKET_ACTIVATION_POSTURE,
    RolePacketRegisterError,
    build_packet_register,
    build_role_assignment_register,
    role_packet_digest,
)


NOW = "2026-06-17T00:00:00Z"


def _occurrence_register() -> dict[str, object]:
    return {
        "schema_version": "capex.source_occurrence_register.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "register_id": "source-occurrence-register-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-role-packet",
        "rows": [
            {
                "source_occurrence_id": "so-primary",
                "source_ref": "source_occurrence:so-primary",
                "content_identity_id": "ci-shared",
                "content_digest": "sha256:" + ("1" * 64),
            },
            {
                "source_occurrence_id": "so-supporting",
                "source_ref": "source_occurrence:so-supporting",
                "content_identity_id": "ci-supporting",
                "content_digest": "sha256:" + ("2" * 64),
            },
        ],
    }


def _role_assignments() -> list[dict[str, object]]:
    return [
        {
            "source_ref": "source_occurrence:so-primary",
            "source_role": "primary_evidence",
            "review_state": "human_reviewed",
            "review_rationale": "Sanitized register row supports the baseline packet.",
            "ai_suggested": True,
        },
        {
            "source_ref": "source_occurrence:so-supporting",
            "source_role": "supporting_evidence",
            "review_state": "human_reviewed",
            "review_rationale": "Sanitized register row supports the same packet.",
            "ai_suggested": False,
        },
    ]


def _role_register() -> dict[str, object]:
    return build_role_assignment_register(
        source_occurrence_register=_occurrence_register(),
        role_assignments=_role_assignments(),
        register_id="role-register-001",
        created_at=NOW,
        reviewed_by_actor_id="human:pm",
        reviewed_by_actor_type="human",
    )


def test_role_assignment_register_records_reviewed_roles_without_official_truth() -> None:
    register = _role_register()

    assert register["schema_version"] == ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION
    assert register["activation_posture"] == ROLE_PACKET_ACTIVATION_POSTURE
    assert register["row_count"] == 2
    assert {row["source_role"] for row in register["rows"]} == {  # type: ignore[index]
        "primary_evidence",
        "supporting_evidence",
    }
    assert all(row["official_truth"] is False for row in register["rows"])  # type: ignore[index]
    assert register["truth_effects"] == {
        "creates_role_assignments": True,
        "creates_packet_register": False,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert role_packet_digest(register).startswith("sha256:")


def test_role_assignment_register_rejects_unknown_duplicate_and_raw_refs() -> None:
    with pytest.raises(RolePacketRegisterError) as unknown:
        build_role_assignment_register(
            source_occurrence_register=_occurrence_register(),
            role_assignments=[
                {
                    "source_ref": "source_occurrence:missing",
                    "source_role": "primary_evidence",
                    "review_state": "human_reviewed",
                    "review_rationale": "not present",
                }
            ],
            register_id="role-register-unknown",
            created_at=NOW,
            reviewed_by_actor_id="human:pm",
            reviewed_by_actor_type="human",
        )
    assert unknown.value.code == "role_assignment_unknown_source_ref"

    duplicate_rows = _role_assignments()
    duplicate_rows[1]["source_ref"] = "source_occurrence:so-primary"
    with pytest.raises(RolePacketRegisterError) as duplicate:
        build_role_assignment_register(
            source_occurrence_register=_occurrence_register(),
            role_assignments=duplicate_rows,
            register_id="role-register-duplicate",
            created_at=NOW,
            reviewed_by_actor_id="human:pm",
            reviewed_by_actor_type="human",
        )
    assert duplicate.value.code == "role_assignment_duplicate_source_ref"

    raw_rows = _role_assignments()
    raw_rows[0]["review_rationale"] = "/Users/pm/raw-source.pdf"
    with pytest.raises(RolePacketRegisterError) as raw:
        build_role_assignment_register(
            source_occurrence_register=_occurrence_register(),
            role_assignments=raw_rows,
            register_id="role-register-raw",
            created_at=NOW,
            reviewed_by_actor_id="human:pm",
            reviewed_by_actor_type="human",
        )
    assert raw.value.code == "role_packet_raw_value_forbidden"


def test_packet_register_supports_split_and_merge_without_baseline_truth() -> None:
    role_register = _role_register()

    packet_register = build_packet_register(
        role_assignment_register=role_register,
        packets=[
            {
                "packet_id": "packet-baseline-core",
                "packet_kind": "corpus_baseline",
                "review_state": "merged",
                "source_refs": [
                    "source_occurrence:so-primary",
                    "source_occurrence:so-supporting",
                ],
                "review_rationale": "Human merged both reviewed rows into one baseline packet.",
            },
            {
                "packet_id": "packet-primary-only",
                "packet_kind": "review_slice",
                "review_state": "split",
                "source_refs": ["source_occurrence:so-primary"],
                "review_rationale": "Human split primary evidence for separate review.",
            },
        ],
        register_id="packet-register-001",
        created_at=NOW,
        reviewed_by_actor_id="human:pm",
        reviewed_by_actor_type="human",
    )

    assert packet_register["schema_version"] == PACKET_REGISTER_SCHEMA_VERSION
    assert packet_register["packet_count"] == 2
    assert packet_register["truth_effects"] == {
        "creates_packet_register": True,
        "creates_reviewed_baseline": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert all(row["official_truth"] is False for row in packet_register["rows"])  # type: ignore[index]
    assert role_packet_digest(packet_register).startswith("sha256:")


def test_packet_register_rejects_unassigned_refs_duplicate_refs_and_invalid_state() -> None:
    role_register = _role_register()
    base_packet = {
        "packet_id": "packet-baseline-core",
        "packet_kind": "corpus_baseline",
        "review_state": "human_reviewed",
        "source_refs": ["source_occurrence:so-primary"],
        "review_rationale": "Human reviewed packet.",
    }

    unknown = dict(base_packet)
    unknown["source_refs"] = ["source_occurrence:missing"]
    with pytest.raises(RolePacketRegisterError) as unknown_exc:
        build_packet_register(
            role_assignment_register=role_register,
            packets=[unknown],
            register_id="packet-register-unknown",
            created_at=NOW,
            reviewed_by_actor_id="human:pm",
            reviewed_by_actor_type="human",
        )
    assert unknown_exc.value.code == "packet_source_ref_not_role_assigned"

    duplicate = dict(base_packet)
    duplicate["source_refs"] = [
        "source_occurrence:so-primary",
        "source_occurrence:so-primary",
    ]
    with pytest.raises(RolePacketRegisterError) as duplicate_exc:
        build_packet_register(
            role_assignment_register=role_register,
            packets=[duplicate],
            register_id="packet-register-duplicate",
            created_at=NOW,
            reviewed_by_actor_id="human:pm",
            reviewed_by_actor_type="human",
        )
    assert duplicate_exc.value.code == "packet_duplicate_source_ref"

    invalid = dict(base_packet)
    invalid["review_state"] = "official"
    with pytest.raises(RolePacketRegisterError) as invalid_exc:
        build_packet_register(
            role_assignment_register=role_register,
            packets=[invalid],
            register_id="packet-register-invalid",
            created_at=NOW,
            reviewed_by_actor_id="human:pm",
            reviewed_by_actor_type="human",
        )
    assert invalid_exc.value.code == "packet_review_state_invalid"
