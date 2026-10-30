import Link from "next/link";

import { formatDistance } from "@/lib/labels";
import type { PlaceSummary } from "@/lib/types";

type Props = {
  places: PlaceSummary[];
  selected: string | null;
  onSelect: (slug: string) => void;
  loading: boolean;
};

export function PlaceList({ places, selected, onSelect, loading }: Props) {
  if (loading) {
    return (
      <p role="status" className="text-sm text-muted">
        Recherche en cours…
      </p>
    );
  }

  if (places.length === 0) {
    return (
      <p className="rounded-card border border-line bg-accent-soft/40 p-4 text-sm text-muted">
        Aucun lieu trouvé. Essayez d'élargir le rayon ou de retirer un filtre.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {places.map((place) => (
        <li key={place.slug}>
          <Link
            href={`/places/${place.slug}`}
            onMouseEnter={() => onSelect(place.slug)}
            onFocus={() => onSelect(place.slug)}
            className={`block rounded-card border p-4 transition-colors ${
              place.slug === selected
                ? "border-accent bg-accent-soft/50"
                : "border-line bg-white/60 hover:border-accent dark:bg-white/5"
            }`}
          >
            <span className="flex items-baseline justify-between gap-2">
              <span className="font-medium">{place.name}</span>
              <span className="text-xs text-muted">{formatDistance(place.distance)}</span>
            </span>
            <span className="mt-1 block text-sm text-muted">
              {place.category ?? "Catégorie inconnue"}
              {place.address ? ` · ${place.address}` : ""}
            </span>
            {place.operating_status !== "open" ? (
              <span className="mt-2 inline-block rounded-full bg-warn/10 px-2 py-0.5 text-xs text-warn">
                {place.operating_status === "duplicate_review"
                  ? "Doublon possible"
                  : place.operating_status}
              </span>
            ) : null}
          </Link>
        </li>
      ))}
    </ul>
  );
}
