import { isApiClientError } from "@/lib/api/httpClient";

export function errorText(error: unknown, fallback: string): string {
  if (isApiClientError(error)) {
    return `${error.code}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}
