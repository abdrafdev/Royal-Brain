import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
};

const bg: Record<Variant, string> = {
  primary: "linear-gradient(135deg, #f6c344, #e89f18)",
  secondary: "rgba(255, 255, 255, 0.06)",
  ghost: "transparent",
};

const color: Record<Variant, string> = {
  primary: "#0d111a",
  secondary: "#e9edf7",
  ghost: "#e9edf7",
};

const border: Record<Variant, string> = {
  primary: "1px solid rgba(246, 195, 68, 0.8)",
  secondary: "1px solid rgba(255, 255, 255, 0.08)",
  ghost: "1px solid transparent",
};

export default function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  iconLeft,
  iconRight,
  disabled,
  style,
  ...rest
}: Props) {
  const height = size === "sm" ? 34 : 42;
  const padding = size === "sm" ? "6px 12px" : "10px 16px";

  return (
    <button
      {...rest}
      disabled={disabled || loading}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        height,
        padding,
        borderRadius: 10,
        border: border[variant],
        background: bg[variant],
        color: color[variant],
        fontWeight: 600,
        cursor: disabled || loading ? "not-allowed" : "pointer",
        opacity: disabled || loading ? 0.6 : 1,
        transition: "transform 120ms ease, box-shadow 120ms ease",
        boxShadow:
          variant === "primary"
            ? "0 14px 30px rgba(246, 195, 68, 0.25)"
            : "0 10px 22px rgba(0,0,0,0.25)",
        ...style,
      }}
    >
      {iconLeft ? <span style={{ display: "inline-flex" }}>{iconLeft}</span> : null}
      <span>{loading ? "Loading..." : children}</span>
      {iconRight ? <span style={{ display: "inline-flex" }}>{iconRight}</span> : null}
    </button>
  );
}
