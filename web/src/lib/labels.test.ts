import { describe, expect, it } from "vitest";

import { formatDate, formatDistance, formatValue, label } from "@/lib/labels";

describe("labels", () => {
  it("prefers the requested locale", () => {
    expect(label({ fr: "Bonjour", en: "Hello" }, "en")).toBe("Hello");
    expect(label({ fr: "Entrée", en: "Entrance" }, "en")).toBe("Entrance");
    expect(label({ fr: "Bonjour" }, "en")).toBe("Bonjour");
    expect(label(undefined)).toBe("");
  });

  it("formats values for the record", () => {
    expect(formatValue(true)).toBe("Oui");
    expect(formatValue(false)).toBe("Non");
    expect(formatValue(null)).toBe("Non renseigné");
    expect(formatValue({ value: "De plain-pied" })).toBe("De plain-pied");
    expect(formatValue(["a", "b"])).toBe("a, b");
  });

  it("formats values in the requested language", () => {
    expect(formatValue(null, "en")).toBe("Not provided");
    expect(formatValue(true, "en")).toBe("Yes");
    // The locale must survive the array branch, not be replaced by the index.
    expect(formatValue(["a", null], "en")).toBe("a, Not provided");
    expect(formatValue({ value: null }, "en")).toBe("Not provided");
  });

  it("formats distances", () => {
    expect(formatDistance(120)).toBe("120 m");
    expect(formatDistance(1500)).toBe("1.5 km");
    expect(formatDistance(null)).toBe("");
  });

  it("formats dates in the requested language", () => {
    expect(formatDate("2026-11-06")).toBe("6 novembre 2026");
    expect(formatDate("2026-11-06", "en")).toBe("6 November 2026");
  });
});
