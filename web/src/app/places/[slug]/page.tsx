import type { Metadata, ResolvingMetadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";

import { VerifyBanner } from "@/components/auth/verify-banner";
import { AccessibilityTree } from "@/components/record/accessibility-tree";
import { ContributionForm } from "@/components/record/contribution-form";
import { PhotoGallery } from "@/components/record/photo-gallery";
import { ReviewForm } from "@/components/record/review-form";
import { ReviewList } from "@/components/record/review-list";
import { ApiError } from "@/lib/api";
import { LOCALE_COOKIE, format, parseLocale, t, tPlural } from "@/lib/i18n";
import { serverApi } from "@/lib/server-api";
import { familyLabel } from "@/lib/search";
import type { PlaceDetail, ReviewPage } from "@/lib/types";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
};

export async function generateMetadata(
  { params }: Pick<Props, "params">,
  parent: ResolvingMetadata,
): Promise<Metadata> {
  const { slug } = await params;
  try {
    const place = await serverApi<PlaceDetail>(`/api/v1/places/${slug}`);
    const where = [place.category, place.address].filter(Boolean).join(" · ");
    const description = `${place.name}${where ? ` — ${where}` : ""}. Accessibilité détaillée : motricité, audition, vision, cognition.`;
    return {
      title: place.name,
      description,
      alternates: { canonical: `/places/${slug}` },
      openGraph: {
        ...(await parent).openGraph,
        type: "article",
        title: place.name,
        description,
        url: `/places/${slug}`,
        images: [
          {
            url: "/opengraph-image",
            width: 1200,
            height: 630,
            alt: "LetMeGetIn — savoir si on peut entrer avant de partir",
          },
        ],
      },
    };
  } catch {
    return { title: "Lieu introuvable", robots: { index: false, follow: false } };
  }
}

export default async function PlacePage({ params, searchParams }: Props) {
  // Same source of truth as the layout and the search page: the cookie decides the
  // interface language, so the server renders the first paint in the reader's language.
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);

  const { slug } = await params;
  const { page } = await searchParams;
  const currentPage = Math.max(1, Number(page) || 1);

  let place: PlaceDetail;
  try {
    place = await serverApi<PlaceDetail>(`/api/v1/places/${slug}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  let reviews: ReviewPage = { items: [], total: 0, page: currentPage, size: 10 };
  try {
    reviews = await serverApi<ReviewPage>(
      `/api/v1/places/${slug}/reviews?page=${currentPage}&size=10`,
    );
  } catch {
    // A reviews outage must not hide the record.
  }

  const filledPercent = Math.round(place.filled_rate * 100);

  return (
    <article className="space-y-8">
      <div>
        <Link href="/" className="text-sm text-muted underline">
          {t(locale, "backToSearch")}
        </Link>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold sm:text-4xl">{place.name}</h1>
            <p className="mt-1 text-muted">
              {place.category ?? t(locale, "unknownCategory")}
              {place.address ? ` · ${place.address}` : ""}
            </p>
          </div>
          <div className="rounded-card border border-line bg-white/60 px-4 py-3 text-sm dark:bg-white/5">
            <p className="font-medium">
              {place.rating !== null
                ? `${place.rating.toFixed(1)}/5`
                : t(locale, "notYetRated")}
            </p>
            <p className="text-muted">
              {format(t(locale, "reviewCountLine"), {
                count: place.review_count,
                percent: filledPercent,
              })}
            </p>
          </div>
        </div>
      </div>

      <VerifyBanner locale={locale} />

      <section aria-labelledby="completion">
        <h2 id="completion" className="text-xl font-semibold">
          {t(locale, "completion")}
        </h2>
        <div className="mt-3 space-y-2">
          <div
            role="progressbar"
            aria-valuenow={filledPercent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t(locale, "completion")}
            className="h-3 overflow-hidden rounded-full bg-line"
          >
            <div className="h-full bg-accent" style={{ width: `${filledPercent}%` }} />
          </div>
          <p className="text-sm text-muted">
            {format(t(locale, "criteriaHaveValue"), { percent: filledPercent })}
          </p>
        </div>

        <dl className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(place.accessibility_by_family).map(([family, score]) => (
            <div key={family} className="rounded-card border border-line px-3 py-2">
              <dt className="text-sm text-muted">{familyLabel(family, locale)}</dt>
              <dd className="text-lg font-medium">{Math.round(score * 100)}%</dd>
            </div>
          ))}
        </dl>
      </section>

      {place.photos.length > 0 ? (
        <section aria-labelledby="photos">
          <h2 id="photos" className="mb-3 text-xl font-semibold">
            {t(locale, "photos")}
          </h2>
          <PhotoGallery photos={place.photos} locale={locale} />
        </section>
      ) : null}

      <section aria-labelledby="accessibility">
        <h2 id="accessibility" className="mb-3 text-xl font-semibold">
          {t(locale, "accessibilitySection")}
        </h2>
        <AccessibilityTree tree={place.tree} locale={locale} />
      </section>

      <section aria-labelledby="contribute" className="rounded-card border border-line p-4">
        <h2 id="contribute" className="text-xl font-semibold">
          {t(locale, "completeThisRecord")}
        </h2>
        <p className="mb-4 mt-1 text-sm text-muted">{t(locale, "contributionHelp")}</p>
        <ContributionForm slug={slug} tree={place.tree} locale={locale} />
      </section>

      <section aria-labelledby="avis">
        <h2 id="avis" className="mb-3 text-xl font-semibold">
          {format(tPlural(locale, "reviewsHeading", place.review_count), {
            count: place.review_count,
          })}
        </h2>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <ReviewList page={reviews} slug={slug} locale={locale} />
          <div className="rounded-card border border-line p-4">
            <h3 className="text-lg font-semibold">{t(locale, "leaveAReview")}</h3>
            <p className="mb-3 mt-1 text-sm text-muted">{t(locale, "reviewHelp")}</p>
            <ReviewForm slug={slug} locale={locale} />
          </div>
        </div>
      </section>
    </article>
  );
}
