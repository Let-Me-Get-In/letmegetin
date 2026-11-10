import { Wordmark } from "@/components/landing/wordmark";
import { t, type Locale } from "@/lib/i18n";

const GITHUB_URL = "https://github.com/Let-Me-Get-In/letmegetin";
const CONTACT_EMAIL = "contact@letmegetin.org";

export function MarketingFooter({ locale, appUrl }: { locale: Locale; appUrl: string }) {
  return (
    <footer id="a-propos" className="border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <Wordmark />
          <p className="mt-4 max-w-sm font-display text-2xl leading-snug">
            {t(locale, "landingFooterTagline")}
          </p>
          <p className="mt-3 max-w-md text-sm text-muted">{t(locale, "landingFooterNote")}</p>
        </div>
        <nav
          aria-label={locale === "en" ? "Footer navigation" : "Navigation de pied de page"}
          className="grid content-start gap-2 text-sm sm:justify-self-end"
        >
          <a className="hover:text-accent" href={`mailto:${CONTACT_EMAIL}`}>
            {t(locale, "landingFooterContact")} — {CONTACT_EMAIL}
          </a>
          <a
            className="hover:text-accent"
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
          >
            {t(locale, "landingFooterSource")}
          </a>
          <a className="hover:text-accent" href="#donnees">
            {t(locale, "landingFooterLicences")}
          </a>
          <a className="hover:text-accent" href={appUrl}>
            {t(locale, "landingFooterApp")}
          </a>
          <a className="hover:text-accent" href="#contenu">
            {t(locale, "landingBackToTop")}
          </a>
        </nav>
      </div>
    </footer>
  );
}
