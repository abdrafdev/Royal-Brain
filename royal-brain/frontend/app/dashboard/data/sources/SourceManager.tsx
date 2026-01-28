"use client";

import { useState } from "react";
import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";

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

type Props = {
  sources: Source[];
};

export default function SourceManager({ sources: initialSources }: Props) {
  const [sources, setSources] = useState<Source[]>(initialSources);
  const [showAddModal, setShowAddModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [sourceType, setSourceType] = useState("BIRTH_CERTIFICATE");
  const [citation, setCitation] = useState("");
  const [issuedDate, setIssuedDate] = useState("");
  const [url, setUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [validFrom, setValidFrom] = useState(new Date().toISOString().split("T")[0]);


  const handleAddSource = async () => {
    if (!citation || !validFrom) {
      setError("Citation and Valid From date are required");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {

      type CreateSourcePayload = {
        source_type: string;
        citation: string;
        valid_from: string;
        issued_date?: string;
        url?: string;
        notes?: string;
      };

      const payload: CreateSourcePayload = {
        source_type: sourceType,
        citation: citation,
        valid_from: validFrom,
      };

      if (issuedDate) payload.issued_date = issuedDate;
      if (url) payload.url = url;
      if (notes) payload.notes = notes;

      const resp = await fetch(`/api/backend/sources`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(errorText || `Failed to create source (${resp.status})`);
      }

      const newSource = await resp.json();
      setSources([newSource, ...sources]);
      setSuccess(`Source #${newSource.id} created successfully`);
      setShowAddModal(false);
      
      // Reset form
      setSourceType("BIRTH_CERTIFICATE");
      setCitation("");
      setIssuedDate("");
      setUrl("");
      setNotes("");
      setValidFrom(new Date().toISOString().split("T")[0]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {error && (
        <Alert tone="error" title="Error" dense>
          {error}
        </Alert>
      )}
      {success && (
        <Alert tone="success" title="Success" dense>
          {success}
        </Alert>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button
          onClick={() => setShowAddModal(true)}
          style={{
            padding: "8px 14px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--panel-soft)",
            color: "var(--text)",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          + Add Source
        </button>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              ID
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Type
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Citation
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Issued Date
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Valid From
            </th>
          </tr>
        </thead>
        <tbody>
          {sources.map((source) => (
            <tr key={source.id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "10px 4px", fontSize: 13 }}>#{source.id}</td>
              <td style={{ padding: "10px 4px", fontSize: 13 }}>
                <Badge tone="neutral">{source.source_type}</Badge>
              </td>
              <td style={{ padding: "10px 4px", fontSize: 13, maxWidth: 300 }}>
                {source.citation}
                {source.url && (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ marginLeft: 8, color: "var(--info)", fontSize: 12 }}
                  >
                    🔗
                  </a>
                )}
              </td>
              <td style={{ padding: "10px 4px", fontSize: 13, color: "var(--muted)" }}>
                {source.issued_date || "—"}
              </td>
              <td style={{ padding: "10px 4px", fontSize: 13, color: "var(--muted)" }}>
                {source.valid_from}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Add Source Modal */}
      {showAddModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            overflowY: "auto",
          }}
          onClick={() => setShowAddModal(false)}
        >
          <div
            style={{
              background: "var(--panel)",
              borderRadius: 12,
              padding: 24,
              minWidth: 500,
              maxWidth: 600,
              border: "1px solid var(--border)",
              margin: "20px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16, fontWeight: 700 }}>Add New Source</h3>
            <div style={{ display: "grid", gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Source Type <span style={{ color: "var(--error)" }}>*</span>
                </label>
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                >
                  <option value="BIRTH_CERTIFICATE">Birth Certificate</option>
                  <option value="DEATH_CERTIFICATE">Death Certificate</option>
                  <option value="MARRIAGE_CERTIFICATE">Marriage Certificate</option>
                  <option value="LEGAL_DOCUMENT">Legal Document</option>
                  <option value="ROYAL_DECREE">Royal Decree</option>
                  <option value="HISTORICAL_RECORD">Historical Record</option>
                  <option value="FAMILY_ARCHIVE">Family Archive</option>
                  <option value="PUBLISHED_GENEALOGY">Published Genealogy</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Citation <span style={{ color: "var(--error)" }}>*</span>
                </label>
                <textarea
                  value={citation}
                  onChange={(e) => setCitation(e.target.value)}
                  placeholder="Full citation or description of the source"
                  rows={3}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                    fontFamily: "inherit",
                    resize: "vertical",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Issued Date
                </label>
                <input
                  type="date"
                  value={issuedDate}
                  onChange={(e) => setIssuedDate(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  URL / Link
                </label>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://..."
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Additional context or notes"
                  rows={2}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                    fontFamily: "inherit",
                    resize: "vertical",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Valid From <span style={{ color: "var(--error)" }}>*</span>
                </label>
                <input
                  type="date"
                  value={validFrom}
                  onChange={(e) => setValidFrom(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowAddModal(false)}
                disabled={loading}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: "var(--text)",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleAddSource}
                disabled={loading}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--panel-soft)",
                  color: "var(--text)",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                {loading ? "Creating..." : "Create Source"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
