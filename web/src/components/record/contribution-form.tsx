"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/api";
import { flattenCriteria } from "@/lib/criteria";
import { label } from "@/lib/labels";
import { useSession } from "@/lib/session";
import type { TreeNode } from "@/lib/types";

type Status = { kind: "idle" | "ok" | "error"; message: string };

export function ContributionForm({ slug, tree }: { slug: string; tree: TreeNode[] }) {
  const { user, authedFetch } = useSession();
  const router = useRouter();
  const criteria = flattenCriteria(tree);

  const [criterionSlug, setCriterionSlug] = useState(criteria[0]?.slug ?? "");
  const [choice, setChoice] = useState("");
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: "idle", message: "" });

  const criterion = criteria.find((item) => item.slug === criterionSlug);

  if (!user) {
    return (
      <p className="text-sm text-muted">
        <Link className="underline" href={`/login?next=${encodeURIComponent(`/places/${slug}`)}`}>
          Connectez-vous
        </Link>{" "}
        pour compléter cette fiche.
      </p>
    );
  }

  if (!user.email_verified) {
    return (
      <p className="text-sm text-muted">
        Vérifiez votre adresse email pour compléter cette fiche.
      </p>
    );
  }

  if (criteria.length === 0) {
    return <p className="text-sm text-muted">Aucun critère disponible pour ce lieu.</p>;
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!criterion) return;

    let value: unknown;
    if (criterion.options.length > 0) value = choice;
    else if (criterion.type === "boolean") value = choice === "oui";
    else value = text.trim();

    if (value === "" || value === undefined || value === null) {
      setStatus({ kind: "error", message: "Choisissez ou saisissez une valeur." });
      return;
    }

    setPending(true);
    setStatus({ kind: "idle", message: "" });
    try {
      await authedFetch(`/api/v1/places/${slug}/accessibility/${criterion.slug}`, {
        method: "PUT",
        body: JSON.stringify({ value }),
      });
      setStatus({ kind: "ok", message: "Contribution enregistrée. Merci !" });
      setChoice("");
      setText("");
      router.refresh();
    } catch (error) {
      setStatus({
        kind: "error",
        message: error instanceof ApiError ? error.message : "Contribution impossible.",
      });
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label htmlFor="criterion" className="block text-sm font-medium">
          Critère
        </label>
        <select
          id="criterion"
          className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
          value={criterionSlug}
          onChange={(event) => {
            setCriterionSlug(event.target.value);
            setChoice("");
            setText("");
            setStatus({ kind: "idle", message: "" });
          }}
        >
          {criteria.map((item) => (
            <option key={item.slug} value={item.slug}>
              {label(item.label)}
            </option>
          ))}
        </select>
      </div>

      {criterion && criterion.options.length > 0 ? (
        <div>
          <label htmlFor="value" className="block text-sm font-medium">
            Valeur
          </label>
          <select
            id="value"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
            value={choice}
            onChange={(event) => setChoice(event.target.value)}
          >
            <option value="">— Choisir —</option>
            {criterion.options.map((option) => (
              <option key={option.slug} value={label(option.label)}>
                {label(option.label)}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {criterion && criterion.options.length === 0 && criterion.type === "boolean" ? (
        <div>
          <label htmlFor="value" className="block text-sm font-medium">
            Valeur
          </label>
          <select
            id="value"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
            value={choice}
            onChange={(event) => setChoice(event.target.value)}
          >
            <option value="">— Choisir —</option>
            <option value="oui">Oui</option>
            <option value="non">Non</option>
          </select>
        </div>
      ) : null}

      {criterion && criterion.options.length === 0 && criterion.type !== "boolean" ? (
        <div>
          <label htmlFor="value" className="block text-sm font-medium">
            Valeur
          </label>
          <input
            id="value"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Ex. 90"
          />
        </div>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-accent px-4 py-2 font-medium text-paper disabled:opacity-50"
      >
        {pending ? "Enregistrement…" : "Enregistrer"}
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
