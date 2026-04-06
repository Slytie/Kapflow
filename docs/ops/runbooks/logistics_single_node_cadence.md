# Logistics Single-Node Cadence

This runbook layers on top of:
- [docs/ops/production_lab_topology.md](../production_lab_topology.md)
- [docs/ops/runbooks/rollback_and_deploy.md](./rollback_and_deploy.md)
- [docs/ops/runbooks/backup_and_restore.md](./backup_and_restore.md)

## Goal
- Run the first continuous logistics operator lane from an external scheduler.
- Keep cadence orchestration outside the runtime kernel.
- Limit the tick to due run/task creation plus live-dispatch day preparation after weekly publish truth exists.

The cadence entrypoint is:

```bash
onetruthctl cadence tick-logistics
```

For deterministic replay or manual smoke checks, override the date explicitly:

```bash
onetruthctl cadence tick-logistics --service-date-id SD-2026-03-06
```

The command is orchestration-only. It does not upload operator inputs, run Stage04, complete reviews, or approve anything.

## Supported Single-Node Recipe
1. Deploy from `release_source_bundle` only.
2. Use Python `3.11` for the backend install path:
   `python3.11 -m pip install -e ".[api]"`
3. Use Node `20` for the frontend build path:
   `cd frontend && npm ci && npm run build`
4. Run `onetruth-api` with the shared environment posture:
   `ONETRUTH_API_BOUNDARY_PROFILE=shared_env`
5. Set environment-specific runtime state:
   - `ONETRUTH_DB_URL`
   - `ONETRUTH_ARTIFACT_ROOT`
   - shared-env JWT settings

This runbook assumes the first-user logistics lane and does not introduce a multi-tenant scheduler surface.

## External Invocation
Cron example:

```cron
*/15 * * * * cd /srv/onetruth/current && ONETRUTH_DB_URL=sqlite:////srv/onetruth/state/prod.db /srv/onetruth/current/.venv/bin/onetruthctl cadence tick-logistics >> /var/log/onetruth/logistics-cadence.log 2>&1
```

`systemd` service example:

```ini
[Unit]
Description=CompanyOS logistics cadence tick

[Service]
Type=oneshot
WorkingDirectory=/srv/onetruth/current
Environment=ONETRUTH_DB_URL=sqlite:////srv/onetruth/state/prod.db
Environment=ONETRUTH_ARTIFACT_ROOT=/srv/onetruth/state/artifacts
ExecStart=/srv/onetruth/current/.venv/bin/onetruthctl cadence tick-logistics
```

`systemd` timer example:

```ini
[Unit]
Description=Run CompanyOS logistics cadence every 15 minutes

[Timer]
OnCalendar=*:0/15
Persistent=true

[Install]
WantedBy=timers.target
```

Kubernetes `CronJob` example:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: onetruth-logistics-cadence
spec:
  schedule: "*/15 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: cadence
              image: companyos-release:current
              command: ["onetruthctl", "cadence", "tick-logistics"]
              env:
                - name: ONETRUTH_DB_URL
                  value: sqlite:////srv/onetruth/state/prod.db
                - name: ONETRUTH_ARTIFACT_ROOT
                  value: /srv/onetruth/state/artifacts
```

## Expected Tick Behavior
- Friday tick: create or confirm the weekly `weekly_schedule_planning.v1` run and its `Stage04/weekly_input_intake` task for the planning week.
- Every tick: create or confirm the daily `dispatch_reporting.v1` run and its `Stage01/eos_input_intake` task for the service date.
- Live-dispatch gate: if `official:planning.published_weekly_schedule.workbook` already exists for that planning week, the next tick prepares the `live_dispatch.v1` service day and returns the `dispatch_seed_intake` task.
- If weekly publish truth does not exist yet, `live_dispatch` stays skipped with `waiting_on_weekly_publish`.

## Operator Smoke Checklist
1. Run `onetruthctl cadence tick-logistics --service-date-id SD-2026-03-06` on a Friday and confirm weekly + reporting state is created or returned as existing.
2. Confirm manual weekly publish happens through the normal workflow/task/approval path; do not bypass it with the cadence command.
3. Re-run `onetruthctl cadence tick-logistics --service-date-id SD-2026-03-06` and confirm the live-dispatch day is prepared.
4. Confirm the reporting intake task remains human-owned and open until an operator uploads EOS input.
5. Confirm repeated cadence runs do not duplicate workflow runs, human tasks, edge executions, or live seed artifacts.
