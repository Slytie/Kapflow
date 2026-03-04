import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { QueueRow } from "@/components/QueueRow";

describe("QueueRow", () => {
  it("renders compact metadata/actions and triggers inline handlers", async () => {
    const user = userEvent.setup();
    const onClaim = vi.fn();
    const onComplete = vi.fn();

    render(
      <QueueRow
        title="Stage06 · information_request"
        subtitle="dispatch_supervisor · wr-1"
        status="OPEN"
        onDetails={() => undefined}
        onClaim={onClaim}
        onComplete={onComplete}
      />
    );

    expect(screen.getByText("Stage06 · information_request")).toBeInTheDocument();
    expect(screen.getByText("dispatch_supervisor · wr-1")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Claim" }));
    await user.click(screen.getByRole("button", { name: "Complete" }));

    expect(onClaim).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
