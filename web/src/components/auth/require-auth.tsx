"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { t, type Locale } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export function RequireAuth({ locale, children }: { locale: Locale; children: ReactNode }) {
  const { user, loading } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, user, router, pathname]);

  if (loading) {
    return <p className="text-sm text-muted">{t(locale, "loadingAccount")}</p>;
  }
  if (!user) {
    return <p className="text-sm text-muted">{t(locale, "redirectingToLogin")}</p>;
  }
  return <>{children}</>;
}
