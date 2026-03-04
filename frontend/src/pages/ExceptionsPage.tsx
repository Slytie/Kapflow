import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { FlagCard } from "@/components/FlagCard";
import { StatePanel } from "@/components/StatePanel";
import { useShellFilters } from "@/app/useShellFilters";
import { flagsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";

export function ExceptionsPage(): JSX.Element {
  const queryClient = useQueryClient();
  const { filters } = useShellFilters();
  const { open } = useDrawer();

  const query = useQuery({
    queryKey: ["exceptions", filters.workflowRunId, filters.state, filters.severity],
    queryFn: () =>
      flagsRepository.list({
        workflowRunId: filters.workflowRunId,
        state: filters.state,
        severity: filters.severity
      }),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const refreshExceptions = (): void => {
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ["exceptions"] }),
      queryClient.invalidateQueries({ queryKey: ["board-view"] }),
      queryClient.invalidateQueries({ queryKey: ["run-detail"] })
    ]);
  };

  const uploadAttachmentMutation = useMutation({
    mutationFn: (payload: { flagId: string; file: File }) =>
      flagsRepository.uploadAttachment(payload.flagId, payload.file),
    onSuccess: refreshExceptions
  });

  const downloadAttachmentMutation = useMutation({
    mutationFn: (flagId: string) => flagsRepository.downloadLatestAttachment(flagId)
  });

  if (query.isLoading) {
    return <StatePanel kind="loading" title="Loading exceptions" detail="Fetching flag queue." />;
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Exception queue failed to load"
        detail={errorText(query.error, "Unable to load flag queue")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const data = query.data ?? [];
  if (data.length === 0) {
    return <StatePanel kind="empty" title="No exceptions in scope" detail="No flags matched current filters." />;
  }

  return (
    <section data-testid="exceptions-page">
      <h2>Exception Queue</h2>
      {uploadAttachmentMutation.isError || downloadAttachmentMutation.isError ? (
        <StatePanel
          kind="error"
          title="Attachment action failed"
          detail={errorText(
            uploadAttachmentMutation.error ?? downloadAttachmentMutation.error,
            "Unable to upload/download exception attachment"
          )}
        />
      ) : null}
      <div className="stack-list">
        {data.map((flag) => {
          const isBusy =
            (uploadAttachmentMutation.isPending &&
              uploadAttachmentMutation.variables?.flagId === flag.flag_id) ||
            (downloadAttachmentMutation.isPending &&
              downloadAttachmentMutation.variables === flag.flag_id);

          return (
            <FlagCard
              key={flag.flag_id}
              flag={flag}
              actionPending={isBusy}
              onUpload={(file) => uploadAttachmentMutation.mutate({ flagId: flag.flag_id, file })}
              onDownload={() => downloadAttachmentMutation.mutate(flag.flag_id)}
              onDetails={() =>
                open({
                  title: flag.summary,
                  subtitle: flag.flag_id,
                  description: "Exception review context.",
                  fields: [
                    { label: "Severity", value: flag.severity },
                    { label: "State", value: flag.state },
                    { label: "Workflow run", value: flag.workflow_run_id }
                  ]
                })
              }
            />
          );
        })}
      </div>
    </section>
  );
}
