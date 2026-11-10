import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/login-form";
import { LOCALE_COOKIE, parseLocale, t } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "Connexion",
  robots: { index: false, follow: false },
};

export default async function LoginPage() {
  // Same source of truth as the layout: the cookie decides the interface language,
  // so the server renders the first paint in the reader's language.
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);
  return (
    <section className="mx-auto max-w-md py-8">
      <h1 className="text-3xl font-semibold">{t(locale, "login")}</h1>
      <p className="mb-6 mt-2 text-sm text-muted">{t(locale, "loginFolderIntro")}</p>
      <Suspense fallback={<p className="text-sm text-muted">{t(locale, "loading")}</p>}>
        <LoginForm locale={locale} />
      </Suspense>
    </section>
  );
}
