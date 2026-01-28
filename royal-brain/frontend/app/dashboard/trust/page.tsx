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

type Person = { id: number; primary_name?: string };

type PageProps = {
  searchParams: Promise<{
    entity_type?: string;
    entity_id?: string;
    action?: string;
  }>;
};

type EntityHash = {
  id: number;
  entity_type: string;
  entity_id: number;
  hash_algorithm: string;
  hash_value: string;
  timestamp: string;
  computed_by_user_id: number | null;
};

type Certificate = {
  id: number;
  entity_type: string;
  entity_id: number;
  certificate_type: string;
  verification_status: string;
  hash_id: number;
  certificate_json: Record<string, unknown>;
  sources_used: { name: string; type: string }[] | null;
  rules_applied: { rule_name: string; result: string }[] | null;
  confidence_score: number | null;
  ai_explanation: string | null;
  issued_at: string;
  issued_by_user_id: number;
};

type BlockchainAnchor = {
  id: number;
  hash_id: number | null;
  merkle_root: string | null;
  batch_id: string | null;
  blockchain_network: string;
  transaction_hash: string;
  block_number: number | null;
  anchor_type: string;
  anchored_at: string;
  explorer_url: string | null;
};

type FullVerification = {
  entity_type: string;
  entity_id: number;
  entity_name: string;
  current_hash: EntityHash;
  certificate: Certificate | null;
  blockchain_anchor: BlockchainAnchor | null;
  audit_trail: {
    id: number;
    event: string;
    user_id: number | null;
    timestamp: string;
    metadata: Record<string, unknown> | null;
    hash_before: string | null;
    hash_after: string | null;
  }[];
};

function toneForStatus(
  status: string
): "success" | "error" | "warning" | "info" {
  if (status === "VALID") return "success";
  if (status === "INVALID") return "error";
  if (status === "UNCERTAIN") return "warning";
  return "info";
}

