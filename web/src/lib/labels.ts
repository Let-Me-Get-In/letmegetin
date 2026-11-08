import { t, type Locale } from "./i18n";
import type { Label } from "./types";

export function label(value: Label | undefined, locale: Locale = "fr"): string {
  if (!value) return "";
  return value[locale] ?? value.fr ?? Object.values(value)[0] ?? "";
}

export function formatValue(value: unknown, locale: Locale = "fr"): string {
  if (value === null || value === undefined) return t(locale, "notProvided");
  if (typeof value === "boolean") return t(locale, value ? "yes" : "no");
  if (typeof value === "string" || typeof value === "number") return String(value);
  // `locale` is threaded explicitly: `value.map(formatValue)` would pass the array
  // index as the second argument.
  if (Array.isArray(value)) return value.map((item) => formatValue(item, locale)).join(", ");
  if (typeof value === "object" && "value" in value) {
    return formatValue((value as { value: unknown }).value, locale);
  }
  return JSON.stringify(value);
}

export function formatDistance(metres: number | null): string {
  if (metres === null) return "";
  if (metres < 1000) return `${Math.round(metres)} m`;
  return `${(metres / 1000).toFixed(1)} km`;
}

export function formatDate(iso: string, locale: Locale = "fr"): string {
  return new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(iso));
}
