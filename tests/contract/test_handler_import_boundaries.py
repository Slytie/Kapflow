from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HANDLERS_DIR = REPO_ROOT / "src" / "onetruth" / "application" / "handlers"
TARGET_MODULE = "onetruth.application.handlers.workflow_task_lifecycle"


def test_approvals_and_shared_handler_modules_do_not_import_legacy_hotspot() -> None:
    target_files = [
        HANDLERS_DIR / "approvals.py",
        HANDLERS_DIR / "human_tasks.py",
        *sorted((HANDLERS_DIR / "_shared").glob("*.py")),
    ]
    violations: list[str] = []

    for target_file in target_files:
        assert target_file.exists(), f"expected handler seam file to exist: {target_file.relative_to(REPO_ROOT)}"
        tree = ast.parse(target_file.read_text(encoding="utf-8"), filename=str(target_file))
        current_package = _package_parts_for_file(target_file)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == TARGET_MODULE or alias.name.startswith(f"{TARGET_MODULE}."):
                        violations.append(
                            f"{target_file.relative_to(REPO_ROOT)} imports legacy hotspot via '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_import_from(node=node, current_package=current_package)
                if resolved == TARGET_MODULE or resolved.startswith(f"{TARGET_MODULE}."):
                    rendered = "." * node.level + (node.module or "")
                    violations.append(
                        f"{target_file.relative_to(REPO_ROOT)} imports legacy hotspot via '{rendered}'"
                    )

    assert not violations, "handler import boundary violations:\n" + "\n".join(violations)


def _package_parts_for_file(path: Path) -> tuple[str, ...]:
    relative_parts = path.relative_to(REPO_ROOT / "src").with_suffix("").parts
    if path.name == "__init__.py":
        return relative_parts[:-1]
    return relative_parts[:-1]


def _resolve_import_from(*, node: ast.ImportFrom, current_package: tuple[str, ...]) -> str:
    if node.level == 0:
        return node.module or ""

    base_parts = current_package[: len(current_package) - (node.level - 1)]
    if node.module:
        return ".".join((*base_parts, *node.module.split(".")))
    return ".".join(base_parts)
