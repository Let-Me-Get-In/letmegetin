"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/api";
import { flattenCriteria } from "@/lib/criteria";
import { t, type Locale } from "@/lib/i18n";
import { label } from "@/lib/labels";
import { useSession } from "@/lib/session";
import type { TreeNode } from "@/lib/types";

type Status = { kind: "idle" | "ok" | "error"; message: string };

export function ContributionForm({
  slug,
  tree,
  locale,
}: {
  slug: string;
  tree: TreeNode[];
  locale: Locale;
}) {
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
          {t(locale, "signInPrompt")}
        </Link>{" "}
        {t(locale, "toCompleteThisRecord")}
      </p>
    );
  }

  if (!user.email_verified) {
    return <p className="text-sm text-muted">{t(locale, "verifyToComplete")}</p>;
  }

  if (criteria.length === 0) {
    return <p className="text-sm text-muted">{t(locale, "noCriteria")}</p>;
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!criterion) return;

    let value: unknown;
    if (criterion.options.length > 0) value = choice;
    else if (criterion.type === "boolean") value = choice === "oui";
    else value = text.trim();

    if (value === "" || value === undefined || value === null) {
      setStatus({ kind: "error", message: t(locale, "chooseValue") });
      return;
    }

    setPending(true);
    setStatus({ kind: "idle", message: "" });
    try {
      await authedFetch(`/api/v1/places/${slug}/accessibility/${criterion.slug}`, {
        method: "PUT",
        body: JSON.stringify({ value }),
      });
      setStatus({ kind: "ok", message: t(locale, "contributionSaved") });
      setChoice("");
      setText("");
      router.refresh();
    } catch (error) {
      setStatus({
        kind: "error",
        message: error instanceof ApiError ? error.message : t(locale, "contributionFailed"),
      });
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label htmlFor="criterion" className="block text-sm font-medium">
          {t(locale, "criterion")}
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
              {label(item.label, locale)}
            </option>
          ))}
        </select>
      </div>

      {criterion && criterion.options.length > 0 ? (
        <div>
          <label htmlFor="value" className="block text-sm font-medium">
            {t(locale, "valueLabel")}
          </label>
          <select
            id="value"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
            value={choice}
            onChange={(event) => setChoice(event.target.value)}
          >
            <option value="">{t(locale, "choose")}</option>
            {/* The submitted value is the slug, never the display label: the stored
                accessibility value must not depend on the interface language. */}
            {criterion.options.map((option) => (
              <option key={option.slug} value={option.slug}>
                {label(option.label, locale)}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {criterion && criterion.options.length === 0 && criterion.type === "boolean" ? (
        <div>
          <label htmlFor="value" className="block text-sm font-medium">
            {t(locale, "valueLabel")}
          </label>
          <select
            id="value"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
            value={choice}
            onChange={(event) => setChoice(event.target.value)}
          >
            <option value="">{t(locale, "choose")}</option>
            <option value="oui">{t(locale, "yes")}</option>
            <option value="non">{t(locale, "no")}</option>
          </select>
        </div>
      ) : null}

      {criterion && criterion.options.length === 0 && criterion.type !== "boolean" ? (
        <div>
          <label htmlFor="value" className="block text-sm font-medium">
            {t(locale, "valueLabel")}
          </label>
          <input
            id="value"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder={t(locale, "exampleNumber")}
          />
        </div>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-accent px-4 py-2 font-medium text-paper disabled:opacity-50"
      >
        {pending ? t(locale, "saving") : t(locale, "save")}
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
