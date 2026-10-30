import { describe, expect, it } from "vitest";

import { formatDistance, formatValue, label } from "@/lib/labels";

describe("labels", () => {
  it("prefers the requested locale", () => {
    expect(label({ fr: "Bonjour", en: "Hello" }, "en")).toBe("Hello");
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

  it("formats distances", () => {
    expect(formatDistance(120)).toBe("120 m");
    expect(formatDistance(1500)).toBe("1.5 km");
    expect(formatDistance(null)).toBe("");
  });
});
