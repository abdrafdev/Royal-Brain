"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import Alert from "@/components/ui/Alert";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Input from "@/components/ui/Input";

type Props = {
  reason?: string;
};

export default function LoginForm({ reason }: Props) {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!resp.ok) {
        const data = (await resp.json().catch(() => ({}))) as { error?: string };
        setError(data.error ?? "Authentication failed.");
        return;
      }

      router.replace("/dashboard");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 32,
        background: "radial-gradient(circle at 20% 30%, rgba(246,195,68,0.12), transparent 30%), radial-gradient(circle at 80% 10%, rgba(105,184,255,0.10), transparent 26%), var(--bg)",
      }}
    >
      <div style={{ width: "100%", maxWidth: 1080 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            style={{
              width: 64,
              height: 64,
              margin: "0 auto",
              borderRadius: 18,
              background: "linear-gradient(135deg, #f6c344, #e89f18)",
              display: "grid",
              placeItems: "center",
              boxShadow: "0 18px 36px rgba(246,195,68,0.35)",
            }}
          >
            <span style={{ color: "#0d111a", fontSize: 26 }}>🛡️</span>
          </div>
          <h1 style={{ marginTop: 14, fontSize: 26, letterSpacing: "-0.01em" }}>Royal BrAIn™</h1>
          <div className="subtle" style={{ marginTop: 4, fontSize: 14 }}>
            Institutional Verification Console
          </div>
        </div>

        <Card padded={false}>
          <div style={{ padding: "22px 22px 24px" }}>
            {reason === "expired" ? (
              <Alert tone="info" dense>
                Session expired. Please sign in again.
              </Alert>
            ) : null}

            {error ? (
              <div style={{ marginTop: 10 }}>
                <Alert tone="error">{error}</Alert>
              </div>
            ) : null}

            <form onSubmit={onSubmit} style={{ marginTop: 14, display: "grid", gap: 14 }}>
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                required
                placeholder="Enter your email"
              />

              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                placeholder="Enter your password"
              />

              <Button type="submit" loading={submitting} style={{ width: "100%", height: 50 }}>
                Sign in
              </Button>
            </form>
          </div>

          <div
            style={{
              padding: "12px 18px 16px",
              borderTop: "1px solid var(--border)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: 12,
              color: "var(--muted)",
            }}
          >
            <span>Demo access</span>
            <span>admin@royalbrain.dev / change-me-now</span>
          </div>
        </Card>
      </div>
    </main>
  );
}
