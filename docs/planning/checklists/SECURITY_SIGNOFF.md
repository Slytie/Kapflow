# SECURITY_SIGNOFF.md - Security gate checklist (Stage 4)

## Tenant + domain isolation
- [ ] APIs enforce tenant and domain scope
- [ ] background consumers enforce tenant and domain scope
- [ ] derived stores and generated outputs enforce tenant and domain scope

## One-truth safety
- [ ] no peer authored workflow-definition system exists beside the repo workflow packs
- [ ] projections used for approval are coherence-checked
- [ ] transcripts are treated as evidence, not state

## Automation safety
- [ ] no side-effecting tool execution without policy / budget / approval controls
- [ ] out-of-plan execution path is deny-by-default
- [ ] capability expansion remains governed and deferred where tooling is absent

## Secrets
- [ ] no secrets in repo
- [ ] CI uses short-lived credentials or equivalent controls
