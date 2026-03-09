import { useQuery } from "@tanstack/react-query";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { LegacyScheduleNotice } from "@/components/LegacyScheduleNotice";
import { PointerCard } from "@/components/PointerCard";
import { StatePanel } from "@/components/StatePanel";
import { useShellFilters } from "@/app/useShellFilters";
import { pointersRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";

export function OfficialOutputsPage(): JSX.Element {
  const { filters } = useShellFilters();
  const { open } = useDrawer();

  const query = useQuery({
    queryKey: ["official-outputs", filters.workflowRunId],
    queryFn: () => pointersRepository.list({ workflowRunId: filters.workflowRunId }),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (query.isLoading) {
    return <StatePanel kind="loading" title="Loading official outputs" detail="Fetching pointer rows." />;
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Official outputs failed to load"
        detail={errorText(query.error, "Unable to load pointers")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const data = query.data ?? [];
  if (data.length === 0) {
    return <StatePanel kind="empty" title="No pointers found" detail="No official outputs in current scope." />;
  }

  return (
    <section>
      <LegacyScheduleNotice surface="Official outputs" />
      <h2>Official Outputs (Legacy Pointer List)</h2>
      <div className="stack-list">
        {data.map((pointer) => (
          <PointerCard
            key={pointer.pointer_key}
            pointer={pointer}
            onDetails={() =>
              open({
                title: pointer.pointer_key,
                subtitle: pointer.artifact_kind,
                description: "Pointer metadata and promotion chain.",
                fields: [
                  { label: "Version", value: pointer.artifact_version_id },
                  { label: "Generation", value: String(pointer.generation) },
                  { label: "Promotion reason", value: pointer.promotion_reason }
                ]
              })
            }
          />
        ))}
      </div>
    </section>
  );
}
