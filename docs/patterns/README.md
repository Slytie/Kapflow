# Architecture Pattern Library

This folder contains **external architecture pattern notes** reformatted for Codex-friendly development.

The library exists to help with:
- durable orchestration patterns,
- human-task and queueing semantics,
- automation / sandbox posture,
- ops-console ideas,
- scheduler / partition / replay lessons.

It does **not** define platform truth.

## How to use this library

- **Default rule:** read **pattern cards** first (`docs/patterns/cards/PATTERN-###.md`).
- Only open the full source notes under `docs/patterns/sources/converted/` if the current task is directly touching that subsystem.
- If a pattern informs a design choice, map it back to our own authoritative docs and invariants before editing source files.
- Pattern cards may inspire design, but they must never override:
  - `docs/architecture/AUTHORITY_MODEL.md`
  - workflow packs under `docs/workflows/*/v1/`
  - schemas under `schemas/`

## Why this exists

Fresh-session agents should not have to load long architecture essays on every task.

So we maintain:
- **Cards**: short, task-oriented, tagged.
- **Sources**: full extraction notes and original files.
- **Index**: `PATTERN_INDEX.yaml` so tasks and epics can reference pattern IDs deterministically.

## Adding a new pattern

1. Drop the raw notes into `docs/patterns/sources/original/`.
2. Convert them to Markdown under `docs/patterns/sources/converted/` (or write a short extracted-text note if conversion is lossy).
3. Write a new card with:
   - when to consult,
   - patterns to borrow,
   - pitfalls / what not to copy,
   - mapping back to our invariants.
4. Add the card to `PATTERN_INDEX.yaml`.
5. If the pattern changes a design decision, record that decision in an ADR and update the relevant authoritative docs.
