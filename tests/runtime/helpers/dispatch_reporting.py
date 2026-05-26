from __future__ import annotations

from .runtime_cli import REPO_ROOT


SUPPORTED_REPORTING_WORKBOOK_PATH = (
    REPO_ROOT
    / "fixtures/workflows/dispatch_reporting/template_pack/Stage01_EOS_Intake/Stage01_EOS_Intake_eos_raw_Spreadsheet_Example_COMPLETED.xlsx"
)
REAL_ZIP_WEEK_ROOT = (
    REPO_ROOT
    / "fixtures/workflows/dispatch_reporting/actual_zip_week_2026_03_15"
)
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
REALISTIC_REPORTING_SERVICE_DATE = "2026-03-24"
REAL_ZIP_WEEK_SERVICE_DATES: tuple[str, ...] = (
    "2026-03-15",
    "2026-03-16",
    "2026-03-17",
    "2026-03-18",
    "2026-03-19",
    "2026-03-20",
    "2026-03-21",
)
REAL_ZIP_WEEK_EXPECTED_DAY_TOTALS: dict[str, tuple[int, int]] = {
    "2026-03-15": (16, 9144),
    "2026-03-16": (22, 11467),
    "2026-03-17": (20, 11050),
    "2026-03-18": (19, 10657),
    "2026-03-19": (20, 11422),
    "2026-03-20": (18, 10793),
    "2026-03-21": (17, 10238),
}
REAL_ZIP_WEEK_SAMPLE_ROW = {
    "service_date": "2026-03-16",
    "driver_id": "A1NQEGRS26IBJA",
    "driver_name": "Suraj Pratap Singh",
    "route_id": "CX93",
    "actual_minutes": 540,
}


def reporting_workbook_upload_metadata(service_date: str) -> dict[str, object]:
    return {
        "service_date": service_date,
        "station_code": "DVC4",
        "dsp_name": "QDCI",
    }


def real_zip_week_workbook_path(service_date: str):
    return REAL_ZIP_WEEK_ROOT / f"{service_date}.xlsx"
