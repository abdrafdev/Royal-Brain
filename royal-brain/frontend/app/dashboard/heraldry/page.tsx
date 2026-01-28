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

type Jurisdiction = { id: number; name: string; code: string };
type Person = { id: number; primary_name?: string };

type SourceReference = {
  id: number;
  source_type: string;
  citation: string;
  url?: string | null;
  issued_date?: string | null;
};

type PageProps = {
  searchParams: Promise<{
    blazon?: string;
    jurisdiction?: string;
    claimant?: string;
    as_of?: string;
  }>;
};

type ValidationResponse = {
  parsed_blazon: {
    field_tincture: string;
    field_tincture_type: string;
    charges: { name: string; tincture: string; position?: string }[];
    ordinaries: { type: string; tincture: string }[];
    valid: boolean;
    errors: string[];
  };
  rule_validation: {
    valid: boolean;
    violations: { rule_name: string; severity: string; message: string }[];
    warnings: { rule_name: string; severity: string; message: string }[];
    pass_rules: string[];
  };
  jurisdiction_compliance: {
    compliant: boolean;
    jurisdiction_code: string;
    jurisdiction_name: string;
    violations: string[];
    allows_nobility_arms: boolean;
    allows_royal_symbols: boolean;
  } | null;
  svg: string | null;
  overall_valid: boolean;
  explanation: {
    summary: string;
    detailed_reasoning: string;
    citations: { category: string; description: string }[];
    confidence: number;
    sources: SourceReference[];
    rules_applied: Record<string, unknown>;
  };
  audit_id: number;
};

function toneForSeverity(severity: string): "error" | "warning" | "info" {
  if (severity === "INVALID" || severity === "FRAUD_INDICATIVE") return "error";
  if (severity === "WARNING") return "warning";
  return "info";
}

