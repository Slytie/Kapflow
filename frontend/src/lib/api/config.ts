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

export interface ApiRequestContext {
  baseUrl: string;
  pollIntervalMs: number | false;
}

interface ApiConfig extends ApiRequestContext {
  readonly tenantId: string;
  readonly domainId: string;
  readonly actorId: string;
  readonly actorType: string;
  readonly actorRoles: string;
}

export interface ApiRequestContextHeaders {
  tenantId: string;
  domainId: string;
  actorId: string;
  actorType: string;
  actorRoles: string;
}

const defaultHeaders: ApiRequestContextHeaders = {
  tenantId: readEnv("VITE_ONETRUTH_TENANT_ID", "tenant-a"),
  domainId: readEnv("VITE_ONETRUTH_DOMAIN_ID", "domain-x"),
  actorId: readEnv("VITE_ONETRUTH_ACTOR_ID", "human:frontend-operator"),
  actorType: readEnv("VITE_ONETRUTH_ACTOR_TYPE", "human"),
  actorRoles: readEnv(
    "VITE_ONETRUTH_ACTOR_ROLES",
    "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  )
};

let currentHeaders: ApiRequestContextHeaders = { ...defaultHeaders };
const listeners = new Set<() => void>();

function normalizeHeaders(headers: ApiRequestContextHeaders): ApiRequestContextHeaders {
  return {
    tenantId: headers.tenantId.trim(),
    domainId: headers.domainId.trim(),
    actorId: headers.actorId.trim(),
    actorType: headers.actorType.trim(),
    actorRoles: headers.actorRoles
      .split(",")
      .map((role) => role.trim())
      .filter(Boolean)
      .join(",")
  };
}

function notifyListeners(): void {
  listeners.forEach((listener) => listener());
}

function headersEqual(left: ApiRequestContextHeaders, right: ApiRequestContextHeaders): boolean {
  return (
    left.tenantId === right.tenantId &&
    left.domainId === right.domainId &&
    left.actorId === right.actorId &&
    left.actorType === right.actorType &&
    left.actorRoles === right.actorRoles
  );
}

export function getApiRequestContextHeaders(): ApiRequestContextHeaders {
  return { ...currentHeaders };
}

export function setApiRequestContextHeaders(next: ApiRequestContextHeaders): void {
  const normalized = normalizeHeaders(next);
  if (headersEqual(currentHeaders, normalized)) {
    return;
  }
  currentHeaders = normalized;
  notifyListeners();
}

export function subscribeApiRequestContextHeaders(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function resetApiRequestContextHeaders(): void {
  currentHeaders = { ...defaultHeaders };
  notifyListeners();
}

export const apiConfig: ApiConfig = {
  baseUrl: readEnv("VITE_ONETRUTH_API_BASE_URL", "/api/v1"),
  pollIntervalMs,
  get tenantId() {
    return currentHeaders.tenantId;
  },
  get domainId() {
    return currentHeaders.domainId;
  },
  get actorId() {
    return currentHeaders.actorId;
  },
  get actorType() {
    return currentHeaders.actorType;
  },
  get actorRoles() {
    return currentHeaders.actorRoles;
  }
};
