import type { HumanTaskRow } from "@/lib/types/contracts";

function titleCaseWords(input: string): string {
  return input
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function taskDisplayLabel(task: Pick<HumanTaskRow, "stage_id" | "task_kind">): string {
  if (task.stage_id === "Stage01" && task.task_kind === "dispatch_seed_intake") {
    return "Prepare Live Day Inputs";
  }
  if (task.stage_id === "Stage01" && task.task_kind === "eos_input_intake") {
    return "End of Day Dispatch Report";
  }
  if (task.stage_id === "Stage04" && task.task_kind === "weekly_input_intake") {
    return "Weekly Scheduling Plan Inputs";
  }
  if (task.stage_id === "Stage04" && task.task_kind === "work_item") {
    return "Weekly Scheduling Agent";
  }
  if (task.stage_id === "Stage03" && task.task_kind === "dispatcher_review") {
    return "Review Live Replan";
  }
  if (task.stage_id === "Stage04" && task.task_kind === "final_packet_review") {
    return "Review EOD Draft";
  }
  if (task.stage_id === "Stage05" && task.task_kind === "final_review") {
    return "Review Weekly Draft";
  }
  return titleCaseWords(task.task_kind);
}

export function taskDisplayHeading(task: Pick<HumanTaskRow, "stage_id" | "task_kind">): string {
  return `${task.stage_id} · ${taskDisplayLabel(task)}`;
}
