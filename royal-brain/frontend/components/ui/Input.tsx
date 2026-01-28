"use client";

import type { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
};

export default function Input({ label, hint, style, ...rest }: Props) {
  return (
    <label style={{ display: "block", width: "100%" }}>
      {label ? (
        <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 6 }}>{label}</div>
      ) : null}
      <input
        {...rest}
        style={{
          width: "100%",
          padding: "12px 14px",
          borderRadius: 10,
          border: "1px solid var(--border)",
          background: "var(--panel-soft)",
          color: "var(--text)",
          fontSize: 14,
          outline: "none",
          transition: "border 120ms ease, box-shadow 120ms ease",
          ...style,
        }}
        onFocus={(e) => {
          e.currentTarget.style.border = "1px solid var(--border-strong)";
          e.currentTarget.style.boxShadow = "0 0 0 3px rgba(246, 195, 68, 0.15)";
        }}
        onBlur={(e) => {
          e.currentTarget.style.border = "1px solid var(--border)";
          e.currentTarget.style.boxShadow = "none";
        }}
      />
      {hint ? (
        <div style={{ marginTop: 4, fontSize: 12, color: "var(--muted)" }}>{hint}</div>
      ) : null}
    </label>
  );
}
