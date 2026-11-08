import { cookies } from "next/headers";

import { AccountView } from "@/components/account/account-view";
import { LOCALE_COOKIE, parseLocale } from "@/lib/i18n";

export default async function AccountPage() {
  // Same source of truth as the layout: the cookie decides the interface language,
  // so the server renders the first paint in the reader's language.
  const locale = parseLocale((await cookies()).get(LOCALE_COOKIE)?.value);
  return <AccountView locale={locale} />;
}
