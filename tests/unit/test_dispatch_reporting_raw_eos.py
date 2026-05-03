from __future__ import annotations

from onetruth.application.services.dispatch_reporting_raw_eos import (
    project_raw_eos_workbook,
)
from tests.runtime.helpers.dispatch_reporting import SUPPORTED_REPORTING_WORKBOOK_PATH


def test_project_raw_eos_workbook_prefers_explicit_metadata_service_date() -> None:
    projection = project_raw_eos_workbook(
        SUPPORTED_REPORTING_WORKBOOK_PATH.read_bytes(),
        source_metadata_json={"service_date": "2026-03-25"},
        source_file_name="2026-03-24.xlsx",
        fallback_service_date="2026-03-23",
    )

    assert projection.service_date == "2026-03-25"
    assert {row["service_date"] for row in projection.route_rows} == {"2026-03-25"}
