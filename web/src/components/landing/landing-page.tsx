import {
  ArrowIcon,
  CheckIcon,
  CodeIcon,
  EntranceIcon,
  LoopIcon,
  SearchIcon,
  StaffIcon,
  ToiletIcon,
} from "@/components/landing/icons";
import { t, type Locale } from "@/lib/i18n";

const GITHUB_URL = "https://github.com/Let-Me-Get-In/letmegetin";
const CONTACT_EMAIL = "contact@letmegetin.org";
const PLACES = 634_931;
const CATEGORIES = 158;
const CRITERIA = 182;

function formatNumber(locale: Locale, value: number) {
  return new Intl.NumberFormat(locale === "en" ? "en-GB" : "fr-FR").format(value);
}

const SAMPLE_CRITERIA = [
  { key: "landingExampleEntrance", Icon: EntranceIcon },
  { key: "landingExampleToilets", Icon: ToiletIcon },
  { key: "landingExampleLoop", Icon: LoopIcon },
  { key: "landingExampleStaff", Icon: StaffIcon },
] as const;

const FAMILIES = [
  { key: "familyMoteur", body: "landingPromiseMoteur" },
  { key: "familyAuditif", body: "landingPromiseAuditif" },
  { key: "familyVisuel", body: "landingPromiseVisuel" },
  { key: "familyMental", body: "landingPromiseMental" },
] as const;

