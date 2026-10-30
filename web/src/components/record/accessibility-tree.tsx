import { formatValue, label } from "@/lib/labels";
import type { TreeNode } from "@/lib/types";

export function AccessibilityTree({ tree }: { tree: TreeNode[] }) {
  if (tree.length === 0) {
    return (
      <p className="rounded-card border border-line bg-accent-soft/40 p-4 text-sm text-muted">
        Aucune grille d'accessibilité n'est encore disponible pour ce lieu.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {tree.map((group) => (
        <section key={group.slug} aria-labelledby={`group-${group.slug}`}>
          <h3 id={`group-${group.slug}`} className="text-lg font-semibold">
            {label(group.label)}
          </h3>
          <dl className="mt-3 divide-y divide-line rounded-card border border-line bg-white/60 dark:bg-white/5">
            {group.children
              .filter((node) => node.type !== "array" && node.type !== "option")
              .map((criterion) => (
                <div
                  key={criterion.slug}
                  className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3"
                >
                  <dt className="font-medium">{label(criterion.label)}</dt>
                  <dd className="text-sm text-muted">{formatValue(criterion.value?.value)}</dd>
                </div>
              ))}
          </dl>
        </section>
      ))}
    </div>
  );
}
