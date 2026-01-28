import type { ReactNode } from "react";

type Tone = "info" | "success" | "warning" | "error";

const palette: Record<Tone, { bg: string; border: string; fg: string }> = {
  info: { bg: "rgba(62,168,255,0.1)", border: "rgba(62,168,255,0.3)", fg: "#b8deff" },
  success: { bg: "rgba(32,201,151,0.1)", border: "rgba(32,201,151,0.3)", fg: "#a8f0d6" },
  warning: { bg: "rgba(240,173,78,0.12)", border: "rgba(240,173,78,0.35)", fg: "#fbe2b6" },
  error: { bg: "rgba(242,95,92,0.12)", border: "rgba(242,95,92,0.35)", fg: "#ffc7c4" },
};

type Props = {
  title?: string;
  children: ReactNode;
  tone?: Tone;
  dense?: boolean;
};

export default function Alert({ title, children, tone = "info", dense = false }: Props) {
  const p = palette[tone];
  return (
    <div
      style={{
        background: p.bg,
        border: `1px solid ${p.border}`,
        color: p.fg,
        borderRadius: 12,
        padding: dense ? "8px 10px" : "12px 14px",
      }}
    >
      {title ? (
        <div style={{ fontWeight: 700, marginBottom: dense ? 4 : 6, color: p.fg }}>{title}</div>
      ) : null}
      <div style={{ fontSize: 14, lineHeight: 1.4 }}>{children}</div>
    </div>
  );
}
