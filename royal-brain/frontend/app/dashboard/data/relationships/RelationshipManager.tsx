"use client";

import { useState } from "react";
import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";

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

type Props = {
  relationships: Relationship[];
  persons: Person[];
  sources: Source[];
};

export default function RelationshipManager({
  relationships: initialRels,
  persons,
  sources,
}: Props) {
  const [relationships, setRelationships] = useState<Relationship[]>(initialRels);
  const [showAddModal, setShowAddModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Canonical relationship_type values are lowercase snake_case.
  const [relType, setRelType] = useState("parent_child");
  const [leftPersonId, setLeftPersonId] = useState("");
  const [rightPersonId, setRightPersonId] = useState("");
  const [validFrom, setValidFrom] = useState(new Date().toISOString().split("T")[0]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);


  const normalizeRelType = (t: string) => t.trim().toLowerCase();

  const validateForm = (): string | null => {
    if (!leftPersonId || !rightPersonId) {
      return "Both persons must be selected";
    }
    if (leftPersonId === rightPersonId) {
      return "Cannot create relationship with the same person";
    }
    if (selectedSourceIds.length === 0) {
      return "At least one source is required";
    }
    // Check for duplicates
    const duplicate = relationships.find(
      (rel) =>
        normalizeRelType(rel.relationship_type) === relType &&
        rel.left_entity_id === parseInt(leftPersonId) &&
        rel.right_entity_id === parseInt(rightPersonId)
    );
    if (duplicate) {
      return `This relationship already exists (ID #${duplicate.id})`;
    }
    return null;
  };

  const handleAddRelationship = async () => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {

      const payload = {
        relationship_type: relType,
        left_entity_type: "person",
        left_entity_id: parseInt(leftPersonId),
        right_entity_type: "person",
        right_entity_id: parseInt(rightPersonId),
        valid_from: validFrom,
        source_ids: selectedSourceIds,
      };

      const resp = await fetch(`/api/backend/relationships`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(errorText || `Failed to create relationship (${resp.status})`);
      }

      const newRel = await resp.json();
      setRelationships([newRel, ...relationships]);

      const leftPerson = persons.find((p) => p.id === parseInt(leftPersonId));
      const rightPerson = persons.find((p) => p.id === parseInt(rightPersonId));

      setSuccess(
        `Relationship created: ${leftPerson?.primary_name} → ${rightPerson?.primary_name} (${relType})`
      );
      setShowAddModal(false);

      // Reset form
      setRelType("parent_child");
      setLeftPersonId("");
      setRightPersonId("");
      setValidFrom(new Date().toISOString().split("T")[0]);
      setSelectedSourceIds([]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (sourceId: number) => {
    setSelectedSourceIds((prev) =>
      prev.includes(sourceId) ? prev.filter((id) => id !== sourceId) : [...prev, sourceId]
    );
  };

  const getPersonName = (id: number) => {
    const person = persons.find((p) => p.id === id);
    return person?.primary_name || `Person #${id}`;
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

      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: "var(--muted)" }}>
          {persons.length} persons available • {sources.length} sources available
        </div>
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
          + Add Relationship
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
              From
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              To
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Valid From
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Sources
            </th>
          </tr>
        </thead>
        <tbody>
          {relationships.length === 0 ? (
            <tr>
              <td colSpan={6} style={{ padding: "20px", textAlign: "center", color: "var(--muted)" }}>
                No relationships yet. Click + Add Relationship to create connections.
              </td>
            </tr>
          ) : (
            relationships.map((rel) => (
              <tr key={rel.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "10px 4px", fontSize: 13 }}>#{rel.id}</td>
                <td style={{ padding: "10px 4px", fontSize: 13 }}>
                  <Badge tone="info">{rel.relationship_type}</Badge>
                </td>
                <td style={{ padding: "10px 4px", fontSize: 13 }}>
                  {getPersonName(rel.left_entity_id)}
                </td>
                <td style={{ padding: "10px 4px", fontSize: 13 }}>
                  {getPersonName(rel.right_entity_id)}
                </td>
                <td style={{ padding: "10px 4px", fontSize: 13, color: "var(--muted)" }}>
                  {rel.valid_from}
                </td>
                <td style={{ padding: "10px 4px", fontSize: 13 }}>
                  <Badge tone="neutral">{rel.source_ids?.length || 0}</Badge>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Add Relationship Modal */}
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
            padding: "20px",
          }}
          onClick={() => setShowAddModal(false)}
        >
          <div
            style={{
              background: "var(--panel)",
              borderRadius: 12,
              padding: 24,
              minWidth: 500,
              maxWidth: 700,
              maxHeight: "90vh",
              overflowY: "auto",
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: 16, fontWeight: 700 }}>Add New Relationship</h3>

            {persons.length < 2 && (
              <Alert tone="warning" title="Insufficient Data" dense>
                You need at least 2 persons to create a relationship.
                <a href="/dashboard/data/persons" style={{ marginLeft: 8, color: "var(--info)" }}>
                  Create Persons →
                </a>
              </Alert>
            )}

            <div style={{ display: "grid", gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Relationship Type <span style={{ color: "var(--error)" }}>*</span>
                </label>
                <select
                  value={relType}
                  onChange={(e) => setRelType(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                >
                  <option value="parent_child">Parent → Child</option>
                  <option value="marriage">Marriage</option>
                  <option value="adoption">Adoption</option>
                </select>
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
                  {relType === "parent_child" && "Parent (left) → Child (right)"}
                  {relType === "marriage" && "Spouse (left) ↔ Spouse (right)"}
                  {relType === "adoption" && "Adoptive Parent (left) → Adopted Child (right)"}
                </div>
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  {relType === "parent_child"
                    ? "Parent"
                    : relType === "marriage"
                    ? "Spouse 1"
                    : "Adoptive Parent"}{" "}
                  <span style={{ color: "var(--error)" }}>*</span>
                </label>
                <select
                  value={leftPersonId}
                  onChange={(e) => setLeftPersonId(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                >
                  <option value="">-- select person --</option>
                  {persons.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.primary_name} (#{p.id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  {relType === "parent_child"
                    ? "Child"
                    : relType === "marriage"
                    ? "Spouse 2"
                    : "Adopted Child"}{" "}
                  <span style={{ color: "var(--error)" }}>*</span>
                </label>
                <select
                  value={rightPersonId}
                  onChange={(e) => setRightPersonId(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                >
                  <option value="">-- select person --</option>
                  {persons.map((p) => (
                    <option key={p.id} value={p.id} disabled={p.id === parseInt(leftPersonId)}>
                      {p.primary_name} (#{p.id})
                    </option>
                  ))}
                </select>
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

              <div>
                <label style={{ display: "block", marginBottom: 8, fontSize: 13, fontWeight: 600 }}>
                  Sources <span style={{ color: "var(--error)" }}>*</span> (select at least 1)
                </label>
                <div
                  style={{
                    maxHeight: 200,
                    overflowY: "auto",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: 8,
                    background: "var(--panel-soft)",
                  }}
                >
                  {sources.length === 0 ? (
                    <div style={{ padding: 8, textAlign: "center", color: "var(--muted)" }}>
                      No sources available
                    </div>
                  ) : (
                    sources.map((source) => (
                      <label
                        key={source.id}
                        style={{
                          display: "flex",
                          alignItems: "start",
                          gap: 8,
                          padding: "8px",
                          cursor: "pointer",
                          borderBottom: "1px solid var(--border)",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={selectedSourceIds.includes(source.id)}
                          onChange={() => toggleSource(source.id)}
                          style={{ marginTop: 2 }}
                        />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 13, fontWeight: 600 }}>
                            #{source.id} - {source.source_type}
                          </div>
                          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                            {source.citation.substring(0, 80)}
                            {source.citation.length > 80 ? "..." : ""}
                          </div>
                        </div>
                      </label>
                    ))
                  )}
                </div>
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
                  {selectedSourceIds.length} source(s) selected
                </div>
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
                onClick={handleAddRelationship}
                disabled={loading || persons.length < 2 || sources.length === 0}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--panel-soft)",
                  color: "var(--text)",
                  cursor:
                    persons.length < 2 || sources.length === 0 ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  opacity: persons.length < 2 || sources.length === 0 ? 0.5 : 1,
                }}
              >
                {loading ? "Creating..." : "Create Relationship"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
