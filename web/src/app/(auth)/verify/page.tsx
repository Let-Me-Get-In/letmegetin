import type { Metadata } from "next";
import { Suspense } from "react";

import { VerifyEmail } from "@/components/auth/verify-email";

export const metadata: Metadata = { title: "Vérification de l'email — LetMeGetIn" };

export default function VerifyPage() {
  return (
    <section className="mx-auto max-w-md py-8">
      <h1 className="text-3xl font-semibold">Vérification de l'email</h1>
      <p className="mb-6 mt-2 text-sm text-muted">
        Cette page confirme l'adresse associée à votre compte.
      </p>
      <Suspense fallback={<p className="text-sm text-muted">Vérification…</p>}>
        <VerifyEmail />
      </Suspense>
    </section>
  );
}
