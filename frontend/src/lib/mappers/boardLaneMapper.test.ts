import runDetailSnapshot from "../../../../fixtures/frontend_contracts/run_detail_state.json";
import stage06Snapshot from "../../../../fixtures/frontend_contracts/stage06_publish_ready_board_state.json";
import stage07Snapshot from "../../../../fixtures/frontend_contracts/stage07_major_replan_board_state.json";

import { deriveBoardLanes } from "@/lib/mappers/boardLaneMapper";
import type { BoardCard, FlagRow } from "@/lib/types/contracts";

function laneCounts(cards: BoardCard[], flags: FlagRow[]): Record<string, number> {
  const lanes = deriveBoardLanes({ cards, flags });
  return Object.fromEntries(lanes.map((lane) => [lane.id, lane.items.length]));
}

describe("Board lane mapper", () => {
  it("stays stable for Stage06 and Stage07 snapshots", () => {
    const stage06Cards = stage06Snapshot.board.board.cards as BoardCard[];
    const stage07Cards = stage07Snapshot.board.board.cards as BoardCard[];
    const stage07Flags = runDetailSnapshot.run_detail.flags as FlagRow[];

    const stage06 = laneCounts(stage06Cards, []);
    const stage07 = laneCounts(stage07Cards, stage07Flags);

    expect(stage06.unclaimed).toBeGreaterThanOrEqual(0);
    expect(stage06.claimed).toBeGreaterThanOrEqual(1);
    expect(stage06.awaiting_approval).toBeGreaterThanOrEqual(1);

    expect(stage07.exception_work).toBeGreaterThanOrEqual(1);
    expect(stage07.awaiting_approval).toBeGreaterThanOrEqual(1);
  });
});
