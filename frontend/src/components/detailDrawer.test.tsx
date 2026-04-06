import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router-dom";

import { DetailDrawer } from "@/components/DetailDrawer";
import { TaskCardWide } from "@/components/TaskCardWide";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { humanTasksRepository } from "@/lib/repositories";
import type { DrawerPayload } from "@/lib/types/ui";
import type { HumanTaskRow } from "@/lib/types/contracts";
import { mutationLog } from "@/test/api/handlers";

function buildActionRef(params: {
  actionId: string;
  workpageKind: string;
  workflowRunId: string;
  artifactVersionId?: string | null;
  subjectKind: "human_task" | "approval";
  subjectId: string;
}) {
  return {
    action_id: params.actionId,
    workpage_kind: params.workpageKind,
    workflow_run_id: params.workflowRunId,
    artifact_version_id: params.artifactVersionId ?? null,
    subject: {
      subject_kind: params.subjectKind,
      subject_id: params.subjectId
    }
  };
}

const task: HumanTaskRow = {
  human_task_id: "ht-2",
  workflow_run_id: "wr-2",
  task_run_id: "tr-2",
  task_kind: "review_packet",
  state: "OPEN",
  candidate_roles: ["dispatch_supervisor"],
  owner_role: "dispatch_supervisor",
  assignee_actor_id: null,
  assignee_actor_type: null,
  due_at: null,
  escalation_at: null,
  lease_version: 0,
  claimed_at: null,
  claimed_until: null,
  linked_approval_id: null,
  reopen_count: 0,
  generation: 0,
  created_at: "2026-03-03T00:00:00Z",
  updated_at: "2026-03-03T00:00:00Z",
  task_run_state: "READY",
  stage_id: "Stage06",
  blocked_on_kind: null,
  blocked_on_ref: null,
  spawned_from_flag_id: null
};

function Harness(): JSX.Element {
  const [payload, setPayload] = useState<DrawerPayload | null>(null);

  return (
    <>
      <TaskCardWide
        task={task}
        onDetails={() =>
          setPayload({
            title: "Task details",
            description: "This description is only visible in the drawer.",
            fields: [{ label: "State", value: "OPEN" }],
            artifacts: [
              {
                artifact_version_id: "av-weekly-001",
                artifact_kind: "schedule.draft_schedule.workbook",
                artifact_role: "evidence",
                media_type:
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                created_at: "2026-03-04T12:00:00Z",
                file_name: "stage05.xlsx",
                source_label: "Step output"
              }
            ]
          })
        }
      />
      <DetailDrawer payload={payload} onClose={() => setPayload(null)} />
    </>
  );
}

function TaskModalHarness(): JSX.Element {
  const [payload, setPayload] = useState<DrawerPayload | null>(null);

  return (
    <>
      <button
        type="button"
        onClick={() =>
          setPayload({
            title: "Task details",
            description: "Modal-only task context.",
            fields: [],
            task: {
              human_task_id: "ht-2",
              workflow_run_id: "wr-2",
              task_run_id: "tr-2",
              stage_id: "Stage06",
              task_kind: "review_packet",
              state: "OPEN",
              assignee_actor_id: null,
              assignee_actor_type: null,
              owner_role: "dispatch_supervisor",
              available_actions: ["claim", "complete"],
              blocking_reason_codes: [],
              missing_required_inputs: []
            }
          })
        }
      >
        Open task
      </button>
      <DetailDrawer payload={payload} onClose={() => setPayload(null)} />
    </>
  );
}

function PayloadModalHarness({
  initialPayload,
  triggerLabel = "Open modal"
}: {
  initialPayload: DrawerPayload;
  triggerLabel?: string;
}): JSX.Element {
  const [payload, setPayload] = useState<DrawerPayload | null>(null);

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setPayload(initialPayload);
        }}
      >
        {triggerLabel}
      </button>
      <DetailDrawer payload={payload} onClose={() => setPayload(null)} />
    </>
  );
}

function renderWithQueryClient(element: JSX.Element) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  });
  return {
    queryClient,
    ...render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>{element}</QueryClientProvider>
      </MemoryRouter>
    )
  };
}

