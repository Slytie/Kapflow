# Supplemental — CAPEX SourceRoot Agent Contract Sketch

## Principle

A desktop agent is an observer. It is not project truth.

```text
agent event / watcher event / scan result
  → observation
  → server reconciliation
  → source-root delta
  → PM review
```

## Agent profile

```json
{
  "agent_source_root_profile": {
    "source_root_id": "uuid",
    "project_id": "uuid",
    "local_path_hint_redacted": "~/Client/...",
    "local_journal_id": "opaque-local-id",
    "permission_status": "granted|permission_lost|unknown",
    "watcher_status": "reliable|degraded|lost_events|permission_denied|unavailable",
    "last_full_scan_at": "timestamp",
    "paused": false
  }
}
```

## Observation submission

```json
{
  "event_type": "AgentManifestSubmitted",
  "source_root_id": "uuid",
  "agent_id": "uuid",
  "observation_basis": "desktop_agent_full_scan",
  "path_scope": "full",
  "observed_at": "timestamp",
  "manifest_digest": "sha256:...",
  "entries": [
    {
      "relative_path": "Drawings/A101.pdf",
      "entry_type": "file",
      "size_bytes": 12345,
      "mtime": "timestamp",
      "digest": "sha256:...",
      "local_file_id_hint": "opaque-platform-id",
      "availability": "present",
      "stability_status": "stable"
    }
  ]
}
```

## Watcher health events

```json
{
  "event_type": "AgentWatcherLostChanges",
  "source_root_id": "uuid",
  "detected_at": "timestamp",
  "platform": "darwin|windows|linux",
  "reason": "event_overflow|root_changed|permission_denied|unknown",
  "required_next_action": "full_scan"
}
```

Server rule:

```text
if watcher lost events:
  source_root.status = watcher_degraded
  reject partial deltas as freshness-complete
  require full scan
  reviewed baseline unchanged
```

## Root/permission events

```json
{
  "event_type": "AgentRootUnavailable",
  "source_root_id": "uuid",
  "status": "root_missing|permission_lost",
  "detected_at": "timestamp"
}
```

Server rule:

```text
root missing / permission lost
  → source-root availability task
  → do not delete prior observations
  → do not mutate reviewed baseline
```

## Prohibited agent capabilities

The agent must not directly:

```text
create ReviewedCorpusBaseline
create OfficialEvidenceBinding
delete evidence because a local file disappeared
collapse occurrences by digest
mark AI proposal as PM-reviewed
expose absolute local paths to global logs/search/prompts
```
