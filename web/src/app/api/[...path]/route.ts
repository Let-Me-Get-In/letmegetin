import { NextResponse, type NextRequest } from "next/server";

const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const REFRESH_COOKIE = "letmegetin_refresh";
const MAX_AGE = 60 * 60 * 24 * 30;

type Context = { params: Promise<{ path: string[] }> };

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export async function handler(request: NextRequest, context: Context) {
  const origin = request.headers.get("origin");
  if (
    request.method !== "GET" &&
    request.method !== "HEAD" &&
    origin !== null &&
    origin !== request.nextUrl.origin
  ) {
    return NextResponse.json({ detail: "Cross-origin request rejected" }, { status: 403 });
  }

  const { path } = await context.params;
  const route = path.join("/");
  const isLogin = route === "v1/auth/login";
  const isRefresh = route === "v1/auth/refresh";
  const isLogout = route === "v1/auth/logout";

  let body: string | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    body = await request.text();
  }

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const authorization = request.headers.get("authorization");
  if (authorization) headers.set("authorization", authorization);
  if (process.env.API_KEY) headers.set("x-api-key", process.env.API_KEY);

  if (isRefresh || isLogout) {
    const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
    if (!refresh) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }
    if (!headers.has("content-type")) headers.set("content-type", "application/json");
    body = JSON.stringify({ refresh_token: refresh });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/api/${route}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "API unavailable" }, { status: 502 });
  }

  const text = await upstream.text();

  if ((isLogin || isRefresh) && upstream.ok) {
    const data = JSON.parse(text) as {
      access_token?: string;
      token_type?: string;
      refresh_token?: string;
    };
    if (!data.access_token || !data.refresh_token) {
      return NextResponse.json({ detail: "Malformed token response" }, { status: 502 });
    }
    const response = NextResponse.json(
      { access_token: data.access_token, token_type: data.token_type ?? "bearer" },
      { status: upstream.status },
    );
    response.cookies.set(REFRESH_COOKIE, data.refresh_token, cookieOptions(MAX_AGE));
    return response;
  }

  if (isRefresh) {
    const response = new NextResponse(text, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
    response.cookies.set(REFRESH_COOKIE, "", cookieOptions(0));
    return response;
  }

  if (isLogout && upstream.ok) {
    const response = new NextResponse(null, { status: 204 });
    response.cookies.set(REFRESH_COOKIE, "", cookieOptions(0));
    return response;
  }

  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}

export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE };
