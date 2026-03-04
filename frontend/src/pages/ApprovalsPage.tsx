import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { ApprovalCard } from "@/components/ApprovalCard";
import { StatePanel } from "@/components/StatePanel";
import { useShellFilters } from "@/app/useShellFilters";
import { approvalsRepository, workflowRunsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";

export function ApprovalsPage(): JSX.Element {
  const queryClient = useQueryClient();
  const { filters } = useShellFilters();
  const { open } = useDrawer();
  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);

  const approvalsQuery = useQuery({
    queryKey: ["approvals", filters.workflowRunId, filters.state],
    queryFn: () =>
      approvalsRepository.list({
        workflowRunId: filters.workflowRunId,
        state: filters.state
      }),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const selectedApproval = useMemo(
    () =>
      approvalsQuery.data?.find((approval) => approval.approval_id === selectedApprovalId) ??
      approvalsQuery.data?.[0],
    [approvalsQuery.data, selectedApprovalId]
  );

  const detailQuery = useQuery({
    queryKey: ["run-detail", selectedApproval?.workflow_run_id ?? filters.workflowRunId],
    queryFn: () => workflowRunsRepository.detail(selectedApproval?.workflow_run_id),
    enabled: Boolean(selectedApproval?.workflow_run_id),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const refreshApprovals = (): void => {
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ["approvals"] }),
      queryClient.invalidateQueries({ queryKey: ["board-view"] }),
      queryClient.invalidateQueries({ queryKey: ["run-detail"] })
    ]);
  };

  const respondMutation = useMutation({
    mutationFn: (payload: { approvalId: string; responseKind: "approve" | "reject" | "request_changes" }) =>
      approvalsRepository.respond(payload.approvalId, payload.responseKind),
    onSuccess: refreshApprovals
  });

  const uploadAttachmentMutation = useMutation({
    mutationFn: (payload: { approvalId: string; file: File }) =>
      approvalsRepository.uploadAttachment(payload.approvalId, payload.file),
    onSuccess: refreshApprovals
  });

  const downloadAttachmentMutation = useMutation({
    mutationFn: (approvalId: string) => approvalsRepository.downloadLatestAttachment(approvalId)
  });

  if (approvalsQuery.isLoading) {
    return <StatePanel kind="loading" title="Loading approvals" detail="Fetching approval queue." />;
  }

  if (approvalsQuery.isError) {
    return (
      <StatePanel
        kind="error"
        title="Approvals failed to load"
        detail={errorText(approvalsQuery.error, "Unable to load approvals")}
        onRetry={() => void approvalsQuery.refetch()}
      />
    );
  }

  const approvals = approvalsQuery.data ?? [];
  if (approvals.length === 0) {
    return <StatePanel kind="empty" title="No approvals in scope" detail="Adjust filters to widen queue." />;
  }

  return (
    <section className="split-layout" data-testid="approvals-page">
      <div>
        <h2>Approval Queue</h2>
        {respondMutation.isError || uploadAttachmentMutation.isError || downloadAttachmentMutation.isError ? (
          <StatePanel
            kind="error"
            title="Approval response failed"
            detail={errorText(
              respondMutation.error ?? uploadAttachmentMutation.error ?? downloadAttachmentMutation.error,
              "Unable to submit response"
            )}
          />
        ) : null}
        <div className="stack-list">
          {approvals.map((approval) => {
            const isSelected = selectedApproval?.approval_id === approval.approval_id;
            const isBusy =
              (respondMutation.isPending &&
                respondMutation.variables?.approvalId === approval.approval_id) ||
              (uploadAttachmentMutation.isPending &&
                uploadAttachmentMutation.variables?.approvalId === approval.approval_id) ||
              (downloadAttachmentMutation.isPending &&
                downloadAttachmentMutation.variables === approval.approval_id);

            return (
              <div
                key={approval.approval_id}
                className={`selectable-card ${isSelected ? "is-selected" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => setSelectedApprovalId(approval.approval_id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setSelectedApprovalId(approval.approval_id);
                  }
                }}
              >
                <ApprovalCard
                  approval={approval}
                  actionPending={isBusy}
                  onApprove={() =>
                    respondMutation.mutate({ approvalId: approval.approval_id, responseKind: "approve" })
                  }
                  onReject={() =>
                    respondMutation.mutate({ approvalId: approval.approval_id, responseKind: "reject" })
                  }
                  onRequestInfo={() =>
                    respondMutation.mutate({
                      approvalId: approval.approval_id,
                      responseKind: "request_changes"
                    })
                  }
                  onUpload={(file) =>
                    uploadAttachmentMutation.mutate({
                      approvalId: approval.approval_id,
                      file
                    })
                  }
                  onDownload={() => downloadAttachmentMutation.mutate(approval.approval_id)}
                  onDetails={() =>
                    open({
                      title: `${approval.approval_kind} ${approval.scope_ref}`,
                      subtitle: approval.approval_id,
                      description: "Approval packet details stay in the drawer.",
                      fields: [
                        { label: "State", value: approval.state },
                        { label: "Required role", value: approval.required_role },
                        { label: "Requested at", value: approval.requested_at }
                      ]
                    })
                  }
                />
              </div>
            );
          })}
        </div>
      </div>

      <div className="review-workspace">
        <h3>Review Workspace</h3>
        {selectedApproval ? (
          <>
            <p>
              Selected approval: <strong>{selectedApproval.approval_id}</strong>
            </p>
            <div className="inline-controls" role="group" aria-label="Approval actions">
              <button
                type="button"
                className="action-btn action-btn--positive"
                onClick={() =>
                  respondMutation.mutate({
                    approvalId: selectedApproval.approval_id,
                    responseKind: "approve"
                  })
                }
              >
                Approve
              </button>
              <button
                type="button"
                className="action-btn action-btn--negative"
                onClick={() =>
                  respondMutation.mutate({
                    approvalId: selectedApproval.approval_id,
                    responseKind: "reject"
                  })
                }
              >
                Reject
              </button>
              <button
                type="button"
                className="action-btn"
                onClick={() =>
                  respondMutation.mutate({
                    approvalId: selectedApproval.approval_id,
                    responseKind: "request_changes"
                  })
                }
              >
                Request More Info
              </button>
            </div>
          </>
        ) : (
          <p>No approvals found.</p>
        )}
        <h4>Evidence Placeholder</h4>
        {detailQuery.isLoading ? <p>Loading artifact metadata...</p> : null}
        {detailQuery.isError ? <p>{errorText(detailQuery.error, "Unable to load run detail")}</p> : null}
        {detailQuery.data ? (
          <ul>
            {detailQuery.data.artifact_versions.slice(0, 3).map((artifact) => (
              <li key={artifact.artifact_version_id}>{artifact.artifact_kind} · {artifact.artifact_version_id}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
