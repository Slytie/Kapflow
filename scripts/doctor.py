#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys


EXPECTED_PYTHON = (3, 11)
EXPECTED_NODE_MAJOR = 20
REQUIRED_FILES = (
    ".nvmrc",
    "LICENSE",
    ".github/CODEOWNERS",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def _python_version(executable: str) -> tuple[int, int, int] | None:
    result = _run_command(
        [
            executable,
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
        ]
    )
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    try:
        major, minor, micro = (int(part) for part in raw.split(".", 2))
    except ValueError:
        return None
    return (major, minor, micro)


def _node_version() -> tuple[int, int, int] | None:
    node = shutil.which("node")
    if node is None:
        return None
    result = _run_command([node, "-v"])
    if result.returncode != 0:
        return None
    raw = result.stdout.strip().lstrip("v")
    try:
        major, minor, patch = (int(part) for part in raw.split(".", 2))
    except ValueError:
        return None
    return (major, minor, patch)


def _load_expected_node_major(repo_root: Path) -> int | None:
    nvmrc_path = repo_root / ".nvmrc"
    if not nvmrc_path.exists():
        return None
    raw = nvmrc_path.read_text(encoding="utf-8").strip().lstrip("v")
    try:
        return int(raw.split(".", 1)[0])
    except ValueError:
        return None


def _check_python_baseline() -> CheckResult:
    python3_path = shutil.which("python3")
    if python3_path is None:
        return CheckResult("python", False, "python3 is not on PATH")

    python3_version = _python_version(python3_path)
    if python3_version is None:
        return CheckResult("python", False, f"unable to inspect python3 at {python3_path}")

    baseline_candidates = []
    current_version = sys.version_info[:3]
    if current_version[:2] == EXPECTED_PYTHON:
        baseline_candidates.append(sys.executable)
    python311_path = shutil.which("python3.11")
    if python311_path is not None and python311_path not in baseline_candidates:
        baseline_candidates.append(python311_path)

    for candidate in baseline_candidates:
        version = _python_version(candidate)
        if version is None:
            continue
        if version[:2] == EXPECTED_PYTHON:
            return CheckResult(
                "python",
                True,
                (
                    f"python3 -> {python3_version[0]}.{python3_version[1]}.{python3_version[2]}; "
                    f"validated baseline available at {candidate} ({version[0]}.{version[1]}.{version[2]})"
                ),
            )

    return CheckResult(
        "python",
        False,
        (
            f"python3 -> {python3_version[0]}.{python3_version[1]}.{python3_version[2]}; "
            "python3.11 is required as the validated dev/CI baseline"
        ),
    )


def _check_node_toolchain(repo_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    expected_major = _load_expected_node_major(repo_root)
    node = shutil.which("node")
    if node is None:
        results.append(CheckResult("node", False, "node is not on PATH"))
    else:
        version = _node_version()
        if version is None:
            results.append(CheckResult("node", False, "unable to inspect node version"))
        elif expected_major is None:
            results.append(CheckResult("node", False, ".nvmrc is missing or unreadable"))
        elif version[0] != expected_major:
            results.append(
                CheckResult(
                    "node",
                    False,
                    (
                        f"node -> {version[0]}.{version[1]}.{version[2]}; "
                        f"expected Node {expected_major} from .nvmrc"
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    "node",
                    True,
                    f"node -> {version[0]}.{version[1]}.{version[2]} matches .nvmrc",
                )
            )

    npm = shutil.which("npm")
    if npm is None:
        results.append(CheckResult("npm", False, "npm is not on PATH"))
    else:
        result = _run_command([npm, "-v"])
        if result.returncode != 0:
            results.append(CheckResult("npm", False, "unable to inspect npm version"))
        else:
            results.append(CheckResult("npm", True, f"npm -> {result.stdout.strip()}"))
    return results


def _check_required_files(repo_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    for relative_path in REQUIRED_FILES:
        path = repo_root / relative_path
        results.append(
            CheckResult(
                relative_path,
                path.exists(),
                "present" if path.exists() else "missing",
            )
        )
    frontend_package = repo_root / "frontend/package.json"
    if frontend_package.exists():
        package_lock = repo_root / "frontend/package-lock.json"
        results.append(
            CheckResult(
                "frontend/package-lock.json",
                package_lock.exists(),
                "present" if package_lock.exists() else "missing",
            )
        )
    return results


def _print_results(results: list[CheckResult]) -> None:
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"{status}: {result.name} - {result.detail}")


def _print_guidance() -> None:
    print("")
    print("Suggested local setup:")
    print('  python3.11 -m pip install -e ".[dev]"')
    print('  python3.11 -m pip install -e ".[api,dev]"')
    print("  cd frontend && npm ci")
    print("  make doctor")
    print("  make lint")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the local developer toolchain and repo governance files.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run strict deterministic checks without additional guidance output.",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    results = [_check_python_baseline(), *_check_node_toolchain(repo_root), *_check_required_files(repo_root)]
    _print_results(results)
    if not args.check:
        _print_guidance()
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
