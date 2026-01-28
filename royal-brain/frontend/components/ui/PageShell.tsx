import Link from "next/link";
import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export default function PageShell({ title, description, actions, children }: Props) {
  return (
    <div className="container">
      <header className="row-between" style={{ marginBottom: 16 }}>
        <div>
          <div className="heading" style={{ fontSize: 22 }}>
            {title}
          </div>
          {description ? (
            <div className="subtle" style={{ marginTop: 6, fontSize: 14 }}>
              {description}
            </div>
          ) : null}
        </div>
        {actions ? <div className="row">{actions}</div> : null}
      </header>
      <nav
        className="row"
        style={{
          gap: 12,
          marginBottom: 20,
          fontSize: 13,
          color: "var(--muted)",
        }}
      >
        <Link href="/dashboard">Home</Link>
        <span>•</span>
        <Link href="/dashboard/genealogy">Genealogy</Link>
        <span>•</span>
        <Link href="/dashboard/succession">Succession</Link>
        <span>•</span>
        <Link href="/dashboard/validation/jurisdiction">Validation</Link>
        <span>•</span>
        <Link href="/dashboard/orders">Orders</Link>
        <span>•</span>
        <Link href="/dashboard/heraldry">Heraldry</Link>
        <span>•</span>
        <Link href="/logout">Logout</Link>
      </nav>
      <div className="grid" style={{ gap: 16 }}>
        {children}
      </div>
    </div>
  );
}
