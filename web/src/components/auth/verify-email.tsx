"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";

type Status = { kind: "pending" | "ok" | "error"; message: string };

export function VerifyEmail() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [status, setStatus] = useState<Status>({
    kind: "pending",
    message: "Vérification en cours…",
  });

  useEffect(() => {
    if (!token) {
      setStatus({ kind: "error", message: "Lien de vérification incomplet." });
      return;
    }
    let active = true;
    api("/api/v1/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then(() => {
        if (active) setStatus({ kind: "ok", message: "Adresse email vérifiée. Merci !" });
      })
      .catch((error) => {
        if (active) {
          setStatus({
            kind: "error",
            message:
              error instanceof ApiError ? error.message : "Vérification impossible ou lien expiré.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [token]);

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
        Aller à mon compte
      </Link>
    </div>
  );
}
