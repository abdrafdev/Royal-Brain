import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Input from "@/components/ui/Input";
import PageShell from "@/components/ui/PageShell";
import Select from "@/components/ui/Select";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

type Me = { email?: string; role?: string };

type Person = {
  id: number;
  primary_name?: string;
};

type Order = {
  id: number;
  name: string;
  jurisdiction_id?: number | null;
  classification?: string | null;
  legitimacy_score?: number | null;
  fraud_flags?: string[] | null;
  last_legitimacy_check?: string | null;
  fons_honorum_person_id?: number | null;
  founding_document_source_id?: number | null;
  recognized_by?: string[] | null;
  granted_date?: string | null;
  grantor_person_id?: number | null;
};

type SourceReference = {
  id: number;
  source_type: string;
  citation: string;
  url?: string | null;
  issued_date?: string | null;
};

type Explanation = {
  summary: string;
  detailed_reasoning: string;
  citations: { category: string; description: string }[];
  confidence: number;
  sources: SourceReference[];
  rules_applied: Record<string, unknown>;
};

type OrderValidationResponse = {
  result: {
    order_id: number;
    order_name: string;
    claimant_person_id: number;
    classification: "LEGITIMATE" | "SELF_STYLED" | "DISPUTED" | "FRAUDULENT";
    legitimacy_score: number;
    fraud_flags: string[];
    factors: {
      fons_honorum_valid: boolean;
      fons_honorum_detail: string;
      succession_valid: boolean | null;
      succession_detail: string;
      jurisdiction_recognition: { recognized: string[]; not_recognized: string[]; partial: string[] };
      documentation_score: number;
      documentation_detail: string;
      timeline_issues_count: number;
      timeline_detail: string;
    };
    sources: number[];
  };
  explanation: Explanation;
  audit_id: number;
};

type PageProps = {
  searchParams: Promise<{ claimant?: string; order?: string; as_of?: string }>;
};

function toneForClassification(c: string) {
  if (c === "LEGITIMATE") return "success";
  if (c === "FRAUDULENT") return "error";
  if (c === "DISPUTED") return "warning";
  return "neutral";
}

