import Link from "next/link";
import { notFound } from "next/navigation";

import { VerifyBanner } from "@/components/auth/verify-banner";
import { AccessibilityTree } from "@/components/record/accessibility-tree";
import { ContributionForm } from "@/components/record/contribution-form";
import { PhotoGallery } from "@/components/record/photo-gallery";
import { ReviewForm } from "@/components/record/review-form";
import { ReviewList } from "@/components/record/review-list";
import { ApiError } from "@/lib/api";
import { serverApi } from "@/lib/server-api";
import { FAMILY_LABELS } from "@/lib/search";
import type { PlaceDetail, ReviewPage } from "@/lib/types";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
};

export default async function PlacePage({ params, searchParams }: Props) {
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
          ← Retour à la recherche
        </Link>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold sm:text-4xl">{place.name}</h1>
            <p className="mt-1 text-muted">
              {place.category ?? "Catégorie inconnue"}
              {place.address ? ` · ${place.address}` : ""}
            </p>
          </div>
          <div className="rounded-card border border-line bg-white/60 px-4 py-3 text-sm dark:bg-white/5">
            <p className="font-medium">
              {place.rating !== null ? `${place.rating.toFixed(1)}/5` : "Pas encore noté"}
            </p>
            <p className="text-muted">
              {place.review_count} avis · {filledPercent}% de la fiche renseignée
            </p>
          </div>
        </div>
      </div>

      <VerifyBanner />

      <section aria-labelledby="completion">
        <h2 id="completion" className="text-xl font-semibold">
          Complétude de la fiche
        </h2>
        <div className="mt-3 space-y-2">
          <div
            role="progressbar"
            aria-valuenow={filledPercent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Complétude de la fiche"
            className="h-3 overflow-hidden rounded-full bg-line"
          >
            <div className="h-full bg-accent" style={{ width: `${filledPercent}%` }} />
          </div>
          <p className="text-sm text-muted">{filledPercent}% des critères ont une valeur.</p>
        </div>

        <dl className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(place.accessibility_by_family).map(([family, score]) => (
            <div key={family} className="rounded-card border border-line px-3 py-2">
              <dt className="text-sm text-muted">{FAMILY_LABELS[family] ?? family}</dt>
              <dd className="text-lg font-medium">{Math.round(score * 100)}%</dd>
            </div>
          ))}
        </dl>
      </section>

      {place.photos.length > 0 ? (
        <section aria-labelledby="photos">
          <h2 id="photos" className="mb-3 text-xl font-semibold">
            Photos
          </h2>
          <PhotoGallery photos={place.photos} />
        </section>
      ) : null}

      <section aria-labelledby="accessibility">
        <h2 id="accessibility" className="mb-3 text-xl font-semibold">
          Accessibilité
        </h2>
        <AccessibilityTree tree={place.tree} />
      </section>

      <section aria-labelledby="contribute" className="rounded-card border border-line p-4">
        <h2 id="contribute" className="text-xl font-semibold">
          Compléter cette fiche
        </h2>
        <p className="mb-4 mt-1 text-sm text-muted">
          Une valeur manque ou a changé ? Ajoutez-la ; chaque contribution est journalisée.
        </p>
        <ContributionForm slug={slug} tree={place.tree} />
      </section>

      <section aria-labelledby="avis">
        <h2 id="avis" className="mb-3 text-xl font-semibold">
          Avis ({place.review_count})
        </h2>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <ReviewList page={reviews} slug={slug} />
          <div className="rounded-card border border-line p-4">
            <h3 className="text-lg font-semibold">Laisser un avis</h3>
            <p className="mb-3 mt-1 text-sm text-muted">Note de 1 à 5 et commentaire libre.</p>
            <ReviewForm slug={slug} />
          </div>
        </div>
      </section>
    </article>
  );
}
