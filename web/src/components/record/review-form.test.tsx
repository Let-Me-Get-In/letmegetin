import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReviewForm } from "./review-form";

const session = vi.hoisted(() => ({ useSession: vi.fn() }));
vi.mock("@/lib/session", () => ({ useSession: session.useSession }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

const verified = {
  user: { id: 1, email: "a@b.test", role: "user", display_name: "A", email_verified: true },
  authedFetch: vi.fn(),
};

beforeEach(() => {
  session.useSession.mockReset();
  verified.authedFetch.mockReset();
});

describe("ReviewForm", () => {
  it("asks an unverified user to verify the email", () => {
    session.useSession.mockReturnValue({
      user: { ...verified.user, email_verified: false },
      authedFetch: vi.fn(),
    });

    render(<ReviewForm slug="demo" />);

    expect(screen.getByText(/Vérifiez votre adresse email/)).toBeInTheDocument();
  });

  it("posts the rating and the body", async () => {
    verified.authedFetch.mockResolvedValue({});
    session.useSession.mockReturnValue(verified);

    render(<ReviewForm slug="demo" />);
    fireEvent.change(screen.getByLabelText("Note"), { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText("Votre avis"), {
      target: { value: "Accueil très bien" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Publier l'avis" }));

    await waitFor(() =>
      expect(verified.authedFetch).toHaveBeenCalledWith("/api/v1/places/demo/reviews", {
        method: "POST",
        body: JSON.stringify({ rating: 4, body: "Accueil très bien" }),
      }),
    );
  });
});
