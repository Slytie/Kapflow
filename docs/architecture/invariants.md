# Platform invariants (non-negotiable)

These are treated as formal requirements for the platform and for Stage 4.

## I1. Durable workflow semantics + safe evolution/versioning
- Workflow runs are long-lived state machines.
- Runs are pinned to workflow definition version/hash and exact input versions.
- No in-flight migrations in MVP: new logic produces new runs.
- Historical pinned execution meaning must not drift under future generator or compiler changes.

## I2. Artifact immutability + auditability
- Artifacts are immutable versions; edits produce new versions.
- Official inputs/outputs are defined by promotion pointers or explicit official delta artifacts.
- The system must always record which exact artifact versions were used and produced.

## I3. Correct tenant isolation + authorization
- Tenant is the top boundary.
- Domain is a hard partition within tenant.
- All reads, writes, background consumers, projections, and generated outputs must enforce tenant+domain scope.

## I4. Automation safety for LLM/tool execution
- Progressive automation exists, but execute requires policy + approval + budget + scope checks.
- Treat tool and LLM outputs as untrusted input until promoted or approved.
- Execution must be sandboxed with strict resource limits and default-deny egress.

## I5. One truth system
- Business execution and agentic execution share one timeline envelope and one authority chain.
- Generated runbooks, CompanyOS IR, dashboards, and transcripts must never become peer truth stores.
- Approval-critical projections must preserve canonical governance fields and drill down to evidence.

## MVP trust level
Stage 4 targets complete timeline + strong linking. Full deterministic replay and general method-patch governance remain future work.
