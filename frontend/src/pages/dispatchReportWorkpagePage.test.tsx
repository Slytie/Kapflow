import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import eodWorkpageStateSnapshot from "@fixtures/workpage_eod_v0_state.json";
import { App } from "@/app/App";
import { server } from "@/test/api/server";
import { mutationLog } from "@/test/api/handlers";

describe("DispatchReportWorkpagePage", () => {
  it(
    "renders the draft/review page, shows backend metadata, and keeps closeout edits local across refresh",
    async () => {
      const user = userEvent.setup();
      let responseCount = 0;
      server.use(
        http.get("*/api/v1/workpages/demo/eod-v0", () => {
          responseCount += 1;
          const payload = structuredClone(eodWorkpageStateSnapshot.workpage_state);
          payload.freshness.generated_at =
            responseCount === 1 ? "2026-03-25T09:00:00Z" : "2026-03-25T09:00:30Z";
          return HttpResponse.json(payload);
        })
      );
      window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0");
      render(<App />);

      const page = await screen.findByTestId("dispatch-report-workpage-page");
      expect(within(page).getByRole("heading", { name: "End-of-day report" })).toBeInTheDocument();
      expect(within(page).getByText(/Formula-integrity warning/i)).toBeInTheDocument();
      expect(
        within(page).getByText(
          "Backend demo query served from repo-native workflow example bundles."
        )
      ).toBeInTheDocument();
      expect(within(page).getByText("dispatch_reporting_2026_03_16_qdci_dvc4_partial_v1")).toBeInTheDocument();
      expect(within(page).getByText("786")).toBeInTheDocument();
      expect(screen.getByLabelText("Secondary detail routes")).toBeInTheDocument();
      expect(
        screen.queryByText(/Server-authoritative view backed by HITL HTTP query contracts/i)
      ).not.toBeInTheDocument();
      expect(screen.queryByPlaceholderText("all or wr-...")).not.toBeInTheDocument();

      await user.type(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i }), "36 online");
      await user.click(screen.getAllByRole("button", { name: "Add entry" })[0]);
      await user.type(screen.getByRole("textbox", { name: "Rescues 1" }), "Route CX100 assist");
      await user.click(screen.getByRole("checkbox", { name: /Brahamvir Singh · CX100/i }));
      await user.type(
        screen.getAllByRole("textbox", { name: /Manager note/i })[0],
        "Review candidate tomorrow"
      );

      expect(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i })).toHaveValue("36 online");
      expect(screen.getByRole("textbox", { name: "Rescues 1" })).toHaveValue("Route CX100 assist");
      expect(screen.getByRole("checkbox", { name: /Brahamvir Singh · CX100/i })).toBeChecked();
      expect(screen.getAllByRole("textbox", { name: /Manager note/i })[0]).toHaveValue(
        "Review candidate tomorrow"
      );

      await user.click(screen.getByRole("button", { name: "Refresh" }));

      expect(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i })).toHaveValue(
        "36 online"
      );
      expect(screen.getByRole("textbox", { name: "Rescues 1" })).toHaveValue("Route CX100 assist");
      expect(screen.getByRole("checkbox", { name: /Brahamvir Singh · CX100/i })).toBeChecked();
      expect(screen.getAllByRole("textbox", { name: /Manager note/i })[0]).toHaveValue(
        "Review candidate tomorrow"
      );
      expect(mutationLog()).toEqual([]);
    },
    10000
  );
});
