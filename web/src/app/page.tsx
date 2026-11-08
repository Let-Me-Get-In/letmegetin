import { cookies } from "next/headers";
import { Suspense } from "react";

import { SearchView } from "@/components/search/search-view";
import { LOCALE_COOKIE, parseLocale, t } from "@/lib/i18n";

export default async function HomePage() {
  // Same source of truth as the layout: the cookie decides the interface language,
  // so the server renders the first paint in the reader's language.
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);
  return (
    <Suspense fallback={<p className="text-sm text-muted">{t(locale, "searchLoading")}</p>}>
      <SearchView locale={locale} />
    </Suspense>
  );
}
