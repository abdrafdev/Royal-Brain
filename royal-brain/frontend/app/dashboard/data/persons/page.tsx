import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Card from "@/components/ui/Card";
import PageShell from "@/components/ui/PageShell";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";
import PersonManager from "./PersonManager";

type Person = {
  id: number;
  primary_name: string;
  sex: string | null;
  birth_date: string | null;
  death_date: string | null;
  notes: string | null;
  valid_from: string;
  source_ids: number[];
};

type Source = {
  id: number;
  source_type: string;
  citation: string;
};

export default async function PersonsPage() {
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
      <PageShell title="Person Management" description="Genealogical records">
        <Alert tone="error" title="Access Denied">
          Only Admins and Researchers can manage persons.
        </Alert>
      </PageShell>
    );
  }

  // Fetch persons
  const personsResp = await fetch(`${backendUrl}/persons?limit=200`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!personsResp.ok) {
    return (
      <PageShell title="Person Management" description="Genealogical records">
        <Alert tone="error" title={`Failed to load persons (${personsResp.status})`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {await personsResp.text()}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  const persons = (await personsResp.json()) as Person[];

  // Fetch sources for dropdown
  const sourcesResp = await fetch(`${backendUrl}/sources?limit=500`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  const sources = sourcesResp.ok ? ((await sourcesResp.json()) as Source[]) : [];

  return (
    <PageShell title="Person Management" description="Genealogical records database">
      <Card title="Persons" description={`${persons.length} registered persons`}>
        <PersonManager persons={persons} sources={sources} />
      </Card>
    </PageShell>
  );
}
