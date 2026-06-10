import type { CapxPmFeDemoStatus } from "./capxPmFeDemoTypes";

interface StatusUi {
  className: string;
  label: string;
  rank: number;
}

const STATUS_UI: Record<CapxPmFeDemoStatus, StatusUi> = {
  blocked: {
    className: "capx-pm-fe-status--blocked",
    label: "blocked",
    rank: 0
  },
  "proof-missing": {
    className: "capx-pm-fe-status--proof-missing",
    label: "proof missing",
    rank: 1
  },
  "needs-approval": {
    className: "capx-pm-fe-status--needs-approval",
    label: "needs approval",
    rank: 2
  },
  "waiting-supplier": {
    className: "capx-pm-fe-status--waiting-supplier",
    label: "waiting on supplier",
    rank: 3
  },
  "waiting-site": {
    className: "capx-pm-fe-status--waiting-site",
    label: "waiting on site",
    rank: 4
  },
  watch: {
    className: "capx-pm-fe-status--watch",
    label: "watch",
    rank: 5
  },
  "on-track": {
    className: "capx-pm-fe-status--on-track",
    label: "on track",
    rank: 6
  },
  "ready-share": {
    className: "capx-pm-fe-status--ready-share",
    label: "ready to share",
    rank: 7
  }
};

export function getCapxPmFeDemoStatusClass(status: CapxPmFeDemoStatus): string {
  return STATUS_UI[status].className;
}

export function getCapxPmFeDemoStatusLabel(status: CapxPmFeDemoStatus): string {
  return STATUS_UI[status].label;
}

export function getCapxPmFeDemoStatusRank(status: CapxPmFeDemoStatus): number {
  return STATUS_UI[status].rank;
}
