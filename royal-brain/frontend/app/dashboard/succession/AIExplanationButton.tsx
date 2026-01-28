"use client";

import { useState } from "react";
import Alert from "@/components/ui/Alert";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";

type EvalResult = {
  status: "VALID" | "INVALID" | "UNCERTAIN";
  path_person_ids?: number[] | null;
  relationship_ids?: number[] | null;
  reasons: { code: string; message: string; severity: string; person_id?: number | null }[];
  rule_type: string;
  root_person_id: number;
  candidate_person_id: number;
  checked_paths: number;
  applied_rule?: unknown;
  as_of?: string | null;
};

type SourceReference = {
  id: number;
  source_type: string;
  citation: string;
  url?: string | null;
  issued_date?: string | null;
};

type AIExplanation = {
  summary: string;
  detailed_reasoning: string;
  citations: { category: string; description: string }[];
  confidence: number;
  sources: SourceReference[];
  rules_applied: Record<string, unknown>;
};

type Props = {
  evaluation: EvalResult;
};

export default function AIExplanationButton({ evaluation }: Props) {
  const [explanation, setExplanation] = useState<AIExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchExplanation() {
    setLoading(true);
    setError(null);

    try {
      const resp = await fetch("/api/ai/explain-succession", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result: evaluation }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({ detail: "AI service unavailable" }));
        setError(data.detail || "Failed to generate explanation");
        return;
      }

      const data = await resp.json();
      setExplanation(data.explanation);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {!explanation && !error && (
        <div style={{ marginTop: 12 }}>
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchExplanation}
            loading={loading}
            disabled={loading}
          >
            Generate AI Explanation
          </Button>
          <div className="subtle" style={{ fontSize: 12, marginTop: 6 }}>
            Uses OpenAI if configured; otherwise returns a deterministic explanation.
          </div>
        </div>
      )}

      {error && (
        <div style={{ marginTop: 12 }}>
          <Alert tone="warning">{error}</Alert>
        </div>
      )}

      {explanation && (
        <Card title="AI Explanation" description="Human-readable analysis with citations">
          <div className="grid" style={{ gap: 12 }}>
            <div>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>Summary</div>
              <div>{explanation.summary}</div>
              <div className="row" style={{ gap: 8, flexWrap: "wrap", marginTop: 8 }}>
                <Badge tone="neutral">
                  confidence: {(explanation.confidence * 100).toFixed(1)}%
                </Badge>
                <Badge tone="neutral">sources: {explanation.sources.length}</Badge>
              </div>
            </div>

            <div>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>Detailed Reasoning</div>
              <div style={{ lineHeight: 1.5 }}>{explanation.detailed_reasoning}</div>
            </div>

            {explanation.sources.length > 0 && (
              <div>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Sources</div>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {explanation.sources.map((s) => (
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
              </div>
            )}

            <div>
              <details>
                <summary style={{ cursor: "pointer", fontWeight: 700 }}>Rules applied</summary>
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
                  {JSON.stringify(explanation.rules_applied, null, 2)}
                </pre>
              </details>
            </div>

            {explanation.citations.length > 0 && (
              <div>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Citations</div>
                <div className="grid" style={{ gap: 6 }}>
                  {explanation.citations.map((c, idx) => (
                    <div key={idx} className="row" style={{ gap: 8, alignItems: "flex-start" }}>
                      <Badge
                        tone={
                          c.category === "applied_rule"
                            ? "info"
                            : c.category === "uncertainty"
                            ? "warning"
                            : "neutral"
                        }
                      >
                        {c.category}
                      </Badge>
                      <span className="subtle" style={{ fontSize: 13 }}>
                        {c.description}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </>
  );
}
