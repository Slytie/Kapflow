function readEnv(name: string, fallback: string): string {
  const value = (import.meta.env as Record<string, string | undefined>)[name];
  if (!value || !value.trim()) {
    return fallback;
  }
  return value.trim();
}

function readEnvInt(name: string, fallback: number): number {
  const value = (import.meta.env as Record<string, string | undefined>)[name];
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed < 0) {
    return fallback;
  }
  return parsed;
}

const pollIntervalMs: number | false =
  import.meta.env.MODE === "test" ? false : readEnvInt("VITE_ONETRUTH_POLL_INTERVAL_MS", 15000);

interface ApiConfig {
  baseUrl: string;
  tenantId: string;
  domainId: string;
  actorId: string;
  actorType: string;
  actorRoles: string;
  pollIntervalMs: number | false;
}

export const apiConfig: ApiConfig = {
  baseUrl: readEnv("VITE_ONETRUTH_API_BASE_URL", "/api/v1"),
  tenantId: readEnv("VITE_ONETRUTH_TENANT_ID", "tenant-a"),
  domainId: readEnv("VITE_ONETRUTH_DOMAIN_ID", "domain-x"),
  actorId: readEnv("VITE_ONETRUTH_ACTOR_ID", "human:frontend-operator"),
  actorType: readEnv("VITE_ONETRUTH_ACTOR_TYPE", "human"),
  actorRoles: readEnv(
    "VITE_ONETRUTH_ACTOR_ROLES",
    "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  ),
  pollIntervalMs
};
