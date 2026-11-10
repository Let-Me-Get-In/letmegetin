import { ImageResponse } from "next/og";

export const alt = "LetMeGetIn — savoir si on peut entrer avant de partir";
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
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="38" height="38" viewBox="0 0 96 96">
              <path
                fill="#f7f4ec"
                fillRule="evenodd"
                d="M22 24h52a12 12 0 0 1 12 12v40H10V36a12 12 0 0 1 12-12Zm-4 52V56a20 20 0 0 1 40 0v20H18Z"
              />
            </svg>
          </div>
          <div style={{ display: "flex", fontSize: "42px", fontWeight: 700, letterSpacing: "-1px" }}>
            LetMeGet<span style={{ color: "#1f6f4a" }}>In</span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              maxWidth: "980px",
              fontSize: "70px",
              fontWeight: 700,
              lineHeight: 1.04,
              letterSpacing: "-2px",
            }}
          >
            <div style={{ display: "flex" }}>Savoir si on peut entrer.</div>
            <div style={{ display: "flex" }}>Avant de partir.</div>
          </div>
          <div style={{ display: "flex", fontSize: "30px", color: "#4b5850" }}>
            L&apos;accessibilité des lieux, pour de vrai.
          </div>
        </div>

        <div style={{ display: "flex", fontSize: "24px", color: "#4b5850" }}>
          letmegetin.org — 634 931 lieux en France · référentiel ouvert
        </div>
      </div>
    ),
    size,
  );
}
