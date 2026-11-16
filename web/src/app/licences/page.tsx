import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";

import { LOCALE_COOKIE, parseLocale, t } from "@/lib/i18n";

const GITHUB_URL = "https://github.com/Let-Me-Get-In/letmegetin";
const ACCESLIBRE_URL = "https://acceslibre.beta.gouv.fr";
const OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright";
const OVERTURE_URL = "https://overturemaps.org";

export async function generateMetadata(): Promise<Metadata> {
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);
  return {
    title: t(locale, "licencesTitle"),
    description: t(locale, "licencesIntro"),
    alternates: { canonical: "/licences" },
  };
}

export default async function LicencesPage() {
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);

  return (
    <main className="mx-auto max-w-3xl px-4 py-16 sm:py-24">
      <h1 className="font-display text-4xl tracking-tight sm:text-5xl">
        {t(locale, "licencesTitle")}
      </h1>
      <p className="mt-6 text-base leading-relaxed text-ink">{t(locale, "licencesIntro")}</p>

      <dl className="mt-12 space-y-8">
        <div>
          <dt className="font-display text-xl">
            Acceslibre
            <span className="ml-2 font-sans text-sm font-normal text-muted">
              Licence Ouverte 2.0
            </span>
          </dt>
          <dd className="mt-2 text-base leading-relaxed">
            {t(locale, "licencesAcceslibreBody")}{" "}
            <a className="underline underline-offset-4 hover:text-accent" href={ACCESLIBRE_URL}>
              acceslibre.beta.gouv.fr
            </a>
          </dd>
        </div>

        <div>
          <dt className="font-display text-xl">
            OpenStreetMap
            <span className="ml-2 font-sans text-sm font-normal text-muted">ODbL 1.0</span>
          </dt>
          <dd className="mt-2 text-base leading-relaxed">
            {t(locale, "licencesOsmBody")}{" "}
            <a
              className="underline underline-offset-4 hover:text-accent"
              href={OSM_COPYRIGHT_URL}
            >
              openstreetmap.org/copyright
            </a>
          </dd>
        </div>

        <div>
          <dt className="font-display text-xl">
            Overture
            <span className="ml-2 font-sans text-sm font-normal text-muted">
              CDLA-Permissive-2.0
            </span>
          </dt>
          <dd className="mt-2 text-base leading-relaxed">
            {t(locale, "licencesOvertureBody")}{" "}
            <a className="underline underline-offset-4 hover:text-accent" href={OVERTURE_URL}>
              overturemaps.org
            </a>
          </dd>
        </div>

        <div>
          <dt className="font-display text-xl">
            {t(locale, "licencesContributionTitle")}
            <span className="ml-2 font-sans text-sm font-normal text-muted">
              {t(locale, "licencesContributionLicence")}
            </span>
          </dt>
          <dd className="mt-2 text-base leading-relaxed">
            {t(locale, "licencesContributionBody")}
          </dd>
        </div>

        <div>
          <dt className="font-display text-xl">
            {t(locale, "licencesCodeTitle")}
            <span className="ml-2 font-sans text-sm font-normal text-muted">AGPL-3.0</span>
          </dt>
          <dd className="mt-2 text-base leading-relaxed">
            {t(locale, "licencesCodeBody")}{" "}
            <a className="underline underline-offset-4 hover:text-accent" href={GITHUB_URL}>
              github.com/Let-Me-Get-In/letmegetin
            </a>
          </dd>
        </div>
      </dl>

      <section className="mt-16 border-t border-line pt-8">
        <h2 className="font-display text-2xl">{t(locale, "licencesDirectionTitle")}</h2>
        <p className="mt-4 text-base leading-relaxed">{t(locale, "licencesDirectionBody")}</p>
      </section>

      <p className="mt-12 text-sm">
        <Link className="underline underline-offset-4 hover:text-accent" href="/">
          {t(locale, "licencesBack")}
        </Link>
      </p>
    </main>
  );
}
