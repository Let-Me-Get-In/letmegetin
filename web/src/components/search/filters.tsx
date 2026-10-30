"use client";

import { label } from "@/lib/labels";
import { FAMILY_LABELS, type SearchState } from "@/lib/search";
import type { Category, CriterionNode } from "@/lib/types";

export type FiltersProps = {
  value: SearchState;
  onChange: (next: SearchState) => void;
  onSubmit: () => void;
  categories: Category[];
  category: string;
  onCategory: (slug: string) => void;
  criteria: CriterionNode[];
  onCriteria: (ids: number[]) => void;
  onLocate: () => void;
  locating: boolean;
};

const RADII = [500, 1000, 2000, 5000, 10000, 25000, 50000];

export function flattenCriteria(nodes: CriterionNode[]): CriterionNode[] {
  const result: CriterionNode[] = [];
  for (const node of nodes) {
    if (node.type !== "array" && node.type !== "option" && node.id !== undefined) {
      result.push(node);
    }
    result.push(...flattenCriteria(node.children ?? []));
  }
  return result;
}

export function Filters({
  value,
  onChange,
  onSubmit,
  categories,
  category,
  onCategory,
  criteria,
  onCriteria,
  onLocate,
  locating,
}: FiltersProps) {
  const selectable = flattenCriteria(criteria);

  function toggleCriterion(id: number, checked: boolean) {
    const next = checked
      ? [...value.criteria, id]
      : value.criteria.filter((current) => current !== id);
    onCriteria(Array.from(new Set(next)));
  }

  return (
    <form
      className="space-y-4 rounded-card border border-line bg-white/60 p-4 dark:bg-white/5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <label htmlFor="q" className="block text-sm font-medium">
            Rechercher
          </label>
          <input
            id="q"
            type="search"
            value={value.q}
            onChange={(event) => onChange({ ...value, q: event.target.value })}
            placeholder="Nom, catégorie, adresse…"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
          />
        </div>

        <div>
          <label htmlFor="radius" className="block text-sm font-medium">
            Rayon
          </label>
          <select
            id="radius"
            value={value.radius}
            onChange={(event) => onChange({ ...value, radius: Number(event.target.value) })}
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
          >
            {RADII.map((radius) => (
              <option key={radius} value={radius}>
                {radius < 1000 ? `${radius} m` : `${radius / 1000} km`}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="family" className="block text-sm font-medium">
            Handicap
          </label>
          <select
            id="family"
            value={value.family}
            onChange={(event) => onChange({ ...value, family: event.target.value })}
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
          >
            <option value="">Tous</option>
            {Object.entries(FAMILY_LABELS).map(([key, text]) => (
              <option key={key} value={key}>
                {text}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="category" className="block text-sm font-medium">
            Catégorie (pour les critères)
          </label>
          <select
            id="category"
            value={category}
            onChange={(event) => onCategory(event.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
          >
            <option value="">Toutes</option>
            {categories.map((item) => (
              <option key={item.slug} value={item.slug}>
                {label(item.label) || item.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button
            type="button"
            onClick={onLocate}
            disabled={locating}
            className="w-full rounded-md border border-line px-3 py-2 text-sm hover:border-accent hover:text-accent disabled:opacity-50"
          >
            {locating ? "Localisation…" : "Autour de moi"}
          </button>
        </div>
      </div>

      {selectable.length > 0 ? (
        <fieldset>
          <legend className="text-sm font-medium">Critères d'accessibilité</legend>
          <div className="mt-2 grid max-h-44 gap-2 overflow-auto pr-1 sm:grid-cols-2">
            {selectable.map((criterion) => (
              <label key={criterion.slug} className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={value.criteria.includes(criterion.id as number)}
                  onChange={(event) => toggleCriterion(criterion.id as number, event.target.checked)}
                />
                <span>{label(criterion.label)}</span>
              </label>
            ))}
          </div>
        </fieldset>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          className="rounded-md bg-accent px-4 py-2 font-medium text-paper hover:opacity-90"
        >
          Rechercher
        </button>
        <button
          type="button"
          className="text-sm text-muted underline"
          onClick={() => {
            onChange({ ...value, q: "", family: "", criteria: [] });
            onCategory("");
          }}
        >
          Réinitialiser les filtres
        </button>
      </div>
    </form>
  );
}
