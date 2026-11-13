import { t, type Locale } from "./i18n";

// The six level slugs the server owns, in ladder order (D-01, D-02). This module maps a
// slug to its localized label and never derives a level from a rate.
export const DOC_LEVELS = [
  "none",
  "sketch",
  "partial",
  "good",
  "very_good",
  "complete",
] as const;

export type DocLevel = (typeof DOC_LEVELS)[number];

const LEVEL_MESSAGE_KEYS = {
  none: "docNone",
  sketch: "docSketch",
  partial: "docPartial",
  good: "docGood",
  very_good: "docVeryGood",
  complete: "docComplete",
} as const;

/** The localized level name, or undefined for a slug this client does not know. */
export function levelLabel(slug: string, locale: Locale = "fr"): string | undefined {
  const level = DOC_LEVELS.find((candidate) => candidate === slug);
  return level ? t(locale, LEVEL_MESSAGE_KEYS[level]) : undefined;
}
