import type { Metadata } from "next";
import type { ReactNode } from "react";

import { SiteHeader } from "@/components/site-header";
import { SessionProvider } from "@/lib/session";

import "./globals.css";

export const metadata: Metadata = {
  title: "LetMeGetIn — l'accessibilité des lieux, pour de vrai",
  description:
    "Recherchez des lieux accessibles et consultez leur fiche d'accessibilité détaillée : motricité, audition, vision, cognition.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-paper text-ink antialiased">
        <SessionProvider>
          <a
            href="#contenu"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-accent focus:px-4 focus:py-2 focus:text-paper"
          >
            Aller au contenu
          </a>
          <SiteHeader />
          <main id="contenu" className="mx-auto w-full max-w-6xl px-4 py-8">
            {children}
          </main>
          <footer className="mt-16 border-t border-line">
            <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
              <p>LetMeGetIn — référentiel ouvert d'accessibilité.</p>
              <p>Données : Acceslibre (Etalab 2.0), OpenStreetMap (ODbL), Overture.</p>
            </div>
          </footer>
        </SessionProvider>
      </body>
    </html>
  );
}
