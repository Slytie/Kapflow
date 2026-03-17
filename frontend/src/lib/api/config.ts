import type { RequestContextMode, ViewerSession } from "@/lib/types/contracts";

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

export interface ApiConfig extends ApiRequestContext {
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
let currentViewerSession: ViewerSession | null = null;
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

function normalizeViewerSession(session: ViewerSession): ViewerSession {
  return {
    tenant_id: session.tenant_id.trim(),
    domain_id: session.domain_id.trim(),
    actor_id: session.actor_id.trim(),
    actor_type: session.actor_type.trim(),
    actor_roles: session.actor_roles
      .map((role) => role.trim())
      .filter(Boolean),
    boundary_profile: session.boundary_profile,
    request_context_mode: session.request_context_mode,
    actor_switching_allowed: session.actor_switching_allowed
  };
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

function viewerSessionsEqual(left: ViewerSession | null, right: ViewerSession | null): boolean {
  if (left === right) {
    return true;
  }
  if (!left || !right) {
    return false;
  }
  return (
    left.tenant_id === right.tenant_id &&
    left.domain_id === right.domain_id &&
    left.actor_id === right.actor_id &&
    left.actor_type === right.actor_type &&
    left.boundary_profile === right.boundary_profile &&
    left.request_context_mode === right.request_context_mode &&
    left.actor_switching_allowed === right.actor_switching_allowed &&
    left.actor_roles.join(",") === right.actor_roles.join(",")
  );
}

function currentIdentitySource(): ViewerSession | ApiRequestContextHeaders {
  return currentViewerSession ?? currentHeaders;
}

function currentTenantId(): string {
  const source = currentIdentitySource();
  return "tenant_id" in source ? source.tenant_id : source.tenantId;
}

function currentDomainId(): string {
  const source = currentIdentitySource();
  return "domain_id" in source ? source.domain_id : source.domainId;
}

function currentActorId(): string {
  const source = currentIdentitySource();
  return "actor_id" in source ? source.actor_id : source.actorId;
}

function currentActorType(): string {
  const source = currentIdentitySource();
  return "actor_type" in source ? source.actor_type : source.actorType;
}

function currentActorRoles(): string {
  const source = currentIdentitySource();
  return "actor_roles" in source ? source.actor_roles.join(",") : source.actorRoles;
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

export function getApiViewerSession(): ViewerSession | null {
  if (!currentViewerSession) {
    return null;
  }
  return {
    ...currentViewerSession,
    actor_roles: [...currentViewerSession.actor_roles]
  };
}

export function setApiViewerSession(next: ViewerSession | null): void {
  const normalized = next ? normalizeViewerSession(next) : null;
  if (viewerSessionsEqual(currentViewerSession, normalized)) {
    return;
  }
  currentViewerSession = normalized;
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

export function resetApiViewerSession(): void {
  currentViewerSession = null;
  notifyListeners();
}

export function requestContextMode(): RequestContextMode | null {
  return currentViewerSession?.request_context_mode ?? null;
}

export function requestContextHeadersForPath(path: string): Record<string, string> {
  const shouldSendTrustedHeaders =
    path === "/viewer" ||
    currentViewerSession === null ||
    currentViewerSession.request_context_mode === "trusted_headers";
  if (!shouldSendTrustedHeaders) {
    return {};
  }
  return {
    "x-onetruth-tenant-id": currentHeaders.tenantId,
    "x-onetruth-domain-id": currentHeaders.domainId,
    "x-onetruth-actor-id": currentHeaders.actorId,
    "x-onetruth-actor-type": currentHeaders.actorType,
    "x-onetruth-actor-roles": currentHeaders.actorRoles
  };
}

export const apiConfig: ApiConfig = {
  baseUrl: readEnv("VITE_ONETRUTH_API_BASE_URL", "/api/v1"),
  pollIntervalMs,
  get tenantId() {
    return currentTenantId();
  },
  get domainId() {
    return currentDomainId();
  },
  get actorId() {
    return currentActorId();
  },
  get actorType() {
    return currentActorType();
  },
  get actorRoles() {
    return currentActorRoles();
  }
};
