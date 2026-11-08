import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Suspense } from "react";

import { VerifyEmail } from "@/components/auth/verify-email";
import { LOCALE_COOKIE, parseLocale, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "Vérification de l'email — LetMeGetIn" };

export default async function VerifyPage() {
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);
  return (
    <section className="mx-auto max-w-md py-8">
      <h1 className="text-3xl font-semibold">{t(locale, "verifyHeading")}</h1>
      <p className="mb-6 mt-2 text-sm text-muted">{t(locale, "verifyFolderIntro")}</p>
      <Suspense fallback={<p className="text-sm text-muted">{t(locale, "verifying")}</p>}>
        <VerifyEmail locale={locale} />
      </Suspense>
    </section>
  );
}
