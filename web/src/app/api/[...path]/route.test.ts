import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { handler } from "./route";

const context = (path: string[]) => ({ params: Promise.resolve({ path }) });

type RequestOptions = {
  method?: string;
  body?: string;
  headers?: HeadersInit;
  cookie?: string;
};

function request(path: string, init: RequestOptions = {}) {
  const headers = new Headers(init.headers);
  if (init.cookie) headers.set("cookie", init.cookie);
  return new NextRequest(`http://localhost:3000${path}`, {
    method: init.method,
    body: init.body,
    headers,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("auth BFF", () => {
  it("sets an httpOnly refresh cookie and strips it from the body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ access_token: "access", refresh_token: "refresh", token_type: "bearer" }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    const response = await handler(
      request("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "a@b.test", password: "password123" }),
        headers: { "content-type": "application/json" },
      }),
      context(["v1", "auth", "login"]),
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      access_token: "access",
      token_type: "bearer",
    });
    const cookie = response.headers.get("set-cookie") ?? "";
    expect(cookie).toContain("letmegetin_refresh=refresh");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("SameSite=lax");
  });

  it("rejects a refresh without the cookie", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await handler(
      request("/api/v1/auth/refresh", { method: "POST" }),
      context(["v1", "auth", "refresh"]),
    );

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a cross-origin state change", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await handler(
      request("/api/v1/auth/login", {
        method: "POST",
        body: "{}",
        headers: { "content-type": "application/json", origin: "https://evil.test" },
      }),
      context(["v1", "auth", "login"]),
    );

    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("clears the cookie on logout", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    const response = await handler(
      request("/api/v1/auth/logout", { method: "POST", cookie: "letmegetin_refresh=refresh" }),
      context(["v1", "auth", "logout"]),
    );

    expect(response.status).toBe(204);
    expect(response.headers.get("set-cookie") ?? "").toContain("Max-Age=0");
  });
});
