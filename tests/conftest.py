from __future__ import annotations

import pytest

from tests.helpers.reference_model import reduce_events
from tests.helpers.repo_paths import REPO_ROOT
from tests.helpers.scenario_catalog import SCENARIO_CATALOG
from tests.helpers.trace_loader import load_trace


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope="session")
def scenario_catalog():
    return SCENARIO_CATALOG


@pytest.fixture()
def trace_loader():
    return load_trace


@pytest.fixture()
def reducer():
    return reduce_events
