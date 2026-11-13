import { describe, expect, it } from "vitest";

import { DOC_LEVELS, levelLabel } from "./documentation";

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
