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

type FraudReport = {
  min_score: number;
  max_score: number;
  total_orders: number;
  by_classification: Record<string, number>;
  by_flag: Record<string, number>;
  orders: {
    id: number;
    name: string;
    classification?: string | null;
    legitimacy_score?: number | null;
    fraud_flags: string[];
    last_legitimacy_check?: string | null;
  }[];
};

type PageProps = {
  searchParams: Promise<{ min_score?: string; max_score?: string }>;
};

function asInt(v: string | undefined, fallback: number) {
  const n = v ? Number.parseInt(v, 10) : NaN;
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(100, n));
}

export default async function FraudReportPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const minScore = asInt(params.min_score, 0);
  const maxScore = asInt(params.max_score, 100);

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
    const body = await meResp.text().catch(() => "");
    return (
      <PageShell title="Fraud report" description="Day 7">
        <Alert tone="error" title={`Backend error ${meResp.status}`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{body}</pre>
        </Alert>
      </PageShell>
    );
  }

  const me = (await meResp.json()) as { role?: string };
  if (me.role !== "ADMIN") {
    return (
      <PageShell title="Fraud report" description="ADMIN only">
        <Alert tone="error" title="Access denied">
          This page requires ADMIN role.
        </Alert>
        <div style={{ marginTop: 12 }}>
          <Link href="/dashboard/orders" className="subtle">
            ← Back to Orders
          </Link>
        </div>
      </PageShell>
    );
  }

  const reportResp = await fetch(
    `${backendUrl}/api/v1/orders/fraud-report?min_score=${minScore}&max_score=${maxScore}`,
    {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    },
  );

  if (reportResp.status === 401 || reportResp.status === 403) redirect("/logout");

  if (!reportResp.ok) {
    const body = await reportResp.text().catch(() => "");
    return (
      <PageShell title="Fraud report" description="Day 7">
        <Alert tone="error" title={`Backend error ${reportResp.status}`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{body}</pre>
        </Alert>
      </PageShell>
    );
  }

  const report = (await reportResp.json()) as FraudReport;

  const classifications = Object.entries(report.by_classification).sort((a, b) => b[1] - a[1]);
  const flags = Object.entries(report.by_flag).sort((a, b) => b[1] - a[1]);

  return (
    <PageShell title="Fraud report" description={`Orders scored ${report.min_score}–${report.max_score} (ADMIN)`}>
      <Card
        title="Filters"
        description="Adjust score range and reload"
        actions={
          <Link href="/dashboard/orders" className="subtle">
            Back to Orders →
          </Link>
        }
      >
        <form method="GET" className="row" style={{ gap: 10, flexWrap: "wrap" }}>
          <div style={{ width: 180 }}>
            <Input name="min_score" type="number" label="Min score" defaultValue={minScore} />
          </div>
          <div style={{ width: 180 }}>
            <Input name="max_score" type="number" label="Max score" defaultValue={maxScore} />
          </div>
          <div className="row" style={{ alignItems: "flex-end" }}>
            <button
              type="submit"
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid var(--border)",
                background: "var(--panel-soft)",
                color: "var(--text)",
                cursor: "pointer",
                height: 42,
              }}
            >
              Apply
            </button>
          </div>
        </form>
      </Card>

      <Card title="Summary">
        <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
          <Badge tone="info">Total: {report.total_orders}</Badge>
          <Badge tone="neutral">Range: {report.min_score}–{report.max_score}</Badge>
        </div>
      </Card>

      <Card title="By classification">
        {classifications.length ? (
          <div className="grid" style={{ gap: 8 }}>
            {classifications.map(([k, v]) => (
              <div key={k} className="row-between">
                <span>{k}</span>
                <Badge tone="neutral">{v}</Badge>
              </div>
            ))}
          </div>
        ) : (
          <Alert tone="info">No classified orders in this score range.</Alert>
        )}
      </Card>

      <Card title="By fraud flag">
        {flags.length ? (
          <div className="grid" style={{ gap: 8 }}>
            {flags.map(([k, v]) => (
              <div key={k} className="row-between">
                <span>{k}</span>
                <Badge tone="warning">{v}</Badge>
              </div>
            ))}
          </div>
        ) : (
          <Alert tone="success">No fraud flags recorded in this score range.</Alert>
        )}
      </Card>

      <Card title="Orders" description="Most relevant entries">
        {report.orders.length ? (
          <div className="grid" style={{ gap: 10 }}>
            {report.orders
              .slice()
              .sort((a, b) => (a.legitimacy_score ?? 999) - (b.legitimacy_score ?? 999))
              .slice(0, 50)
              .map((o) => (
                <div key={o.id} className="row-between" style={{ gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{o.name}</div>
                    <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>
                      id #{o.id}
                      {o.last_legitimacy_check ? ` • checked ${o.last_legitimacy_check}` : ""}
                    </div>
                  </div>
                  <div className="row" style={{ gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                    <Badge tone="neutral">score: {o.legitimacy_score ?? "n/a"}</Badge>
                    <Badge tone={o.classification === "FRAUDULENT" ? "error" : o.classification === "LEGITIMATE" ? "success" : "warning"}>
                      {o.classification ?? "(unclassified)"}
                    </Badge>
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <Alert tone="info">No orders found in this range.</Alert>
        )}
      </Card>
    </PageShell>
  );
}
