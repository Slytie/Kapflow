# Research Library

This folder contains research and reference material that informs the Stage 4 repo.

## Why this exists

Codex and other LLM agents often enter the repo fresh. These documents preserve background and rationale without requiring chat history.

Most research documents are too large to load into working context by default, so the intended pattern is:

1. Read `docs/research/AGENT_DIGEST.md` first.
2. Only open a full doc in `docs/research/full/` when you need deeper justification.
3. If the research changes what we will build, update the relevant authoritative docs and record the decision.

## Structure
- `docs/research/AGENT_DIGEST.md` — curated summaries and routing guidance.
- `docs/research/full/` — full converted Markdown source documents.
- `docs/patterns/` — architecture summaries reshaped into a Codex-friendly pattern library.

## Change control

Treat research docs as **reference**, not authority.

The authoritative "what we will build" lives in:
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
- `docs/planning/STAGE4_PLAN.md`
- workflow packs under `docs/workflows/*/v1/`
- schemas under `schemas/`
