import type { TreeNode } from "@/lib/types";

export type CriterionOption = { slug: string; label: Record<string, string> };

export type FlatCriterion = {
  slug: string;
  label: Record<string, string>;
  type: string;
  options: CriterionOption[];
};

export function flattenCriteria(tree: TreeNode[]): FlatCriterion[] {
  const criteria: FlatCriterion[] = [];
  for (const group of tree) {
    for (const node of group.children) {
      if (node.type === "array" || node.type === "option") continue;
      criteria.push({
        slug: node.slug,
        label: node.label,
        type: node.type,
        options: node.children
          .filter((child) => child.type === "option")
          .map((child) => ({ slug: child.slug, label: child.label })),
      });
    }
  }
  return criteria;
}
