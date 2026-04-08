from __future__ import annotations

import json
from pathlib import Path

from tests.runtime.helpers.logistics_workpage_demo import (
    run_logistics_demo_frontend_launcher_script,
    run_logistics_workpage_demo_prep_script,
)


def test_logistics_demo_frontend_launcher_uses_prep_request_context_and_expected_vite_env(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'workpage-demo.db'}"
    output_json_path = tmp_path / "workpage-demo.json"
    prepared = run_logistics_workpage_demo_prep_script(
        db_url=db_url,
        output_json_path=output_json_path,
    )

    payload = run_logistics_demo_frontend_launcher_script(
        demo_json_path=output_json_path,
    )

    assert payload["status"] == "ok"
    assert payload["command"] == "logistics-demo-frontend.launch"
    assert payload["demo_json_path"] == str(output_json_path)
    assert payload["frontend_cwd"].endswith("/frontend")
    assert payload["frontend_command"] == ["npm", "run", "dev", "--", "--host", "127.0.0.1"]
    assert payload["frontend_origin_hint"] == "http://127.0.0.1:5173"
    assert payload["frontend_request_context"] == prepared["frontend_request_context"]
    assert payload["frontend_env"] == {
        "VITE_ONETRUTH_API_BASE_URL": "http://127.0.0.1:8080/api/v1",
        "VITE_ONETRUTH_TENANT_ID": "tenant-logistics",
        "VITE_ONETRUTH_DOMAIN_ID": "domain-hub",
        "VITE_ONETRUTH_ACTOR_ID": "human:frontend-operator",
        "VITE_ONETRUTH_ACTOR_TYPE": "human",
        "VITE_ONETRUTH_ACTOR_ROLES": (
            "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
        ),
    }
    assert payload["routes"]["recommended_story_url"] == prepared["recommended_story_url"]
    assert payload["routes"]["schedule_workpage_url"] == prepared["schedule_workpage_url"]
    assert payload["routes"]["schedule_artifact_url"] == prepared["schedule_artifact_url"]
    assert payload["routes"]["eod_workpage_url"] == prepared["eod_workpage_url"]


def test_logistics_demo_frontend_launcher_falls_back_to_canonical_logistics_context(
    tmp_path: Path,
) -> None:
    demo_json_path = tmp_path / "local-demo.json"
    demo_json_path.write_text(
        json.dumps(
            {
                "recommended_story_url": (
                    "/demo/logistics?planning_week_id=PW-2026-W10&service_date_id=SD-2026-03-06"
                ),
                "weekly_workspace_url": "/runs/wr-demo-weekly-bff9cf41d4dd/workspace",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_logistics_demo_frontend_launcher_script(
        demo_json_path=demo_json_path,
    )

    assert payload["frontend_request_context"] == {
        "tenant_id": "tenant-logistics",
        "domain_id": "domain-hub",
        "actor_id": "human:frontend-operator",
        "actor_type": "human",
        "actor_roles": [
            "dispatch_supervisor",
            "schedule_planner",
            "fleet_coordinator",
            "operations_manager",
        ],
    }
    assert payload["routes"] == {
        "recommended_story_url": (
            "/demo/logistics?planning_week_id=PW-2026-W10&service_date_id=SD-2026-03-06"
        ),
        "weekly_workspace_url": "/runs/wr-demo-weekly-bff9cf41d4dd/workspace",
    }
