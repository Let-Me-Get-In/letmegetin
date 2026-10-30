import { Suspense } from "react";

import { SearchView } from "@/components/search/search-view";

export default function HomePage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted">Chargement de la recherche…</p>}>
      <SearchView />
    </Suspense>
  );
}
