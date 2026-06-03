# Desktop Sync Activation Gate

Activation is allowed only if:

```text
PM explicitly selected the source root
source root is not inside repo, build output, CI workspace, or artifact folder
local raw path grant exists only in protected local agent state
source-root capability allows only read/stat/lstat/watch
source-root capability denies write/remove/rename/truncate
shell/upload/opener reveal are disabled for raw source roots
structured logging is enabled and arbitrary frontend logging is disabled
quarantine store is configured under app-controlled directory
redaction gate is active
leak sentinel scan passes
```

Activation must fail with `DESKTOP_SYNC_ACTIVATION_BLOCKED` if any condition fails.
