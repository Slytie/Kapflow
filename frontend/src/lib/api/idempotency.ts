function randomToken(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createIdempotencyKey(prefix: string, resourceId: string): string {
  return `frontend:${prefix}:${resourceId}:${randomToken()}`;
}
