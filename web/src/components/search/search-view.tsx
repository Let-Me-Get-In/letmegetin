"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Filters } from "@/components/search/filters";
import { PlaceList } from "@/components/search/place-list";
import { ApiError, api } from "@/lib/api";
import { placesPath, parseSearch, toSearchParams, type SearchState } from "@/lib/search";
import type { Category, CriterionNode, PlaceSummary } from "@/lib/types";

const MapView = dynamic(() => import("./map-view").then((mod) => mod.MapView), {
  ssr: false,
  loading: () => <div className="h-[420px] w-full animate-pulse rounded-card border border-line" />,
});

export function SearchView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const state = useMemo(() => parseSearch(new URLSearchParams(query)), [query]);

  const [draft, setDraft] = useState<SearchState>(state);
  const [places, setPlaces] = useState<PlaceSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [category, setCategory] = useState("");
  const [criteria, setCriteria] = useState<CriterionNode[]>([]);
  const [locating, setLocating] = useState(false);
  const [geoMessage, setGeoMessage] = useState("");

  useEffect(() => {
    setDraft(parseSearch(new URLSearchParams(query)));
  }, [query]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<PlaceSummary[]>(placesPath(state))
      .then((data) => {
        if (!active) return;
        setPlaces(data);
        setSelected(data[0]?.slug ?? null);
      })
      .catch((cause) => {
        if (!active) return;
        setPlaces([]);
        setError(cause instanceof ApiError ? cause.message : "Recherche indisponible.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [state]);

  useEffect(() => {
    api<Category[]>("/api/v1/categories")
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (!category) {
      setCriteria([]);
      return;
    }
    let active = true;
    api<CriterionNode[]>(`/api/v1/categories/${category}/criteria`)
      .then((data) => {
        if (active) setCriteria(data);
      })
      .catch(() => {
        if (active) setCriteria([]);
      });
    return () => {
      active = false;
    };
  }, [category]);

  const submit = useCallback(() => {
    router.push(`/?${toSearchParams(draft).toString()}`);
  }, [router, draft]);

  const locate = useCallback(() => {
    if (!navigator.geolocation) {
      setGeoMessage("La géolocalisation n'est pas disponible dans ce navigateur.");
      return;
    }
    setLocating(true);
    setGeoMessage("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const next = {
          ...draft,
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          radius: 2000,
        };
        setDraft(next);
        setLocating(false);
        router.push(`/?${toSearchParams(next).toString()}`);
      },
      () => {
        setLocating(false);
        setGeoMessage("Localisation refusée : la recherche reste centrée sur Paris.");
      },
      { timeout: 8000 },
    );
  }, [draft, router]);

  return (
    <section>
      <div className="mb-6">
        <h1 className="text-3xl font-semibold sm:text-4xl">Trouver un lieu vraiment accessible.</h1>
        <p className="mt-2 max-w-2xl text-muted">
          Cherchez autour de vous, filtrez par handicap et ouvrez la fiche détaillée : entrée,
          sanitaires, signalétique, calme. Les données viennent de sources ouvertes et des
          contributions.
        </p>
      </div>

      <Filters
        value={draft}
        onChange={setDraft}
        onSubmit={submit}
        categories={categories}
        category={category}
        onCategory={(slug) => {
          setCategory(slug);
          setDraft((current) => ({ ...current, criteria: [] }));
        }}
        criteria={criteria}
        onCriteria={(ids) => setDraft((current) => ({ ...current, criteria: ids }))}
        onLocate={locate}
        locating={locating}
      />

      {geoMessage ? (
        <p role="status" className="mt-3 text-sm text-warn">
          {geoMessage}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-3 rounded-card border border-warn/40 bg-warn/10 p-3 text-sm">
          {error}
        </p>
      ) : null}

      <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <MapView
          places={places}
          center={{ lat: state.lat, lng: state.lng }}
          selected={selected}
          onSelect={setSelected}
        />
        <div>
          <h2 className="mb-3 text-lg font-semibold">
            {loading ? "Résultats" : `${places.length} lieu${places.length > 1 ? "x" : ""}`}
          </h2>
          <PlaceList
            places={places}
            selected={selected}
            onSelect={setSelected}
            loading={loading}
          />
        </div>
      </div>
    </section>
  );
}
