import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  maxWidth?: number;
};

export default function ConsoleCard({ children, maxWidth = 420 }: Props) {
  return (
    <section
      style={{
        width: "100%",
        maxWidth,
        border: "1px solid rgba(0,0,0,0.12)",
        borderRadius: 12,
        padding: 24,
      }}
    >
      {children}
    </section>
  );
}
