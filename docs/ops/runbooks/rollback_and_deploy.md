# Rollback and deploy

## Before deploy
- validate source schemas
- validate generated-artifact freshness
- confirm no open authority-model migration without ADR / sign-off

## If rollback is required
1. stop new deploy traffic
2. preserve authoritative events and artifacts
3. do not rewrite or delete historical runs
4. rebuild derived views and generated caches against the rolled-back code if needed
5. record decision and impact in `DECISIONS_SINCE_LAST.md`

## Special caution
A rollback must not reinterpret historical pinned execution artifacts under a new meaning without an explicit compatibility decision.
