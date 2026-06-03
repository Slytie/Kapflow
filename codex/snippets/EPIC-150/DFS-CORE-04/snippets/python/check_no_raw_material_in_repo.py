"""Illustrative repo/CI guard against raw project material."""

from __future__ import annotations

from pathlib import Path
import sys


FORBIDDEN_PATH_PARTS = {
    "capex-local-sources",
    "capex-quarantine",
    "capex-custody-dev",
    "capex-generated-packs-unreviewed",
    "desktop-sync-sentinel",
}
FORBIDDEN_EXTENSIONS = {".capexraw", ".rawproject"}


def main() -> int:
    errors = []
    for path in Path(".").rglob("*"):
        if set(path.parts) & FORBIDDEN_PATH_PARTS:
            errors.append(str(path))
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
            errors.append(str(path))
    if errors:
        print("RAW_PROJECT_MATERIAL_IN_REPO_CHECK_FAILED")
        for e in errors[:200]:
            print(f" - {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
