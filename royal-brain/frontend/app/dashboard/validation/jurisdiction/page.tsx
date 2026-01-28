import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import Input from "@/components/ui/Input";
import PageShell from "@/components/ui/PageShell";
import Select from "@/components/ui/Select";
import { AUTH_COOKIE } from "@/lib/constants";
import { getBackendUrl } from "@/lib/server-env";

type Person = {
  id: number;
  primary_name?: string;
};

type Title = {
  id: number;
  name: string;
  rank?: string | null;
  jurisdiction_id?: number | null;
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

type ValidationResponse = {
  result: {
    person_id: number;
    title_id: number;
    jurisdiction: {
      id: number;
      name: string;
      code?: string | null;
      legal_system?: string | null;
      nobility_abolished_date?: string | null;
      legal_references?: string[] | null;
    } | null;
    time_validity: { valid: boolean; status: string; reason: string };
    jurisdiction_rules: { allowed: boolean; conditions: string[]; requirements: string[] };
    genealogy: {
      root_person_id: number;
      depth: number;
      issues: { severity: string; code: string; message: string; person_id?: number | null; relationship_id?: number | null }[];
    };
    succession:
      | {
          status: "VALID" | "INVALID" | "UNCERTAIN";
          rule_type: string;
          root_person_id: number;
          candidate_person_id: number;
          path_person_ids?: number[] | null;
          relationship_ids?: number[] | null;
          checked_paths: number;
          reasons: { code: string; message: string; severity: string; person_id?: number | null; relationship_id?: number | null }[];
        }
      | null;
    valid: boolean;
    confidence: number;
    sources: number[];
  };
  explanation: Explanation;
  audit_id: number;
};

type PageProps = {
  searchParams: Promise<{ person?: string; title?: string; as_of?: string }>;
};

export default async function JurisdictionValidationPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const personId = params.person ? Number.parseInt(params.person, 10) : undefined;
  const titleId = params.title ? Number.parseInt(params.title, 10) : undefined;
  const asOf = (params.as_of ?? "").trim() || undefined;

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  let personsResp: Response;
  let titlesResp: Response;

  try {
    [personsResp, titlesResp] = await Promise.all([
      fetch(`${backendUrl}/persons?limit=200`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
      fetch(`${backendUrl}/titles?limit=200`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
    ]);
  } catch (err) {
    return (
      <PageShell title="Jurisdiction Engine" description="Jurisdiction-aware title validation (Day 6)">
        <Alert tone="error" title="Backend unreachable">
          <div>Failed to fetch required data from the backend.</div>
          <div className="subtle" style={{ marginTop: 6, fontSize: 12 }}>
            Backend URL: <code>{backendUrl}</code>
            <br />
            Make sure the backend is running and ready at <code>{backendUrl}/ready</code>.
          </div>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 10, fontSize: 12 }}>
            {String(err)}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  if (personsResp.status === 401 || personsResp.status === 403) redirect("/logout");
  if (titlesResp.status === 401 || titlesResp.status === 403) redirect("/logout");

  if (!personsResp.ok || !titlesResp.ok) {
    const pBody = await personsResp.text().catch(() => "");
    const tBody = await titlesResp.text().catch(() => "");
    return (
      <PageShell title="Jurisdiction Engine" description="Jurisdiction-aware title validation (Day 6)">
        <Alert tone="error" title="Backend error while loading data">
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {personsResp.ok ? "" : `Persons: ${personsResp.status}\n${pBody}\n\n`}
            {titlesResp.ok ? "" : `Titles: ${titlesResp.status}\n${tBody}`}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  const persons = (await personsResp.json()) as Person[];
  const titles = (await titlesResp.json()) as Title[];

  let validation: ValidationResponse | null = null;
  let validationError: { status: number; body: string } | null = null;

  if (personId && titleId) {
    const resp = await fetch(`${backendUrl}/api/v1/validate/jurisdiction`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        person_id: personId,
        title_id: titleId,
        as_of: asOf ?? null,
      }),
      cache: "no-store",
    });

    if (resp.ok) {
      validation = (await resp.json()) as ValidationResponse;
    } else {
      validation = null;
      validationError = { status: resp.status, body: await resp.text().catch(() => "") };
    }
  }

  const titleLookup = new Map<number, Title>(titles.map((t) => [t.id, t]));
  const selectedTitle = titleId ? titleLookup.get(titleId) : undefined;

  return (
    <PageShell
      title="Jurisdiction Validation"
      description="Time validity • Jurisdiction rules • Genealogy • Succession (with AI explanation)"
    >
      <Card
        title="Validate a title claim"
        description="Select claimant and title. If the title has a grantor recorded, the succession engine will be applied." 
      >
        <form method="GET" className="grid" style={{ gap: 12 }}>
          <div className="grid" style={{ gap: 8 }}>
            <Select name="person" defaultValue={personId ?? ""} label="Claimant (person)">
              <option value="">-- select --</option>
              {persons.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.primary_name ?? `Person ${p.id}`} (#{p.id})
                </option>
              ))}
            </Select>

            <Select
              name="title"
              defaultValue={titleId ?? ""}
              label="Title"
              hint={
                selectedTitle
                  ? `rank: ${selectedTitle.rank ?? "(none)"} • jurisdiction_id: ${selectedTitle.jurisdiction_id ?? "(none)"} • grantor_person_id: ${selectedTitle.grantor_person_id ?? "(none)"}`
                  : undefined
              }
            >
              <option value="">-- select --</option>
              {titles.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} (#{t.id})
                </option>
              ))}
            </Select>

            <Input
              name="as_of"
              type="date"
              label="As-of date (optional)"
              defaultValue={asOf ?? ""}
              hint="Filters genealogy relationship validity and can affect rule evaluation."
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
            Note: this endpoint includes AI explainability. If OpenAI is not configured, a deterministic explanation will be returned.
          </div>
        </Card>
      ) : null}

      {validation ? (
        <>
          <Card
            title="Result"
            description={`audit_id: ${validation.audit_id} • confidence: ${validation.result.confidence.toFixed(2)}`}
          >
            <div className="row" style={{ gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
              <Badge tone={validation.result.valid ? "success" : "error"}>
                {validation.result.valid ? "VALID" : "INVALID"}
              </Badge>
              <Badge tone="neutral">Person #{validation.result.person_id}</Badge>
              <Badge tone="neutral">Title #{validation.result.title_id}</Badge>
              {validation.result.jurisdiction?.code ? (
                <Badge tone="info">{validation.result.jurisdiction.code}</Badge>
              ) : null}
            </div>

            <div className="grid" style={{ gap: 12 }}>
              <Alert
                tone={validation.result.time_validity.valid ? "success" : "warning"}
                title={`Time validity: ${validation.result.time_validity.status}`}
              >
                {validation.result.time_validity.reason}
              </Alert>

              <Alert
                tone={validation.result.jurisdiction_rules.allowed ? "info" : "warning"}
                title={`Jurisdiction rules: ${validation.result.jurisdiction_rules.allowed ? "allowed" : "blocked"}`}
              >
                <div className="grid" style={{ gap: 8 }}>
                  {validation.result.jurisdiction ? (
                    <div className="subtle" style={{ fontSize: 13 }}>
                      {validation.result.jurisdiction.name}
                      {validation.result.jurisdiction.legal_system
                        ? ` • ${validation.result.jurisdiction.legal_system}`
                        : ""}
                    </div>
                  ) : (
                    <div className="subtle" style={{ fontSize: 13 }}>No jurisdiction assigned.</div>
                  )}

                  {validation.result.jurisdiction_rules.conditions.length ? (
                    <div>
                      <div className="subtle" style={{ fontSize: 12, marginBottom: 4 }}>
                        Conditions
                      </div>
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {validation.result.jurisdiction_rules.conditions.map((c, idx) => (
                          <li key={idx}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {validation.result.jurisdiction_rules.requirements.length ? (
                    <div>
                      <div className="subtle" style={{ fontSize: 12, marginBottom: 4 }}>
                        Legal references
                      </div>
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {validation.result.jurisdiction_rules.requirements.map((r, idx) => (
                          <li key={idx}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </Alert>

              <Card
                title={`Genealogy check (depth ${validation.result.genealogy.depth})`}
                description={`issues: ${validation.result.genealogy.issues.length}`}
              >
                {validation.result.genealogy.issues.length ? (
                  <div className="grid" style={{ gap: 10 }}>
                    {validation.result.genealogy.issues.map((i, idx) => (
                      <Alert
                        key={idx}
                        tone={i.severity === "error" ? "error" : "warning"}
                        dense
                        title={i.code}
                      >
                        <div>{i.message}</div>
                        <div className="subtle" style={{ fontSize: 12, marginTop: 4 }}>
                          {i.person_id ? `person:${i.person_id} ` : ""}
                          {i.relationship_id ? `rel:${i.relationship_id}` : ""}
                        </div>
                      </Alert>
                    ))}
                  </div>
                ) : (
                  <Alert tone="success">No genealogy issues reported.</Alert>
                )}
              </Card>

              <Card
                title="Succession engine"
                description={validation.result.succession ? `status: ${validation.result.succession.status}` : "Not evaluated (no grantor recorded)"}
              >
                {validation.result.succession ? (
                  <>
                    <div className="row" style={{ gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
                      <Badge
                        tone={
                          validation.result.succession.status === "VALID"
                            ? "success"
                            : validation.result.succession.status === "INVALID"
                            ? "error"
                            : "warning"
                        }
                      >
                        {validation.result.succession.status}
                      </Badge>
                      <Badge tone="neutral">rule: {validation.result.succession.rule_type}</Badge>
                      <Badge tone="neutral">root: #{validation.result.succession.root_person_id}</Badge>
                    </div>

                    {validation.result.succession.path_person_ids ? (
                      <div className="subtle" style={{ marginBottom: 10 }}>
                        Path: {validation.result.succession.path_person_ids.join(" → ")}
                      </div>
                    ) : null}

                    {validation.result.succession.reasons.length ? (
                      <div className="grid" style={{ gap: 10 }}>
                        {validation.result.succession.reasons.map((r, idx) => (
                          <Alert
                            key={idx}
                            tone={r.severity === "error" ? "error" : r.severity === "warning" ? "warning" : "info"}
                            dense
                            title={r.code}
                          >
                            <div>{r.message}</div>
                          </Alert>
                        ))}
                      </div>
                    ) : (
                      <Alert tone="success">No succession issues reported.</Alert>
                    )}
                  </>
                ) : (
                  <Alert tone="warning">
                    This title has no <code>grantor_person_id</code> recorded, so succession validation could not be applied.
                  </Alert>
                )}
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
                  Legal and genealogical validation above remains valid, but the AI explanation service is
                  currently unavailable or over quota.
                </div>
              </Alert>
            )}
          </Card>
        </>
      ) : (
        <Card title="Status">
          <Alert tone="info">Select a person and a title, then click Validate.</Alert>
          <div className="subtle" style={{ fontSize: 12, marginTop: 8 }}>
            Tip: for full validation, set <code>titles.grantor_person_id</code> (the original granting authority) and 
            <code>titles.granted_date</code>.
          </div>
        </Card>
      )}
    </PageShell>
  );
}
