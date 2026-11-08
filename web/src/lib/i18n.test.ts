import { describe, expect, it } from "vitest";

import { format, parseLocale, t, tPlural } from "./i18n";

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

  it("pluralises in the reader's language", () => {
    expect(tPlural("fr", "places", 1)).toBe("lieu");
    expect(tPlural("fr", "places", 4)).toBe("lieux");
    expect(tPlural("en", "places", 1)).toBe("place");
    expect(tPlural("en", "places", 4)).toBe("places");
  });

  it("treats zero as singular in French only", () => {
    expect(tPlural("fr", "places", 0)).toBe("lieu");
    expect(tPlural("en", "places", 0)).toBe("places");
  });

  it("resolves {name} placeholders", () => {
    expect(format("Page {page} / {count}", { page: 1, count: 3 })).toBe("Page 1 / 3");
    expect(format("Avis ({count})", { count: 2 })).toBe("Avis (2)");
    expect(format("No placeholder", {})).toBe("No placeholder");
  });
});
