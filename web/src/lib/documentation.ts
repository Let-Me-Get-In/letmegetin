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

// UI-SPEC "Level → class mapping": the chip is the only colour surface, so a card never
// tints its border (selection and hover own the border, and the dark tints collapsed).
const LEVEL_CHIP_CLASSES: Record<DocLevel, string> = {
  none: "border border-line text-muted",
  sketch: "bg-doc-sketch text-ink",
  partial: "bg-doc-partial text-ink",
  good: "bg-doc-good text-ink",
  very_good: "bg-doc-very-good text-ink",
  complete: "bg-accent text-paper",
};

// The search card's marker dot: decorative, the level name next to it carries the fact.
const LEVEL_DOT_CLASSES: Record<DocLevel, string> = {
  none: "border border-dashed border-muted",
  sketch: "bg-doc-sketch",
  partial: "bg-doc-partial",
  good: "bg-doc-good",
  very_good: "bg-doc-very-good",
  complete: "bg-accent",
};

function docLevel(slug: string): DocLevel | undefined {
  return DOC_LEVELS.find((candidate) => candidate === slug);
}

/** The localized level name, or undefined for a slug this client does not know. */
export function levelLabel(slug: string, locale: Locale = "fr"): string | undefined {
  const level = docLevel(slug);
  return level ? t(locale, LEVEL_MESSAGE_KEYS[level]) : undefined;
}

/** Tailwind classes for a level chip, or undefined for a slug this client does not know. */
export function levelChipClass(slug: string): string | undefined {
  const level = docLevel(slug);
  return level ? LEVEL_CHIP_CLASSES[level] : undefined;
}

/** Tailwind classes for the search card's marker dot, or undefined for an unknown slug. */
export function levelDotClass(slug: string): string | undefined {
  const level = docLevel(slug);
  return level ? LEVEL_DOT_CLASSES[level] : undefined;
}

// The bounds the server serves with the documentation contract (D-02, D-09).
export type LevelBounds = { slug: string; min: number; max: number };

/** The server's own bounds for a level slug, or undefined when it does not serve it. */
export function levelBounds(
  ladder: readonly LevelBounds[],
  slug: string,
): LevelBounds | undefined {
  return ladder.find((rung) => rung.slug === slug);
}

/** The served rungs in the declared ladder order, so a reordered payload cannot reorder the key. */
export function legendEntries(ladder: readonly LevelBounds[]): LevelBounds[] {
  return DOC_LEVELS.flatMap((slug) => levelBounds(ladder, slug) ?? []);
}
