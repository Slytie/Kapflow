import type { CapxStatus } from "./capxCeoCockpitTypes";

interface StatusUi {
  className: string;
  label: string;
}

const STATUS_UI: Record<CapxStatus, StatusUi> = {
  critical: {
    className: "capx-status--critical",
    label: "critical executive attention required"
  },
  watch: {
    className: "capx-status--watch",
    label: "watch closely"
  },
  verified: {
    className: "capx-status--verified",
    label: "verified"
  },
  neutral: {
    className: "capx-status--neutral",
    label: "neutral"
  }
};

export function getCapxStatusClass(status: CapxStatus): string {
  return STATUS_UI[status].className;
}

export function getCapxStatusLabel(status: CapxStatus): string {
  return STATUS_UI[status].label;
}

export function capxStatusRank(status: CapxStatus): number {
  switch (status) {
    case "critical":
      return 0;
    case "watch":
      return 1;
    case "neutral":
      return 2;
    case "verified":
      return 3;
  }
}
