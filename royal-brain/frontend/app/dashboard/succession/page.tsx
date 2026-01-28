import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import PageShell from "@/components/ui/PageShell";
import Select from "@/components/ui/Select";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";
import AIExplanationButton from "./AIExplanationButton";

type Person = {
  id: number;
  primary_name?: string;
};

type EvalResult = {
  status: "VALID" | "INVALID" | "UNCERTAIN";
  path_person_ids?: number[] | null;
  relationship_ids?: number[] | null;
  reasons: {
    code: string;
    message: string;
    severity: string;
    person_id?: number | null;
    relationship_id?: number | null;
  }[];
  rule_type: string;
  root_person_id: number;
  candidate_person_id: number;
  checked_paths: number;
};

type PageProps = {
  searchParams: Promise<{
    root?: string;
    candidate?: string;
    rule?: string;
  }>;
};

const RULE_OPTIONS = [
  { value: "agnatic", label: "Agnatic (male line only)" },
  { value: "cognatic", label: "Cognatic (gender-neutral)" },
  { value: "salic", label: "Salic (strict agnatic)" },
  { value: "semi_salic", label: "Semi-salic (female can transmit; male heir)" },
];

export default async function SuccessionPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const rootId = params.root ? Number.parseInt(params.root, 10) : undefined;
  const candId = params.candidate ? Number.parseInt(params.candidate, 10) : undefined;
  const rule = params.rule ?? "agnatic";

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  const personsResp = await fetch(`${backendUrl}/persons?limit=200`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (personsResp.status === 401 || personsResp.status === 403) redirect("/logout");
  if (!personsResp.ok) {
    const body = await personsResp.text();
    return (
      <PageShell title="Succession Engine" description="Rule-based lineage validation">
        <Alert tone="error" title={`Backend error ${personsResp.status}`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{body}</pre>
        </Alert>
      </PageShell>
    );
  }
  const persons = (await personsResp.json()) as Person[];

  let evaluation: EvalResult | null = null;
  if (rootId && candId && rule) {
    const evalResp = await fetch(`${backendUrl}/succession/evaluate`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        root_person_id: rootId,
        candidate_person_id: candId,
        rule_type: rule,
      }),
      cache: "no-store",
    });

    if (evalResp.ok) {
      evaluation = (await evalResp.json()) as EvalResult;
    } else {
      evaluation = null;
    }
  }

  return (
    <PageShell title="Succession Rule Engine" description="Deterministic lineage validation">
      <Card title="Evaluate a claim" description="Select root, candidate, and rule set.">
        <form method="GET" className="grid" style={{ gap: 12 }}>
          <div className="grid" style={{ gap: 8 }}>
            <Select name="root" defaultValue={rootId ?? ""} label="Root person">
              <option value="">-- select --</option>
              {persons.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.primary_name ?? `Person ${p.id}`} (#{p.id})
                </option>
              ))}
            </Select>

            <Select name="candidate" defaultValue={candId ?? ""} label="Candidate heir">
              <option value="">-- select --</option>
              {persons.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.primary_name ?? `Person ${p.id}`} (#{p.id})
                </option>
              ))}
            </Select>

            <Select name="rule" defaultValue={rule} label="Rule set">
              {RULE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </Select>
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
              Evaluate
            </button>
          </div>
        </form>
      </Card>

      {evaluation ? (
        <Card
          title="Result"
          description={`Rule: ${evaluation.rule_type} • Paths checked: ${evaluation.checked_paths}`}
        >
          <div className="row" style={{ gap: 10, marginBottom: 12 }}>
            <Badge
              tone={
                evaluation.status === "VALID"
                  ? "success"
                  : evaluation.status === "INVALID"
                  ? "error"
                  : "warning"
              }
            >
              {evaluation.status}
            </Badge>
            <Badge tone="neutral">Root #{evaluation.root_person_id}</Badge>
            <Badge tone="neutral">Candidate #{evaluation.candidate_person_id}</Badge>
          </div>

          {evaluation.path_person_ids ? (
            <div className="subtle" style={{ marginBottom: 12 }}>
              Path: {evaluation.path_person_ids.join(" → ")}
            </div>
          ) : null}

          {evaluation.reasons.length ? (
            <div className="grid" style={{ gap: 10 }}>
              {evaluation.reasons.map((r, idx) => (
                <Alert
                  key={idx}
                  tone={r.severity === "error" ? "error" : r.severity === "warning" ? "warning" : "info"}
                  dense
                  title={r.code}
                >
                  <div>{r.message}</div>
                  <div className="subtle" style={{ fontSize: 12, marginTop: 4 }}>
                    {r.person_id ? `person:${r.person_id} ` : ""}
                    {r.relationship_id ? `rel:${r.relationship_id}` : ""}
                  </div>
                </Alert>
              ))}
            </div>
          ) : (
            <Alert tone="success">No issues reported.</Alert>
          )}
          <AIExplanationButton evaluation={evaluation} />
        </Card>
      ) : (
        <Card title="Status">
          <Alert tone="info">Select a root and candidate, then click Evaluate.</Alert>
          <div className="subtle" style={{ fontSize: 12, marginTop: 8 }}>
            <div>Rules:</div>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              <li>Agnatic/Salic: male-only inheritance and transmission.</li>
              <li>Semi-salic: female may transmit, heir must be male.</li>
              <li>Cognatic: gender-neutral.</li>
            </ul>
          </div>
        </Card>
      )}
    </PageShell>
  );
}
