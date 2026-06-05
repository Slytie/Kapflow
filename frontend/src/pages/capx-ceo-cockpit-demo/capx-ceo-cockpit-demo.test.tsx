import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { resetCapxCeoCockpitAcknowledgementForTest } from "./CapxCeoCockpitAccessGate";

const ACKNOWLEDGEMENT_KEY = "capx-ceo-cockpit-demo-acknowledged";

async function renderUnlockedCapxRoute(route: string) {
  const user = userEvent.setup();
  window.sessionStorage.setItem(ACKNOWLEDGEMENT_KEY, "true");
  window.history.pushState({}, "", route);
  const rendered = render(<App />);
  return { user, rendered };
}

describe("CAPX CEO Cockpit demo", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    resetCapxCeoCockpitAcknowledgementForTest();
    window.history.pushState({}, "", "/");
  });

  it("shows a local acknowledgement gate before opening the demo", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/capx/ceo-cockpit");
    render(<App />);

    const gate = screen.getByTestId("capx-access-gate");
    expect(within(gate).getByRole("heading", { name: "CAPX CEO Cockpit" })).toBeInTheDocument();
    expect(within(gate).getByText(/local design-review speed bump/i)).toBeInTheDocument();
    expect(within(gate).getByText(/does not protect bundled javascript/i)).toBeInTheDocument();

    await user.click(within(gate).getByRole("button", { name: /acknowledge and open demo/i }));

    expect(await screen.findByTestId("capx-overview-page")).toBeInTheDocument();
  });

  it("renders the overview route with action lanes, risk metrics, and required project columns", async () => {
    await renderUnlockedCapxRoute("/demo/capx/ceo-cockpit");

    expect(await screen.findByTestId("capx-overview-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "CEO Actions" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Portfolio Risk" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Project" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "PM status" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "AI status" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Status" })).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Opportunity cost per week" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Evidence freshness" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Board impact" })).toBeInTheDocument();
    expect(screen.getAllByLabelText(/PM status:/i).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/AI status:/i).length).toBeGreaterThan(0);
  });

  it("links overview project rows to the project drill-down route", async () => {
    const { rendered } = await renderUnlockedCapxRoute("/demo/capx/ceo-cockpit");
    expect(await screen.findByTestId("capx-overview-page")).toBeInTheDocument();

    const projectLink = rendered.container.querySelector(
      'a[href="/demo/capx/ceo-cockpit/projects/P-104"]'
    );
    expect(projectLink).toBeInTheDocument();
  });

  it("renders the known project drill-down evidence brief", async () => {
    await renderUnlockedCapxRoute("/demo/capx/ceo-cockpit/projects/P-104");

    expect(await screen.findByTestId("capx-project-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /P-104 Orion Facility/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Why this status?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "CEO Next Action" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Stage & Milestones" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Current Flags & Triggers" })).toBeInTheDocument();
  });

  it("lets the CEO save a session-local project comment", async () => {
    const { user } = await renderUnlockedCapxRoute("/demo/capx/ceo-cockpit/projects/P-104");

    await user.type(screen.getByLabelText("CEO comment"), "Press supplier recovery by Friday.");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(screen.getByLabelText("Saved CEO comment")).toHaveTextContent(
      "Press supplier recovery by Friday."
    );
    expect(screen.getByLabelText("CEO comment")).toHaveValue("");
    expect(screen.getByText(/not canonical project truth/i)).toBeInTheDocument();
  });

  it("renders a bounded not-found state for unknown project IDs", async () => {
    await renderUnlockedCapxRoute("/demo/capx/ceo-cockpit/projects/P-999");

    const notFound = await screen.findByTestId("capx-project-not-found");
    expect(within(notFound).getByRole("heading", { name: "Project not found" })).toBeInTheDocument();
    expect(within(notFound).getByRole("link", { name: "Back to cockpit" })).toHaveAttribute(
      "href",
      "/demo/capx/ceo-cockpit"
    );
  });

  it("uses filled status chips without visible color-name labels", async () => {
    const { rendered } = await renderUnlockedCapxRoute("/demo/capx/ceo-cockpit");

    const chips = Array.from(rendered.container.querySelectorAll("[data-status-chip]"));
    expect(chips.length).toBeGreaterThan(0);
    expect(screen.queryByText(/\b(red|yellow|green|amber)\b/i)).not.toBeInTheDocument();
    for (const chip of chips) {
      expect(chip.textContent).not.toMatch(/\b(red|yellow|green|amber)\b/i);
      expect(chip).toHaveAttribute("aria-label");
    }
  });
});
