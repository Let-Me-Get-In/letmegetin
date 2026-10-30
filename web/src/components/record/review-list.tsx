import Link from "next/link";

import { formatDate } from "@/lib/labels";
import type { ReviewPage } from "@/lib/types";

export function ReviewList({ page, slug }: { page: ReviewPage; slug: string }) {
  if (page.total === 0) {
    return (
      <p className="rounded-card border border-line bg-accent-soft/40 p-4 text-sm text-muted">
        Aucun avis pour ce lieu. Sois la première personne à en écrire un.
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
                {review.rating}/5 · {review.author_name ?? "Anonyme"}
              </p>
              <p className="text-xs text-muted">{formatDate(review.created)}</p>
            </div>
            {review.body ? <p className="mt-2 text-sm">{review.body}</p> : null}
          </li>
        ))}
      </ul>
      {pageCount > 1 ? (
        <nav aria-label="Pagination des avis" className="flex items-center gap-3 text-sm">
          {page.page > 1 ? (
            <Link className="underline" href={`/places/${slug}?page=${page.page - 1}#avis`}>
              Précédent
            </Link>
          ) : null}
          <span className="text-muted">
            Page {page.page} / {pageCount}
          </span>
          {page.page < pageCount ? (
            <Link className="underline" href={`/places/${slug}?page=${page.page + 1}#avis`}>
              Suivant
            </Link>
          ) : null}
        </nav>
      ) : null}
    </div>
  );
}
