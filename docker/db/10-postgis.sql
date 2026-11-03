-- Runs once, on first initialisation of an empty data directory.
-- Idempotent on purpose: a re-run must not fail the entrypoint.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
