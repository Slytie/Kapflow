from __future__ import annotations

from .runtime_cli import REPO_ROOT


SUPPORTED_REPORTING_WORKBOOK_PATH = (
    REPO_ROOT
    / "fixtures/workflows/dispatch_reporting/template_pack/Stage03_Threshold_Detection_and_Draft_Packet/Stage03_Threshold_Detection_and_Draft_Packet_upd_draft_Spreadsheet_Example_COMPLETED.xlsx"
)
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def reporting_workbook_upload_metadata(service_date: str) -> dict[str, object]:
    return {
        "service_date": service_date,
        "station_code": "DVC4",
        "dsp_name": "QDCI",
    }
