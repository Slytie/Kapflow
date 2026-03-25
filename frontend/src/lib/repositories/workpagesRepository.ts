import {
  buildEndOfDayWorkpageViewModel,
  buildScheduleWorkpageViewModel
} from "@/lib/workpages/exampleViewModels";
import type { WorkpageViewModel } from "@/lib/types/workpages";

export const workpagesRepository = {
  async scheduleExample(): Promise<WorkpageViewModel> {
    return buildScheduleWorkpageViewModel();
  },

  async eodExample(): Promise<WorkpageViewModel> {
    return buildEndOfDayWorkpageViewModel();
  }
};
