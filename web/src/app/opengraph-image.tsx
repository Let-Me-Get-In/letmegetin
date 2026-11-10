import { ImageResponse } from "next/og";

export const alt = "LetMeGetIn — trouver un lieu vraiment accessible";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background: "#f7f4ec",
          color: "#18211c",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <div
            style={{
              display: "flex",
              width: "56px",
              height: "56px",
              borderRadius: "14px",
              background: "#1f6f4a",
            }}
          />
          <div style={{ display: "flex", fontSize: "42px", fontWeight: 700, letterSpacing: "-1px" }}>
            LetMeGet<span style={{ color: "#1f6f4a" }}>In</span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          <div style={{ display: "flex", fontSize: "74px", fontWeight: 700, lineHeight: 1.05, letterSpacing: "-2px" }}>
            Trouver un lieu vraiment accessible.
          </div>
          <div style={{ display: "flex", fontSize: "30px", color: "#4b5850" }}>
            Motricité · Audition · Vision · Cognition
          </div>
        </div>

        <div style={{ display: "flex", fontSize: "24px", color: "#4b5850" }}>
          letmegetin.org — référentiel ouvert d&apos;accessibilité
        </div>
      </div>
    ),
    size,
  );
}
