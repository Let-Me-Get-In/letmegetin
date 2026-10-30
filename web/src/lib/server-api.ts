import "server-only";

import { ApiError } from "./api";

const SERVER_API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function serverApi<T>(path: string): Promise<T> {
  const response = await fetch(`${SERVER_API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    let detail = response.statusText || "Request failed";
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON error body: keep the status text.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}
