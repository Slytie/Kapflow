# Stuck workflow or task

## Symptoms
- task lease expired repeatedly
- execution session hit no-progress threshold
- approval waiting beyond SLA
- workflow run state unchanged beyond expected bound

## Checks
1. inspect latest `workflow.run.state_changed` and `task.run.state_changed`
2. inspect linked human task and approval objects
3. inspect linked execution session and tool events
4. determine whether the block is:
   - missing approval
   - stale inputs
   - no progress in execution
   - scope or policy denial
   - downstream degradation

## Recovery principles
- create or escalate a human task rather than silently extending hidden loops
- preserve evidence; do not rewrite history
- if rerun is needed, create a new run or task run with explicit lineage
