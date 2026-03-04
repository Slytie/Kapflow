# Derivation and generation policy

This doc defines how source files, compiled artifacts, generated artifacts, evidence, and derived views relate.

## 1) Artifact classes

| Class | Examples | Edit policy | Authority |
|---|---|---|---|
| Authored source | workflow contract pack, decision catalog, execution profile, schemas | hand-edited in repo | authoritative |
| Compiled | per-run `ExecutionSpec`, source-hash manifest | produced by compiler from source + policy | authoritative once pinned |
| Generated | runbook DOCX, tool matrix XLSX, approval log XLSX, generated CompanyOS IR | never the first place to edit semantics | non-authoritative |
| Evidence | logs, transcripts, sandbox outputs, generated reports explicitly linked from events | created by execution | evidentiary |
| Derived | dashboards, approval packets, WorkGraph, operative schedule views | regenerated from substrate | non-authoritative |

## 2) Generated artifacts must carry lineage
Every generated or compiled artifact should carry at least:
- source file refs
- source content hashes
- generator / compiler version
- generation timestamp
- scope
- workflow ID + version

Without this, drift becomes hard to prove.

## 3) Manual edit rule
If a generated artifact needs a semantic change:
1. edit the authoritative source file(s)
2. regenerate the artifact
3. record the lineage
4. never treat the generated file as the canonical definition

## 4) Lowering to CompanyOS IR
CompanyOS artifacts are treated as a lowering target, not a peer authored source system.

Stage 4 lowering path:

`workflow pack + decision catalog + execution profile + policy profile`
-> generated CompanyOS IR
-> compiled `ExecutionSpec`

This means:
- CompanyOS `WorkflowSpec` is generated from repo-native source if needed
- CompanyOS `CascadeSpec` is generated from execution profile guidance if needed
- `ExecutionSpec` is compiled and pinned per run
- future ProcessPatch ideas remain backlog items until governance and capability diff tooling exist

## 5) What may change official business state
Only actions that write authoritative events, objects, or pointers through the platform may change official state.

Generated packets, dashboards, and transcripts may inform decisions but do not themselves become official state.

## 6) CI implications
Future CI should validate:
- source files conform to schemas
- overlay refines rather than expands the workflow contract
- generated artifacts are fresh relative to source hashes
- projection packets preserve canonical fields
- no stale references remain in planning docs

## 7) Prototype lineage manifest format (TASK-0032)
The first generator prototype writes lineage manifests to:
- `build/generated/lineage/<workflow_id>.lineage.json`

Minimum required fields:
- `workflow_id`
- `workflow_version`
- `generator_version`
- `generated_at`
- `sources[]` with `path` and `sha256`
- `outputs[]` with `path` and `sha256`

Freshness checks must fail when:
- source file hashes differ from lineage hashes,
- generated output bytes differ from lineage output hashes,
- generated runbook/IR no longer matches deterministic regeneration from authoritative source.
