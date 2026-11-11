import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({
  headers: async () => new Headers({ "x-forwarded-for": "203.0.113.7, 10.0.0.1" }),
}));

import { serverApi } from "@/lib/server-api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("serverApi", () => {
  it("forwards the client IP so the API buckets per visitor", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true })));
    vi.stubGlobal("fetch", fetchMock);

    await serverApi<{ ok: boolean }>("/api/v1/places/example");

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect((init.headers as Headers).get("x-forwarded-for")).toBe("203.0.113.7, 10.0.0.1");
  });

  it("sends the service API key when configured", async () => {
    vi.stubEnv("API_KEY", "service-key");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true })));
    vi.stubGlobal("fetch", fetchMock);

    await serverApi("/api/v1/places/example");

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect((init.headers as Headers).get("x-api-key")).toBe("service-key");
  });
});
