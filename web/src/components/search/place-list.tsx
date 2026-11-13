import Link from "next/link";

import { levelDotClass, levelLabel } from "@/lib/documentation";
import { t, type Locale } from "@/lib/i18n";
import { formatDistance } from "@/lib/labels";
import type { PlaceSummary } from "@/lib/types";

type Props = {
  locale: Locale;
  places: PlaceSummary[];
  selected: string | null;
  onSelect: (slug: string) => void;
  loading: boolean;
};

// A dot plus the level name, deliberately not a pill: in this row a pill would read as a
// sibling status of the "possible duplicate" pill beside it (D-08, UI-SPEC). The dot is
// decorative; the name is the fact, so colour never carries it alone.
function LevelMarker({ level, locale }: { level: string; locale: Locale }) {
  const label = levelLabel(level, locale);
  const dot = levelDotClass(level);
  // An unknown slug renders nothing rather than a guess (D-02).
  if (!label || !dot) return null;
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted">
      <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

export function PlaceList({ locale, places, selected, onSelect, loading }: Props) {
  if (loading) {
    return (
      <p role="status" className="text-sm text-muted">
        {t(locale, "searching")}
      </p>
    );
  }

  if (places.length === 0) {
    return (
      <p className="rounded-card border border-line bg-accent-soft/40 p-4 text-sm text-muted">
        {t(locale, "noPlaces")}
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
              {place.category ?? t(locale, "unknownCategory")}
              {place.address ? ` · ${place.address}` : ""}
            </span>
            {place.documentation || place.operating_status !== "open" ? (
              <span className="mt-2 flex flex-wrap items-center gap-2">
                {place.documentation ? (
                  <LevelMarker level={place.documentation.level} locale={locale} />
                ) : null}
                {place.operating_status !== "open" ? (
                  <span className="inline-block rounded-full bg-warn/10 px-2 py-0.5 text-xs text-warn">
                    {place.operating_status === "duplicate_review"
                      ? t(locale, "possibleDuplicate")
                      : place.operating_status}
                  </span>
                ) : null}
              </span>
            ) : null}
          </Link>
        </li>
      ))}
    </ul>
  );
}
