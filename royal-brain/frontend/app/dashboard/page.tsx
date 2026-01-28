import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import PageShell from "@/components/ui/PageShell";
import Alert from "@/components/ui/Alert";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;

  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  const meResp = await fetch(`${backendUrl}/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (meResp.status === 401 || meResp.status === 403) redirect("/logout");

  if (!meResp.ok) {
    const body = await meResp.text();
    return (
      <PageShell title="Dashboard" description="Authority-first console">
        <Alert tone="error" title={`Backend error ${meResp.status}`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{body}</pre>
        </Alert>
      </PageShell>
    );
  }

  const me = (await meResp.json()) as { email?: string; role?: string };

  return (
    <PageShell title="Royal BrAIn™" description="Identity • Authority • Auditability">
      <Card title="Authenticated identity" description="Session context">
        <div className="grid" style={{ gap: 8 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="subtle">Email</span>
            <span>{me.email ?? "(unknown)"}</span>
          </div>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="subtle">Role</span>
            <Badge tone="info">{me.role ?? "Unknown"}</Badge>
          </div>
        </div>
      </Card>

      {(me.role === "ADMIN" || me.role === "RESEARCHER") && (
        <Card title="Data Management" description="Enter and manage genealogical data">
          <div className="grid" style={{ gap: 12 }}>
            <div className="row-between">
              <div>
                <div style={{ fontWeight: 700 }}>Data Entry</div>
                <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                  Create persons, sources, relationships, and families.
                </div>
              </div>
              <Link href="/dashboard/data" className="subtle">
                Open →
              </Link>
            </div>
          </div>
        </Card>
      )}

      <Card title="Engines" description="Go straight to a module">
        <div className="grid" style={{ gap: 12 }}>
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Genealogy Engine v1</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Trees, timelines, consistency checks.
              </div>
            </div>
            <Link href="/dashboard/genealogy" className="subtle">
              Open →
            </Link>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Succession Rule Engine</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Deterministic lineage validity (Day 4).
              </div>
            </div>
            <Link href="/dashboard/succession" className="subtle">
              Open →
            </Link>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Jurisdiction Engine</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Jurisdiction-aware title validation (Day 6).
              </div>
            </div>
            <Link href="/dashboard/validation/jurisdiction" className="subtle">
              Open →
            </Link>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Orders Engine</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Legitimacy scoring + fraud detection (Day 7).
              </div>
            </div>
            <Link href="/dashboard/orders" className="subtle">
              Open →
            </Link>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Heraldry Engine</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Blazon parsing, validation, SVG generation (Day 8).
              </div>
            </div>
            <Link href="/dashboard/heraldry" className="subtle">
              Open →
            </Link>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Trust & Certification</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Cryptographic hashing, blockchain anchoring, certificates (Day 9).
              </div>
            </div>
            <Link href="/dashboard/trust" className="subtle">
              Open →
            </Link>
          </div>
        </div>
      </Card>

      {me.role === "ADMIN" && (
        <Card title="Administration" description="System management">
          <div className="grid" style={{ gap: 12 }}>
            <div className="row-between">
              <div>
                <div style={{ fontWeight: 700 }}>User Management</div>
                <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                  Create, edit, and delete user accounts.
                </div>
              </div>
              <Link href="/dashboard/admin/users" className="subtle">
                Open →
              </Link>
            </div>
          </div>
        </Card>
      )}

      <Card title="Auditability" description="Health & trust">
        <div className="grid" style={{ gap: 10, fontSize: 13 }}>
          <div>
            <span className="subtle">API</span>
            <span style={{ marginLeft: 8 }}>
              <Badge tone="success">Healthy</Badge>
            </span>
          </div>
          <div className="subtle">
            Actions are logged; view via backend `/audit/logs` (future UI link).
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
