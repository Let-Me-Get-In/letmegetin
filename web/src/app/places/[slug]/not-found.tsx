import Link from "next/link";

export default function PlaceNotFound() {
  return (
    <section className="mx-auto max-w-xl py-16 text-center">
      <h1 className="text-3xl font-semibold">Lieu introuvable</h1>
      <p className="mt-3 text-muted">
        Cette fiche n'existe pas ou a été déplacée. Essayez une nouvelle recherche.
      </p>
      <Link
        href="/"
        className="mt-6 inline-block rounded-md bg-accent px-4 py-2 font-medium text-paper"
      >
        Retour à la recherche
      </Link>
    </section>
  );
}
