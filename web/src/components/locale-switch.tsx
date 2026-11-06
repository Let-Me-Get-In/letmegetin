"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { LOCALE_COOKIE, type Locale } from "@/lib/i18n";

// The choice is a cookie, not localStorage, so the server can read it and put it
// on <html lang>: assistive tech announces the language from that attribute, and a
// client-only preference would leave it wrong on first paint.
const ONE_YEAR = 60 * 60 * 24 * 365;

// Outside the component: the React compiler forbids assigning to a value defined
// outside a component's scope from inside it.
function rememberLocale(next: Locale) {
  document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${ONE_YEAR}; samesite=lax`;
}

export function LocaleSwitch({ locale, label }: { locale: Locale; label: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function choose(next: Locale) {
    if (next === locale) return;
    rememberLocale(next);
    startTransition(() => router.refresh());
  }

  return (
    <div className="flex items-center gap-1 text-sm" role="group" aria-label={label}>
      {(["fr", "en"] as const).map((value) => (
        <button
          key={value}
          type="button"
          lang={value}
          onClick={() => choose(value)}
          disabled={pending}
          aria-pressed={value === locale}
          className={`rounded px-2 py-1 uppercase ${
            value === locale ? "bg-accent text-paper" : "text-muted hover:text-accent"
          }`}
        >
          {value}
        </button>
      ))}
    </div>
  );
}
