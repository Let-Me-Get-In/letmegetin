"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";

export function RegisterForm() {
  const { register } = useSession();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await register(email, password, displayName);
      router.push("/account");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Inscription impossible.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
        />
      </div>
      <div>
        <label htmlFor="display_name" className="block text-sm font-medium">
          Nom affiché (optionnel)
        </label>
        <input
          id="display_name"
          type="text"
          autoComplete="nickname"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
          placeholder="Apparaît sur vos avis"
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium">
          Mot de passe
        </label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
        />
        <p className="mt-1 text-xs text-muted">8 caractères minimum.</p>
      </div>
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-md bg-accent px-4 py-2 font-medium text-paper disabled:opacity-50"
      >
        {pending ? "Création…" : "Créer mon compte"}
      </button>
      {error ? (
        <p role="alert" className="text-sm text-warn">
          {error}
        </p>
      ) : null}
      <p className="text-sm text-muted">
        Déjà inscrit ?{" "}
        <Link className="underline" href="/login">
          Se connecter
        </Link>
      </p>
    </form>
  );
}
