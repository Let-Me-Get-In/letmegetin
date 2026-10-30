"use client";

import {
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  type StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import type { PlaceSummary } from "@/lib/types";

const TILE_URL =
  process.env.NEXT_PUBLIC_MAP_TILE_URL ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION =
  process.env.NEXT_PUBLIC_MAP_ATTRIBUTION ?? "© OpenStreetMap contributors";

const STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: [TILE_URL],
      tileSize: 256,
      attribution: ATTRIBUTION,
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

type Props = {
  places: PlaceSummary[];
  center: { lat: number; lng: number };
  selected: string | null;
  onSelect: (slug: string) => void;
};

export function MapView({ places, center, selected, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const markers = useRef<Marker[]>([]);

  useEffect(() => {
    if (!container.current || map.current) return;
    const instance = new MapLibreMap({
      container: container.current,
      style: STYLE,
      center: [center.lng, center.lat],
      zoom: 13,
    });
    instance.addControl(new NavigationControl(), "top-right");
    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
    };
    // The map is created once; center updates are handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map.current) return;
    markers.current.forEach((marker) => marker.remove());
    markers.current = [];
    for (const place of places) {
      if (place.lat === null || place.lng === null) continue;
      const marker = new Marker({
        color: place.slug === selected ? "#1f6f4a" : "#5d6a61",
      })
        .setLngLat([place.lng, place.lat])
        .addTo(map.current);
      marker.getElement().addEventListener("click", () => onSelect(place.slug));
      markers.current.push(marker);
    }
  }, [places, selected, onSelect]);

  useEffect(() => {
    map.current?.flyTo({ center: [center.lng, center.lat], zoom: 13 });
  }, [center.lat, center.lng]);

  useEffect(() => {
    const place = places.find((item) => item.slug === selected);
    if (place?.lat != null && place.lng != null) {
      map.current?.flyTo({ center: [place.lng, place.lat], zoom: 15 });
    }
  }, [selected, places]);

  return (
    <div
      ref={container}
      className="h-[420px] w-full rounded-card border border-line"
      role="application"
      aria-label="Carte des lieux accessibles. La liste à côté donne les mêmes résultats au clavier."
    />
  );
}
