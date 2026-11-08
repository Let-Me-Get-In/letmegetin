import Link from "next/link";

import { format, t, type Locale } from "@/lib/i18n";
import { formatDate } from "@/lib/labels";
import type { ReviewPage } from "@/lib/types";

export function ReviewList({
  page,
  slug,
  locale,
}: {
  page: ReviewPage;
  slug: string;
  locale: Locale;
}) {
  if (page.total === 0) {
    return (
      <p className="rounded-card border border-line bg-accent-soft/40 p-4 text-sm text-muted">
        {t(locale, "noReviews")}
      </p>
    );
  }

  const pageCount = Math.max(1, Math.ceil(page.total / page.size));

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {page.items.map((review) => (
          <li key={review.id} className="rounded-card border border-line bg-white/60 p-4 dark:bg-white/5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="font-medium">
                {review.rating}/5 · {review.author_name ?? t(locale, "anonymous")}
              </p>
              <p className="text-xs text-muted">{formatDate(review.created, locale)}</p>
            </div>
            {review.body ? <p className="mt-2 text-sm">{review.body}</p> : null}
          </li>
        ))}
      </ul>
      {pageCount > 1 ? (
        <nav aria-label={t(locale, "reviewPagination")} className="flex items-center gap-3 text-sm">
          {/* `#avis` in the links below is an anchor target, not display copy. */}
          {page.page > 1 ? (
            <Link className="underline" href={`/places/${slug}?page=${page.page - 1}#avis`}>
              {t(locale, "previous")}
            </Link>
          ) : null}
          <span className="text-muted">
            {format(t(locale, "pageOf"), { page: page.page, count: pageCount })}
          </span>
          {page.page < pageCount ? (
            <Link className="underline" href={`/places/${slug}?page=${page.page + 1}#avis`}>
              {t(locale, "nextPage")}
            </Link>
          ) : null}
        </nav>
      ) : null}
    </div>
  );
}