export default async function TrustPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const entityType = params.entity_type?.trim() || "";
  const entityId = params.entity_id
    ? Number.parseInt(params.entity_id, 10)
    : undefined;
  const action = params.action?.trim() || "";

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE)?.value;
  if (!token) redirect("/login");

  const backendUrl = getBackendUrl();

  const [meResp, personsResp] = await Promise.all([
    fetch(`${backendUrl}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
    fetch(`${backendUrl}/persons?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }),
  ]);

  if (meResp.status === 401 || meResp.status === 403) redirect("/logout");
  if (!meResp.ok || !personsResp.ok) {
    const meBody = await meResp.text().catch(() => "");
    const pBody = await personsResp.text().catch(() => "");

    return (
      <PageShell
        title="Trust & Certification"
        description="Day 9 cryptographic verification & blockchain anchoring"
      >
        <Alert tone="error" title="Backend error">
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {meResp.ok ? "" : `Me: ${meResp.status}\n${meBody}\n\n`}
            {personsResp.ok ? "" : `Persons: ${personsResp.status}\n${pBody}`}
          </pre>
        </Alert>
      </PageShell>
    );
  }

  await meResp.json();
  const persons = (await personsResp.json()) as Person[];

  let verification: FullVerification | null = null;
  let verificationError: { status: number; body: string } | null = null;
  let actionResult: { message: string; data?: unknown } | null = null;
  let actionError: { status: number; body: string } | null = null;

  // Fetch full verification if entity is selected
  if (entityType && entityId) {
    const resp = await fetch(
      `${backendUrl}/api/v1/trust/verify/${entityType}/${entityId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }
    );

    if (resp.ok) {
      verification = (await resp.json()) as FullVerification;
    } else {
      verificationError = {
        status: resp.status,
        body: await resp.text().catch(() => ""),
      };
    }
  }

  // Handle actions
  if (action === "hash" && entityType && entityId) {
    const resp = await fetch(`${backendUrl}/api/v1/trust/hash`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ entity_type: entityType, entity_id: entityId }),
      cache: "no-store",
    });

    if (resp.ok) {
      const hash = (await resp.json()) as EntityHash;
      actionResult = {
        message: "Hash computed successfully",
        data: hash,
      };
    } else {
      actionError = {
        status: resp.status,
        body: await resp.text().catch(() => ""),
      };
    }
  }

  if (action === "certificate" && verification?.current_hash) {
    const resp = await fetch(`${backendUrl}/api/v1/trust/certificate`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        entity_type: entityType,
        entity_id: entityId,
        certificate_type: "standard",
        verification_status: "VALID",
        confidence_score: 0.95,
      }),
      cache: "no-store",
    });

    if (resp.ok) {
      const cert = (await resp.json()) as Certificate;
      actionResult = {
        message: "Certificate generated successfully",
        data: cert,
      };
    } else {
      actionError = {
        status: resp.status,
        body: await resp.text().catch(() => ""),
      };
    }
  }

  if (action === "anchor" && verification?.current_hash) {
    const resp = await fetch(`${backendUrl}/api/v1/trust/anchor`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        hash_ids: [verification.current_hash.id],
        blockchain_network: "polygon-mumbai",
        batch_mode: false,
      }),
      cache: "no-store",
    });

    if (resp.ok) {
      const anchors = (await resp.json()) as BlockchainAnchor[];
      actionResult = {
        message: "Hash anchored to blockchain successfully",
        data: anchors[0],
      };
    } else {
      actionError = {
        status: resp.status,
        body: await resp.text().catch(() => ""),
      };
    }
  }

  return (
    <PageShell
      title="Trust & Certification Layer"
      description="Cryptographic hashing • Verification certificates • Blockchain anchoring • Immutable audit trails"
    >
      <Card
        title="Verify entity"
        description="Select an entity to view its cryptographic verification status, certificates, and blockchain anchoring."
      >
        <form method="GET" className="grid" style={{ gap: 12 }}>
          <Select
            name="entity_type"
            defaultValue={entityType}
            label="Entity Type"
            required
          >
            <option value="">-- select --</option>
            <option value="Person">Person</option>
            <option value="Title">Title</option>
            <option value="Order">Order</option>
            <option value="HeraldicEntity">Heraldic Entity</option>
            <option value="Family">Family</option>
          </Select>

          {entityType === "Person" && (
            <Select
              name="entity_id"
              defaultValue={entityId ?? ""}
              label="Person"
              required
            >
              <option value="">-- select --</option>
              {persons.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.primary_name ?? `Person ${p.id}`} (#{p.id})
                </option>
              ))}
            </Select>
          )}

          {entityType && entityType !== "Person" && (
            <Input
              name="entity_id"
              defaultValue={entityId ?? ""}
              label="Entity ID"
              placeholder="Enter entity ID"
              type="number"
              required
            />
          )}

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
            View Verification
          </button>
        </form>
      </Card>

      {actionResult && (
        <Alert tone="success" title={actionResult.message}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6, fontSize: 13 }}>
            {JSON.stringify(actionResult.data, null, 2)}
          </pre>
        </Alert>
      )}

      {actionError && (
        <Alert tone="error" title={`Action error (${actionError.status})`}>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {actionError.body}
          </pre>
        </Alert>
      )}

      {verificationError && !verification && (
        <Alert
          tone="error"
          title={`Verification error (${verificationError.status})`}
        >
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
            {verificationError.body}
          </pre>
        </Alert>
      )}

      {verification && (
        <>
          <Card
            title={`${verification.entity_type}: ${verification.entity_name}`}
            description={`Entity ID: ${verification.entity_id}`}
            actions={
              <Badge tone="info">
                {verification.certificate
                  ? verification.certificate.verification_status
                  : "NOT CERTIFIED"}
              </Badge>
            }
          >
            <div className="grid" style={{ gap: 16 }}>
              {/* Current Hash */}
              <div>
                <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                  Cryptographic Hash
                </h4>
                <div
                  style={{
                    fontSize: 13,
                    fontFamily: "monospace",
                    background: "#f5f5f5",
                    padding: 12,
                    borderRadius: 4,
                    wordBreak: "break-all",
                  }}
                >
                  <div style={{ marginBottom: 8 }}>
                    <strong>Algorithm:</strong>{" "}
                    {verification.current_hash.hash_algorithm.toUpperCase()}
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <strong>Hash:</strong>
                  </div>
                  <div style={{ color: "#0070f3" }}>
                    {verification.current_hash.hash_value}
                  </div>
                  <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
                    Computed: {new Date(verification.current_hash.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Actions */}
              {!verification.certificate && (
                <div>
                  <form method="GET" style={{ display: "inline-block" }}>
                    <input type="hidden" name="entity_type" value={entityType} />
                    <input type="hidden" name="entity_id" value={entityId} />
                    <input type="hidden" name="action" value="certificate" />
                    <button
                      type="submit"
                      style={{
                        padding: "8px 14px",
                        background: "#10b981",
                        color: "#fff",
                        border: "none",
                        borderRadius: 4,
                        fontWeight: 500,
                        cursor: "pointer",
                        fontSize: 14,
                      }}
                    >
                      Generate Certificate
                    </button>
                  </form>
                </div>
              )}

              {verification.certificate && !verification.blockchain_anchor && (
                <div>
                  <form method="GET" style={{ display: "inline-block" }}>
                    <input type="hidden" name="entity_type" value={entityType} />
                    <input type="hidden" name="entity_id" value={entityId} />
                    <input type="hidden" name="action" value="anchor" />
                    <button
                      type="submit"
                      style={{
                        padding: "8px 14px",
                        background: "#8b5cf6",
                        color: "#fff",
                        border: "none",
                        borderRadius: 4,
                        fontWeight: 500,
                        cursor: "pointer",
                        fontSize: 14,
                      }}
                    >
                      Anchor to Blockchain
                    </button>
                  </form>
                </div>
              )}
            </div>
          </Card>

          {/* Certificate Details */}
          {verification.certificate && (
            <Card
              title="Verification Certificate"
              description={`Issued: ${new Date(verification.certificate.issued_at).toLocaleString()}`}
              actions={
                <Badge tone={toneForStatus(verification.certificate.verification_status)}>
                  {verification.certificate.verification_status}
                </Badge>
              }
            >
              <div className="grid" style={{ gap: 16 }}>
                <div>
                  <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                    Certificate Details
                  </h4>
                  <div style={{ fontSize: 14 }}>
                    <p>
                      <strong>Type:</strong> {verification.certificate.certificate_type}
                    </p>
                    <p>
                      <strong>Confidence Score:</strong>{" "}
                      {verification.certificate.confidence_score
                        ? `${(verification.certificate.confidence_score * 100).toFixed(1)}%`
                        : "N/A"}
                    </p>
                    <p>
                      <strong>Certificate ID:</strong> #{verification.certificate.id}
                    </p>
                  </div>
                </div>

                {verification.certificate.sources_used &&
                  verification.certificate.sources_used.length > 0 && (
                    <div>
                      <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                        Sources Used
                      </h4>
                      <ul style={{ paddingLeft: 20, fontSize: 14 }}>
                        {verification.certificate.sources_used.map((s, i) => (
                          <li key={i}>
                            {s.name} ({s.type})
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                {verification.certificate.rules_applied &&
                  verification.certificate.rules_applied.length > 0 && (
                    <div>
                      <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                        Rules Applied
                      </h4>
                      <ul style={{ paddingLeft: 20, fontSize: 14 }}>
                        {verification.certificate.rules_applied.map((r, i) => (
                          <li key={i}>
                            {r.rule_name}: <Badge tone="success">{r.result}</Badge>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                {verification.certificate.ai_explanation && (
                  <div>
                    <h4 style={{ fontWeight: 600, marginBottom: 8 }}>
                      AI Explanation
                    </h4>
                    <p
                      style={{
                        fontSize: 14,
                        whiteSpace: "pre-wrap",
                        background: "#f9f9f9",
                        padding: 12,
                        borderRadius: 4,
                      }}
                    >
                      {verification.certificate.ai_explanation}
                    </p>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Blockchain Anchor */}
          {verification.blockchain_anchor && (
            <Card
              title="Blockchain Anchor"
              description={`Anchored: ${new Date(verification.blockchain_anchor.anchored_at).toLocaleString()}`}
              actions={<Badge tone="success">ANCHORED</Badge>}
            >
              <div className="grid" style={{ gap: 12 }}>
                <div style={{ fontSize: 14 }}>
                  <p>
                    <strong>Network:</strong>{" "}
                    {verification.blockchain_anchor.blockchain_network}
                  </p>
                  <p>
                    <strong>Anchor Type:</strong>{" "}
                    {verification.blockchain_anchor.anchor_type}
                  </p>
                  {verification.blockchain_anchor.merkle_root && (
                    <p>
                      <strong>Merkle Root:</strong>{" "}
                      <code style={{ fontSize: 12 }}>
                        {verification.blockchain_anchor.merkle_root}
                      </code>
                    </p>
                  )}
                  {verification.blockchain_anchor.batch_id && (
                    <p>
                      <strong>Batch ID:</strong>{" "}
                      {verification.blockchain_anchor.batch_id}
                    </p>
                  )}
                </div>

                <div
                  style={{
                    background: "#f5f5f5",
                    padding: 12,
                    borderRadius: 4,
                    fontSize: 13,
                    fontFamily: "monospace",
                    wordBreak: "break-all",
                  }}
                >
                  <strong>Transaction Hash:</strong>
                  <div style={{ color: "#8b5cf6", marginTop: 4 }}>
                    {verification.blockchain_anchor.transaction_hash}
                  </div>
                </div>

                {verification.blockchain_anchor.explorer_url && (
                  <a
                    href={verification.blockchain_anchor.explorer_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: "#0070f3",
                      textDecoration: "none",
                      fontSize: 14,
                    }}
                  >
                    View on Blockchain Explorer →
                  </a>
                )}
              </div>
            </Card>
          )}

          {/* Audit Trail */}
          {verification.audit_trail.length > 0 && (
            <Card
              title="Audit Trail"
              description={`${verification.audit_trail.length} events recorded`}
            >
              <div
                className="grid"
                style={{
                  gap: 8,
                  maxHeight: 400,
                  overflowY: "auto",
                  fontSize: 13,
                }}
              >
                {verification.audit_trail.map((log) => (
                  <div
                    key={log.id}
                    style={{
                      padding: 12,
                      background: "#f9f9f9",
                      borderRadius: 4,
                      borderLeft: "3px solid #0070f3",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: 4,
                      }}
                    >
                      <Badge tone="info">{log.event}</Badge>
                      <span style={{ color: "#666", fontSize: 12 }}>
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {log.hash_before && (
                      <div style={{ fontSize: 12, color: "#666" }}>
                        Hash before: <code>{log.hash_before.slice(0, 16)}...</code>
                      </div>
                    )}
                    {log.hash_after && (
                      <div style={{ fontSize: 12, color: "#666" }}>
                        Hash after: <code>{log.hash_after.slice(0, 16)}...</code>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {!verification && !verificationError && entityType && entityId && (
        <Alert tone="info" title="Entity not yet hashed">
          <p>This entity has not been hashed yet. Compute its hash first:</p>
          <form
            method="GET"
            style={{ marginTop: 12, display: "inline-block" }}
          >
            <input type="hidden" name="entity_type" value={entityType} />
            <input type="hidden" name="entity_id" value={entityId} />
            <input type="hidden" name="action" value="hash" />
            <button
              type="submit"
              style={{
                padding: "8px 14px",
                background: "#0070f3",
                color: "#fff",
                border: "none",
                borderRadius: 4,
                fontWeight: 500,
                cursor: "pointer",
                fontSize: 14,
              }}
            >
              Compute Hash
            </button>
          </form>
        </Alert>
      )}
    </PageShell>
  );
}
