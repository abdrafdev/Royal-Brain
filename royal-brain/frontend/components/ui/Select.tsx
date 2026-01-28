"use client";

import type { SelectHTMLAttributes, ReactNode } from "react";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  hint?: string;
  icon?: ReactNode;
};

export default function Select({ label, hint, icon, style, children, ...rest }: Props) {
  return (
    <label style={{ display: "block", width: "100%" }}>
      {label ? (
        <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 6 }}>{label}</div>
      ) : null}
      <div
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          background: "var(--panel-soft)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: "2px 10px",
        }}
      >
        {icon ? <span style={{ color: "var(--muted)", marginRight: 6 }}>{icon}</span> : null}
        <select
          {...rest}
          style={{
            flex: 1,
            padding: "10px 6px",
            background: "transparent",
            border: "none",
            color: "var(--text)",
            fontSize: 14,
            outline: "none",
            appearance: "none",
            ...style,
          }}
          onFocus={(e) => {
            const parent = e.currentTarget.parentElement;
            if (parent) {
              parent.style.border = "1px solid var(--border-strong)";
              parent.style.boxShadow = "0 0 0 3px rgba(246, 195, 68, 0.12)";
            }
          }}
          onBlur={(e) => {
            const parent = e.currentTarget.parentElement;
            if (parent) {
              parent.style.border = "1px solid var(--border)";
              parent.style.boxShadow = "none";
            }
          }}
        >
          {children}
        </select>
      </div>
      {hint ? (
        <div style={{ marginTop: 4, fontSize: 12, color: "var(--muted)" }}>{hint}</div>
      ) : null}
    </label>
  );
}
