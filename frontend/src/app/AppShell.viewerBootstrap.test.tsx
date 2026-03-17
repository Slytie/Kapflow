import { HttpResponse, http } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";

import { App } from "@/app/App";
import { server } from "@/test/api/server";

describe("AppShell viewer bootstrap", () => {
  it("uses shared-env viewer bootstrap and omits trusted headers after bootstrap", async () => {
    let workflowRunsHeaders:
      | {
          tenant: string | null;
          domain: string | null;
          actorId: string | null;
          actorType: string | null;
          actorRoles: string | null;
        }
      | null = null;

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
      http.get("*/api/v1/workflow-runs", ({ request }) => {
        workflowRunsHeaders = {
          tenant: request.headers.get("x-onetruth-tenant-id"),
          domain: request.headers.get("x-onetruth-domain-id"),
          actorId: request.headers.get("x-onetruth-actor-id"),
          actorType: request.headers.get("x-onetruth-actor-type"),
          actorRoles: request.headers.get("x-onetruth-actor-roles")
        };
        return HttpResponse.json({
          status: "ok",
          command: "api.workflow_runs.list",
          workflow_runs: [],
          page: { limit: 100, offset: 0 }
        });
      })
    );

    window.history.pushState({}, "", "/runs");
    render(<App />);

    const viewerPanel = await screen.findByTestId("viewer-session-panel");
    expect(within(viewerPanel).getByText("Viewer session")).toBeInTheDocument();
    expect(within(viewerPanel).getByText("service:shared-gateway")).toBeInTheDocument();
    expect(screen.queryByLabelText("Active user")).not.toBeInTheDocument();
    expect(await screen.findByText(/No runs in scope/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(workflowRunsHeaders).not.toBeNull();
    });
    expect(workflowRunsHeaders).toEqual({
      tenant: null,
      domain: null,
      actorId: null,
      actorType: null,
      actorRoles: null
    });
  });
});
