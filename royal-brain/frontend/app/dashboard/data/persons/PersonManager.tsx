"use client";

import { useState } from "react";
import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";

type Person = {
  id: number;
  primary_name: string;
  sex: string | null;
  birth_date: string | null;
  death_date: string | null;
  notes: string | null;
  valid_from: string;
  source_ids: number[];
};

type Source = {
  id: number;
  source_type: string;
  citation: string;
};

type Props = {
  persons: Person[];
  sources: Source[];
};

export default function PersonManager({ persons: initialPersons, sources }: Props) {
  const [persons, setPersons] = useState<Person[]>(initialPersons);
  const [showAddModal, setShowAddModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [primaryName, setPrimaryName] = useState("");
  const [sex, setSex] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [deathDate, setDeathDate] = useState("");
  const [notes, setNotes] = useState("");
  const [validFrom, setValidFrom] = useState(new Date().toISOString().split("T")[0]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);


  const validateForm = (): string | null => {
    if (!primaryName.trim()) {
      return "Primary name is required";
    }
    if (selectedSourceIds.length === 0) {
      return "At least one source is required";
    }
    if (birthDate && deathDate) {
      const birth = new Date(birthDate);
      const death = new Date(deathDate);
      if (death < birth) {
        return "Death date cannot be before birth date";
      }
    }
    return null;
  };

  const handleAddPerson = async () => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {

      type CreatePersonPayload = {
        primary_name: string;
        valid_from: string;
        source_ids: number[];
        sex?: string;
        birth_date?: string;
        death_date?: string;
        notes?: string;
      };

      const payload: CreatePersonPayload = {
        primary_name: primaryName,
        valid_from: validFrom,
        source_ids: selectedSourceIds,
      };

      if (sex) payload.sex = sex;
      if (birthDate) payload.birth_date = birthDate;
      if (deathDate) payload.death_date = deathDate;
      if (notes) payload.notes = notes;

      const resp = await fetch(`/api/backend/persons`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(errorText || `Failed to create person (${resp.status})`);
      }

      const newPerson = await resp.json();
      setPersons([newPerson, ...persons]);
      setSuccess(`Person "${newPerson.primary_name}" (ID #${newPerson.id}) created successfully`);
      setShowAddModal(false);

      // Reset form
      setPrimaryName("");
      setSex("");
      setBirthDate("");
      setDeathDate("");
      setNotes("");
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
          {sources.length} sources available for linking
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
          + Add Person
        </button>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              ID
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Name
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Sex
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Birth
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Death
            </th>
            <th style={{ textAlign: "left", padding: "8px 4px", fontSize: 12, fontWeight: 600 }}>
              Sources
            </th>
          </tr>
        </thead>
        <tbody>
          {persons.length === 0 ? (
            <tr>
              <td colSpan={6} style={{ padding: "20px", textAlign: "center", color: "var(--muted)" }}>
                No persons yet. Click + Add Person to create the first entry.
              </td>
            </tr>
          ) : (
            persons.map((person) => (
              <tr key={person.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "10px 4px", fontSize: 13 }}>#{person.id}</td>
                <td style={{ padding: "10px 4px", fontSize: 13, fontWeight: 600 }}>
                  {person.primary_name}
                </td>
                <td style={{ padding: "10px 4px", fontSize: 13 }}>
                  {person.sex ? <Badge tone="neutral">{person.sex}</Badge> : "—"}
                </td>
                <td style={{ padding: "10px 4px", fontSize: 13, color: "var(--muted)" }}>
                  {person.birth_date || "—"}
                </td>
                <td style={{ padding: "10px 4px", fontSize: 13, color: "var(--muted)" }}>
                  {person.death_date || "—"}
                </td>
                <td style={{ padding: "10px 4px", fontSize: 13 }}>
                  <Badge tone="info">{person.source_ids?.length || 0} sources</Badge>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Add Person Modal */}
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
            <h3 style={{ marginBottom: 16, fontWeight: 700 }}>Add New Person</h3>

            {sources.length === 0 && (
              <Alert tone="warning" title="No Sources Available" dense>
                You must create at least one source before adding persons.
                <a
                  href="/dashboard/data/sources"
                  style={{ marginLeft: 8, color: "var(--info)" }}
                >
                  Create Source →
                </a>
              </Alert>
            )}

            <div style={{ display: "grid", gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Primary Name <span style={{ color: "var(--error)" }}>*</span>
                </label>
                <input
                  type="text"
                  value={primaryName}
                  onChange={(e) => setPrimaryName(e.target.value)}
                  placeholder="e.g., Elizabeth II"
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
                  Sex
                </label>
                <select
                  value={sex}
                  onChange={(e) => setSex(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    background: "var(--panel-soft)",
                    color: "var(--text)",
                  }}
                >
                  <option value="">-- select --</option>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                </select>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                    Birth Date
                  </label>
                  <input
                    type="date"
                    value={birthDate}
                    onChange={(e) => setBirthDate(e.target.value)}
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
                    Death Date
                  </label>
                  <input
                    type="date"
                    value={deathDate}
                    onChange={(e) => setDeathDate(e.target.value)}
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

              <div>
                <label style={{ display: "block", marginBottom: 4, fontSize: 13, fontWeight: 600 }}>
                  Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Additional information"
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
                            {source.citation.substring(0, 100)}
                            {source.citation.length > 100 ? "..." : ""}
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
                onClick={handleAddPerson}
                disabled={loading || sources.length === 0}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--panel-soft)",
                  color: "var(--text)",
                  cursor: sources.length === 0 ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  opacity: sources.length === 0 ? 0.5 : 1,
                }}
              >
                {loading ? "Creating..." : "Create Person"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
