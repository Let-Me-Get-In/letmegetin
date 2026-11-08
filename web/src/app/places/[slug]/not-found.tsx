import { cookies } from "next/headers";
import Link from "next/link";

import { LOCALE_COOKIE, parseLocale, t } from "@/lib/i18n";

export default async function PlaceNotFound() {
  // Same cookie as the page tree: the 404 speaks the reader's language.
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);

  return (
    <section className="mx-auto max-w-xl py-16 text-center">
      <h1 className="text-3xl font-semibold">{t(locale, "placeNotFoundTitle")}</h1>
      <p className="mt-3 text-muted">{t(locale, "placeNotFoundBody")}</p>
      <Link
        href="/"
        className="mt-6 inline-block rounded-md bg-accent px-4 py-2 font-medium text-paper"
      >
        {t(locale, "backToSearchPlain")}
      </Link>
    </section>
  );
}
