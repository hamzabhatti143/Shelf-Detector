import { ImageResponse } from "next/og";
import { SITE } from "@/lib/config";

export const alt = `${SITE.name} | ${SITE.tagline}`;
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
          justifyContent: "center",
          padding: 80,
          background: "#09090b",
          color: "#fafafa",
        }}
      >
        <div style={{ fontSize: 40, color: "#a3e635", marginBottom: 24 }}>{SITE.name}</div>
        <div style={{ fontSize: 76, fontWeight: 700, lineHeight: 1.1 }}>{SITE.tagline}</div>
      </div>
    ),
    size,
  );
}