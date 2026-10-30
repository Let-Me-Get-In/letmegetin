import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import type { TreeNode } from "@/lib/types";

import { ContributionForm } from "./contribution-form";

const session = vi.hoisted(() => ({ useSession: vi.fn() }));
vi.mock("@/lib/session", () => ({ useSession: session.useSession }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

const tree: TreeNode[] = [
  {
    slug: "entree",
    label: { fr: "Entrée" },
    type: "array",
    children: [
      {
        slug: "entree-acces",
        label: { fr: "Accès" },
        type: "boolean",
        children: [],
      },
    ],
  },
];

const verified = {
  user: { id: 1, email: "a@b.test", role: "user", display_name: "A", email_verified: true },
  authedFetch: vi.fn(),
};

beforeEach(() => {
  session.useSession.mockReset();
  verified.authedFetch.mockReset();
});

describe("ContributionForm", () => {
  it("asks an anonymous visitor to log in", () => {
    session.useSession.mockReturnValue({ user: null, authedFetch: vi.fn() });

    render(<ContributionForm slug="demo" tree={tree} />);

    expect(screen.getByText(/Connectez-vous/)).toBeInTheDocument();
  });

  it("sends a boolean value for a verified user", async () => {
    verified.authedFetch.mockResolvedValue({});
    session.useSession.mockReturnValue(verified);

    render(<ContributionForm slug="demo" tree={tree} />);
    fireEvent.change(screen.getByLabelText("Valeur"), { target: { value: "oui" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));

    await waitFor(() =>
      expect(verified.authedFetch).toHaveBeenCalledWith(
        "/api/v1/places/demo/accessibility/entree-acces",
        { method: "PUT", body: JSON.stringify({ value: true }) },
      ),
    );
  });

  it("shows the API error when the write is refused", async () => {
    verified.authedFetch.mockRejectedValue(new ApiError(403, "Email verification required"));
    session.useSession.mockReturnValue(verified);

    render(<ContributionForm slug="demo" tree={tree} />);
    fireEvent.change(screen.getByLabelText("Valeur"), { target: { value: "non" } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer" }));

    await waitFor(() =>
      expect(screen.getByText("Email verification required")).toBeInTheDocument(),
    );
  });
});
