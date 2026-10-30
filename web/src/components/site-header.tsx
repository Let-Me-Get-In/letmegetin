"use client";

import Link from "next/link";

import { useSession } from "@/lib/session";

export function SiteHeader() {
  const { user, loading, logout } = useSession();

  return (
    <header className="border-b border-line bg-paper/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
        <Link href="/" className="font-display text-xl font-semibold tracking-tight">
          Let<span className="text-accent">Me</span>GetIn
        </Link>
        <nav aria-label="Navigation principale" className="flex items-center gap-4 text-sm">
          <Link className="hover:text-accent" href="/">
            Rechercher
          </Link>
          {loading ? (
            <span className="text-muted" aria-hidden="true">
              …
            </span>
          ) : user ? (
            <>
              <Link className="hover:text-accent" href="/account">
                Mon compte
              </Link>
              <button
                type="button"
                className="rounded-md border border-line px-3 py-1.5 hover:border-accent hover:text-accent"
                onClick={() => void logout()}
              >
                Déconnexion
              </button>
            </>
          ) : (
            <Link
              className="rounded-md bg-accent px-3 py-1.5 text-paper hover:opacity-90"
              href="/login"
            >
              Connexion
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
