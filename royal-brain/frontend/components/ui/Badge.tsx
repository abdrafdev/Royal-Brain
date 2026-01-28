import type { ReactNode } from "react";

type Tone = "info" | "success" | "warning" | "error" | "neutral";

const toneColor: Record<Tone, { bg: string; fg: string }> = {
  info: { bg: "rgba(62,168,255,0.14)", fg: "#9bd4ff" },
  success: { bg: "rgba(32,201,151,0.16)", fg: "#7be2c4" },
  warning: { bg: "rgba(240,173,78,0.16)", fg: "#f9d7a6" },
  error: { bg: "rgba(242,95,92,0.16)", fg: "#ffb6b3" },
  neutral: { bg: "rgba(255,255,255,0.08)", fg: "#eef2ff" },
};

type Props = {
  children: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
};

export default function Badge({ children, tone = "neutral", icon }: Props) {
  const palette = toneColor[tone];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 10px",
        borderRadius: 999,
        background: palette.bg,
        color: palette.fg,
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: "-0.01em",
      }}
    >
      {icon ? <span style={{ display: "inline-flex" }}>{icon}</span> : null}
      {children}
    </span>
  );
}
