import type { ReactNode } from "react";

export function Muted({ children }: { children: ReactNode }) {
  return <span style={{ color: "var(--muted)" }}>{children}</span>;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h2 style={{ fontSize: 16, fontWeight: 700 }}>{children}</h2>;
}

export function Small({ children }: { children: ReactNode }) {
  return <span style={{ fontSize: 12, color: "var(--muted)" }}>{children}</span>;
}