export function LandingPage({
  locale,
  appUrl,
  apiUrl,
}: {
  locale: Locale;
  appUrl: string;
  apiUrl: string;
}) {
  return (
    <div className="bg-paper">
      <section aria-labelledby="landing-title" className="border-b border-line">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 pb-14 pt-12 lg:grid-cols-[1.05fr_0.95fr] lg:items-start lg:gap-16 lg:pb-20 lg:pt-20">
          <div>
            <h1
              id="landing-title"
              className="landing-rise max-w-[13ch] font-display text-[clamp(2.7rem,6vw,5rem)] font-semibold leading-[0.97] tracking-[-0.035em]"
            >
              {t(locale, "landingHeroTitle")}
            </h1>
            <p className="landing-rise landing-rise-1 mt-6 max-w-[54ch] text-lg leading-relaxed text-muted">
              {t(locale, "landingHeroIntro")}
            </p>

            <form
              role="search"
              action={appUrl}
              method="get"
              className="landing-rise landing-rise-2 mt-8"
            >
              <label htmlFor="landing-q" className="sr-only">
                {t(locale, "landingSearchLabel")}
              </label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <div className="relative min-w-0 flex-1">
                  <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" />
                  <input
                    id="landing-q"
                    name="q"
                    type="search"
                    required
                    placeholder={t(locale, "landingSearchPlaceholder")}
                    className="w-full rounded-md border border-line bg-paper py-3.5 pl-12 pr-4 text-base text-ink placeholder:text-muted focus:border-accent"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded-md bg-accent px-6 py-3.5 text-base font-medium text-paper hover:opacity-90"
                >
                  {t(locale, "landingSearchSubmit")}
                </button>
              </div>
              <input type="hidden" name="lat" value="48.8566" />
              <input type="hidden" name="lng" value="2.3522" />
              <input type="hidden" name="radius" value="2000" />
              <p className="mt-3 text-sm text-muted">{t(locale, "landingSearchHint")}</p>
            </form>

            <p className="landing-rise landing-rise-3 mt-8 flex items-center gap-2 text-sm text-muted">
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-accent" />
              {t(locale, "landingTrust")}
            </p>
          </div>

          <div className="landing-rise landing-rise-2 lg:pl-4">
            <div className="border border-line bg-paper shadow-[0_18px_45px_-32px_rgba(24,33,28,0.55)]">
              <div className="flex items-center justify-between gap-4 border-b border-line px-5 py-3 text-[0.7rem] font-medium uppercase tracking-[0.16em] text-muted">
                <span>{t(locale, "landingExampleBadge")}</span>
                <span aria-hidden="true">LetMeGetIn</span>
              </div>
              <div className="p-5 sm:p-7">
                <h2 className="font-display text-3xl font-semibold">
                  {t(locale, "landingExampleName")}
                </h2>
                <p className="mt-1 text-sm text-muted">{t(locale, "landingExampleAddress")}</p>

                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-accent-soft px-3 py-1 text-sm font-medium text-accent">
                    <CheckIcon className="h-4 w-4" />
                    {t(locale, "landingExampleStatus")}
                  </span>
                  <span className="text-sm text-muted">{t(locale, "landingExampleMeta")}</span>
                </div>

                <ul className="mt-5 border-t border-line">
                  {SAMPLE_CRITERIA.map(({ key, Icon }) => (
                    <li
                      key={key}
                      className="flex items-center gap-3 border-b border-line py-3 text-sm"
                    >
                      <Icon className="h-5 w-5 shrink-0 text-accent" />
                      <span>{t(locale, key)}</span>
                      <CheckIcon className="ml-auto h-4 w-4 shrink-0 text-accent" />
                    </li>
                  ))}
                </ul>

                <a
                  className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-accent underline underline-offset-4 hover:text-ink"
                  href={`${appUrl}/?q=caf%C3%A9`}
                >
                  {t(locale, "landingExampleLink")}
                  <ArrowIcon className="h-4 w-4" />
                </a>
              </div>
            </div>
          </div>
        </div>

        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-4 text-[0.7rem] uppercase tracking-[0.16em] text-muted">
          <span>{t(locale, "landingDataSourcesValue")}</span>
          <span>{t(locale, "landingDataPlaces")} · {formatNumber(locale, PLACES)}</span>
        </div>
      </section>

      <section aria-labelledby="promise-title" className="mx-auto max-w-6xl px-4 py-16 sm:py-24">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-16">
          <div className="self-start lg:sticky lg:top-8">
            <h2
              id="promise-title"
              className="max-w-[14ch] font-display text-4xl font-semibold leading-[1.02] tracking-[-0.02em] sm:text-5xl"
            >
              {t(locale, "landingPromiseTitle")}
            </h2>
            <p className="mt-5 max-w-[46ch] text-base leading-relaxed text-muted">
              {t(locale, "landingPromiseIntro")}
            </p>
          </div>

          <dl className="border-t border-line">
            {FAMILIES.map(({ key, body }) => (
              <div
                key={key}
                className="grid gap-2 border-b border-line py-5 sm:grid-cols-[10rem_1fr] sm:gap-6"
              >
                <dt className="font-medium">{t(locale, key)}</dt>
                <dd className="text-muted">{t(locale, body)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section
        id="donnees"
        aria-labelledby="data-title"
        className="scroll-mt-8 border-y border-line bg-accent-soft/40"
      >
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16 lg:py-20">
          <div>
            <h2
              id="data-title"
              className="max-w-[15ch] font-display text-4xl font-semibold leading-[1.02] tracking-[-0.02em] sm:text-5xl"
            >
              {t(locale, "landingDataTitle")}
            </h2>
            <p className="mt-5 max-w-[52ch] text-base leading-relaxed text-muted">
              {t(locale, "landingDataIntro")}
            </p>
          </div>

          <div>
            <dl className="divide-y divide-line border-y border-line">
              <div className="flex items-baseline justify-between gap-6 py-4">
                <dt className="text-sm text-muted">{t(locale, "landingDataPlaces")}</dt>
                <dd className="font-display text-4xl font-semibold tabular-nums">
                  {formatNumber(locale, PLACES)}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-6 py-4">
                <dt className="text-sm text-muted">{t(locale, "landingDataCategories")}</dt>
                <dd className="font-display text-4xl font-semibold tabular-nums">
                  {formatNumber(locale, CATEGORIES)}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-6 py-4">
                <dt className="text-sm text-muted">{t(locale, "landingDataCriteria")}</dt>
                <dd className="font-display text-4xl font-semibold tabular-nums">
                  {formatNumber(locale, CRITERIA)}
                </dd>
              </div>
            </dl>

            <dl className="mt-8 grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-[0.7rem] uppercase tracking-[0.16em] text-muted">
                  {t(locale, "landingDataSources")}
                </dt>
                <dd className="mt-1">{t(locale, "landingDataSourcesValue")}</dd>
              </div>
              <div>
                <dt className="text-[0.7rem] uppercase tracking-[0.16em] text-muted">
                  {t(locale, "landingDataLicences")}
                </dt>
                <dd className="mt-1">{t(locale, "landingDataLicencesValue")}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-[0.7rem] uppercase tracking-[0.16em] text-muted">
                  {t(locale, "landingDataCode")}
                </dt>
                <dd className="mt-1">
                  <a
                    className="underline underline-offset-4 hover:text-accent"
                    href={GITHUB_URL}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t(locale, "landingDataCodeValue")}
                  </a>
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      <section id="api" aria-labelledby="api-title" className="scroll-mt-8 bg-ink text-paper">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16 lg:py-20">
          <div>
            <h2
              id="api-title"
              className="max-w-[13ch] font-display text-4xl font-semibold leading-[1.02] tracking-[-0.02em] sm:text-5xl"
            >
              {t(locale, "landingApiTitle")}
            </h2>
            <p className="mt-5 max-w-[48ch] text-base leading-relaxed text-paper/75">
              {t(locale, "landingApiIntro")}
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4 text-sm">
              <a
                className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 font-medium text-paper hover:opacity-90"
                href={`${apiUrl}/docs`}
              >
                {t(locale, "landingApiDocs")}
                <ArrowIcon className="h-4 w-4" />
              </a>
              <a
                className="inline-flex items-center gap-2 underline underline-offset-4 hover:text-accent"
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer"
              >
                <CodeIcon className="h-4 w-4" />
                {t(locale, "landingApiGithub")}
              </a>
            </div>
          </div>

          <div className="min-w-0 border border-paper/20 p-5 font-mono text-xs sm:p-6 sm:text-sm">
            <p className="text-paper/55">{t(locale, "landingApiExample")}</p>
            <pre className="mt-2 overflow-x-auto leading-relaxed">
              <code>{`GET /v1/places?lat=48.8566&lng=2.3522&radius=2000
Host: api.letmegetin.org
Accept: application/json`}</code>
            </pre>
            <p className="mt-6 text-paper/55">{t(locale, "landingApiResponse")}</p>
            <pre className="mt-2 overflow-x-auto leading-relaxed">
              <code>{`HTTP/2 200
{
  "name": "Cafe de quartier",
  "category": "cafe",
  "accessibility": {
    "entrance": "step_free",
    "toilets": "adapted"
  }
}`}</code>
            </pre>
          </div>
        </div>
      </section>

      <section aria-labelledby="contribute-title" className="mx-auto max-w-6xl px-4 py-16 sm:py-24">
        <div className="grid gap-8 border-y border-line py-12 lg:grid-cols-[1.2fr_0.8fr] lg:items-end lg:gap-16">
          <div>
            <h2
              id="contribute-title"
              className="max-w-[18ch] font-display text-4xl font-semibold leading-[1.02] tracking-[-0.02em] sm:text-5xl"
            >
              {t(locale, "landingContributeTitle")}
            </h2>
            <p className="mt-5 max-w-[58ch] text-base leading-relaxed text-muted">
              {t(locale, "landingContributeIntro")}
            </p>
          </div>
          <div className="lg:justify-self-end">
            <a
              className="inline-flex items-center gap-2 rounded-md bg-accent px-5 py-3 font-medium text-paper hover:opacity-90"
              href={`${appUrl}/login`}
            >
              {t(locale, "landingContributeCta")}
              <ArrowIcon className="h-4 w-4" />
            </a>
            <p className="mt-3 max-w-[34ch] text-sm text-muted">
              {t(locale, "landingContributeNote")}
            </p>
          </div>
        </div>
        <p className="mt-8 text-sm text-muted">
          <a className="underline underline-offset-4 hover:text-accent" href={`mailto:${CONTACT_EMAIL}`}>
            {t(locale, "landingFooterContact")} — {CONTACT_EMAIL}
          </a>
        </p>
      </section>
    </div>
  );
}
