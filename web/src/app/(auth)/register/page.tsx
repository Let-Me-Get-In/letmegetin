import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = { title: "Créer un compte — LetMeGetIn" };

export default function RegisterPage() {
  return (
    <section className="mx-auto max-w-md py-8">
      <h1 className="text-3xl font-semibold">Créer un compte</h1>
      <p className="mb-6 mt-2 text-sm text-muted">
        Un compte permet de compléter les fiches et de publier des avis. La contribution reste
        ouverte à tous et la donnée reste libre.
      </p>
      <RegisterForm />
    </section>
  );
}
