from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import tomllib

from tests.helpers.repo_paths import REPO_ROOT


def _run_probe(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT / "src"),
        },
        check=False,
        capture_output=True,
        text=True,
    )


def _pyproject_dependencies() -> tuple[list[str], dict[str, list[str]]]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        loaded = tomllib.load(handle)
    project = loaded["project"]
    dependencies = list(project["dependencies"])
    optional_dependencies = {
        key: list(value)
        for key, value in project["optional-dependencies"].items()
    }
    return dependencies, optional_dependencies


def test_pyyaml_is_a_core_runtime_dependency() -> None:
    dependencies, optional_dependencies = _pyproject_dependencies()

    assert "PyYAML>=6,<7" in dependencies
    assert "PyYAML>=6,<7" not in optional_dependencies["dev"]


def test_bare_package_imports_stay_lazy() -> None:
    result = _run_probe(
        textwrap.dedent(
            """
            import sys

            import onetruth.infrastructure.definitions
            import onetruth.infrastructure.generation
            import onetruth.integrations.openai

            blocked = {
                "yaml",
                "onetruth.infrastructure.definitions.control_layer",
                "onetruth.infrastructure.definitions.family_compiler",
                "onetruth.infrastructure.generation.prototype",
                "onetruth.integrations.openai.responses_adapter",
                "onetruth.integrations.openai.responses_agent_runner",
                "onetruth.infrastructure.events.event_store",
            }

            loaded = blocked.intersection(sys.modules)
            assert not loaded, sorted(loaded)
            print("ok")
            """
        ).strip()
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_exported_symbols_still_resolve_when_accessed() -> None:
    result = _run_probe(
        textwrap.dedent(
            """
            import sys

            import onetruth.infrastructure.definitions as definitions
            import onetruth.infrastructure.generation as generation
            import onetruth.integrations.openai as openai_exports

            assert callable(definitions.compile_control_layer)
            assert callable(generation.generate_workflow_prototype)
            assert openai_exports.OpenAIResponsesFunctionCallingRunner.__name__ == "OpenAIResponsesFunctionCallingRunner"

            required = {
                "yaml",
                "onetruth.infrastructure.definitions.control_layer",
                "onetruth.infrastructure.generation.prototype",
                "onetruth.integrations.openai.responses_agent_runner",
            }
            missing = sorted(name for name in required if name not in sys.modules)
            assert not missing, missing
            print("ok")
            """
        ).strip()
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
