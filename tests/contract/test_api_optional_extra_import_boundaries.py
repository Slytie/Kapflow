from __future__ import annotations

import os
import subprocess
import sys
import textwrap

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


def _blocked_import_script(
    *,
    blocked: tuple[str, ...],
    body: str,
) -> str:
    blocked_literals = ", ".join(repr(name) for name in blocked)
    return textwrap.dedent(
        f"""
import importlib.abc
import sys

class Blocker(importlib.abc.MetaPathFinder):
    def __init__(self, blocked):
        self.blocked = set(blocked)

    def find_spec(self, fullname, path, target=None):
        root = fullname.split(".", 1)[0]
        if fullname in self.blocked or root in self.blocked:
            raise ModuleNotFoundError(f"blocked import: {{fullname}}")
        return None

sys.meta_path.insert(0, Blocker(({blocked_literals},)))
{textwrap.dedent(body).strip()}
"""
    ).strip()


def test_import_onetruth_api_succeeds_without_optional_api_dependencies() -> None:
    result = _run_probe(
        _blocked_import_script(
            blocked=("jwt", "uvicorn"),
            body="""
import onetruth.api
print("ok")
""",
        )
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_import_onetruth_api_main_succeeds_without_optional_api_dependencies() -> None:
    result = _run_probe(
        _blocked_import_script(
            blocked=("jwt", "uvicorn"),
            body="""
import onetruth.api.main
print("ok")
""",
        )
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_import_shared_env_principal_resolver_succeeds_without_pyjwt() -> None:
    result = _run_probe(
        _blocked_import_script(
            blocked=("jwt",),
            body="""
import onetruth.api.shared_env_principal_resolver
print("ok")
""",
        )
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_from_onetruth_api_import_create_app_succeeds_without_optional_api_dependencies() -> None:
    result = _run_probe(
        _blocked_import_script(
            blocked=("jwt", "uvicorn"),
            body="""
from onetruth.api import create_app
assert callable(create_app)
print("ok")
""",
        )
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_create_app_fails_with_clear_pyjwt_message_when_shared_env_jwt_path_is_activated() -> None:
    result = _run_probe(
        _blocked_import_script(
            blocked=("jwt",),
            body="""
import os

from onetruth.api import create_app

os.environ["ONETRUTH_SHARED_ENV_JWT_ISSUER"] = "issuer"
os.environ["ONETRUTH_SHARED_ENV_JWT_AUDIENCE"] = "audience"
os.environ["ONETRUTH_SHARED_ENV_JWT_PUBLIC_KEY_PEM"] = "public-key"

try:
    create_app()
except Exception as exc:
    print(type(exc).__name__)
    print(str(exc))
else:
    raise SystemExit("expected create_app() to fail without PyJWT")
""",
        )
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "RuntimeError",
        "PyJWT is required for the shared_env JWT principal resolver. Install with `python3 -m pip install -e .[api]`.",
    ]


def test_main_retains_explicit_uvicorn_install_hint() -> None:
    result = _run_probe(
        _blocked_import_script(
            blocked=("uvicorn",),
            body="""
from onetruth.api.main import main

try:
    main([])
except SystemExit as exc:
    print(str(exc))
else:
    raise SystemExit("expected main([]) to fail without uvicorn")
""",
        )
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "uvicorn is required to run the API server. Install with `python3 -m pip install -e .[api]`."
    )
