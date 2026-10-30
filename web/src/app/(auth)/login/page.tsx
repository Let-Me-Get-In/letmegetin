import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Connexion — LetMeGetIn" };

export default function LoginPage() {
  return (
    <section className="mx-auto max-w-md py-8">
      <h1 className="text-3xl font-semibold">Connexion</h1>
      <p className="mb-6 mt-2 text-sm text-muted">
        Connectez-vous pour contribuer à une fiche ou laisser un avis.
      </p>
      <Suspense fallback={<p className="text-sm text-muted">Chargement…</p>}>
        <LoginForm />
      </Suspense>
    </section>
  );
}
