import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";

import Card from "@/components/ui/Card";
import PageShell from "@/components/ui/PageShell";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

export default async function DataPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;

  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();
  const meResp = await fetch(`${backendUrl}/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (meResp.status === 401 || meResp.status === 403) redirect("/logout");

  const me = (await meResp.json()) as { role?: string };

  if (me.role !== "ADMIN" && me.role !== "RESEARCHER") {
    return (
      <PageShell title="Data Management" description="Entry forms">
        <Card title="Access Denied">
          <p>Only Admins and Researchers can access data entry forms.</p>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell title="Data Management" description="Create and manage genealogical data">
      <Card title="Data Entry" description="Choose what to create">
        <div className="grid" style={{ gap: 12 }}>
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Sources</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Register documentary evidence (birth certificates, legal documents, etc.)
              </div>
            </div>
            <Link href="/dashboard/data/sources" className="subtle">
              Open →
            </Link>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Persons</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Add individuals to the genealogical database
              </div>
            </div>
            <Link href="/dashboard/data/persons" className="subtle">
              Open →
            </Link>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Relationships</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Link persons (parent-child, marriage, adoption)
              </div>
            </div>
            <Link href="/dashboard/data/relationships" className="subtle">
              Open →
            </Link>
          </div>
          <div style={{ height: 1, background: "var(--border)" }} />
          <div className="row-between">
            <div>
              <div style={{ fontWeight: 700 }}>Families</div>
              <div className="subtle" style={{ fontSize: 13, marginTop: 2 }}>
                Create family groupings and dynasties
              </div>
            </div>
            <Link href="/dashboard/data/families" className="subtle">
              Open →
            </Link>
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
