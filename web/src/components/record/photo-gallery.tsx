import type { Photo } from "@/lib/types";

export function PhotoGallery({ photos }: { photos: Photo[] }) {
  if (photos.length === 0) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {photos.map((photo) => (
        <figure key={photo.url} className="overflow-hidden rounded-card border border-line">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photo.url}
            alt=""
            loading="lazy"
            className="h-48 w-full object-cover"
          />
          <figcaption className="px-3 py-2 text-xs text-muted">
            {photo.credit ?? "Source non précisée"}
            {photo.license ? ` · ${photo.license}` : ""}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}
