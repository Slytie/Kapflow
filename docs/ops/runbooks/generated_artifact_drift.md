# Generated artifact drift

## Trigger
- CI or operator notices that a runbook pack, tool matrix, approval packet, or generated CompanyOS IR no longer matches repo-native source hashes

## Checks
1. identify the authoritative source files involved
2. compare recorded source hashes to current content
3. determine whether:
   - source changed and regeneration was skipped
   - generator version changed
   - someone hand-edited a generated artifact

## Remediation
- regenerate from authoritative source
- record generator version and source lineage
- if semantics changed, update source docs and task / decision logs before regeneration

## Anti-pattern
Do not "fix the generated file" as the main repair if the underlying source is wrong or outdated.
