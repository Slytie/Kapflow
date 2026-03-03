# Degraded mode

Degraded mode in this repo means some non-authoritative or downstream surfaces are impaired while the truth substrate still records correctly.

## What may degrade
- export sinks
- search / index pipelines
- derived dashboards
- projection caches
- generated packet delivery
- secondary observability enrichments

## What may not silently degrade
- timeline event persistence
- artifact version persistence
- pointer updates
- approval persistence
- scope enforcement

## Operator rule
If a derived surface is degraded:
- emit `audit.degraded_mode.changed`
- keep recording authoritative events
- make the degraded state visible and alertable
- provide rebuild or catch-up steps in runbooks

## Stage 4 minimum signals
Track at least:
- outbox backlog age / size
- projection render failures
- coherence failures
- event persistence health
- generated-artifact freshness failures
