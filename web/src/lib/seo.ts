// Search engines must only see production. Preview, local and dev hosts stay
// out of the index even when they happen to be publicly reachable.
const INDEXABLE_HOSTS = new Set(["letmegetin.org", "www.letmegetin.org", "app.letmegetin.org"]);

export function isIndexableHost(host: string | null): boolean {
  if (!host) return false;
  return INDEXABLE_HOSTS.has(host.split(":")[0].toLowerCase());
}
