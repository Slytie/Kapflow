from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "src" / "onetruth" / "api"
ROUTE_SPECS_DIR = API_DIR / "route_specs"
ROUTES_DIR = API_DIR / "routes"
ROUTE_REGISTRY = API_DIR / "route_registry.py"
API_MAIN = API_DIR / "main.py"


def test_route_spec_modules_do_not_import_forbidden_framework_neighbors() -> None:
    spec_files = sorted(
        path
        for path in ROUTE_SPECS_DIR.glob("*.py")
        if path.name not in {"__init__.py", "_core.py"}
    )
    spec_module_names = {path.stem for path in spec_files}
    violations: list[str] = []

    for spec_file in spec_files:
        for imported in _imported_modules(spec_file):
            if imported == "onetruth.api.main":
                violations.append(_render_violation(spec_file, imported))
            if imported == "onetruth.api.route_registry":
                violations.append(_render_violation(spec_file, imported))
            if imported.startswith("onetruth.api.route_specs."):
                target = imported.removeprefix("onetruth.api.route_specs.").split(".", 1)[0]
                if target in spec_module_names and target != spec_file.stem:
                    violations.append(_render_violation(spec_file, imported))

    assert not violations, "route-spec framework boundary violations:\n" + "\n".join(violations)


def test_route_registry_does_not_import_api_main_or_route_handlers_directly() -> None:
    imported = set(_imported_modules(ROUTE_REGISTRY))
    route_handler_imports = sorted(
        module
        for module in imported
        if module.startswith("onetruth.api.routes.")
    )

    assert "onetruth.api.main" not in imported
    assert not route_handler_imports, (
        "route_registry.py imports route handlers directly:\n"
        + "\n".join(route_handler_imports)
    )


def test_api_main_does_not_import_route_spec_modules_directly() -> None:
    imported = set(_imported_modules(API_MAIN))
    direct_spec_imports = sorted(
        module
        for module in imported
        if module.startswith("onetruth.api.route_specs.")
    )
    assert not direct_spec_imports, (
        "main.py imports route-spec modules directly:\n"
        + "\n".join(direct_spec_imports)
    )


def test_route_endpoint_modules_do_not_import_route_spec_modules() -> None:
    violations: list[str] = []
    route_files = sorted(path for path in ROUTES_DIR.glob("*.py") if path.name != "__init__.py")

    for route_file in route_files:
        spec_imports = sorted(
            module
            for module in _imported_modules(route_file)
            if module.startswith("onetruth.api.route_specs.")
        )
        for imported in spec_imports:
            violations.append(_render_violation(route_file, imported))

    assert not violations, "route modules import route-spec modules:\n" + "\n".join(violations)


def _render_violation(source: Path, imported: str) -> str:
    return f"{source.relative_to(REPO_ROOT)} imports '{imported}'"


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            modules.extend(_resolved_import_from_modules(node=node, source=path))

    return modules


def _resolved_import_from_modules(*, node: ast.ImportFrom, source: Path) -> list[str]:
    module_names: list[str] = []
    base_module = _resolve_import_from_base(node=node, source=source)

    if node.module is None:
        for alias in node.names:
            module_names.append(f"{base_module}.{alias.name}")
    else:
        module_names.append(base_module)

    return module_names


def _resolve_import_from_base(*, node: ast.ImportFrom, source: Path) -> str:
    if node.level == 0:
        assert node.module is not None
        return node.module

    relative_parts = list(source.relative_to(REPO_ROOT).with_suffix("").parts)
    anchor_parts = relative_parts[:-node.level]
    if node.module:
        anchor_parts.extend(node.module.split("."))
    return ".".join(anchor_parts)
