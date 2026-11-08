"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Filters } from "@/components/search/filters";
import { PlaceList } from "@/components/search/place-list";
import { ApiError, api } from "@/lib/api";
import { t, tPlural, type Locale } from "@/lib/i18n";
import { placesPath, parseSearch, toSearchParams, type SearchState } from "@/lib/search";
import type { Category, CriterionNode, PlaceSummary } from "@/lib/types";

const MapView = dynamic(() => import("./map-view").then((mod) => mod.MapView), {
  ssr: false,
  loading: () => <div className="h-[420px] w-full animate-pulse rounded-card border border-line" />,
});

const PAGE_SIZE = 100;

export function SearchView({ locale }: { locale: Locale }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const state = useMemo(() => parseSearch(new URLSearchParams(query)), [query]);

  const [draft, setDraft] = useState<SearchState>(state);
  const [places, setPlaces] = useState<PlaceSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [more, setMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const [error, setError] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
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
        setMore(data.length === PAGE_SIZE);
        setSelected(data[0]?.slug ?? null);
      })
      .catch((cause) => {
        if (!active) return;
        setPlaces([]);
        setMore(false);
        setError(cause instanceof ApiError ? cause.message : t(locale, "searchUnavailable"));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [state, locale]);

  useEffect(() => {
    api<Category[]>("/api/v1/categories")
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (!draft.category) {
      setCriteria([]);
      return;
    }
    let active = true;
    api<CriterionNode[]>(`/api/v1/categories/${draft.category}/criteria`)
      .then((data) => {
        if (active) setCriteria(data);
      })
      .catch(() => {
        if (active) setCriteria([]);
      });
    return () => {
      active = false;
    };
  }, [draft.category]);

  const submit = useCallback(() => {
    router.push(`/?${toSearchParams(draft).toString()}`);
  }, [router, draft]);

  const loadMore = useCallback(() => {
    if (loadingMore) return;
    setLoadingMore(true);
    // A new search resets `places`; the effect below then restarts at page 1.
    api<PlaceSummary[]>(placesPath(state, places.length))
      .then((next) => {
        setPlaces((current) => [...current, ...next]);
        setMore(next.length === PAGE_SIZE);
        // Without this the list grows silently: a screen reader stays on the
        // button and never learns that 100 more places arrived.
        setAnnouncement(
          next.length === 0
            ? t(locale, "noMorePlaces")
            : `${next.length} ${tPlural(locale, "placesAdded", next.length)}.`,
        );
      })
      .catch((cause) => {
        setError(cause instanceof ApiError ? cause.message : t(locale, "searchUnavailable"));
      })
      .finally(() => setLoadingMore(false));
  }, [state, places.length, loadingMore, locale]);

  const locate = useCallback(() => {
    if (!navigator.geolocation) {
      setGeoMessage(t(locale, "geoUnavailable"));
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
        setGeoMessage(t(locale, "geoDenied"));
      },
      { timeout: 8000 },
    );
  }, [draft, router, locale]);

  return (
    <section>
      <div className="mb-6">
        <h1 className="text-3xl font-semibold sm:text-4xl">{t(locale, "title")}</h1>
        <p className="mt-2 max-w-2xl text-muted">{t(locale, "intro")}</p>
      </div>

      <Filters
        locale={locale}
        value={draft}
        onChange={setDraft}
        onSubmit={submit}
        categories={categories}
        category={draft.category}
        onCategory={(slug) => {
          setDraft((current) => ({ ...current, category: slug, criteria: [] }));
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
          locale={locale}
          places={places}
          center={{ lat: state.lat, lng: state.lng }}
          selected={selected}
          onSelect={setSelected}
        />
        <div>
          <p role="status" aria-live="polite" className="sr-only">
            {announcement}
          </p>
          <h2 className="mb-3 text-lg font-semibold">
            {loading
              ? t(locale, "results")
              : `${places.length} ${tPlural(locale, "places", places.length)}`}
          </h2>
          <PlaceList
            locale={locale}
            places={places}
            selected={selected}
            onSelect={setSelected}
            loading={loading}
          />
          {more && !loading ? (
            <button
              type="button"
              onClick={loadMore}
              disabled={loadingMore}
              className="mt-3 w-full rounded-md border border-line px-3 py-2 text-sm hover:border-accent hover:text-accent disabled:opacity-50"
            >
              {loadingMore ? t(locale, "loading") : t(locale, "more")}
            </button>
          ) : null}
        </div>
      </div>
    </section>
  );
}
