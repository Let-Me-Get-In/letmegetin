"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import { t, type Locale } from "@/lib/i18n";

type Status = { kind: "pending" | "ok" | "error"; message: string };

export function VerifyEmail({ locale }: { locale: Locale }) {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [status, setStatus] = useState<Status>({
    kind: "pending",
    message: t(locale, "verificationInProgress"),
  });

  useEffect(() => {
    if (!token) {
      setStatus({ kind: "error", message: t(locale, "incompleteVerificationLink") });
      return;
    }
    let active = true;
    api("/api/v1/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then(() => {
        if (active) setStatus({ kind: "ok", message: t(locale, "emailVerified") });
      })
      .catch((error) => {
        if (active) {
          setStatus({
            kind: "error",
            message: error instanceof ApiError ? error.message : t(locale, "verificationFailed"),
          });
        }
      });
    return () => {
      active = false;
    };
  }, [token, locale]);

  return (
    <div className="space-y-4">
      <p
        role="status"
        className={`rounded-card border p-4 text-sm ${
          status.kind === "error"
            ? "border-warn/40 bg-warn/10"
            : "border-accent/40 bg-accent-soft/50"
        }`}
      >
        {status.message}
      </p>
      <Link className="inline-block rounded-md bg-accent px-4 py-2 text-paper" href="/account">
        {t(locale, "goToAccount")}
      </Link>
    </div>
  );
}
