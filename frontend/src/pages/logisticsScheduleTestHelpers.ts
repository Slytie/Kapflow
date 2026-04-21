import { within } from "@testing-library/react";

export function scheduleHeatmapSectionIn(container: HTMLElement): HTMLElement {
  const section = within(container)
    .getByRole("heading", { name: "Planned schedule heatmap" })
    .closest("section");
  if (!section) {
    throw new Error("Heatmap section not found");
  }
  return section as HTMLElement;
}

export function expectHeatmapHeaderStatusGroups(container: HTMLElement): {
  dependencyGroup: HTMLElement;
  checksGroup: HTMLElement;
} {
  const heatmap = scheduleHeatmapSectionIn(container);
  const header = heatmap.querySelector(".schedule-heatmap__header");
  expect(header).not.toBeNull();
  const heatmapHeader = header as HTMLElement;
  expect(container.querySelector(".schedule-workpage-surface__overview")).toBeNull();
  expect(container.querySelector("section.schedule-dependencies")).toBeNull();
  expect(container.querySelector("section.schedule-checks")).toBeNull();
  expect(within(heatmapHeader).getByText("Assigned route")).toBeInTheDocument();
  expect(within(heatmapHeader).getByText("On call")).toBeInTheDocument();
  expect(within(heatmapHeader).getByText("No planned work")).toBeInTheDocument();
  expect(within(heatmapHeader).getByText("Manual override")).toBeInTheDocument();

  const dependencyHeading = within(heatmapHeader).getByRole("heading", {
    level: 3,
    name: "Dependency status"
  });
  const checksHeading = within(heatmapHeader).getByRole("heading", { level: 3, name: "Checks" });
  const dependencyGroup = dependencyHeading.closest(".schedule-heatmap__header-group");
  const checksGroup = checksHeading.closest(".schedule-heatmap__header-group");
  expect(dependencyGroup).not.toBeNull();
  expect(checksGroup).not.toBeNull();
  expect(within(dependencyGroup as HTMLElement).getByText("Route Slot Requirements")).toBeInTheDocument();
  expect(
    within(checksGroup as HTMLElement).getByText("Routes within scheduled capacity")
  ).toBeInTheDocument();

  return {
    dependencyGroup: dependencyGroup as HTMLElement,
    checksGroup: checksGroup as HTMLElement
  };
}

export function expectSelectedDateHeaderStats(container: HTMLElement): void {
  const heatmap = scheduleHeatmapSectionIn(container);
  const selectedHeatmapDate = heatmap.querySelector(".schedule-heatmap__date-header--selected");
  expect(selectedHeatmapDate).not.toBeNull();
  const selectedHeader = selectedHeatmapDate as HTMLElement;
  expect(selectedHeader).toHaveTextContent("2026-03-24");
  expect(within(selectedHeader).getByText("Req")).toBeInTheDocument();
  expect(within(selectedHeader).getByText("20")).toBeInTheDocument();
  expect(within(selectedHeader).getByText("Sched")).toBeInTheDocument();
  expect(within(selectedHeader).getAllByText("23").length).toBeGreaterThan(0);
  expect(within(selectedHeader).getByText("OC")).toBeInTheDocument();
  expect(within(selectedHeader).getByText("4 / 4")).toBeInTheDocument();
  expect(within(selectedHeader).getByText("Avail")).toBeInTheDocument();
  expect(selectedHeader.textContent ?? "").toMatch(/Avail(\d+|—)/);
}

export function expectHeatmapPreferenceBars(container: HTMLElement): void {
  const heatmap = scheduleHeatmapSectionIn(container);
  const preferenceBars = heatmap.querySelectorAll(".schedule-heatmap__preference-bar");
  expect(preferenceBars.length).toBeGreaterThan(0);
  const firstPreferenceBar = preferenceBars[0] as HTMLElement;
  expect(firstPreferenceBar.getAttribute("aria-label")).toMatch(/^Preference: /);
  expect(firstPreferenceBar.getAttribute("title")).toMatch(/^Preference: /);
  expect(heatmap.querySelector(".schedule-heatmap__cell--assigned")).not.toBeNull();
  expect(heatmap.querySelector(".schedule-heatmap__cell--on_call")).not.toBeNull();
}
