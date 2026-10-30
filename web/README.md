# LetMeGetIn — web

Next.js (App Router) frontend for the public accessibility referential.

## Run locally

```bash
# from the repo root, with the API on :8000 and PostGIS on :55433
cd web
cp .env.example .env.local   # API_URL=http://localhost:8000
npm ci
npm run dev                  # http://localhost:3000
```

The browser only talks to the Next BFF (`/api/*`); the refresh token is an httpOnly cookie and the
access token stays in memory. `API_URL` is server-side only.

## Checks

```bash
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

## Map tiles

The map defaults to the OpenStreetMap raster tile server (fine for development and low volume).
A production deployment sets a provider that allows the traffic:

```bash
NEXT_PUBLIC_MAP_TILE_URL=https://your-tile-provider/{z}/{x}/{y}.png
NEXT_PUBLIC_MAP_ATTRIBUTION=© Your provider
```

## Security

The BFF sets the refresh token in an httpOnly, SameSite=Lax cookie and rejects state-changing
requests whose `Origin` is not the app origin. The access token stays in memory.
