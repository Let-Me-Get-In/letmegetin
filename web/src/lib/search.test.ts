import { describe, expect, it } from "vitest";

import { DEFAULT_SEARCH, parseSearch, placesPath, toSearchParams } from "@/lib/search";

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
      criteria: [7],
    });

    expect(path).toContain("/api/v1/places?");
    expect(path).toContain("q=h%C3%B4tel");
    expect(path).toContain("family=moteur");
    expect(path).toContain("filters=7");
  });
});
