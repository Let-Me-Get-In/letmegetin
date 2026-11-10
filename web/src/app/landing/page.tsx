import type { Metadata } from "next";
import { cookies } from "next/headers";

import { LandingPage } from "@/components/landing/landing-page";
import { LOCALE_COOKIE, parseLocale, t } from "@/lib/i18n";
import { requestSite } from "@/lib/site";

export async function generateMetadata(): Promise<Metadata> {
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);
  const title = "LetMeGetIn — l'accessibilité des lieux, pour de vrai";
  const { url, indexable } = await requestSite();
  const host = new URL(url).host;
  const isApex = host === "letmegetin.org" || host === "www.letmegetin.org";
  const description = t(locale, "landingHeroIntro");
  const canonical = isApex ? "/" : indexable ? "https://letmegetin.org/" : "/landing";

  return {
    title: { absolute: title },
    description,
    alternates: { canonical },
    openGraph: {
      type: "website",
      url: canonical,
      title,
      description,
      siteName: "LetMeGetIn",
      locale: locale === "en" ? "en_GB" : "fr_FR",
    },
    twitter: { card: "summary_large_image", title, description },
    // The landing is canonical on the apex only. Served on the app host for
    // previews, it must not compete with the apex page in search results.
    robots: { index: indexable && isApex, follow: true },
  };
}

export default async function Page() {
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);
  const { url, indexable } = await requestSite();
  const appUrl = indexable ? "https://app.letmegetin.org" : url;
  const apiUrl = indexable ? "https://api.letmegetin.org" : "https://api.dev.letmegetin.org";

  return <LandingPage locale={locale} appUrl={appUrl} apiUrl={apiUrl} />;
}
