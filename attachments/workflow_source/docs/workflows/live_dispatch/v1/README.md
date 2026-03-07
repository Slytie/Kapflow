# Live Dispatch - Per-day exceptions and official replan deltas

This folder contains the target authored workflow surface for `live_dispatch.v1`.

Files:
- `WORKFLOW_CONTRACT.yaml` - stages, approvals, partition semantics, and event inventory
- `ARTIFACT_MAP.yaml` - dataset keys mapped to template files
- `ACCEPTANCE_CRITERIA.md` - tests-as-spec guidance
- `OPERATING_MODEL.md` - domain assumptions, first-principles formalism, and review model
- `DECISION_CATALOG.yaml` - canonical decision IDs and evidence requirements
- `EXECUTION_PROFILE.yaml` - canonical execution pattern and tool-class guidance
- `examples/` - human-readable normalized examples based on the real source artifacts provided

Alignment rules:
- Workflow packs remain canonical.
- Branching lives in code, not prompts.
- Deterministic logic owns hard constraints; bounded LLM help may draft summaries or packets.
- Official state changes only through canonical approvals and pointer promotion.
