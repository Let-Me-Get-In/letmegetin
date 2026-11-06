// Minimal i18n: two locales, one dictionary, no dependency.
//
// Scope is the interface chrome. Place, category and criterion labels come from
// the API and are translated in the data (`label` holds fr/en/…); when a locale
// is missing for a datum the helper falls back, so a partly translated referential
// never renders empty.
export type Locale = "fr" | "en";

export const LOCALE_COOKIE = "locale";
export const DEFAULT_LOCALE: Locale = "fr";

export function parseLocale(value: string | undefined | null): Locale {
  return value === "en" ? "en" : DEFAULT_LOCALE;
}

const MESSAGES = {
  fr: {
    skip: "Aller au contenu",
    search: "Rechercher",
    login: "Connexion",
    logout: "Déconnexion",
    account: "Mon compte",
    language: "Langue",
    title: "Trouver un lieu vraiment accessible.",
    intro:
      "Cherchez autour de vous, filtrez par handicap et ouvrez la fiche détaillée : entrée, sanitaires, signalétique, calme. Les données viennent de sources ouvertes et des contributions.",
    radius: "Rayon",
    handicap: "Handicap",
    all: "Tous",
    categories: "Catégorie (pour les critères)",
    allCategories: "Toutes",
    around: "Autour de moi",
    reset: "Réinitialiser les filtres",
    results: "Résultats",
    places: "lieux",
    more: "Voir plus",
    loading: "Chargement…",
    searching: "Recherche en cours…",
    footer: "LetMeGetIn — référentiel ouvert d'accessibilité.",
    sources: "Données : Acceslibre (Etalab 2.0), OpenStreetMap (ODbL), Overture.",
  },
  en: {
    skip: "Skip to content",
    search: "Search",
    login: "Sign in",
    logout: "Sign out",
    account: "My account",
    language: "Language",
    title: "Find places you can actually get into.",
    intro:
      "Search around you, filter by disability and open the record: entrance, toilets, signage, quiet. The data comes from open sources and contributions.",
    radius: "Radius",
    handicap: "Disability",
    all: "All",
    categories: "Category (for criteria)",
    allCategories: "All",
    around: "Near me",
    reset: "Reset filters",
    results: "Results",
    places: "places",
    more: "Load more",
    loading: "Loading…",
    searching: "Searching…",
    footer: "LetMeGetIn — an open accessibility referential.",
    sources: "Data: Acceslibre (Etalab 2.0), OpenStreetMap (ODbL), Overture.",
  },
} as const;

export type MessageKey = keyof (typeof MESSAGES)["fr"];

export function t(locale: Locale, key: MessageKey): string {
  return MESSAGES[locale][key] ?? MESSAGES[DEFAULT_LOCALE][key];
}
