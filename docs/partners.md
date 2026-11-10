# Partenaires

LetMeGetIn exposes a normalised accessibility referential as an open API. A partner does not
have to rebuild the data model, the criteria tree or the official labels: it can read them and
put them in front of its own audience.

The public partner page is planned at **`letmegetin.org/partenaires`**, not on a subdomain. A
subdomain will only make sense when there is a real partner portal (keys, quotas, support,
integrator directory). Until then, a page that tells the truth is enough.

## The open ledger

The page can borrow the ledger composition from the landing comps: show the chain, not a logo
wall.

```
Sources ouvertes            Acceslibre (Etalab 2.0) · OpenStreetMap (ODbL) · Overture
        │
        ▼
Référentiel normalisé       catégories · critères typés · labels officiels
        │
        ▼
API publique                recherche · fiche · grille · filtres
        │
        ▼
Votre produit               guide · carte · parcours · service public
```

Each step is a fact, not a promise. The sources and their licences stay visible; attribution is
part of the deal.

## Who it is for

- Offices de tourisme and local authorities publishing accessible places.
- Associations and guides that already maintain a list and want a shared referential.
- Developers building a map, a route planner or an accessibility filter.
- Integrators who need a stable read API rather than a scraping target.

## What a partner can do today

- Read the public API: `GET /api/v1/places`, `/places/{slug}`, `/categories`,
  `/categories/{slug}/criteria`, `/categories/{slug}/grid`.
- Request a partner key for a higher rate limit; anonymous reads are limited per IP.
- Cite the sources and licences shown on every record.
- Contribute corrections through the application.

Start with [`docs/public-api.md`](public-api.md) for the endpoints, pagination, filters and rate
limits.

## What does not exist yet

No self-service portal, no SLA, no white-label product, no partner logo wall. The page should
not imply otherwise. The contact address is the honest next step:
[contact@letmegetin.org](mailto:contact@letmegetin.org).

## Page brief (LET-65)

- Route `/partenaires`, rendered with the marketing header and footer.
- Ledger hero, then audience, API, licences/coverage, contribution and contact.
- Primary action: read the API docs. Secondary: write to contact@letmegetin.org.
- Link it from the landing API section and the footer.
- French first, English when the page is localized.
- Index only on the production apex; noindex on dev and on the app host.
