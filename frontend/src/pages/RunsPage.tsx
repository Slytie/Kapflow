import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { QueueRow } from "@/components/QueueRow";
import { StatePanel } from "@/components/StatePanel";
import { useShellFilters } from "@/app/useShellFilters";
import { workflowRunsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";

export function RunsPage(): JSX.Element {
  const { filters } = useShellFilters();
  const { open } = useDrawer();

  const query = useQuery({
    queryKey: ["runs", filters.state],
    queryFn: () => workflowRunsRepository.list({ state: filters.state }),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (query.isLoading) {
    return <StatePanel kind="loading" title="Loading runs" detail="Fetching workflow runs." />;
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Workflow runs failed to load"
        detail={errorText(query.error, "Unable to load runs")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const data = query.data ?? [];
  if (data.length === 0) {
    return <StatePanel kind="empty" title="No runs in scope" detail="Try clearing state filters." />;
  }

  return (
    <section>
      <h2>Workflow Runs</h2>
      <div className="stack-list">
        {data.map((run) => (
          <div key={run.workflow_run_id}>
            <QueueRow
              title={`${run.workflow_id} · ${run.partition_key}`}
              subtitle={`Logical date ${run.logical_date}`}
              status={run.state}
              onDetails={() =>
                open({
                  title: run.workflow_run_id,
                  subtitle: run.workflow_id,
                  description: "Run summary details.",
                  fields: [
                    { label: "State", value: run.state },
                    { label: "Domain", value: run.domain_id },
                    { label: "Tenant", value: run.tenant_id }
                  ]
                })
              }
            />
            <Link className="link-button" to={`/runs/${run.workflow_run_id}`}>
              Open run detail
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
