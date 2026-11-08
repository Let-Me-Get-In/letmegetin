import type { Metadata } from "next";
import { cookies } from "next/headers";

import { RegisterForm } from "@/components/auth/register-form";
import { LOCALE_COOKIE, parseLocale, t } from "@/lib/i18n";

export const metadata: Metadata = { title: "Créer un compte — LetMeGetIn" };

export default async function RegisterPage() {
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);
  return (
    <section className="mx-auto max-w-md py-8">
      <h1 className="text-3xl font-semibold">{t(locale, "createAccountLink")}</h1>
      <p className="mb-6 mt-2 text-sm text-muted">{t(locale, "registerFolderIntro")}</p>
      <RegisterForm locale={locale} />
    </section>
  );
}
