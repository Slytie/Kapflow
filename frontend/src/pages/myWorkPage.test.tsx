import { screen } from "@testing-library/react";

import { MyWorkPage } from "@/pages/MyWorkPage";
import { renderRoute } from "@/test/renderRoute";

describe("MyWorkPage", () => {
  it("filters rows by URL state filter", async () => {
    renderRoute(<MyWorkPage />, {
      route: "/my-work?run=wr-test-001&state=OPEN",
      path: "/my-work"
    });

    expect(await screen.findByText(/information_request/i)).toBeInTheDocument();
    expect(screen.queryByText(/exception_triage/i)).not.toBeInTheDocument();
  });
});
