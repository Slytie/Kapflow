# Dispatch Reporting v1 - operating model

## Why this workflow exists
The EOS workbook is not just an archive; it is a working operational closeout tool.
It contains:
- route-level planned vs actual timing,
- packages dispatched / delivered / returned,
- return reasons,
- rescue and note fields,
- route adherence checks,
- break tracking,
- `> 600 MIN` / UPD-like sections.

That means there is a distinct reporting-closeout workflow after dispatch.

## Truth model
The source workbook may contain broken summary formulas.
Therefore:
- row-level route actuals are primary truth,
- normalized summaries are derived truth,
- broken formulas must be surfaced as warnings, not silently trusted.

## Threshold model
Reporting thresholds such as `> 600 minutes` belong to the reporting / UPD domain.
They are adjacent to, but not identical to, scheduling WHC thresholds.

## Review boundary
The draft packet remains draft-only until manager confirmation.
Finalized output must link to:
- the raw EOS upload,
- the normalized actuals,
- the reviewed draft workbook,
- the review confirmation evidence.
