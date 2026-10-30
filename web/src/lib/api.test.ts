import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/lib/api";

function mockFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api", () => {
  it("parses a JSON response", async () => {
    mockFetch(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await expect(api<{ ok: boolean }>("/api/v1/health")).resolves.toEqual({ ok: true });
  });

  it("returns undefined for 204", async () => {
    mockFetch(new Response(null, { status: 204 }));

    await expect(api("/api/v1/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });

  it("raises an ApiError with the API detail", async () => {
    mockFetch(
      new Response(JSON.stringify({ detail: "Place not found" }), { status: 404 }),
    );

    await expect(api("/api/v1/places/nope")).rejects.toMatchObject({
      status: 404,
      message: "Place not found",
    });
  });

  it("attaches the bearer token", async () => {
    const fetchMock = mockFetch(new Response("{}", { status: 200 }));

    await api("/api/v1/auth/me", {}, "token-123");

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer token-123");
  });

  it("keeps the status when the body is not JSON", async () => {
    mockFetch(new Response("Bad gateway", { status: 502 }));

    await expect(api("/api/v1/places")).rejects.toBeInstanceOf(ApiError);
  });
});
