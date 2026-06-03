# Logging and Redaction Policy

Allowed log fields:

```text
project_id
source_root_id
occurrence_id
version_id
relative_path_hash
parent_path_hash
extension_hint
filename_display under policy
reason_code
operation
event_type
```

Forbidden log fields:

```text
raw absolute path
raw local basename unless policy allows it
raw unreviewed content
full AI prompt containing source text
filesystem exception string with raw path
watcher notify event containing raw path
script environment containing source/working/archive path
```

All filesystem errors must be converted to structured redacted errors before UI/log/telemetry.
