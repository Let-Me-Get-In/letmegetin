"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/api";
import { useSession } from "@/lib/session";

type Status = { kind: "idle" | "ok" | "error"; message: string };

export function ReviewForm({ slug }: { slug: string }) {
  const { user, authedFetch } = useSession();
  const router = useRouter();
  const [rating, setRating] = useState("5");
  const [body, setBody] = useState("");
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: "idle", message: "" });

  if (!user) {
    return (
      <p className="text-sm text-muted">
        <Link className="underline" href={`/login?next=${encodeURIComponent(`/places/${slug}`)}`}>
          Connectez-vous
        </Link>{" "}
        pour laisser un avis.
      </p>
    );
  }

  if (!user.email_verified) {
    return <p className="text-sm text-muted">Vérifiez votre adresse email pour laisser un avis.</p>;
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setStatus({ kind: "idle", message: "" });
    try {
      await authedFetch(`/api/v1/places/${slug}/reviews`, {
        method: "POST",
        body: JSON.stringify({ rating: Number(rating), body }),
      });
      setBody("");
      setStatus({ kind: "ok", message: "Avis publié. Merci !" });
      router.refresh();
    } catch (error) {
      setStatus({
        kind: "error",
        message: error instanceof ApiError ? error.message : "Publication impossible.",
      });
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <label htmlFor="rating" className="block text-sm font-medium">
          Note
        </label>
        <select
          id="rating"
          className="mt-1 rounded-md border border-line bg-paper px-3 py-2"
          value={rating}
          onChange={(event) => setRating(event.target.value)}
        >
          {[5, 4, 3, 2, 1].map((value) => (
            <option key={value} value={value}>
              {value}/5
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="body" className="block text-sm font-medium">
          Votre avis
        </label>
        <textarea
          id="body"
          className="mt-1 min-h-24 w-full rounded-md border border-line bg-paper px-3 py-2"
          value={body}
          maxLength={5000}
          onChange={(event) => setBody(event.target.value)}
          placeholder="Accueil, cheminement, sanitaires…"
        />
      </div>
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-accent px-4 py-2 font-medium text-paper disabled:opacity-50"
      >
        {pending ? "Publication…" : "Publier l'avis"}
      </button>
      {status.message ? (
        <p
          role="status"
          className={`text-sm ${status.kind === "error" ? "text-warn" : "text-accent"}`}
        >
          {status.message}
        </p>
      ) : null}
    </form>
  );
}
