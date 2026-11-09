import { describe, expect, it } from "vitest";

import { formatDate, formatDistance, formatValue, label } from "@/lib/labels";

describe("labels", () => {
  it("prefers the requested locale", () => {
    expect(label({ fr: "Bonjour", en: "Hello" }, "en")).toBe("Hello");
    expect(label({ fr: "Entrée", en: "Entrance" }, "en")).toBe("Entrance");
    expect(label({ fr: "Bonjour" }, "en")).toBe("Bonjour");
    expect(label(undefined)).toBe("");
  });

  it.each([
    [true, "Oui"],
    [false, "Non"],
    [null, "Non renseigné"],
    [{ value: "De plain-pied" }, "De plain-pied"],
    [["a", "b"], "a, b"],
  ] as const)("formats %j for the record", (value, expected) => {
    expect(formatValue(value)).toBe(expected);
  });

  it.each([
    // The locale must survive the array branch, not be replaced by the index.
    [null, "Not provided"],
    [true, "Yes"],
    [["a", null], "a, Not provided"],
    [{ value: null }, "Not provided"],
  ] as const)("formats %j in English", (value, expected) => {
    expect(formatValue(value, "en")).toBe(expected);
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
