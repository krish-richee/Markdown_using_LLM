export default function TopBar() {
  return (
    <div style={{
      background: "#fff", borderBottom: "0.5px solid #e2e4e9",
      padding: "0 20px", height: 44, display: "flex",
      alignItems: "center", justifyContent: "space-between", flexShrink: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
        <span style={{ color: "#9ca3af", cursor: "pointer" }}>Price IQ</span>
        <span style={{ color: "#d1d5db" }}>›</span>
        <span style={{ fontWeight: 600, color: "#1a1d23" }}>Markdown Management</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, border: "0.5px solid #e2e4e9", borderRadius: 20, padding: "4px 12px", fontSize: 12, color: "#374151" }}>
          <div style={{ width: 8, height: 8, background: "#10b981", borderRadius: "50%" }}></div>
          APeak.ai — All Markets
        </div>
        <span style={{ fontSize: 11, fontWeight: 600, background: "#f0fdf4", color: "#15803d", padding: "2px 8px", borderRadius: 10 }}>AED</span>
      </div>
    </div>
  );
}