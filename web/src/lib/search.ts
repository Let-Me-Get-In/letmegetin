export type SearchState = {
  lat: number;
  lng: number;
  radius: number;
  q: string;
  family: string;
  criteria: number[];
};

export const DEFAULT_SEARCH: SearchState = {
  lat: 48.8566,
  lng: 2.3522,
  radius: 2000,
  q: "",
  family: "",
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
  if (state.criteria.length > 0) params.set("filters", state.criteria.join(","));
  return params;
}

export function placesPath(state: SearchState): string {
  const params = new URLSearchParams({
    lat: String(state.lat),
    lng: String(state.lng),
    radius: String(state.radius),
    limit: "100",
  });
  if (state.q) params.set("q", state.q);
  if (state.family) params.set("family", state.family);
  if (state.criteria.length > 0) params.set("filters", state.criteria.join(","));
  return `/api/v1/places?${params.toString()}`;
}

export const FAMILY_LABELS: Record<string, string> = {
  moteur: "Motricité",
  auditif: "Audition",
  visuel: "Vision",
  mental: "Cognitif / psychique",
};
