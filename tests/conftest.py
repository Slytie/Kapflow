from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tests.helpers.reference_model import reduce_events
from tests.helpers.repo_paths import REPO_ROOT as TEST_REPO_ROOT
from tests.helpers.scenario_catalog import SCENARIO_CATALOG
from tests.helpers.suite_markers import is_logistics_regression_test_path
from tests.helpers.trace_loader import load_trace


@pytest.fixture(scope="session")
def repo_root():
    return TEST_REPO_ROOT


@pytest.fixture(scope="session")
def scenario_catalog():
    return SCENARIO_CATALOG


@pytest.fixture()
def trace_loader():
    return load_trace


@pytest.fixture()
def reducer():
    return reduce_events


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    del config
    for item in items:
        item_raw_path = getattr(item, "path", None)
        if item_raw_path is None:
            item_raw_path = item.fspath
        item_path = Path(str(item_raw_path))
        if is_logistics_regression_test_path(item_path, repo_root=REPO_ROOT):
            item.add_marker(pytest.mark.logistics_regression)
