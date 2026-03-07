# Workflow packs

Each workflow pack should contain the canonical authored workflow surface for Stage 4:

- `WORKFLOW_CONTRACT.yaml`
- `ARTIFACT_MAP.yaml`
- `ACCEPTANCE_CRITERIA.md`
- `OPERATING_MODEL.md`
- `DECISION_CATALOG.yaml`
- `EXECUTION_PROFILE.yaml`

Anything else - runbook packs, tool matrices, approval logs, generated CompanyOS IR - is downstream.

For cross-workflow composition metadata, authored family surfaces live in dedicated family folders such as:
- `docs/workflows/logistics_ops_family/v1/WORKFLOW_FAMILY.yaml`
- `docs/workflows/logistics_ops_family/v1/PARTITION_TRANSFORMS.yaml`
- `docs/workflows/logistics_ops_family/v1/METHOD_PACKAGES.yaml`