export default async function HeraldryPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const blazon = params.blazon?.trim() || "";
  const jurisdictionId = params.jurisdiction
    ? Number.parseInt(params.jurisdiction, 10)
    : undefined;
  const claimantId = params.claimant
    ? Number.parseInt(params.claimant, 10)
    : undefined;
  const asOf = params.as_of?.trim() || undefined;

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  const [meResp, jurisdictionsResp, personsResp] = await Promise.all([
    fetch(`${backendUrl}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
    fetch(`${backendUrl}/jurisdictions?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
    fetch(`${backendUrl}/persons?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
  ]);

  if (meResp.status === 401 || meResp.status === 403) redirect("/logout");
  if (!meResp.ok || !jurisdictionsResp.ok || !personsResp.ok) {
    const meBody = await meResp.text().catch(() => "");
    const jBody = await jurisdictionsResp.text().catch(() => "");
    const pBody = await personsResp.text().catch(() => "");

    return (
      <PageShell
        title="Heraldry Engine"
        description="Day 8 blazon parsing, validation, SVG generation"
      >
        <Alert tone="error" title="Backend error">
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {meResp.ok ? "" : `Me: ${meResp.status}\n${meBody}\n\n`}
            {jurisdictionsResp.ok
              ? ""
              : `Jurisdictions: ${jurisdictionsResp.status}\n${jBody}\n\n`}
            {personsResp.ok ? "" : `Persons: ${personsResp.status}\n${pBody}`}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  await meResp.json();
  const jurisdictions = (await jurisdictionsResp.json()) as Jurisdiction[];
  const persons = (await personsResp.json()) as Person[];

  let validation: ValidationResponse | null = null;
  let validationError: { status: number; body: string } | null = null;

  if (blazon && jurisdictionId) {
    const resp = await fetch(`${backendUrl}/api/v1/heraldry/validate`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        blazon,
        jurisdiction_id: jurisdictionId,
        claimant_person_id: claimantId ?? null,
        as_of: asOf ?? null,
        generate_svg: true,
      }),
      cache: "no-store",
    });

    if (resp.ok) {
      validation = (await resp.json()) as ValidationResponse;
    } else {
      validationError = {
        status: resp.status,
        body: await resp.text().catch(() => ""),
      };
    }
  }

  return (
    <PageShell
      title="Heraldry Engine"
      description="Blazon parsing • Rule validation • SVG generation • Jurisdiction compliance"
    >
      <Card
        title="Validate heraldic blazon"
        description="Enter a blazon description to parse, validate against heraldic rules, check jurisdictional compliance, and generate SVG."
      >
        <form method="GET" className="grid" style={{ gap: 12 }}>
          <div className="grid" style={{ gap: 8 }}>
            <label htmlFor="blazon" style={{ fontWeight: 500 }}>
              Blazon
            </label>
            <Input
              id="blazon"
              name="blazon"
              defaultValue={blazon}
              placeholder='e.g. "Gules, a lion rampant Or"'
              required
            />
            <p style={{ fontSize: 14, color: "#666" }}>
              Standard heraldic description (field tincture, charges, positions)
            </p>
          </div>

          <Select
            name="jurisdiction"
            defaultValue={jurisdictionId ?? ""}
            label="Jurisdiction"
            required
          >
            <option value="">-- select --</option>
            {jurisdictions.map((j) => (
              <option key={j.id} value={j.id}>
                {j.name} ({j.code})
              </option>
            ))}
          </Select>

          <Select
            name="claimant"
            defaultValue={claimantId ?? ""}
            label="Claimant (optional)"
          >
            <option value="">-- none --</option>
            {persons.map((p) => (
              <option key={p.id} value={p.id}>
                {p.primary_name ?? `Person ${p.id}`} (#{p.id})
              </option>
            ))}
          </Select>

          <Input
            name="as_of"
            defaultValue={asOf ?? ""}
            label="Historical date (optional)"
            placeholder="YYYY-MM-DD"
            type="date"
          />

          <button
            type="submit"
            style={{
              padding: "10px 16px",
              background: "#0070f3",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Validate Heraldry
          </button>
        </form>
      </Card>

      {validationError && (
        <Alert tone="error" title={`Validation error (${validationError.status})`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {validationError.body}
          </pre>
        </Alert>
      )}

      {validation && (
        <>
          <Card
            title="Validation Result"
            description={
              validation.overall_valid
                ? "Arms are valid and heraldically correct"
                : "Arms failed validation"
            }
            actions={
              <Badge tone={validation.overall_valid ? "success" : "error"}>
                {validation.overall_valid ? "VALID" : "INVALID"}
              </Badge>
            }
          >
            <div className="grid" style={{ gap: 16 }}>
              {/* Parsed Blazon */}
              <div>
                <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                  Parsed Structure
                </h4>
                <div style={{ fontSize: 14 }}>
                  <p>
                    <strong>Field:</strong> {validation.parsed_blazon.field_tincture} (
                    {validation.parsed_blazon.field_tincture_type})
                  </p>
                  {validation.parsed_blazon.charges.length > 0 && (
                    <p>
                      <strong>Charges:</strong>{" "}
                      {validation.parsed_blazon.charges
                        .map(
                          (c) =>
                            `${c.name} ${c.position || ""} ${c.tincture}`.trim()
                        )
                        .join(", ")}
                    </p>
                  )}
                  {validation.parsed_blazon.ordinaries.length > 0 && (
                    <p>
                      <strong>Ordinaries:</strong>{" "}
                      {validation.parsed_blazon.ordinaries
                        .map((o) => `${o.type} ${o.tincture}`)
                        .join(", ")}
                    </p>
                  )}
                  {validation.parsed_blazon.errors.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <strong>Parsing Errors:</strong>
                      <ul style={{ marginTop: 4, paddingLeft: 20 }}>
                        {validation.parsed_blazon.errors.map((err, i) => (
                          <li key={i} style={{ color: "#c00" }}>
                            {err}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {/* Rule Validation */}
              <div>
                <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                  Heraldic Rules
                </h4>
                {validation.rule_validation.violations.length === 0 &&
                validation.rule_validation.warnings.length === 0 ? (
                  <p style={{ color: "#0a0" }}>
                    ✓ All heraldic rules passed:{" "}
                    {validation.rule_validation.pass_rules.join(", ")}
                  </p>
                ) : (
                  <div className="grid" style={{ gap: 8 }}>
                    {validation.rule_validation.violations.map((v, i) => (
                      <Alert
                        key={`v-${i}`}
                        tone={toneForSeverity(v.severity)}
                        title={v.rule_name}
                      >
                        {v.message}
                      </Alert>
                    ))}
                    {validation.rule_validation.warnings.map((w, i) => (
                      <Alert
                        key={`w-${i}`}
                        tone="warning"
                        title={w.rule_name}
                      >
                        {w.message}
                      </Alert>
                    ))}
                  </div>
                )}
              </div>

              {/* Jurisdiction Compliance */}
              {validation.jurisdiction_compliance && (
                <div>
                  <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                    Jurisdiction Compliance
                  </h4>
                  <div style={{ fontSize: 14 }}>
                    <p>
                      <strong>Jurisdiction:</strong>{" "}
                      {validation.jurisdiction_compliance.jurisdiction_name} (
                      {validation.jurisdiction_compliance.jurisdiction_code})
                    </p>
                    <p>
                      <Badge
                        tone={
                          validation.jurisdiction_compliance.compliant
                            ? "success"
                            : "error"
                        }
                      >
                        {validation.jurisdiction_compliance.compliant
                          ? "COMPLIANT"
                          : "NON-COMPLIANT"}
                      </Badge>
                    </p>
                    {validation.jurisdiction_compliance.violations.length > 0 && (
                      <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                        {validation.jurisdiction_compliance.violations.map(
                          (v, i) => (
                            <li key={i} style={{ color: "#c00" }}>
                              {v}
                            </li>
                          )
                        )}
                      </ul>
                    )}
                  </div>
                </div>
              )}

              {/* AI Explanation */}
              {validation.explanation &&
              !validation.explanation.summary.toLowerCase().startsWith("ai explanation failed") ? (
                <div>
                  <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                    AI Explanation
                  </h4>
                  <p style={{ fontSize: 14, marginBottom: 8 }}>
                    <strong>{validation.explanation.summary}</strong>
                  </p>

                  <div className="row" style={{ gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                    <Badge tone="neutral">
                      confidence: {(validation.explanation.confidence * 100).toFixed(1)}%
                    </Badge>
                    <Badge tone="neutral">
                      sources: {validation.explanation.sources.length}
                    </Badge>
                  </div>

                  <p
                    style={{
                      fontSize: 14,
                      whiteSpace: "pre-wrap",
                      marginBottom: 8,
                    }}
                  >
                    {validation.explanation.detailed_reasoning}
                  </p>

                  <details>
                    <summary style={{ cursor: "pointer", fontWeight: 500 }}>
                      Sources ({validation.explanation.sources.length})
                    </summary>
                    {validation.explanation.sources.length ? (
                      <ul style={{ marginTop: 8, paddingLeft: 20, fontSize: 13 }}>
                        {validation.explanation.sources.map((s) => (
                          <li key={s.id}>
                            <strong>#{s.id}</strong> ({s.source_type}) {s.citation}
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

                  <details style={{ marginTop: 10 }}>
                    <summary style={{ cursor: "pointer", fontWeight: 500 }}>Rules applied</summary>
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

                  <details style={{ marginTop: 10 }}>
                    <summary style={{ cursor: "pointer", fontWeight: 500 }}>
                      Citations ({validation.explanation.citations.length})
                    </summary>
                    <ul style={{ marginTop: 8, paddingLeft: 20, fontSize: 13 }}>
                      {validation.explanation.citations.map((c, i) => (
                        <li key={i}>
                          <strong>{c.category}:</strong> {c.description}
                        </li>
                      ))}
                    </ul>
                  </details>
                </div>
              ) : (
                <div>
                  <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                    AI Explanation
                  </h4>
                  <Alert tone="warning" title="AI explanation unavailable">
                    <div style={{ fontSize: 14 }}>
                      The arms were validated successfully, but the AI explanation service is currently
                      unavailable or rate-limited. Validation results above are still valid.
                    </div>
                  </Alert>
                </div>
              )}
            </div>
          </Card>

          {/* SVG Preview */}
          {validation.svg && (
            <Card title="Coat of Arms" description="Generated SVG">
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  padding: 20,
                  background: "#f9f9f9",
                  borderRadius: 8,
                }}
                dangerouslySetInnerHTML={{ __html: validation.svg }}
              />
            </Card>
          )}

          {!validation.svg && validation.overall_valid && (
            <Alert tone="warning" title="No SVG generated">
              Arms are valid but SVG generation was not requested or failed.
            </Alert>
          )}

          {!validation.svg && !validation.overall_valid && (
            <Alert tone="info" title="No SVG generated">
              SVG is only generated for valid arms.
            </Alert>
          )}
        </>
      )}
    </PageShell>
  );
}
