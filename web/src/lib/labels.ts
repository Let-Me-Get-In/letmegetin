import type { Label } from "./types";

export function label(value: Label | undefined, locale = "fr"): string {
  if (!value) return "";
  return value[locale] ?? value.fr ?? Object.values(value)[0] ?? "";
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "Non renseigné";
  if (typeof value === "boolean") return value ? "Oui" : "Non";
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map(formatValue).join(", ");
  if (typeof value === "object" && "value" in value) {
    return formatValue((value as { value: unknown }).value);
  }
  return JSON.stringify(value);
}

export function formatDistance(metres: number | null): string {
  if (metres === null) return "";
  if (metres < 1000) return `${Math.round(metres)} m`;
  return `${(metres / 1000).toFixed(1)} km`;
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(iso));
}
