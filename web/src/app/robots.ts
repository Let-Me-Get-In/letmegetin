import type { MetadataRoute } from "next";

import { requestSite } from "@/lib/site";

// Reading the request headers keeps this route dynamic: the same build serves
// production (indexable) and dev (blocked) without a rebuild.
export default async function robots(): Promise<MetadataRoute.Robots> {
  const { url, indexable } = await requestSite();

  if (!indexable) {
    return { rules: { userAgent: "*", disallow: "/" } };
  }

  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/account", "/login", "/register", "/verify"],
    },
    sitemap: `${url}/sitemap.xml`,
  };
}
