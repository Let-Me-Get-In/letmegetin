import { describe, expect, it } from "vitest";

import { DOC_LEVELS, legendEntries, levelBounds, levelLabel } from "./documentation";

// The ladder exactly as GET /api/v1/places/{slug} serves it.
const LADDER = [
  { slug: "none", min: 0, max: 0 },
  { slug: "sketch", min: 1, max: 25 },
  { slug: "partial", min: 26, max: 50 },
  { slug: "good", min: 51, max: 75 },
  { slug: "very_good", min: 76, max: 99 },
  { slug: "complete", min: 100, max: 100 },
];

describe("documentation levels", () => {
  it("lists the six server slugs in ladder order", () => {
    expect([...DOC_LEVELS]).toEqual([
      "none",
      "sketch",
      "partial",
      "good",
      "very_good",
      "complete",
    ]);
  });

  it.each([
    ["none", "Fiche non documentée", "Undocumented record"],
    ["sketch", "Fiche peu documentée", "Sparsely documented"],
    ["partial", "Fiche partielle", "Partially documented"],
    ["good", "Fiche bien documentée", "Well documented"],
    ["very_good", "Fiche très documentée", "Very well documented"],
    ["complete", "Fiche complète", "Complete record"],
  ] as const)("labels %s in both locales", (slug, fr, en) => {
    expect(levelLabel(slug, "fr")).toBe(fr);
    expect(levelLabel(slug, "en")).toBe(en);
  });

  it("returns undefined for a slug it does not know", () => {
    expect(levelLabel("almost_there")).toBeUndefined();
    expect(levelLabel("", "en")).toBeUndefined();
  });
});

describe("documentation legend bounds", () => {
  it("reads a level's bounds from the served ladder, never from a local table", () => {
    // A ladder the web has never been told about: the answer must come from the payload.
    const served = [{ slug: "good", min: 40, max: 60 }];

    expect(levelBounds(served, "good")).toEqual({ slug: "good", min: 40, max: 60 });
    expect(levelBounds(LADDER, "very_good")).toEqual({ slug: "very_good", min: 76, max: 99 });
  });

  it("returns undefined for a slug the server did not serve", () => {
    expect(levelBounds(LADDER, "brand_new")).toBeUndefined();
  });

  it("keeps the declared ladder order even when the payload is reordered", () => {
    const shuffled = [...LADDER].reverse();

    expect(legendEntries(shuffled).map((rung) => rung.slug)).toEqual([...DOC_LEVELS]);
  });

  it("skips a level the server does not serve instead of inventing its bounds", () => {
    const partialLadder = LADDER.filter((rung) => rung.slug !== "partial");

    expect(legendEntries(partialLadder).map((rung) => rung.slug)).toEqual([
      "none",
      "sketch",
      "good",
      "very_good",
      "complete",
    ]);
  });
});
