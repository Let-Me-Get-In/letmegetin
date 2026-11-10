import "server-only";

import { headers } from "next/headers";

import { isIndexableHost } from "./seo";

// Caddy terminates TLS and forwards Host + X-Forwarded-Proto, so the metadata
// routes can build absolute URLs without baking a domain into the image.
export async function requestSite(): Promise<{ url: string; indexable: boolean }> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("host") ?? "localhost:3000";
  const proto = requestHeaders.get("x-forwarded-proto")?.split(",")[0].trim() || "http";
  return { url: `${proto}://${host}`, indexable: isIndexableHost(host) };
}
