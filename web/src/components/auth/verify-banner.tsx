"use client";

import { useState } from "react";

import { ApiError } from "@/lib/api";
import { t, type Locale } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export function VerifyBanner({ locale }: { locale: Locale }) {
  const { user, authedFetch } = useSession();
  const [message, setMessage] = useState("");

  if (!user || user.email_verified) return null;

  async function resend() {
    setMessage(t(locale, "sending"));
    try {
      await authedFetch("/api/v1/auth/resend-verification", { method: "POST" });
      setMessage(t(locale, "verificationSent"));
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : t(locale, "sendFailed"));
    }
  }

  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-3 rounded-card border border-warn/40 bg-warn/10 px-4 py-3 text-sm"
    >
      <p className="flex-1">{t(locale, "verifyDisabled")}</p>
      <button
        type="button"
        className="rounded-md border border-warn px-3 py-1.5 font-medium text-warn hover:bg-warn/10"
        onClick={() => void resend()}
      >
        {t(locale, "resendLink")}
      </button>
      {message ? <span className="text-muted">{message}</span> : null}
    </div>
  );
}