export default async function OrdersPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const claimantId = params.claimant ? Number.parseInt(params.claimant, 10) : undefined;
  const orderId = params.order ? Number.parseInt(params.order, 10) : undefined;
  const asOf = (params.as_of ?? "").trim() || undefined;

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  const [meResp, personsResp, ordersResp] = await Promise.all([
    fetch(`${backendUrl}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
    fetch(`${backendUrl}/persons?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
    fetch(`${backendUrl}/orders?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
  ]);

  if (meResp.status === 401 || meResp.status === 403) redirect("/logout");
  if (personsResp.status === 401 || personsResp.status === 403) redirect("/logout");
  if (ordersResp.status === 401 || ordersResp.status === 403) redirect("/logout");

  if (!meResp.ok || !personsResp.ok || !ordersResp.ok) {
    const meBody = await meResp.text().catch(() => "");
    const pBody = await personsResp.text().catch(() => "");
    const oBody = await ordersResp.text().catch(() => "");

    return (
      <PageShell title="Orders Engine" description="Day 7 legitimacy scoring & fraud detection">
        <Alert tone="error" title="Backend error while loading data">
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {meResp.ok ? "" : `Me: ${meResp.status}\n${meBody}\n\n`}
            {personsResp.ok ? "" : `Persons: ${personsResp.status}\n${pBody}\n\n`}
            {ordersResp.ok ? "" : `Orders: ${ordersResp.status}\n${oBody}`}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  const me = (await meResp.json()) as Me;
  const persons = (await personsResp.json()) as Person[];
  const orders = (await ordersResp.json()) as Order[];

  const orderLookup = new Map<number, Order>(orders.map((o) => [o.id, o]));
  const selectedOrder = orderId ? orderLookup.get(orderId) : undefined;

  let validation: OrderValidationResponse | null = null;
  let validationError: { status: number; body: string } | null = null;

  if (claimantId && orderId) {
    const resp = await fetch(`${backendUrl}/api/v1/validate/order`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        order_id: orderId,
        claimant_person_id: claimantId,
        as_of: asOf ?? null,
      }),
      cache: "no-store",
    });

    if (resp.ok) {
      validation = (await resp.json()) as OrderValidationResponse;
    } else {
      validation = null;
      validationError = { status: resp.status, body: await resp.text().catch(() => "") };
    }
  }

  return (
    <PageShell title="Orders Engine" description="Legitimacy scoring • Fraud flags • AI explainability">
      <Card
        title="Validate an order"
        description="Choose claimant (person) and order. The system will score legitimacy and detect fraud flags."
        actions={
          me.role === "ADMIN" ? (
            <Link href="/dashboard/orders/fraud-report" className="subtle">
              Fraud report →
            </Link>
          ) : null
        }
      >
        <form method="GET" className="grid" style={{ gap: 12 }}>
          <div className="grid" style={{ gap: 8 }}>
            <Select name="claimant" defaultValue={claimantId ?? ""} label="Claimant (person)">
              <option value="">-- select --</option>
              {persons.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.primary_name ?? `Person ${p.id}`} (#{p.id})
                </option>
              ))}
            </Select>

            <Select
              name="order"
              defaultValue={orderId ?? ""}
              label="Order"
              hint={
                selectedOrder
                  ? `stored: ${selectedOrder.classification ?? "(unclassified)"} • score: ${
                      selectedOrder.legitimacy_score ?? "(n/a)"
                    } • fons: ${selectedOrder.fons_honorum_person_id ?? "(none)"}`
                  : undefined
              }
            >
              <option value="">-- select --</option>
              {orders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name} (#{o.id})
                </option>
              ))}
            </Select>

            <Input
              name="as_of"
              type="date"
              label="As-of date (optional)"
              defaultValue={asOf ?? ""}
              hint="Affects genealogy/succession checks when relevant."
            />
          </div>

          <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
            <button
              type="submit"
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid var(--border)",
                background: "var(--panel-soft)",
                color: "var(--text)",
                cursor: "pointer",
              }}
            >
              Validate
            </button>
          </div>
        </form>
      </Card>

      {validationError ? (
        <Card title="Validation failed">
          <Alert tone="error" title={`Backend error ${validationError.status}`}>
            <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{validationError.body}</pre>
          </Alert>
          <div className="subtle" style={{ fontSize: 12, marginTop: 10 }}>
            Note: validation includes AI explainability. If OpenAI is not configured, a deterministic explanation will be returned.
          </div>
        </Card>
      ) : null}

      {validation ? (
        <>
          <Card title="Result" description={`audit_id: ${validation.audit_id} • score: ${validation.result.legitimacy_score}/100`}>
            <div className="row" style={{ gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
              <Badge tone={toneForClassification(validation.result.classification)}>
                {validation.result.classification}
              </Badge>
              <Badge tone="neutral">Order #{validation.result.order_id}</Badge>
              <Badge tone="neutral">Claimant #{validation.result.claimant_person_id}</Badge>
              <Badge tone="info">Score {validation.result.legitimacy_score}</Badge>
            </div>

            {validation.result.fraud_flags.length ? (
              <Alert tone="warning" title="Fraud flags">
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {validation.result.fraud_flags.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </Alert>
            ) : (
              <Alert tone="success">No fraud flags detected from available data.</Alert>
            )}

            <div className="grid" style={{ gap: 12, marginTop: 12 }}>
              <Alert
                tone={validation.result.factors.fons_honorum_valid ? "success" : "warning"}
                title="Fons honorum"
              >
                {validation.result.factors.fons_honorum_detail}
              </Alert>

              <Alert
                tone={
                  validation.result.factors.succession_valid === true
                    ? "success"
                    : validation.result.factors.succession_valid === false
                    ? "error"
                    : "info"
                }
                title="Succession"
              >
                {validation.result.factors.succession_detail}
              </Alert>

              <Alert tone="info" title={`Documentation score: ${validation.result.factors.documentation_score}/100`}>
                {validation.result.factors.documentation_detail}
              </Alert>

              <Alert
                tone={validation.result.factors.timeline_issues_count ? "warning" : "success"}
                title={`Timeline: ${validation.result.factors.timeline_issues_count} issue(s)`}
              >
                {validation.result.factors.timeline_detail}
              </Alert>

              <Card title="Jurisdiction recognition">
                <div className="grid" style={{ gap: 10 }}>
                  <div>
                    <div className="subtle" style={{ fontSize: 12, marginBottom: 4 }}>
                      Recognized
                    </div>
                    <div className="subtle" style={{ fontSize: 13 }}>
                      {validation.result.factors.jurisdiction_recognition.recognized.length
                        ? validation.result.factors.jurisdiction_recognition.recognized.join(", ")
                        : "(none)"}
                    </div>
                  </div>
                  <div>
                    <div className="subtle" style={{ fontSize: 12, marginBottom: 4 }}>
                      Partial
                    </div>
                    <div className="subtle" style={{ fontSize: 13 }}>
                      {validation.result.factors.jurisdiction_recognition.partial.length
                        ? validation.result.factors.jurisdiction_recognition.partial.join(", ")
                        : "(none)"}
                    </div>
                  </div>
                  <div>
                    <div className="subtle" style={{ fontSize: 12, marginBottom: 4 }}>
                      Not recognized
                    </div>
                    <div className="subtle" style={{ fontSize: 13 }}>
                      {validation.result.factors.jurisdiction_recognition.not_recognized.length
                        ? validation.result.factors.jurisdiction_recognition.not_recognized.join(", ")
                        : "(none)"}
                    </div>
                  </div>
                </div>
              </Card>

              <Card title="Sources" description="IDs used in the validation result">
                <div className="subtle" style={{ fontSize: 13 }}>
                  {validation.result.sources.length ? validation.result.sources.join(", ") : "(none)"}
                </div>
              </Card>
            </div>
          </Card>

          <Card title="AI explanation" description="Day 5 explainability (no-hallucination)">
            {validation.explanation &&
            !validation.explanation.summary.toLowerCase().startsWith("ai explanation failed") ? (
              <>
                <Alert tone="info" title="Summary">
                  {validation.explanation.summary}
                </Alert>

                <div className="row" style={{ gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                  <Badge tone="neutral">
                    confidence: {(validation.explanation.confidence * 100).toFixed(1)}%
                  </Badge>
                  <Badge tone="neutral">
                    sources: {validation.explanation.sources.length}
                  </Badge>
                </div>

                <div
                  className="subtle"
                  style={{ marginTop: 12, whiteSpace: "pre-wrap", lineHeight: 1.6 }}
                >
                  {validation.explanation.detailed_reasoning}
                </div>

                <details style={{ marginTop: 14 }}>
                  <summary style={{ cursor: "pointer", fontWeight: 600 }}>
                    Sources ({validation.explanation.sources.length})
                  </summary>
                  {validation.explanation.sources.length ? (
                    <ul style={{ marginTop: 8, paddingLeft: 18 }}>
                      {validation.explanation.sources.map((s) => (
                        <li key={s.id}>
                          <span style={{ fontWeight: 700 }}>#{s.id}</span> ({s.source_type}) {s.citation}
                          {s.issued_date ? (
                            <span className="subtle" style={{ fontSize: 12 }}>
                              {" "}
                              • {s.issued_date}
                            </span>
                          ) : null}
                          {s.url ? (
                            <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>
                              <a href={s.url} target="_blank" rel="noreferrer">
                                {s.url}
                              </a>
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="subtle" style={{ fontSize: 13, marginTop: 8 }}>
                      (none)
                    </div>
                  )}
                </details>

                <details style={{ marginTop: 12 }}>
                  <summary style={{ cursor: "pointer", fontWeight: 600 }}>Rules applied</summary>
                  <pre
                    style={{
                      marginTop: 8,
                      whiteSpace: "pre-wrap",
                      background: "var(--panel-soft)",
                      border: "1px solid var(--border)",
                      borderRadius: 10,
                      padding: 10,
                      fontSize: 12,
                    }}
                  >
                    {JSON.stringify(validation.explanation.rules_applied, null, 2)}
                  </pre>
                </details>

                {validation.explanation.citations?.length ? (
                  <div style={{ marginTop: 14 }}>
                    <div className="subtle" style={{ fontSize: 12, marginBottom: 6 }}>
                      Citations
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {validation.explanation.citations.map((c, idx) => (
                        <li key={idx}>
                          <span style={{ fontWeight: 700 }}>{c.category}:</span> {c.description}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </>
            ) : (
              <Alert tone="warning" title="AI explanation unavailable">
                <div className="subtle" style={{ fontSize: 13 }}>
                  Result classification and scores above are still valid, but the AI explanation service is
                  currently unavailable or over quota.
                </div>
              </Alert>
            )}
          </Card>
        </>
      ) : (
        <Card title="Status">
          <Alert tone="info">Select a claimant and an order, then click Validate.</Alert>
        </Card>
      )}

      <Card title="Orders" description="Current database snapshot">
        {orders.length ? (
          <div className="grid" style={{ gap: 10 }}>
            {orders
              .slice()
              .sort((a, b) => b.id - a.id)
              .slice(0, 20)
              .map((o) => (
                <div key={o.id} className="row-between" style={{ gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{o.name}</div>
                    <div className="subtle" style={{ fontSize: 12, marginTop: 2 }}>
                      id #{o.id}
                      {o.jurisdiction_id ? ` • jurisdiction_id ${o.jurisdiction_id}` : ""}
                    </div>
                  </div>
                  <div className="row" style={{ gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                    <Badge tone={toneForClassification(o.classification ?? "")}>{o.classification ?? "(unclassified)"}</Badge>
                    <Badge tone="neutral">score: {o.legitimacy_score ?? "n/a"}</Badge>
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <Alert tone="warning">No orders found. Create one via the Orders API first.</Alert>
        )}
      </Card>
    </PageShell>
  );
}
