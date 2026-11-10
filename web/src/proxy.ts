import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const APEX_HOSTS = new Set(["letmegetin.org", "www.letmegetin.org"]);

// The apex hosts the public landing page; the app keeps `/` on its own host.
// A request header tells the root layout which chrome to render, so the landing
// can stay full-bleed while the app keeps its max-width shell.
export function proxy(request: NextRequest) {
  const host = (request.headers.get("host") ?? "").split(":")[0].toLowerCase();
  const { pathname, search } = request.nextUrl;

  if (pathname === "/landing") {
    const headers = new Headers(request.headers);
    headers.set("x-lmgi-surface", "marketing");
    return NextResponse.next({ request: { headers } });
  }

  if (!APEX_HOSTS.has(host)) return NextResponse.next();

  if (host === "www.letmegetin.org") {
    return NextResponse.redirect(new URL(`https://letmegetin.org${pathname}${search}`), 301);
  }

  if (pathname === "/") {
    const url = request.nextUrl.clone();
    url.pathname = "/landing";
    const headers = new Headers(request.headers);
    headers.set("x-lmgi-surface", "marketing");
    return NextResponse.rewrite(url, { request: { headers } });
  }

  // Every app route on the apex belongs to the app host; keep shared links working.
  return NextResponse.redirect(new URL(`https://app.letmegetin.org${pathname}${search}`), 301);
}

export const config = {
  matcher: ["/", "/landing", "/places/:path*", "/account/:path*", "/login", "/register", "/verify"],
};
