from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTES_DIR = REPO_ROOT / "src" / "onetruth" / "api" / "routes"


def test_route_modules_do_not_import_sibling_route_modules() -> None:
    route_files = sorted(path for path in ROUTES_DIR.glob("*.py") if path.name != "__init__.py")
    route_module_names = {path.stem for path in route_files}
    violations: list[str] = []

    for route_file in route_files:
        tree = ast.parse(route_file.read_text(encoding="utf-8"), filename=str(route_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = _absolute_route_target(alias.name, route_module_names)
                    if target is not None:
                        violations.append(
                            f"{route_file.relative_to(REPO_ROOT)} imports route module "
                            f"'{target}' via '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                target = _import_from_target(node=node, route_module_names=route_module_names)
                if target is not None:
                    rendered = "." * node.level + (node.module or "")
                    violations.append(
                        f"{route_file.relative_to(REPO_ROOT)} imports route module "
                        f"'{target}' via '{rendered}'"
                    )

    assert not violations, "route-layer boundary violations:\n" + "\n".join(violations)


def _absolute_route_target(module_name: str, route_module_names: set[str]) -> str | None:
    prefix = "onetruth.api.routes."
    if not module_name.startswith(prefix):
        return None
    target = module_name.removeprefix(prefix).split(".", 1)[0]
    if target in route_module_names:
        return target
    return None


def _import_from_target(*, node: ast.ImportFrom, route_module_names: set[str]) -> str | None:
    absolute_target = _absolute_route_target(node.module or "", route_module_names)
    if absolute_target is not None:
        return absolute_target

    if node.level != 1:
        return None

    if node.module:
        relative_target = node.module.split(".", 1)[0]
        if relative_target in route_module_names:
            return relative_target
        return None

    for alias in node.names:
        if alias.name in route_module_names:
            return alias.name
    return None
