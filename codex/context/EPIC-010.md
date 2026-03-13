# EPIC-010 Context Pack — API trust boundaries, scope enforcement, and principal resolution

**Purpose (why you might open this):**

- You are changing request-context resolution, scope/authz boundary assumptions, or how principals enter the HTTP/API surface.
- You need to separate local-dev affordances from shared-environment trust.

## Non-negotiable invariants to keep in mind
- Tenant/domain isolation is strict at every boundary, including derived read models and thin HTTP adapters.
- Asserted identity is not the same as attested identity; trusted headers are a local/CI affordance, not a shared-env default.
- Shared environments must fail closed rather than silently trusting ambient headers.
- Capability enforcement should consume canonical principal/scope data, not ad hoc request metadata.

## Current frozen posture after TASK-0078
- `shared_env` is the default API boundary profile and fails closed with `principal_resolver_unavailable` unless a non-header principal resolver is injected.
- Trusted `x-onetruth-*` headers are allowed only in `local_dev` and `ci_test`.
- Trusted-header CORS exists only in `local_dev`, and only for loopback browser origins.

## Contracts / schemas to treat as authoritative
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `schemas/policy/permissions.yaml`
- `schemas/policy/governance_vocabulary.yaml`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-008.md`

## Required test coverage (tests-as-spec)
- Negative tests proving cross-tenant and cross-domain API denial.
- Profile tests proving local-dev header trust does not leak into shared-env behavior.
- Capability tests proving request-context resolution feeds consistent principal/scope data to read and write paths.
- Primary profile-spec suite: `tests/runtime/api/test_request_context_profiles.py`.

## Typical failure modes (red-team prompts)
- “Could a malicious webpage hit localhost and inherit trusted headers plus permissive CORS?”
- “Does shared-env silently trust missing or malformed principal metadata?”
- “Are we turning routing hints into hard permissions without an explicit product decision?”
- “Do local-dev shortcuts leak into shared HTTP surfaces?”
