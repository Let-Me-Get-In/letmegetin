"use client";

import Link from "next/link";

import { LocaleSwitch } from "@/components/locale-switch";
import { t, type Locale } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export function SiteHeader({ locale }: { locale: Locale }) {
  const { user, loading, logout } = useSession();

  return (
    <header className="border-b border-line bg-paper/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
        <Link href="/" className="font-display text-xl font-semibold tracking-tight">
          Let<span className="text-accent">Me</span>GetIn
        </Link>
        <nav
          aria-label={locale === "en" ? "Main navigation" : "Navigation principale"}
          className="flex items-center gap-4 text-sm"
        >
          <Link className="hover:text-accent" href="/">
            {t(locale, "search")}
          </Link>
          {loading ? (
            <span className="text-muted" aria-hidden="true">
              …
            </span>
          ) : user ? (
            <>
              <Link className="hover:text-accent" href="/account">
                {t(locale, "account")}
              </Link>
              <button
                type="button"
                className="rounded-md border border-line px-3 py-1.5 hover:border-accent hover:text-accent"
                onClick={() => void logout()}
              >
                {t(locale, "logout")}
              </button>
            </>
          ) : (
            <Link
              className="rounded-md bg-accent px-3 py-1.5 text-paper hover:opacity-90"
              href="/login"
            >
              {t(locale, "login")}
            </Link>
          )}
          <LocaleSwitch locale={locale} label={t(locale, "language")} />
        </nav>
      </div>
    </header>
  );
}
