"use client";

import Link from "next/link";

import { RequireAuth } from "@/components/auth/require-auth";
import { VerifyBanner } from "@/components/auth/verify-banner";
import { useSession } from "@/lib/session";

export default function AccountPage() {
  const { user, logout } = useSession();

  return (
    <RequireAuth>
      <section className="mx-auto max-w-2xl space-y-6 py-8">
        <div>
          <h1 className="text-3xl font-semibold">Mon compte</h1>
          <p className="mt-2 text-sm text-muted">
            Vos contributions et avis sont publiés sous votre nom affiché.
          </p>
        </div>

        <VerifyBanner />

        <dl className="divide-y divide-line rounded-card border border-line bg-white/60 dark:bg-white/5">
          <div className="flex flex-wrap justify-between gap-2 px-4 py-3">
            <dt className="text-sm text-muted">Email</dt>
            <dd className="font-medium">{user?.email}</dd>
          </div>
          <div className="flex flex-wrap justify-between gap-2 px-4 py-3">
            <dt className="text-sm text-muted">Nom affiché</dt>
            <dd className="font-medium">{user?.display_name ?? "Anonyme"}</dd>
          </div>
          <div className="flex flex-wrap justify-between gap-2 px-4 py-3">
            <dt className="text-sm text-muted">Email vérifié</dt>
            <dd className="font-medium">{user?.email_verified ? "Oui" : "Non"}</dd>
          </div>
          <div className="flex flex-wrap justify-between gap-2 px-4 py-3">
            <dt className="text-sm text-muted">Rôle</dt>
            <dd className="font-medium">{user?.role}</dd>
          </div>
        </dl>

        <div className="flex flex-wrap gap-3">
          <Link className="rounded-md border border-line px-4 py-2 text-sm" href="/">
            Rechercher un lieu
          </Link>
          <button
            type="button"
            className="rounded-md border border-warn px-4 py-2 text-sm text-warn"
            onClick={() => void logout()}
          >
            Se déconnecter
          </button>
        </div>
      </section>
    </RequireAuth>
  );
}
