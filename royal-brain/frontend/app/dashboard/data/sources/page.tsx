import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Card from "@/components/ui/Card";
import PageShell from "@/components/ui/PageShell";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";
import SourceManager from "./SourceManager";

type Source = {
  id: number;
  source_type: string;
  citation: string;
  issued_date: string | null;
  url: string | null;
  notes: string | null;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
};

export default async function SourcesPage() {
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
      <PageShell title="Source Management" description="Documentary evidence">
        <Alert tone="error" title="Access Denied">
          Only Admins and Researchers can manage sources.
        </Alert>
      </PageShell>
    );
  }

  const sourcesResp = await fetch(`${backendUrl}/sources?limit=200`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!sourcesResp.ok) {
    return (
      <PageShell title="Source Management" description="Documentary evidence">
        <Alert tone="error" title={`Failed to load sources (${sourcesResp.status})`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {await sourcesResp.text()}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  const sources = (await sourcesResp.json()) as Source[];

  return (
    <PageShell title="Source Management" description="Documentary evidence registry">
      <Card title="Sources" description={`${sources.length} registered sources`}>
        <SourceManager sources={sources} />
      </Card>
    </PageShell>
  );
}