describe("Detail drawer flow", () => {
  it("keeps card compact and shows description in drawer", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<Harness />);
    const closedDrawer = document.querySelector(".detail-drawer--closed");

    expect(closedDrawer).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByText("This description is only visible in the drawer.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Details" }));

    const openDrawer = await screen.findByLabelText("Details drawer");
    expect(openDrawer).toHaveClass("detail-drawer--open");
    expect(screen.getByText("This description is only visible in the drawer.")).toBeInTheDocument();
    expect(await screen.findByText("Task Artifacts (1)")).toBeInTheDocument();
    expect(screen.getByText("stage05.xlsx")).toBeInTheDocument();
    const artifactsSection = screen.getByLabelText("Task artifacts");
    const downloadButton = within(artifactsSection).getByRole("button", { name: "Download" });
    expect(downloadButton).toBeInTheDocument();
    await user.click(downloadButton);
    await waitFor(() => {
      expect(mutationLog()).toContain("artifact-download-bin:av-weekly-001");
    });
    expect(screen.getByTestId("task-card-wide")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close drawer" }));

    await waitFor(() => {
      expect(document.querySelector(".detail-drawer--open")).toBeNull();
    });
    expect(document.querySelector(".detail-drawer--closed")).toHaveAttribute("aria-hidden", "true");
  });

  it("opens task payloads in a modal, traps focus, and returns focus on close", async () => {
    const user = userEvent.setup();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      available_actions: ["claim", "complete"],
      missing_required_inputs: [],
      blocking_reason_codes: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    renderWithQueryClient(<TaskModalHarness />);

    const trigger = screen.getByRole("button", { name: "Open task" });
    await user.click(trigger);

    const modal = await screen.findByRole("dialog", { name: "Task details" });
    expect(modal).toHaveClass("task-modal");
    expect(screen.queryByLabelText("Details drawer")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Task Process" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close task modal" })).toHaveFocus();

    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(screen.getByRole("button", { name: "Complete Task" })).toHaveFocus();
    await user.keyboard("{Tab}");
    expect(screen.getByRole("button", { name: "Close task modal" })).toHaveFocus();

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Task details" })).not.toBeInTheDocument();
    });
    expect(trigger).toHaveFocus();

    getSpy.mockRestore();
  });

  it("keeps raw identifiers out of the modal body and reveals them through the info dialog", async () => {
    const user = userEvent.setup();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      available_actions: ["claim"],
      missing_required_inputs: [],
      blocking_reason_codes: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    renderWithQueryClient(<TaskModalHarness />);

    await user.click(screen.getByRole("button", { name: "Open task" }));
    await screen.findByRole("dialog", { name: "Task details" });

    expect(screen.queryByText("Task ID")).not.toBeInTheDocument();
    expect(screen.queryByText("Run ID")).not.toBeInTheDocument();
    expect(screen.queryByText("Workflow run")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show task technical details" }));
    expect(await screen.findByRole("heading", { name: "Task technical details" })).toBeInTheDocument();
    expect(screen.getByText("Task ID")).toBeInTheDocument();
    expect(screen.getByText("Run ID")).toBeInTheDocument();
    expect(screen.getByText("Task Run ID")).toBeInTheDocument();
    expect(screen.getByText("ht-2")).toBeInTheDocument();
    expect(screen.getByText("wr-2")).toBeInTheDocument();
    expect(screen.getByText("tr-2")).toBeInTheDocument();

    getSpy.mockRestore();
  });

  it("dismisses the task modal from the backdrop", async () => {
    const user = userEvent.setup();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      available_actions: ["claim"],
      missing_required_inputs: [],
      blocking_reason_codes: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    renderWithQueryClient(<TaskModalHarness />);

    await user.click(screen.getByRole("button", { name: "Open task" }));
    const backdrop = (await screen.findByRole("dialog", { name: "Task details" })).parentElement;
    expect(backdrop).toHaveClass("task-modal-backdrop");

    await user.click(backdrop as HTMLElement);
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Task details" })).not.toBeInTheDocument();
    });

    getSpy.mockRestore();
  });

  it("renders lightweight family-node artifacts in the shared drawer", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Weekly Schedule Planning",
          subtitle: "Family node artifacts",
          fields: [
            { label: "Workflow", value: "weekly_schedule_planning.v1" },
            { label: "Status", value: "active" }
          ],
          downloadable_artifacts: [
            {
              artifact_version_id: "av-weekly-001",
              label: "weekly_schedule.xlsx",
              source_label: "Official output"
            }
          ]
        }}
        onClose={() => undefined}
      />
    );

    expect(await screen.findByRole("heading", { name: "Downloadable Artifacts (1)" })).toBeInTheDocument();
    const artifactsSection = screen.getByLabelText("Downloadable artifacts");
    expect(within(artifactsSection).getByText("weekly_schedule.xlsx")).toBeInTheDocument();
    expect(within(artifactsSection).getByText("Official output")).toBeInTheDocument();

    await user.click(within(artifactsSection).getByRole("button", { name: "Download" }));
    await waitFor(() => {
      expect(mutationLog()).toContain("artifact-download-bin:av-weekly-001");
    });
  });

  it("executes task actions from the modal and refreshes relevant query views", async () => {
    const user = userEvent.setup();
    const claimSpy = vi.spyOn(humanTasksRepository, "claim").mockResolvedValue();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      available_actions: ["claim"],
      missing_required_inputs: [],
      blocking_reason_codes: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    const { queryClient } = renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage06 review_packet",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage06",
            task_kind: "review_packet",
            state: "OPEN",
            assignee_actor_id: null,
            assignee_actor_type: null,
            owner_role: "dispatch_supervisor",
            available_actions: ["claim"],
            blocking_reason_codes: [],
            missing_required_inputs: []
          }
        }}
        onClose={() => undefined}
      />
    );
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    expect(await screen.findByRole("dialog", { name: "Stage06 review_packet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Claim" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete Task" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Claim" }));

    await waitFor(() => {
      expect(claimSpy).toHaveBeenCalledWith("ht-2");
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["logistics-demo-story"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["board-view"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["my-work"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["run-detail", "wr-2"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["run-workspace", "wr-2"] });
    });

    claimSpy.mockRestore();
    getSpy.mockRestore();
  });

  it("renders only available task actions and calls Stage06 review when offered", async () => {
    const user = userEvent.setup();
    const runStage06Spy = vi.spyOn(humanTasksRepository, "runStage06AgentReview").mockResolvedValue();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      available_actions: ["run_stage06_agent_review", "upload_attachment"],
      missing_required_inputs: [],
      blocking_reason_codes: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage06 review_packet",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage06",
            task_kind: "review_packet",
            state: "OPEN",
            assignee_actor_id: null,
            assignee_actor_type: null,
            owner_role: "dispatch_supervisor",
            available_actions: ["run_stage06_agent_review", "upload_attachment"],
            blocking_reason_codes: [],
            missing_required_inputs: []
          }
        }}
        onClose={() => undefined}
      />
    );

    expect(await screen.findByRole("button", { name: "Run Stage06 Review" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add supporting attachment" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete Task" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Run Stage06 Review" }));
    await waitFor(() => {
      expect(runStage06Spy).toHaveBeenCalledWith("ht-2");
    });

    runStage06Spy.mockRestore();
    getSpy.mockRestore();
  });

  it("renders task workpage links in the modal when available", async () => {
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      stage_id: "Stage04",
      task_kind: "work_item",
      available_actions: ["complete"],
      missing_required_inputs: [],
      blocking_reason_codes: [],
      workpage_actions: [
        {
          action_id: "workpage.schedule-v0.open_latest_draft",
          workpage_kind: "schedule-v0",
          label: "Open schedule draft",
          presentation: "open_route",
          state: "available",
          route: "/runs/wr-2/workpages/schedule-v0/artifacts/av-weekly-draft-001",
          create_path: null,
          subject_context: {
            subject_kind: "human_task",
            subject_id: "ht-2",
            workflow_run_id: "wr-2"
          },
          link_policy: {
            create_relation_kind: null,
            submit_relation_kind: "response"
          },
          action_ref: buildActionRef({
            actionId: "workpage.schedule-v0.open_latest_draft",
            workpageKind: "schedule-v0",
            workflowRunId: "wr-2",
            artifactVersionId: "av-weekly-draft-001",
            subjectKind: "human_task",
            subjectId: "ht-2"
          }),
          disabled_reason: null
        }
      ]
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);

    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage04 · Weekly Scheduling Agent",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage04",
            task_kind: "work_item",
            state: "CLAIMED",
            assignee_actor_id: "human:schedule-planner-1",
            assignee_actor_type: "human",
            owner_role: "schedule_planner",
            available_actions: ["complete"],
            blocking_reason_codes: [],
            missing_required_inputs: [],
            workpage_actions: [
              {
                action_id: "workpage.schedule-v0.open_latest_draft",
                workpage_kind: "schedule-v0",
                label: "Open schedule draft",
                presentation: "open_route",
                state: "available",
                route: "/runs/wr-2/workpages/schedule-v0/artifacts/av-weekly-draft-001",
                create_path: null,
                subject_context: {
                  subject_kind: "human_task",
                  subject_id: "ht-2",
                  workflow_run_id: "wr-2"
                },
                link_policy: {
                  create_relation_kind: null,
                  submit_relation_kind: "response"
                },
                action_ref: buildActionRef({
                  actionId: "workpage.schedule-v0.open_latest_draft",
                  workpageKind: "schedule-v0",
                  workflowRunId: "wr-2",
                  artifactVersionId: "av-weekly-draft-001",
                  subjectKind: "human_task",
                  subjectId: "ht-2"
                }),
                disabled_reason: null
              }
            ]
          }
        }}
        onClose={() => undefined}
      />
    );

    expect(
      await screen.findByRole("dialog", { name: "Stage04 · Weekly Scheduling Agent" })
    ).toBeInTheDocument();
    const workpageLink = screen.getByRole("link", { name: "Open schedule draft" });
    expect(workpageLink).toHaveAttribute(
      "href",
      "/runs/wr-2/workpages/schedule-v0/artifacts/av-weekly-draft-001"
    );

    getSpy.mockRestore();
  });

  it("renders requirement-specific uploads in the modal and refreshes completion state", async () => {
    const uploadRequiredResponseSpy = vi
      .spyOn(humanTasksRepository, "uploadRequiredResponse")
      .mockResolvedValue();
    const getSpy = vi
      .spyOn(humanTasksRepository, "get")
      .mockResolvedValueOnce({
        ...task,
        stage_id: "Stage04",
        task_kind: "weekly_input_intake",
        owner_role: "schedule_planner",
        available_actions: ["upload_attachment"],
        missing_required_inputs: ["planning.route_slot_requirements.workbook"],
        blocking_reason_codes: ["required_upload_missing:planning.route_slot_requirements.workbook"],
        required_uploads: [
          {
            dataset_key: "planning.route_slot_requirements.workbook",
            artifact_kind: "planning.route_slot_requirements.workbook",
            artifact_role: "official_input",
            template_id: "tpl-weekly-route-slots",
            required: true,
            required_count: 1,
            current_count: 0,
            status: "missing"
          }
        ],
        required_reviews: []
      })
      .mockResolvedValueOnce({
        ...task,
        stage_id: "Stage04",
        task_kind: "weekly_input_intake",
        owner_role: "schedule_planner",
        available_actions: ["complete", "upload_attachment"],
        missing_required_inputs: [],
        blocking_reason_codes: [],
        required_uploads: [
          {
            dataset_key: "planning.route_slot_requirements.workbook",
            artifact_kind: "planning.route_slot_requirements.workbook",
            artifact_role: "official_input",
            template_id: "tpl-weekly-route-slots",
            required: true,
            required_count: 1,
            current_count: 1,
            status: "satisfied"
          }
        ],
        required_reviews: []
      });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);

    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage04 · Weekly Scheduling Plan Inputs",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage04",
            task_kind: "weekly_input_intake",
            state: "CLAIMED",
            assignee_actor_id: "human:schedule-planner-1",
            assignee_actor_type: "human",
            owner_role: "schedule_planner",
            available_actions: ["upload_attachment"],
            blocking_reason_codes: [
              "required_upload_missing:planning.route_slot_requirements.workbook"
            ],
            missing_required_inputs: ["planning.route_slot_requirements.workbook"],
            required_uploads: [
              {
                dataset_key: "planning.route_slot_requirements.workbook",
                artifact_kind: "planning.route_slot_requirements.workbook",
                artifact_role: "official_input",
                template_id: "tpl-weekly-route-slots",
                required: true,
                required_count: 1,
                current_count: 0,
                status: "missing"
              }
            ],
            required_reviews: []
          }
        }}
        onClose={() => undefined}
      />
    );

    expect(await screen.findByRole("heading", { name: "Required Documents" })).toBeInTheDocument();
    const requirementRow = screen
      .getByText("Route Slot Requirements")
      .closest(".task-modal__document-row");
    expect(requirementRow).not.toBeNull();
    expect(within(requirementRow as HTMLElement).getByText("Missing")).toBeInTheDocument();
    expect(within(requirementRow as HTMLElement).getByRole("button", { name: "Add File" })).toBeInTheDocument();
    expect(
      within(requirementRow as HTMLElement).getByRole("button", { name: "Download template" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add supporting attachment" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete Task" })).not.toBeInTheDocument();

    const fileInput = (requirementRow as HTMLElement).querySelector("input[type='file']");
    expect(fileInput).not.toBeNull();
    const file = new File(["fixture"], "weekly-route-slots.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    });
    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [file] } });

    await waitFor(() => {
      expect(uploadRequiredResponseSpy).toHaveBeenCalledWith(
        "ht-2",
        expect.objectContaining({
          dataset_key: "planning.route_slot_requirements.workbook",
          artifact_role: "official_input"
        }),
        file
      );
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Complete Task" })).toBeInTheDocument();
      expect(screen.getByText("Satisfied")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Replace" })).toBeInTheDocument();
    });

    uploadRequiredResponseSpy.mockRestore();
    getSpy.mockRestore();
  });

  it("renders review rows with a View action and shows task artifacts as chips", async () => {
    const user = userEvent.setup();
    const openDraftSpy = vi.spyOn(humanTasksRepository, "openDraftArtifact").mockResolvedValue();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      state: "CLAIMED",
      assignee_actor_id: "human:reviewer-1",
      assignee_actor_type: "human",
      available_actions: ["confirm_review", "upload_attachment"],
      missing_required_inputs: ["reporting.final_packet.workbook"],
      blocking_reason_codes: ["required_review_confirmation_missing:reporting.final_packet.workbook"],
      required_uploads: [],
      required_reviews: [
        {
          dataset_key: "reporting.final_packet.workbook",
          artifact_kind: "reporting.final_packet.workbook",
          required_count: 1,
          reviewed_artifact_version_id: "av-review-001",
          review_confirmation_artifact_version_id: null,
          status: "pending_confirmation"
        }
      ]
    });
    const listArtifactsSpy = vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([
      {
        artifact_version_id: "av-support-001",
        workflow_run_id: "wr-2",
        task_run_id: "tr-2",
        artifact_kind: "task.supporting_note.txt",
        artifact_role: "evidence",
        media_type: "text/plain",
        storage_uri: "memory://task/supporting_note.txt",
        content_digest: "sha256:av-support-001",
        byte_size: 12,
        metadata_json: {
          file_name: "supervisor-note.txt"
        },
        parent_artifact_version_id: null,
        supersedes_artifact_version_id: null,
        lineage_note: null,
        created_at: "2026-03-04T12:00:00Z",
        links: []
      }
    ]);

    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Review EOD Draft",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage04",
            task_kind: "final_packet_review",
            state: "CLAIMED",
            assignee_actor_id: "human:reviewer-1",
            assignee_actor_type: "human",
            owner_role: "dispatch_supervisor",
            available_actions: ["confirm_review", "upload_attachment"],
            blocking_reason_codes: [
              "required_review_confirmation_missing:reporting.final_packet.workbook"
            ],
            missing_required_inputs: ["reporting.final_packet.workbook"],
            required_uploads: [],
            required_reviews: [
              {
                dataset_key: "reporting.final_packet.workbook",
                artifact_kind: "reporting.final_packet.workbook",
                required_count: 1,
                reviewed_artifact_version_id: "av-review-001",
                review_confirmation_artifact_version_id: null,
                status: "pending_confirmation"
              }
            ]
          }
        }}
        onClose={() => undefined}
      />
    );

    const reviewLabel = await screen.findByText("Final Packet Workbook");
    const reviewRow = reviewLabel.closest(".task-modal__document-row");
    expect(reviewRow).not.toBeNull();
    expect(screen.getByText("Review Required")).toBeInTheDocument();
    expect(within(reviewRow as HTMLElement).getByRole("button", { name: "View" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit for Review" })).toBeEnabled();
    expect(await screen.findByRole("button", { name: "Download supervisor-note.txt" })).toBeInTheDocument();

    await user.click(within(reviewRow as HTMLElement).getByRole("button", { name: "View" }));
    await waitFor(() => {
      expect(openDraftSpy).toHaveBeenCalledWith("av-review-001");
    });

    listArtifactsSpy.mockRestore();
    getSpy.mockRestore();
    openDraftSpy.mockRestore();
  });

  it("shows the schedule workpage link after the weekly Stage04 build refreshes task detail", async () => {
    const user = userEvent.setup();
    const runSpy = vi
      .spyOn(humanTasksRepository, "runWeeklyStage04OpenAIAgent")
      .mockResolvedValue();
    const getSpy = vi
      .spyOn(humanTasksRepository, "get")
      .mockResolvedValueOnce({
        ...task,
        stage_id: "Stage04",
        task_kind: "work_item",
        owner_role: "schedule_planner",
        assignee_actor_id: "human:schedule-planner-1",
        assignee_actor_type: "human",
        available_actions: ["run_weekly_stage04_openai_agent"],
        missing_required_inputs: [],
        blocking_reason_codes: [],
        required_uploads: [],
        required_reviews: [],
        workpage_actions: []
      })
      .mockResolvedValueOnce({
        ...task,
        stage_id: "Stage04",
        task_kind: "work_item",
        owner_role: "schedule_planner",
        assignee_actor_id: "human:schedule-planner-1",
        assignee_actor_type: "human",
        available_actions: ["complete"],
        missing_required_inputs: [],
        blocking_reason_codes: [],
        required_uploads: [],
        required_reviews: [],
        workpage_actions: [
          {
            action_id: "workpage.schedule-v0.open_latest_draft",
            workpage_kind: "schedule-v0",
            label: "Open schedule draft",
            presentation: "open_route",
            state: "available",
            route: "/runs/wr-2/workpages/schedule-v0/artifacts/av-weekly-draft-001",
            create_path: null,
            subject_context: {
              subject_kind: "human_task",
              subject_id: "ht-2",
              workflow_run_id: "wr-2"
            },
            link_policy: {
              create_relation_kind: null,
              submit_relation_kind: "response"
            },
            action_ref: buildActionRef({
              actionId: "workpage.schedule-v0.open_latest_draft",
              workpageKind: "schedule-v0",
              workflowRunId: "wr-2",
              artifactVersionId: "av-weekly-draft-001",
              subjectKind: "human_task",
              subjectId: "ht-2"
            }),
            disabled_reason: null
          }
        ]
      });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);

    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage04 · Weekly Scheduling Agent",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage04",
            task_kind: "work_item",
            state: "CLAIMED",
            assignee_actor_id: "human:schedule-planner-1",
            assignee_actor_type: "human",
            owner_role: "schedule_planner",
            available_actions: ["run_weekly_stage04_openai_agent"],
            blocking_reason_codes: [],
            missing_required_inputs: [],
            required_uploads: [],
            required_reviews: [],
            workpage_actions: []
          }
        }}
        onClose={() => undefined}
      />
    );

    expect(await screen.findByRole("button", { name: "Run Stage04 Build" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open schedule draft" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Run Stage04 Build" }));

    await waitFor(() => {
      expect(runSpy).toHaveBeenCalledWith("ht-2");
    });
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Open schedule draft" })).toHaveAttribute(
        "href",
        "/runs/wr-2/workpages/schedule-v0/artifacts/av-weekly-draft-001"
      );
    });

    runSpy.mockRestore();
    getSpy.mockRestore();
  });

  it("keeps optional uploads from blocking completion in the modal", async () => {
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      available_actions: ["complete", "upload_attachment"],
      missing_required_inputs: [],
      blocking_reason_codes: [],
      required_uploads: [
        {
          dataset_key: "planning.route_horizon.doc",
          artifact_kind: "planning.route_horizon.doc",
          artifact_role: "evidence",
          template_id: null,
          required: false,
          required_count: 1,
          current_count: 0,
          status: "missing"
        }
      ],
      required_reviews: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);

    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage04 · Weekly Scheduling Plan Inputs",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage04",
            task_kind: "weekly_input_intake",
            state: "CLAIMED",
            assignee_actor_id: "human:schedule-planner-1",
            assignee_actor_type: "human",
            owner_role: "schedule_planner",
            available_actions: ["complete", "upload_attachment"],
            blocking_reason_codes: [],
            missing_required_inputs: [],
            required_uploads: [
              {
                dataset_key: "planning.route_horizon.doc",
                artifact_kind: "planning.route_horizon.doc",
                artifact_role: "evidence",
                template_id: null,
                required: false,
                required_count: 1,
                current_count: 0,
                status: "missing"
              }
            ],
            required_reviews: []
          }
        }}
        onClose={() => undefined}
      />
    );

    expect(await screen.findByText(/Optional context not yet attached/i)).toBeInTheDocument();
    expect(screen.getByText("Optional")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Complete Task" })).toBeEnabled();

    getSpy.mockRestore();
  });

  it("renders the weekly Stage04 build action and invokes it from the modal", async () => {
    const user = userEvent.setup();
    const runStage04Spy = vi
      .spyOn(humanTasksRepository, "runWeeklyStage04OpenAIAgent")
      .mockResolvedValue();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      stage_id: "Stage04",
      task_kind: "work_item",
      owner_role: "schedule_planner",
      available_actions: ["run_weekly_stage04_openai_agent"],
      missing_required_inputs: [],
      blocking_reason_codes: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage04 · Weekly Scheduling Agent",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage04",
            task_kind: "work_item",
            state: "CLAIMED",
            assignee_actor_id: "human:schedule-planner-1",
            assignee_actor_type: "human",
            owner_role: "schedule_planner",
            available_actions: ["run_weekly_stage04_openai_agent"],
            blocking_reason_codes: [],
            missing_required_inputs: []
          }
        }}
        onClose={() => undefined}
      />
    );

    expect(await screen.findByRole("button", { name: "Run Stage04 Build" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run Stage04 Build" }));
    await waitFor(() => {
      expect(runStage04Spy).toHaveBeenCalledWith("ht-2");
    });

    runStage04Spy.mockRestore();
    getSpy.mockRestore();
  });

  it("auto-loads the composite task process as a collapsed-start timeline and closes on Escape", async () => {
    const user = userEvent.setup();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      task_kind: "planning_feedback_review",
      available_actions: ["claim"],
      missing_required_inputs: [],
      blocking_reason_codes: [],
      is_composite: true,
      expansion_kind: "task_subgraph",
      subgraph_ref: {
        human_task_id: "ht-2",
        endpoint: "/api/v1/human-tasks/ht-2/subgraph"
      }
    });
    const getSubgraphSpy = vi.spyOn(humanTasksRepository, "getSubgraph").mockResolvedValue({
      graph_id: "task_subgraph:ht-2",
      template_id: "schedule_planning.feedback_review.v1",
      title: "Planning feedback review",
      nodes: [
        {
          node_id: "ingest_actual_hours",
          label: "Ingest actual-hours snapshot",
          node_kind: "step",
          status: "in_progress",
          row: 0,
          column: 0,
          is_blocking: false
        },
        {
          node_id: "reconcile_plan_variance",
          label: "Reconcile plan variance",
          node_kind: "step",
          status: "not_started",
          row: 0,
          column: 1,
          is_blocking: false
        }
      ],
      edges: [
        {
          edge_id: "ingest_actual_hours->reconcile_plan_variance",
          from_node_id: "ingest_actual_hours",
          to_node_id: "reconcile_plan_variance",
          edge_kind: "linear",
          label: null
        }
      ],
      freshness: {
        status: "fresh",
        as_of: "2026-03-09T10:00:00Z",
        note: "Mock freshness"
      },
      artifact_refs: [
        {
          artifact_version_id: "av-subgraph-1",
          label: "actual-hours.xlsx",
          source_label: "Task step output"
        }
      ]
    });
    const downloadSpy = vi.spyOn(onetruthApi, "downloadArtifact").mockResolvedValue({
      body: new Blob(["fixture"], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      }),
      mediaType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      fileName: "actual-hours.xlsx",
      contentLength: 7,
      requestId: "req-subgraph-download"
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    renderWithQueryClient(
      <PayloadModalHarness
        triggerLabel="Open composite task"
        initialPayload={{
          title: "Stage03 planning_feedback_review",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage03",
            task_kind: "planning_feedback_review",
            state: "OPEN",
            assignee_actor_id: null,
            assignee_actor_type: null,
            owner_role: "dispatch_supervisor",
            available_actions: ["claim"],
            blocking_reason_codes: [],
            missing_required_inputs: [],
            is_composite: true,
            expansion_kind: "task_subgraph",
            subgraph_ref: {
              human_task_id: "ht-2",
              endpoint: "/api/v1/human-tasks/ht-2/subgraph"
            }
          }
        }}
      />
    );

    await user.click(screen.getByRole("button", { name: "Open composite task" }));

    await waitFor(() => {
      expect(getSubgraphSpy).toHaveBeenCalledWith("ht-2");
    });
    const processHeading = await screen.findByRole("heading", { name: "Task Process" });
    const requiredHeading = screen.getByRole("heading", { name: "Required Documents" });
    const artifactHeading = screen.getByRole("heading", { name: "Task Artifacts" });

    expect(
      requiredHeading.compareDocumentPosition(processHeading) & Node.DOCUMENT_POSITION_FOLLOWING
    ).not.toBe(0);
    expect(
      processHeading.compareDocumentPosition(artifactHeading) & Node.DOCUMENT_POSITION_FOLLOWING
    ).not.toBe(0);
    expect(screen.queryByRole("button", { name: "Expand process" })).not.toBeInTheDocument();

    const ingestStep = screen.getByRole("button", { name: /Ingest actual-hours snapshot/i });
    const reconcileStep = screen.getByRole("button", { name: /Reconcile plan variance/i });
    expect(ingestStep).toHaveAttribute("aria-expanded", "false");
    expect(reconcileStep).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Flows to Reconcile plan variance")).not.toBeInTheDocument();

    await user.click(ingestStep);
    expect(ingestStep).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Flows to Reconcile plan variance")).toBeInTheDocument();

    await user.click(reconcileStep);
    expect(reconcileStep).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Receives from Ingest actual-hours snapshot")).toBeInTheDocument();

    const processArtifacts = screen.getByLabelText("Process artifacts");
    expect(within(processArtifacts).getByText("actual-hours.xlsx")).toBeInTheDocument();
    await user.click(within(processArtifacts).getByRole("button", { name: "Download" }));
    await waitFor(() => {
      expect(downloadSpy).toHaveBeenCalledWith("av-subgraph-1");
    });

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Stage03 planning_feedback_review" })).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Open composite task" })).toHaveFocus();
    expect(getSubgraphSpy).toHaveBeenCalledTimes(1);

    downloadSpy.mockRestore();
    getSpy.mockRestore();
    getSubgraphSpy.mockRestore();
  });
});
