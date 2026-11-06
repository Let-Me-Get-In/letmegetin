import { describe, expect, it } from "vitest";

import { parseLocale, t } from "./i18n";

describe("i18n", () => {
  it("falls back to French for an unknown or missing cookie", () => {
    expect(parseLocale(undefined)).toBe("fr");
    expect(parseLocale("de")).toBe("fr");
    expect(parseLocale("en")).toBe("en");
  });

  it("translates a key in both locales", () => {
    expect(t("fr", "search")).toBe("Rechercher");
    expect(t("en", "search")).toBe("Search");
  });
});
