#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO_ROOT / "frontend"
DEFAULT_DEMO_JSON = ".tmp/logistics-canonical-workpage-demo.json"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8080/api/v1"
DEFAULT_FRONTEND_HOST = "127.0.0.1"
DEFAULT_FRONTEND_CONTEXT = {
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Launch the local logistics demo frontend with the trusted-header request "
            "context that matches the seeded logistics tenant/domain."
        ),
    )
    parser.add_argument(
        "--demo-json",
        default=DEFAULT_DEMO_JSON,
        help="Prep/seeder JSON path. Defaults to the canonical workpage demo output.",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help="Base API URL passed through to Vite.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_FRONTEND_HOST,
        help="Host passed to `npm run dev -- --host ...`.",
    )
    parser.add_argument(
        "--print-launch-config",
        action="store_true",
        help="Print the derived launch configuration as JSON and exit.",
    )
    return parser


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _load_demo_payload(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"demo JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"demo JSON is not valid JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError(f"demo JSON must contain an object payload: {path}")
    return raw


def _normalize_actor_roles(value: object) -> list[str]:
    if isinstance(value, list):
        roles = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if roles:
            return roles
    if isinstance(value, str):
        roles = [item.strip() for item in value.split(",") if item.strip()]
        if roles:
            return roles
    return list(DEFAULT_FRONTEND_CONTEXT["actor_roles"])


def _frontend_request_context(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("frontend_request_context")
    source = raw if isinstance(raw, dict) else {}
    return {
        "tenant_id": str(source.get("tenant_id") or DEFAULT_FRONTEND_CONTEXT["tenant_id"]),
        "domain_id": str(source.get("domain_id") or DEFAULT_FRONTEND_CONTEXT["domain_id"]),
        "actor_id": str(source.get("actor_id") or DEFAULT_FRONTEND_CONTEXT["actor_id"]),
        "actor_type": str(source.get("actor_type") or DEFAULT_FRONTEND_CONTEXT["actor_type"]),
        "actor_roles": _normalize_actor_roles(source.get("actor_roles")),
    }


def _route_payload(payload: dict[str, Any]) -> dict[str, str]:
    routes: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(value, str) or not value.strip():
            continue
        if not value.startswith("/"):
            continue
        if key.endswith("_url") or key.endswith("_path"):
            routes[key] = value
    return routes


def _build_launch_config(
    *,
    demo_json_path: Path,
    payload: dict[str, Any],
    api_base_url: str,
    host: str,
) -> dict[str, Any]:
    request_context = _frontend_request_context(payload)
    frontend_env = {
        "VITE_ONETRUTH_API_BASE_URL": api_base_url,
        "VITE_ONETRUTH_TENANT_ID": str(request_context["tenant_id"]),
        "VITE_ONETRUTH_DOMAIN_ID": str(request_context["domain_id"]),
        "VITE_ONETRUTH_ACTOR_ID": str(request_context["actor_id"]),
        "VITE_ONETRUTH_ACTOR_TYPE": str(request_context["actor_type"]),
        "VITE_ONETRUTH_ACTOR_ROLES": ",".join(request_context["actor_roles"]),
    }
    return {
        "status": "ok",
        "command": "logistics-demo-frontend.launch",
        "demo_json_path": str(demo_json_path),
        "frontend_cwd": str(FRONTEND_ROOT),
        "frontend_command": ["npm", "run", "dev", "--", "--host", host],
        "frontend_origin_hint": f"http://{host}:5173",
        "frontend_request_context": request_context,
        "frontend_env": frontend_env,
        "routes": _route_payload(payload),
    }


def _print_summary(config: dict[str, Any]) -> None:
    context = config["frontend_request_context"]
    print("Launching logistics demo frontend with local-dev trusted headers:", flush=True)
    print(
        f"- scope: {context['tenant_id']} / {context['domain_id']}",
        flush=True,
    )
    print(
        f"- actor: {context['actor_id']} ({','.join(context['actor_roles'])})",
        flush=True,
    )
    print(f"- demo JSON: {config['demo_json_path']}", flush=True)
    print(f"- frontend origin hint: {config['frontend_origin_hint']}", flush=True)
    routes = config["routes"]
    if routes:
        print("- routes from prep JSON:", flush=True)
        for key, value in routes.items():
            print(f"  {key}: {value}", flush=True)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    demo_json_path = _resolve_path(str(args.demo_json))
    try:
        payload = _load_demo_payload(demo_json_path)
    except RuntimeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    config = _build_launch_config(
        demo_json_path=demo_json_path,
        payload=payload,
        api_base_url=str(args.api_base_url),
        host=str(args.host),
    )
    if args.print_launch_config:
        sys.stdout.write(json.dumps(config, indent=2, sort_keys=True) + "\n")
        return 0

    _print_summary(config)
    env = os.environ.copy()
    env.update(config["frontend_env"])
    try:
        completed = subprocess.run(
            config["frontend_command"],
            cwd=FRONTEND_ROOT,
            env=env,
            check=False,
        )
    except KeyboardInterrupt:
        return 130
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
