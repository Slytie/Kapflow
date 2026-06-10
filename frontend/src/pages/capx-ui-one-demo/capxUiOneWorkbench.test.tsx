import { fireEvent, render, screen, within } from "@testing-library/react";

import { App } from "@/app/App";
import { capxUiOnePhases, capxUiOneReports, capxUiOneTasks } from "./capxUiOneData";

describe("CAPX UI-One K12 workbench", () => {
  it("mounts an isolated UI-One shell with K12 project navigation", () => {
    window.history.pushState({}, "", "/demo/capx/ui-one/home");

    const { container } = render(<App />);

    expect(screen.getByTestId("capx-ui-one-workbench")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /UI-One CAPEX Workbench/i })).toHaveAttribute(
      "href",
      "/demo/capx/ui-one/home"
    );
    expect(screen.getByRole("heading", { name: "What needs attention today?" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "UI-One navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Work Queue" })).toHaveAttribute("href", "/demo/capx/ui-one/queue");
    expect(screen.getByRole("link", { name: "State Snapshot" })).toHaveAttribute(
      "href",
      "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/overview"
    );
    expect(screen.getByRole("link", { name: "Evidence Library" })).toHaveAttribute(
      "href",
      "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/evidence"
    );
    expect(screen.getByLabelText("Project context")).toHaveTextContent("K12 Packaging Line Upgrade");
    expect(screen.getByLabelText("Project context")).toHaveTextContent("capex.project_state_snapshot.v1:k12:001");
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("renders the K12 snapshot basis, blockers, next actions, and workpage projections", () => {
    window.history.pushState({}, "", "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/overview");

    render(<App />);

    expect(screen.getByRole("heading", { name: "Governed current state" })).toBeInTheDocument();
    expect(screen.getAllByText("Basic Engineering / Procurement Readiness").length).toBeGreaterThan(0);
    expect(screen.getAllByText("capex.project_state_snapshot.v1:k12:001").length).toBeGreaterThan(0);
    expect(screen.getByText("Compressed-air interface missing current site measurement")).toBeInTheDocument();
    expect(screen.getByText("Request current compressed-air measurement from utilities owner")).toBeInTheDocument();
    expect(screen.getByText("Owner Interface Resolution")).toBeInTheDocument();
    expect(screen.getByText("Rendered workpages are projections, not source of truth")).toBeInTheDocument();
  });

  it("renders the ten-stage lifecycle and guarded K12 phase workspace", () => {
    window.history.pushState({}, "", "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/phases/procurement");

    render(<App />);

    expect(screen.getByRole("heading", { name: "Procurement" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Ten stage lifecycle context" })).getAllByRole("link")).toHaveLength(
      capxUiOnePhases.length
    );
    expect(screen.getByText("Inputs panel")).toBeInTheDocument();
    expect(screen.getByText("AI processing panel")).toBeInTheDocument();
    expect(screen.getByText("Draft output panel")).toBeInTheDocument();
    expect(screen.getByText("Review and decision panel")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Publish AI output" }));

    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("Blocked receipt");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("publish_ai_output_directly");
    expect(screen.getByLabelText("Policy Check Panel")).toHaveTextContent("human approves the exact version");

    fireEvent.click(screen.getByRole("button", { name: "Submit for human review" }));

    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("Accepted receipt");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("submit_for_human_review");
  });

  it("opens an evidence drawer with extraction, review, and provenance state", () => {
    window.history.pushState({}, "", "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/evidence");

    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Open evidence drawer for Current Compressed-Air Measurement" }));

    const drawer = screen.getByLabelText("Evidence policy decision and audit drawer");
    expect(within(drawer).getByText("Evidence drawer")).toBeInTheDocument();
    expect(within(drawer).getByText("ev-004")).toBeInTheDocument();
    expect(within(drawer).getByText("Required current site measurement")).toBeInTheDocument();
    expect(within(drawer).getAllByText("not_available").length).toBeGreaterThan(0);
    expect(within(drawer).getByText("Current pressure measurement is required.")).toBeInTheDocument();
  });

  it("keeps task-close commands evidence-bound with the K12 blocked receipt", () => {
    window.history.pushState({}, "", "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/tasks");

    render(<App />);

    expect(screen.getByRole("heading", { name: "Project-scoped review and pointer promotion queue" })).toBeInTheDocument();
    expect(within(screen.getByRole("table", { name: "Role scoped work queue" })).getAllByRole("link")).toHaveLength(
      capxUiOneTasks.length
    );

    fireEvent.click(screen.getByRole("button", { name: "Close without evidence" }));

    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("Blocked receipt");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("close_task_with_evidence");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent(
      /current compressed-air measurement is missing/i
    );
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent(
      /stale 2022 drawing is insufficient/i
    );

    fireEvent.click(screen.getByRole("button", { name: "Request measurement evidence" }));

    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("Accepted receipt");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("request_current_measurement");
  });

  it("shows K12 report basis, draft-only status, and blocked publication", () => {
    window.history.pushState({}, "", "/demo/capx/ui-one/projects/k12-packaging-line-upgrade/reports");

    render(<App />);

    expect(screen.getByRole("heading", { name: "Generate reports from governed snapshots" })).toBeInTheDocument();
    const reportBuilder = screen.getByRole("region", { name: "Report builder" });
    for (const report of capxUiOneReports) {
      expect(within(reportBuilder).getAllByText(report.snapshotId).length).toBeGreaterThan(0);
      expect(within(reportBuilder).getByText(report.warning)).toBeInTheDocument();
    }
    expect(within(reportBuilder).getByText("K12 Management Snapshot")).toBeInTheDocument();
    expect(within(reportBuilder).getByText("Generated draft")).toBeInTheDocument();
    expect(within(reportBuilder).getAllByText("Not official").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Publish report as official" }));
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("Blocked receipt");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("publish_management_report");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent(
      "Report generated does not mean published"
    );

    fireEvent.click(screen.getByRole("button", { name: "Generate report draft" }));
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent("Accepted receipt");
    expect(screen.getByRole("status", { name: "Command receipt" })).toHaveTextContent(
      "generate_management_report_draft"
    );
  });

  it("links the UI-One build from the existing CAPX UI comparison page", () => {
    window.history.pushState({}, "", "/demo/capx/ui-versions");

    render(<App />);

    expect(screen.getByRole("link", { name: "UI-One OPML build" })).toHaveAttribute(
      "href",
      "/demo/capx/ui-one/home"
    );
  });
});
