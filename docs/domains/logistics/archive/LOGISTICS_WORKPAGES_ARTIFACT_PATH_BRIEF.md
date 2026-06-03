> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# Logistics workpages artifact path - product brief

## Purpose
This brief freezes the next product step after the query-backed workpage tranche. The goal is to prove, with one bounded vertical slice, that a workpage can be connected to a real spreadsheet artifact version and save back into a **new immutable artifact version** without breaking the repo's one-truth model.

## What this epic is
The next epic is the **first artifact-backed workpage slice**.

The first slice is intentionally narrow:
- **workflow family:** `dispatch_reporting.v1`
- **artifact family:** `reporting.upd_draft.workbook`
- **page:** end-of-day draft/review workpage
- **surface:** logistics demo shell first

## Why EOD first
The original workpage goals were always artifact-first:
- the page should be easier to use than the spreadsheet,
- the spreadsheet artifact should remain downloadable,
- and every meaningful save should become a new immutable artifact version.

EOD is the right first slice because:
- it already behaves like a guided form + review surface,
- it maps more naturally to a single reporting workbook family,
- and it avoids forcing the schedule page into a premature single-artifact identity while schedule is still composite.

## What the operator should be able to do
From the logistics demo shell, the operator should be able to:
1. open the query-backed EOD page,
2. create an editable EOD workbook draft,
3. land on an artifact-backed EOD workpage tied to a concrete `artifact_version_id`,
4. edit route-review and closeout fields in a guided UI,
5. explicitly save/submit to create a **new workbook artifact version**,
6. download that new workbook artifact,
7. inspect recent version lineage from the page.

## What remains out of scope
- no schedule artifact-backed write path in this epic
- no generic workpage builder
- no final-packet/approval/pointer promotion path yet
- no workbook-clone UI
- no per-keystroke autosave into `artifact_versions`
- no requirement that this first slice already plugs into a dispatch-reporting human-task/workspace lane

## Product boundary
The workpage remains a **derived editing surface**. The workbook artifact version remains canonical truth.

\[
A_v \xrightarrow{\text{project}} UI \xrightarrow{\text{submit}} A_{v+1}
\]

The product promise is not “edit the spreadsheet directly in a browser.”
The product promise is “edit the operational content through a better page, while preserving authoritative workbook artifacts.”

## User-visible route posture
Keep the artifact-backed slice inside the existing logistics shell.
Recommended posture:
- keep `/demo/logistics/workpages/eod-v0` as the query-backed landing page,
- add an artifact-backed sibling route such as `/demo/logistics/workpages/eod-v0/artifacts/:artifactVersionId`.

This keeps the first write path visually close to the validated page while making the artifact identity explicit.
