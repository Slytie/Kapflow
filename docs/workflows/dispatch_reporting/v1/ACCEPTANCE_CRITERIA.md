# ACCEPTANCE_CRITERIA.md - Dispatch Reporting v1

## Happy path
- [ ] EOS workbook ingestion creates raw-input artifacts for one `ServiceDateID`.
- [ ] Row-level route actuals are normalized into a safer canonical workbook.
- [ ] Reportable cases such as `> 600 minutes` are detected and surfaced in a draft packet.
- [ ] Manager confirmation is required before the final packet becomes official.

## Critical business cases
- [ ] Route adherence and break-tracker content are linked into the same reporting run.
- [ ] Formula-integrity problems such as `#REF!` or `#VALUE!` are visible and do not silently become truth.
- [ ] Finalized actual-hours output can feed later planning or live-dispatch eligibility.

## Negative cases
- [ ] Broken summary formulas do not block normalization when raw row data is present.
- [ ] Missing route rows or inconsistent totals are flagged.
- [ ] Draft reporting output does not become official until the review boundary is crossed.
