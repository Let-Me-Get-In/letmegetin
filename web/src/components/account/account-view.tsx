"use client";

import Link from "next/link";

import { RequireAuth } from "@/components/auth/require-auth";
import { VerifyBanner } from "@/components/auth/verify-banner";
import { t, type Locale } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export function AccountView({ locale }: { locale: Locale }) {
  const { user, logout } = useSession();

  return (
    <RequireAuth locale={locale}>
      <section className="mx-auto max-w-2xl space-y-6 py-8">
        <div>
          <h1 className="text-3xl font-semibold">{t(locale, "account")}</h1>
          <p className="mt-2 text-sm text-muted">{t(locale, "accountFolderIntro")}</p>
        </div>

        <VerifyBanner locale={locale} />

        <dl className="divide-y divide-line rounded-card border border-line bg-white/60 dark:bg-white/5">
          <div className="flex flex-wrap justify-between gap-2 px-4 py-3">
            <dt className="text-sm text-muted">{t(locale, "emailLabel")}</dt>
            <dd className="font-medium">{user?.email}</dd>
          </div>
          <div className="flex flex-wrap justify-between gap-2 px-4 py-3">
            <dt className="text-sm text-muted">{t(locale, "displayNameLabel")}</dt>
            <dd className="font-medium">{user?.display_name ?? t(locale, "anonymous")}</dd>
          </div>
          <div className="flex flex-wrap justify-between gap-2 px-4 py-3">
            <dt className="text-sm text-muted">{t(locale, "emailVerifiedLabel")}</dt>
            <dd className="font-medium">{user?.email_verified ? t(locale, "yes") : t(locale, "no")}</dd>
          </div>
          <div className="flex flex-wrap justify-between gap-2 px-4 py-3">
            <dt className="text-sm text-muted">{t(locale, "roleLabel")}</dt>
            <dd className="font-medium">{user?.role}</dd>
          </div>
        </dl>

        <div className="flex flex-wrap gap-3">
          <Link className="rounded-md border border-line px-4 py-2 text-sm" href="/">
            {t(locale, "searchLink")}
          </Link>
          <button
            type="button"
            className="rounded-md border border-warn px-4 py-2 text-sm text-warn"
            onClick={() => void logout()}
          >
            {t(locale, "signOut")}
          </button>
        </div>
      </section>
    </RequireAuth>
  );
}
