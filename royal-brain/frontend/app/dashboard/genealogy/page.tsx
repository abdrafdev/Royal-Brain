import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Input from "@/components/ui/Input";
import PageShell from "@/components/ui/PageShell";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

type PersonListItem = {
  id: number;
  primary_name?: string;
  birth_date?: string | null;
  death_date?: string | null;
};

type PageProps = {
  searchParams: Promise<{ q?: string }>;
};

export default async function GenealogyIndexPage({ searchParams }: PageProps) {
  const { q = "" } = await searchParams;

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  const resp = await fetch(`${backendUrl}/persons?limit=200`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (resp.status === 401 || resp.status === 403) redirect("/logout");

  if (!resp.ok) {
    const body = await resp.text();
    return (
      <PageShell title="Genealogy" description="Persons and lineages">
        <Alert tone="error" title={`Backend error ${resp.status}`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{body}</pre>
        </Alert>
      </PageShell>
    );
  }

  const persons = (await resp.json()) as PersonListItem[];
  const filtered = q
    ? persons.filter((p) =>
        (p.primary_name ?? "").toLowerCase().includes(q.toLowerCase().trim()),
      )
    : persons;

  return (
    <PageShell title="Genealogy" description="Multi-generation family trees">
      <Card
        title="People"
        description="Select a person to view their tree"
        actions={
          <form method="get" className="row" style={{ gap: 8 }}>
            <Input
              name="q"
              placeholder="Search name…"
              defaultValue={q}
              style={{ width: 220 }}
            />
            <button type="submit" style={{ display: "none" }}>
              Search
            </button>
          </form>
        }
      >
        {filtered.length === 0 ? (
          <Alert tone="info">No persons found. Add some via the API first.</Alert>
        ) : (
          <table className="table" style={{ marginTop: 4 }}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Birth</th>
                <th>Death</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontWeight: 600 }}>{p.primary_name ?? `(Person ${p.id})`}</td>
                  <td className="subtle">{p.birth_date ?? "—"}</td>
                  <td className="subtle">{p.death_date ?? "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <Link href={`/dashboard/genealogy/${p.id}`} className="subtle">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Engine status">
        <div className="row" style={{ gap: 12 }}>
          <Badge tone="success">Live</Badge>
          <span className="subtle">Timeline checks available on each person detail page.</span>
        </div>
      </Card>
    </PageShell>
  );
}
