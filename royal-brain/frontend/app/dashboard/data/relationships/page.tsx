import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Card from "@/components/ui/Card";
import PageShell from "@/components/ui/PageShell";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";
import RelationshipManager from "./RelationshipManager";

type Relationship = {
  id: number;
  relationship_type: string;
  left_entity_type: string;
  left_entity_id: number;
  right_entity_type: string;
  right_entity_id: number;
  valid_from: string;
  source_ids: number[];
};

type Person = {
  id: number;
  primary_name: string;
};

type Source = {
  id: number;
  source_type: string;
  citation: string;
};

export default async function RelationshipsPage() {
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
      <PageShell title="Relationship Management" description="Genealogical connections">
        <Alert tone="error" title="Access Denied">
          Only Admins and Researchers can manage relationships.
        </Alert>
      </PageShell>
    );
  }

  // Fetch relationships
  const relsResp = await fetch(`${backendUrl}/relationships?limit=500`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!relsResp.ok) {
    return (
      <PageShell title="Relationship Management" description="Genealogical connections">
        <Alert tone="error" title={`Failed to load relationships (${relsResp.status})`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{await relsResp.text()}</pre>
        </Alert>
      </PageShell>
    );
  }

  const relationships = (await relsResp.json()) as Relationship[];

  // Fetch persons for dropdown
  const personsResp = await fetch(`${backendUrl}/persons?limit=500`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  const persons = personsResp.ok ? ((await personsResp.json()) as Person[]) : [];

  // Fetch sources
  const sourcesResp = await fetch(`${backendUrl}/sources?limit=500`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  const sources = sourcesResp.ok ? ((await sourcesResp.json()) as Source[]) : [];

  return (
    <PageShell title="Relationship Management" description="Genealogical connections">
      <Card title="Relationships" description={`${relationships.length} registered relationships`}>
        <RelationshipManager
          relationships={relationships}
          persons={persons}
          sources={sources}
        />
      </Card>
    </PageShell>
  );
}
