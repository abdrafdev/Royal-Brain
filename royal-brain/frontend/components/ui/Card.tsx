import type { ReactNode } from "react";

type Props = {
  title?: string;
  description?: string;
  children: ReactNode;
  padded?: boolean;
  actions?: ReactNode;
};

export default function Card({ title, description, children, padded = true, actions }: Props) {
  return (
    <section
      className="card"
      style={{
        padding: padded ? "18px 20px" : "0",
        border: "1px solid var(--border)",
      }}
    >
      {(title || description || actions) && (
        <header
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 12,
            marginBottom: padded ? 12 : 16,
            padding: padded ? 0 : "16px 18px",
          }}
        >
          <div>
            {title ? <div style={{ fontWeight: 700 }}>{title}</div> : null}
            {description ? (
              <div style={{ marginTop: 4, color: "var(--muted)", fontSize: 13 }}>
                {description}
              </div>
            ) : null}
          </div>
          {actions ? <div style={{ display: "flex", gap: 8 }}>{actions}</div> : null}
        </header>
      )}
      <div style={{ padding: padded ? 0 : "0 18px 16px" }}>{children}</div>
    </section>
  );
}
