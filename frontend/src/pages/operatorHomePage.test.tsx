import { HttpResponse, http } from "msw";
import { render, screen, within } from "@testing-library/react";

import { App } from "@/app/App";
import { server } from "@/test/api/server";

describe("OperatorHomePage", () => {
  it("loads at the app root in shared_env and surfaces failure-state findings", async () => {
    server.use(
      http.get("*/api/v1/viewer", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.viewer.bootstrap",
          viewer_session: {
            tenant_id: "tenant-a",
            domain_id: "domain-x",
            actor_id: "service:shared-gateway",
            actor_type: "service",
            actor_roles: ["dispatch_supervisor"],
            boundary_profile: "shared_env",
            request_context_mode: "server_derived",
            actor_switching_allowed: false
          }
        })
      ),
      http.get("*/api/v1/operator/home", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.operator.home",
          operator_home: {
            schema_version: "operator_home.v1",
            status: "attention",
            viewer: {
              tenant_id: "tenant-a",
              domain_id: "domain-x",
              actor_id: "service:shared-gateway",
              actor_type: "service",
              actor_roles: ["dispatch_supervisor"],
              boundary_profile: "shared_env",
              request_context_mode: "server_derived",
              actor_switching_allowed: false
            },
            failure_state: {
              schema_version: "logistics_reconciler_dry_run.v1",
              mode: "dry_run",
              summary: {
                finding_count: 4,
                error_count: 3,
                warning_count: 1,
                info_count: 0,
                mutations_performed: 0,
                code_counts: {
                  artifact_blob_missing: 1,
                  late_reporting_input_conflict: 1,
                  stale_edge_execution: 1,
                  weekly_daily_seed_missing: 1
                }
              },
              findings: [
                {
                  finding_id: "lrd-seed",
                  code: "weekly_daily_seed_missing",
                  severity: "error",
                  subject: {
                    workflow_run_id: "wr-weekly-001",
                    partition_key: "PW-2026-W10"
                  },
                  expected: {},
                  observed: {},
                  message: "published weekly schedule is missing a daily dispatch seed artifact",
                  mode: "dry_run",
                  mutates: false,
                  repair_hint: "Future apply mode must materialize the missing seed once."
                },
                {
                  finding_id: "lrd-blob",
                  code: "artifact_blob_missing",
                  severity: "error",
                  subject: { artifact_version_id: "av-seed-001" },
                  expected: {},
                  observed: {},
                  message: "file-backed artifact row points at a missing blob",
                  mode: "dry_run",
                  mutates: false,
                  repair_hint: "Restore the blob from backup."
                },
                {
                  finding_id: "lrd-late",
                  code: "late_reporting_input_conflict",
                  severity: "error",
                  subject: { workflow_run_id: "wr-reporting-002" },
                  expected: {},
                  observed: {},
                  message: "reporting final packet would collide with an existing planning actual-hours input",
                  mode: "dry_run",
                  mutates: false,
                  repair_hint: "Safe/default profile leaves late reporting blocked.",
                  conflict_code: "late_reporting_handoff_conflict",
                  boundary_profile: "shared_env"
                },
                {
                  finding_id: "lrd-stale",
                  code: "stale_edge_execution",
                  severity: "warning",
                  subject: { edge_execution_id: "ee-stale-001" },
                  expected: {},
                  observed: {},
                  message: "handoff edge execution is marked stale",
                  mode: "dry_run",
                  mutates: false,
                  repair_hint: "Dry-run reports stale edges only."
                }
              ]
            }
          }
        })
      )
    );

    window.history.pushState({}, "", "/");
    render(<App />);

    const page = await screen.findByTestId("operator-home-page");
    expect(window.location.pathname).toBe("/");
    expect(within(page).getByRole("heading", { name: "Current runtime posture" })).toBeInTheDocument();
    expect(within(page).getByText("Attention")).toBeInTheDocument();
    expect(within(page).getByText("Missing seed: 1")).toBeInTheDocument();
    expect(within(page).getByText("Missing blob: 1")).toBeInTheDocument();
    expect(within(page).getByText("Late report: 1")).toBeInTheDocument();
    expect(within(page).getByText("Stale edge: 1")).toBeInTheDocument();
    expect(within(page).getByText("Dry-run mutations")).toBeInTheDocument();
    expect(within(page).getAllByText("0").length).toBeGreaterThan(0);
    expect(screen.getByTestId("viewer-session-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("actor-switcher")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Open actor switcher/i)).not.toBeInTheDocument();
  });
});
