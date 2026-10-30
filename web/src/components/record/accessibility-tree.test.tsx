import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AccessibilityTree } from "@/components/record/accessibility-tree";
import type { TreeNode } from "@/lib/types";

const tree: TreeNode[] = [
  {
    slug: "entree",
    label: { fr: "Entrée" },
    type: "array",
    children: [
      {
        slug: "entree-acces",
        label: { fr: "Accès" },
        type: "multichoice",
        value: { value: "De plain-pied" },
        children: [],
      },
      {
        slug: "entree-largeur",
        label: { fr: "Largeur de porte (cm)" },
        type: "user_value",
        value: { value: 90 },
        children: [],
      },
      {
        slug: "entree-sanitaires",
        label: { fr: "Sanitaires" },
        type: "boolean",
        value: null,
        children: [],
      },
    ],
  },
];

describe("AccessibilityTree", () => {
  it("renders the group and each criterion value", () => {
    render(<AccessibilityTree tree={tree} />);

    expect(screen.getByRole("heading", { name: "Entrée" })).toBeInTheDocument();
    expect(screen.getByText("De plain-pied")).toBeInTheDocument();
    expect(screen.getByText("90")).toBeInTheDocument();
    expect(screen.getByText("Non renseigné")).toBeInTheDocument();
  });

  it("explains an empty grid", () => {
    render(<AccessibilityTree tree={[]} />);

    expect(screen.getByText(/Aucune grille/)).toBeInTheDocument();
  });
});
