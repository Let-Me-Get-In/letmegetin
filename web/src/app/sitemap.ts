import type { MetadataRoute } from "next";

import { requestSite } from "@/lib/site";

// shortcut: the home page only; listing the 600k+ place records needs a slugs
// endpoint on the API, so it is a separate ticket rather than a blind crawl.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { url, indexable } = await requestSite();
  if (!indexable) return [];
  return [{ url, changeFrequency: "daily", priority: 1 }];
}
