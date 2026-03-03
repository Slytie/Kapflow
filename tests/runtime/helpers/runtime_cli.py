from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"


def run_cli(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = str(SRC_ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "onetruth.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if expect_ok and result.returncode != 0:
        pytest.fail(
            f"CLI failed ({result.returncode})\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    return result


def stdout_json(result: subprocess.CompletedProcess[str]) -> Any:
    assert result.stdout
    return json.loads(result.stdout)


def stderr_json(result: subprocess.CompletedProcess[str]) -> Any:
    assert result.stderr
    return json.loads(result.stderr)
