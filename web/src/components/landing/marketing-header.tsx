import { LocaleSwitch } from "@/components/locale-switch";
import { Wordmark } from "@/components/landing/wordmark";
import { t, type Locale } from "@/lib/i18n";

export function MarketingHeader({ locale, appUrl }: { locale: Locale; appUrl: string }) {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-4">
        <Wordmark />
        <nav
          aria-label={locale === "en" ? "Main navigation" : "Navigation principale"}
          className="flex items-center gap-x-4 gap-y-2 text-sm"
        >
          <div className="hidden items-center gap-x-5 sm:flex">
            <a className="hover:text-accent" href="#donnees">
              {t(locale, "landingNavData")}
            </a>
            <a className="hover:text-accent" href="#api">
              {t(locale, "landingNavApi")}
            </a>
            <a className="hover:text-accent" href="#a-propos">
              {t(locale, "landingNavAbout")}
            </a>
          </div>
          <LocaleSwitch locale={locale} label={t(locale, "language")} />
          <a
            className="hidden rounded-md bg-accent px-3 py-1.5 text-paper hover:opacity-90 sm:inline-flex"
            href={appUrl}
          >
            {t(locale, "landingOpenApp")}
          </a>
        </nav>
      </div>
    </header>
  );
}
