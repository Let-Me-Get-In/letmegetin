import { describe, expect, it } from "vitest";

import { DEFAULT_SEARCH, FAMILY_KEYS, familyLabel, parseSearch, placesPath, toSearchParams } from "@/lib/search";

describe("search state", () => {
  it("falls back to the default search", () => {
    expect(parseSearch(new URLSearchParams())).toEqual(DEFAULT_SEARCH);
  });

  it("round-trips through the URL", () => {
    const state = {
      lat: 45.764,
      lng: 4.8357,
      radius: 5000,
      q: "bibliothèque",
      family: "visuel",
      category: "pharmacy",
      criteria: [12, 18],
    };

    expect(parseSearch(toSearchParams(state))).toEqual(state);
  });

  it("ignores an unknown family and malformed criteria", () => {
    const state = parseSearch(
      new URLSearchParams("family=inconnu&filters=3,abc,-1,4"),
    );

    expect(state.family).toBe("");
    expect(state.criteria).toEqual([3, 4]);
  });

  it("builds the places URL with the active filters", () => {
    const path = placesPath({
      ...DEFAULT_SEARCH,
      q: "hôtel",
      family: "moteur",
      category: "pharmacy",
      criteria: [7],
    });

    expect(path).toContain("/api/v1/places?");
    expect(path).toContain("q=h%C3%B4tel");
    expect(path).toContain("family=moteur");
    expect(path).toContain("category=pharmacy");
    expect(path).toContain("filters=7");
  });

  it("omits an empty category from the places URL", () => {
    const path = placesPath({ ...DEFAULT_SEARCH, criteria: [7] });

    expect(path).not.toContain("category=");
  });

  it("sends offset only past the first page", () => {
    expect(placesPath(DEFAULT_SEARCH)).not.toContain("offset=");
    expect(placesPath(DEFAULT_SEARCH, 100)).toContain("offset=100");
  });

  it("always asks for the documentation signal", () => {
    expect(placesPath(DEFAULT_SEARCH)).toContain("with_documentation=true");
    expect(placesPath({ ...DEFAULT_SEARCH, q: "hôtel" }, 100)).toContain(
      "with_documentation=true",
    );
  });
});

describe("handicap families", () => {
  it("keeps the declared filter order", () => {
    expect([...FAMILY_KEYS]).toEqual(["moteur", "auditif", "visuel", "mental"]);
  });

  it("labels a family in the requested language", () => {
    expect(familyLabel("moteur", "fr")).toBe("Motricité");
    expect(familyLabel("moteur", "en")).toBe("Mobility");
    expect(familyLabel("mental", "en")).toBe("Cognitive / psychosocial");
  });

  it("falls back to the raw slug for an unknown family", () => {
    expect(familyLabel("inconnu", "en")).toBe("inconnu");
  });
});
