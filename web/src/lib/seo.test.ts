import { describe, expect, it } from "vitest";

import { isIndexableHost } from "./seo";

describe("isIndexableHost", () => {
  it("indexes the production hosts", () => {
    expect(isIndexableHost("app.letmegetin.org")).toBe(true);
    expect(isIndexableHost("letmegetin.org")).toBe(true);
    expect(isIndexableHost("app.letmegetin.org:443")).toBe(true);
  });

  it("keeps every other host out of the index", () => {
    expect(isIndexableHost("app.dev.letmegetin.org")).toBe(false);
    expect(isIndexableHost("localhost:3000")).toBe(false);
    expect(isIndexableHost("127.0.0.1:3000")).toBe(false);
    expect(isIndexableHost("")).toBe(false);
    expect(isIndexableHost(null)).toBe(false);
  });
});
