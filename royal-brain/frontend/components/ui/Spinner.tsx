export default function Spinner({ size = 16 }: { size?: number }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        border: `${Math.max(2, Math.floor(size / 8))}px solid rgba(255,255,255,0.15)`,
        borderTopColor: "#7c5dff",
        animation: "spin 0.8s linear infinite",
      }}
    />
  );
}

// Inject keyframes once (safe in module scope for Next.js app router)
if (typeof document !== "undefined") {
  const id = "rb-spin";
  if (!document.getElementById(id)) {
    const style = document.createElement("style");
    style.id = id;
    style.innerHTML = `@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
  }
}
