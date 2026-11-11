import "server-only";

import { headers } from "next/headers";

import { ApiError } from "./api";

const SERVER_API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function serverApi<T>(path: string): Promise<T> {
  // Without these, every visitor's server render lands in the web container's
  // single rate-limit bucket and a busy page starts answering 500 once it empties.
  const incoming = await headers();
  const forwarded = incoming.get("x-forwarded-for");
  const requestHeaders = new Headers();
  if (forwarded) requestHeaders.set("x-forwarded-for", forwarded);
  if (process.env.API_KEY) requestHeaders.set("x-api-key", process.env.API_KEY);

  const response = await fetch(`${SERVER_API_URL}${path}`, {
    cache: "no-store",
    headers: requestHeaders,
  });
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
