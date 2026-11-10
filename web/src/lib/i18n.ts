// Minimal i18n: two locales, one dictionary, no dependency.
//
// Scope is the interface chrome. Place, category and criterion labels come from
// the API and are translated in the data (`label` holds fr/en/…); when a locale
// is missing for a datum the helper falls back, so a partly translated referential
// never renders empty.
//
// This file is the single owner of every message the interface renders. The `fr`
// column is the reference: it must stay byte-identical to the literals the interface
// used before they moved here, because the e2e suite text-selects the French values.
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
    places: { one: "lieu", many: "lieux" },
    more: "Voir plus",
    loading: "Chargement…",
    searching: "Recherche en cours…",
    footer: "LetMeGetIn — référentiel ouvert d'accessibilité.",
    sources: "Données : Acceslibre (Etalab 2.0), OpenStreetMap (ODbL), Overture.",

    // Search
    searchLoading: "Chargement de la recherche…",
    searchUnavailable: "Recherche indisponible.",
    noMorePlaces: "Aucun autre lieu.",
    placesAdded: { one: "lieu supplémentaire", many: "lieux supplémentaires" },
    geoUnavailable: "La géolocalisation n'est pas disponible dans ce navigateur.",
    geoDenied: "Localisation refusée : la recherche reste centrée sur Paris.",
    searchPlaceholder: "Nom, catégorie, adresse…",
    criteriaLegend: "Critères d'accessibilité",
    noPlaces:
      "Aucun lieu trouvé. Essayez d'élargir le rayon ou de retirer un filtre.",
    unknownCategory: "Catégorie inconnue",
    possibleDuplicate: "Doublon possible",
    mapAriaLabel:
      "Carte des lieux accessibles. La liste à côté donne les mêmes résultats au clavier.",
    notProvided: "Non renseigné",
    yes: "Oui",
    no: "Non",
    familyMoteur: "Motricité",
    familyAuditif: "Audition",
    familyVisuel: "Vision",
    familyMental: "Cognitif / psychique",
    locating: "Localisation…",

    // Record
    criterion: "Critère",
    valueLabel: "Valeur",
    choose: "— Choisir —",
    exampleNumber: "Ex. 90",
    saving: "Enregistrement…",
    save: "Enregistrer",
    publishing: "Publication…",
    publishReview: "Publier l'avis",
    signInPrompt: "Connectez-vous",
    toCompleteThisRecord: "pour compléter cette fiche.",
    verifyToComplete: "Vérifiez votre adresse email pour compléter cette fiche.",
    toLeaveAReview: "pour laisser un avis.",
    verifyToReview: "Vérifiez votre adresse email pour laisser un avis.",
    noCriteria: "Aucun critère disponible pour ce lieu.",
    noTree: "Aucune grille d'accessibilité n'est encore disponible pour ce lieu.",
    chooseValue: "Choisissez ou saisissez une valeur.",
    contributionSaved: "Contribution enregistrée. Merci !",
    contributionFailed: "Contribution impossible.",
    reviewPublished: "Avis publié. Merci !",
    reviewFailed: "Publication impossible.",
    rating: "Note",
    yourReview: "Votre avis",
    reviewPlaceholder: "Accueil, cheminement, sanitaires…",
    verifyDisabled:
      "Votre adresse email n'est pas encore vérifiée : la contribution et les avis sont désactivés.",
    resendLink: "Renvoyer le lien",
    sending: "Envoi…",
    verificationSent: "Lien de vérification renvoyé.",
    sendFailed: "Envoi impossible.",
    noReviews: "Aucun avis pour ce lieu. Sois la première personne à en écrire un.",
    anonymous: "Anonyme",
    reviewPagination: "Pagination des avis",
    previous: "Précédent",
    nextPage: "Suivant",
    backToSearch: "← Retour à la recherche",
    backToSearchPlain: "Retour à la recherche",
    notYetRated: "Pas encore noté",
    unspecifiedSource: "Source non précisée",
    completion: "Complétude de la fiche",
    criteriaHaveValue: "{percent}% des critères ont une valeur.",
    reviewCountLine: "{count} avis · {percent}% de la fiche renseignée",
    photos: "Photos",
    accessibilitySection: "Accessibilité",
    completeThisRecord: "Compléter cette fiche",
    contributionHelp:
      "Une valeur manque ou a changé ? Ajoutez-la ; chaque contribution est journalisée.",
    reviewsHeading: { one: "Avis ({count})", many: "Avis ({count})" },
    leaveAReview: "Laisser un avis",
    reviewHelp: "Note de 1 à 5 et commentaire libre.",
    pageOf: "Page {page} / {count}",
    placeNotFoundTitle: "Lieu introuvable",
    placeNotFoundBody:
      "Cette fiche n'existe pas ou a été déplacée. Essayez une nouvelle recherche.",

    // Auth and account
    loginFolderIntro: "Connectez-vous pour contribuer à une fiche ou laisser un avis.",
    email: "Email",
    password: "Mot de passe",
    signInSubmit: "Se connecter",
    signingIn: "Connexion…",
    loginFailed: "Connexion impossible.",
    noAccountYet: "Pas encore de compte ?",
    createAccountLink: "Créer un compte",
    registerFolderIntro:
      "Un compte permet de compléter les fiches et de publier des avis. La contribution reste ouverte à tous et la donnée reste libre.",
    displayName: "Nom affiché (optionnel)",
    displayNamePlaceholder: "Apparaît sur vos avis",
    passwordMinLength: "8 caractères minimum.",
    registering: "Création…",
    createMyAccount: "Créer mon compte",
    alreadyRegistered: "Déjà inscrit ?",
    registerFailed: "Inscription impossible.",
    verifyHeading: "Vérification de l'email",
    verifyFolderIntro: "Cette page confirme l'adresse associée à votre compte.",
    verifying: "Vérification…",
    verificationInProgress: "Vérification en cours…",
    incompleteVerificationLink: "Lien de vérification incomplet.",
    emailVerified: "Adresse email vérifiée. Merci !",
    verificationFailed: "Vérification impossible ou lien expiré.",
    goToAccount: "Aller à mon compte",
    accountFolderIntro:
      "Vos contributions et avis sont publiés sous votre nom affiché.",
    emailLabel: "Email",
    displayNameLabel: "Nom affiché",
    emailVerifiedLabel: "Email vérifié",
    roleLabel: "Rôle",
    searchLink: "Rechercher un lieu",
    signOut: "Se déconnecter",
    loadingAccount: "Chargement du compte…",
    redirectingToLogin: "Redirection vers la connexion…",

    // Landing
    landingNavSearch: "Chercher",
    landingNavData: "La donnée",
    landingNavApi: "API",
    landingNavAbout: "À propos",
    landingOpenApp: "Ouvrir l'app",
    landingHeroTitle: "Savoir si on peut entrer. Avant de partir.",
    landingHeroIntro:
      "L'accessibilité réelle des lieux, vérifiée critère par critère. Cherchez un lieu, ouvrez sa fiche, sachez ce qui vous attend.",
    landingSearchLabel: "Rechercher un lieu",
    landingSearchPlaceholder: "Adresse, lieu, ville",
    landingSearchSubmit: "Chercher",
    landingSearchHint: "La recherche s'ouvre dans l'application.",
    landingTrust: "634 931 lieux en France · données ouvertes",
    landingExampleBadge: "Exemple de fiche",
    landingExampleName: "Café de quartier",
    landingExampleAddress: "Paris 11e",
    landingExampleStatus: "Accessible",
    landingExampleMeta: "12 critères renseignés",
    landingExampleEntrance: "Entrée sans marche",
    landingExampleToilets: "Sanitaires adaptés",
    landingExampleLoop: "Boucle magnétique",
    landingExampleStaff: "Personnel formé",
    landingExampleLink: "Voir une fiche",
    landingPromiseTitle: "Une fiche, pas une note vague.",
    landingPromiseIntro:
      "Chaque lieu est décrit par des critères typés, regroupés par famille de handicap. Ce qui est renseigné est daté ; ce qui manque reste visible.",
    landingPromiseMoteur: "Entrée, circulation, sanitaires, stationnement.",
    landingPromiseAuditif: "Boucle magnétique, signalétique, personnel formé.",
    landingPromiseVisuel: "Guidage, contraste, éclairage, lecteurs d'écran.",
    landingPromiseMental: "Calme, attente, consignes claires, accompagnement.",
    landingDataTitle: "La donnée est ouverte. Le code aussi.",
    landingDataIntro:
      "LetMeGetIn agrège des sources publiques et des contributions, puis expose le tout via une API. Rien n'est enfermé dans une application propriétaire.",
    landingDataPlaces: "lieux",
    landingDataCategories: "catégories",
    landingDataCriteria: "critères",
    landingDataSources: "Sources",
    landingDataSourcesValue: "Acceslibre (Etalab 2.0) · OpenStreetMap (ODbL) · Overture",
    landingDataLicences: "Licences",
    landingDataLicencesValue: "Etalab 2.0 · ODbL",
    landingDataCode: "Code source",
    landingDataCodeValue: "GitHub · Let-Me-Get-In/letmegetin",
    landingApiTitle: "Une API publique pour bâtir dessus.",
    landingApiIntro:
      "Cherchez par proximité, filtrez par famille de handicap, lisez une fiche complète. La documentation est ouverte, les clés se demandent en ligne.",
    landingApiDocs: "Lire la documentation API",
    landingApiGithub: "Voir le code source",
    landingApiExample: "Exemple de requête",
    landingApiResponse: "Réponse",
    landingContributeTitle: "La donnée s'améliore quand quelqu'un la corrige.",
    landingContributeIntro:
      "Une marche ajoutée, un sanitaire adapté, une boucle magnétique installée : signalez ce qui a changé. Chaque contribution est journalisée et la fiche reste lisible par tous.",
    landingContributeCta: "Contribuer à une fiche",
    landingContributeNote: "Un compte suffit. La consultation reste ouverte sans compte.",
    landingFooterTagline: "L'accessibilité des lieux, pour de vrai.",
    landingFooterContact: "Contact",
    landingFooterSource: "Code source",
    landingFooterLicences: "Licences et sources",
    landingFooterApp: "Ouvrir l'application",
    landingFooterNote: "Projet open source. Données sous licences ouvertes.",
    landingBackToTop: "Retour en haut",
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
    places: { one: "place", many: "places" },
    more: "Load more",
    loading: "Loading…",
    searching: "Searching…",
    footer: "LetMeGetIn — an open accessibility referential.",
    sources: "Data: Acceslibre (Etalab 2.0), OpenStreetMap (ODbL), Overture.",

    // Search
    searchLoading: "Loading the search…",
    searchUnavailable: "Search is unavailable.",
    noMorePlaces: "No more places.",
    placesAdded: { one: "place added", many: "places added" },
    geoUnavailable: "Geolocation is not available in this browser.",
    geoDenied: "Location denied: search stays centred on Paris.",
    searchPlaceholder: "Name, category, address…",
    criteriaLegend: "Accessibility criteria",
    noPlaces: "No places found. Try widening the radius or removing a filter.",
    unknownCategory: "Unknown category",
    possibleDuplicate: "Possible duplicate",
    mapAriaLabel:
      "Map of accessible places. The list beside it gives the same results by keyboard.",
    notProvided: "Not provided",
    yes: "Yes",
    no: "No",
    familyMoteur: "Mobility",
    familyAuditif: "Hearing",
    familyVisuel: "Vision",
    familyMental: "Cognitive / psychosocial",
    locating: "Locating…",

    // Record
    criterion: "Criterion",
    valueLabel: "Value",
    choose: "— Choose —",
    exampleNumber: "E.g. 90",
    saving: "Saving…",
    save: "Save",
    publishing: "Publishing…",
    publishReview: "Publish review",
    signInPrompt: "Sign in",
    toCompleteThisRecord: "to complete this record.",
    verifyToComplete: "Verify your email address to complete this record.",
    toLeaveAReview: "to leave a review.",
    verifyToReview: "Verify your email address to leave a review.",
    noCriteria: "No criteria available for this place.",
    noTree: "No accessibility grid is available for this place yet.",
    chooseValue: "Choose or enter a value.",
    contributionSaved: "Contribution saved. Thank you!",
    contributionFailed: "Contribution failed.",
    reviewPublished: "Review published. Thank you!",
    reviewFailed: "Review couldn't be published.",
    rating: "Rating",
    yourReview: "Your review",
    reviewPlaceholder: "Reception, access route, toilets…",
    verifyDisabled:
      "Your email address is not verified yet: contribution and reviews are disabled.",
    resendLink: "Resend the link",
    sending: "Sending…",
    verificationSent: "Verification link resent.",
    sendFailed: "Could not send.",
    noReviews: "No reviews for this place yet. Be the first to write one.",
    anonymous: "Anonymous",
    reviewPagination: "Review pagination",
    previous: "Previous",
    nextPage: "Next",
    backToSearch: "← Back to search",
    backToSearchPlain: "Back to search",
    notYetRated: "Not rated yet",
    unspecifiedSource: "Source not specified",
    completion: "Record completion",
    criteriaHaveValue: "{percent}% of criteria have a value.",
    reviewCountLine: "{count} reviews · {percent}% of the record filled",
    photos: "Photos",
    accessibilitySection: "Accessibility",
    completeThisRecord: "Complete this record",
    contributionHelp:
      "A value is missing or changed? Add it; every contribution is logged.",
    reviewsHeading: { one: "Review ({count})", many: "Reviews ({count})" },
    leaveAReview: "Leave a review",
    reviewHelp: "Rating from 1 to 5 and a free comment.",
    pageOf: "Page {page} / {count}",
    placeNotFoundTitle: "Place not found",
    placeNotFoundBody:
      "This record does not exist or has moved. Try a new search.",

    // Auth and account
    loginFolderIntro: "Sign in to contribute to a record or leave a review.",
    email: "Email",
    password: "Password",
    signInSubmit: "Sign in",
    signingIn: "Signing in…",
    loginFailed: "Could not sign in.",
    noAccountYet: "No account yet?",
    createAccountLink: "Create an account",
    registerFolderIntro:
      "An account lets you complete records and publish reviews. Contribution stays open to everyone and the data stays free.",
    displayName: "Display name (optional)",
    displayNamePlaceholder: "Appears on your reviews",
    passwordMinLength: "At least 8 characters.",
    registering: "Creating…",
    createMyAccount: "Create my account",
    alreadyRegistered: "Already registered?",
    registerFailed: "Could not register.",
    verifyHeading: "Email verification",
    verifyFolderIntro: "This page confirms the address linked to your account.",
    verifying: "Verifying…",
    verificationInProgress: "Verification in progress…",
    incompleteVerificationLink: "Incomplete verification link.",
    emailVerified: "Email address verified. Thank you!",
    verificationFailed: "Verification failed or the link expired.",
    goToAccount: "Go to my account",
    accountFolderIntro:
      "Your contributions and reviews are published under your display name.",
    emailLabel: "Email",
    displayNameLabel: "Display name",
    emailVerifiedLabel: "Email verified",
    roleLabel: "Role",
    searchLink: "Search for a place",
    signOut: "Sign out",
    loadingAccount: "Loading account…",
    redirectingToLogin: "Redirecting to sign in…",

    // Landing
    landingNavSearch: "Search",
    landingNavData: "The data",
    landingNavApi: "API",
    landingNavAbout: "About",
    landingOpenApp: "Open the app",
    landingHeroTitle: "Know if you can get in. Before you leave.",
    landingHeroIntro:
      "The real accessibility of places, checked criterion by criterion. Search a place, open its record, know what to expect.",
    landingSearchLabel: "Search for a place",
    landingSearchPlaceholder: "Address, place, city",
    landingSearchSubmit: "Search",
    landingSearchHint: "Search opens in the app.",
    landingTrust: "634,931 places in France · open data",
    landingExampleBadge: "Sample record",
    landingExampleName: "Neighbourhood café",
    landingExampleAddress: "Paris 11e",
    landingExampleStatus: "Accessible",
    landingExampleMeta: "12 criteria filled",
    landingExampleEntrance: "Step-free entrance",
    landingExampleToilets: "Adapted toilets",
    landingExampleLoop: "Hearing loop",
    landingExampleStaff: "Trained staff",
    landingExampleLink: "See a record",
    landingPromiseTitle: "A record, not a vague rating.",
    landingPromiseIntro:
      "Every place is described by typed criteria, grouped by disability family. What is filled is dated; what is missing stays visible.",
    landingPromiseMoteur: "Entrance, circulation, toilets, parking.",
    landingPromiseAuditif: "Hearing loop, signage, trained staff.",
    landingPromiseVisuel: "Wayfinding, contrast, lighting, screen readers.",
    landingPromiseMental: "Quiet, waiting, clear instructions, support.",
    landingDataTitle: "The data is open. The code too.",
    landingDataIntro:
      "LetMeGetIn combines public sources and contributions, then exposes everything through an API. Nothing is locked inside a proprietary app.",
    landingDataPlaces: "places",
    landingDataCategories: "categories",
    landingDataCriteria: "criteria",
    landingDataSources: "Sources",
    landingDataSourcesValue: "Acceslibre (Etalab 2.0) · OpenStreetMap (ODbL) · Overture",
    landingDataLicences: "Licences",
    landingDataLicencesValue: "Etalab 2.0 · ODbL",
    landingDataCode: "Source code",
    landingDataCodeValue: "GitHub · Let-Me-Get-In/letmegetin",
    landingApiTitle: "A public API to build on.",
    landingApiIntro:
      "Search by proximity, filter by disability family, read a complete record. The documentation is open and keys are requested online.",
    landingApiDocs: "Read the API documentation",
    landingApiGithub: "See the source code",
    landingApiExample: "Sample request",
    landingApiResponse: "Response",
    landingContributeTitle: "The data improves when someone corrects it.",
    landingContributeIntro:
      "A step added, an adapted toilet, a hearing loop installed: report what changed. Every contribution is logged and the record stays readable by everyone.",
    landingContributeCta: "Contribute to a record",
    landingContributeNote: "An account is enough. Reading stays open without one.",
    landingFooterTagline: "Accessibility of places, for real.",
    landingFooterContact: "Contact",
    landingFooterSource: "Source code",
    landingFooterLicences: "Licences and sources",
    landingFooterApp: "Open the app",
    landingFooterNote: "Open-source project. Data under open licences.",
    landingBackToTop: "Back to top",
  },
} as const;

type Messages = (typeof MESSAGES)["fr"];

// `t` only accepts keys that are plain strings; a plural key is an object and is
// therefore unreachable through `t`, so a plural word can only come from `tPlural`.
export type StringMessageKey = {
  [K in keyof Messages]: Messages[K] extends string ? K : never;
}[keyof Messages];

export type PluralKey = {
  [K in keyof Messages]: Messages[K] extends { one: string; many: string } ? K : never;
}[keyof Messages];

export function t(locale: Locale, key: StringMessageKey): string {
  return MESSAGES[locale][key] ?? MESSAGES[DEFAULT_LOCALE][key];
}

// French counts 0 as singular ("0 lieu"), English does not ("0 places").
export function tPlural(locale: Locale, key: PluralKey, count: number): string {
  const message = MESSAGES[locale][key] ?? MESSAGES[DEFAULT_LOCALE][key];
  const singular = count === 1 || (locale === "fr" && count === 0);
  return singular ? message.one : message.many;
}

export function format(message: string, vars: Record<string, string | number>): string {
  return message.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    name in vars ? String(vars[name]) : placeholder,
  );
}
