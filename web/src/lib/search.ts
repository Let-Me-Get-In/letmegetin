import { t, type Locale } from "./i18n";

export type SearchState = {
  lat: number;
  lng: number;
  radius: number;
  q: string;
  family: string;
  category: string;
  criteria: number[];
};

export const DEFAULT_SEARCH: SearchState = {
  lat: 48.8566,
  lng: 2.3522,
  radius: 2000,
  q: "",
  family: "",
  category: "",
  criteria: [],
};

const FAMILIES = new Set(["moteur", "auditif", "visuel", "mental"]);

function numberOr(value: string | null, fallback: number): number {
  if (value === null || value.trim() === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function parseSearch(params: URLSearchParams): SearchState {
  return {
    lat: numberOr(params.get("lat"), DEFAULT_SEARCH.lat),
    lng: numberOr(params.get("lng"), DEFAULT_SEARCH.lng),
    radius: numberOr(params.get("radius"), DEFAULT_SEARCH.radius),
    q: params.get("q")?.trim() ?? "",
    family: FAMILIES.has(params.get("family") ?? "") ? (params.get("family") as string) : "",
    category: params.get("category")?.trim() ?? "",
    criteria: (params.get("filters") ?? "")
      .split(",")
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0),
  };
}

export function toSearchParams(state: SearchState): URLSearchParams {
  const params = new URLSearchParams();
  params.set("lat", state.lat.toFixed(5));
  params.set("lng", state.lng.toFixed(5));
  params.set("radius", String(state.radius));
  if (state.q) params.set("q", state.q);
  if (state.family) params.set("family", state.family);
  if (state.category) params.set("category", state.category);
  if (state.criteria.length > 0) params.set("filters", state.criteria.join(","));
  return params;
}

export function placesPath(state: SearchState, offset = 0): string {
  const params = new URLSearchParams({
    lat: String(state.lat),
    lng: String(state.lng),
    radius: String(state.radius),
    limit: "100",
    // The search view always wants the documentation signal; the field is additive and
    // the card simply omits the marker when the response does not carry it (D-07).
    with_documentation: "true",
  });
  if (state.q) params.set("q", state.q);
  if (state.family) params.set("family", state.family);
  if (state.category) params.set("category", state.category);
  if (state.criteria.length > 0) params.set("filters", state.criteria.join(","));
  // Page 1 keeps the URL shape it always had, so shared links stay unchanged.
  if (offset > 0) params.set("offset", String(offset));
  return `/api/v1/places?${params.toString()}`;
}

// The order the handicap filter renders in, independent of dictionary ordering.
export const FAMILY_KEYS = ["moteur", "auditif", "visuel", "mental"] as const;

const FAMILY_MESSAGE_KEYS = {
  moteur: "familyMoteur",
  auditif: "familyAuditif",
  visuel: "familyVisuel",
  mental: "familyMental",
} as const;

export function familyLabel(family: string, locale: Locale = "fr"): string {
  const key = FAMILY_MESSAGE_KEYS[family as keyof typeof FAMILY_MESSAGE_KEYS];
  return key ? t(locale, key) : family;
}
