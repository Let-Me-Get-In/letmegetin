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
        <Link
          href="/"
          className="flex items-center gap-2.5 font-display text-xl font-semibold tracking-tight"
        >
          <svg viewBox="0 0 96 96" aria-hidden="true" className="h-[26px] w-[26px] text-accent">
            <path
              fill="currentColor"
              fillRule="evenodd"
              d="M22 24h52a12 12 0 0 1 12 12v40H10V36a12 12 0 0 1 12-12Zm-4 52V56a20 20 0 0 1 40 0v20H18Z"
            />
          </svg>
          <span>
            LetMeGet<span className="text-accent">In</span>
          </span>
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
