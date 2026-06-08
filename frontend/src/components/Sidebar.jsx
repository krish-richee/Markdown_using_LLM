import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

const groups = [
  {
    id: "priceiq", label: "Price IQ", icon: "💲",
    meta: "3 agents · 173K dec",
    children: [
      { label: "Dynamic Pricing", badge: "89K", path: null },
      { label: "Promo Optimization", badge: "52K", path: null },
      { label: "Markdown Mgmt", badge: "31K", path: "/dashboard" },
    ],
  },
  {
    id: "supplyiq", label: "Supply IQ", icon: "📦",
    meta: "0 agents · 3 coming", children: [],
  },
  {
    id: "growthiq", label: "Growth IQ", icon: "📈",
    meta: "4 agents · 62K dec", children: [],
  },
];

export default function Sidebar() {
  const [open, setOpen] = useState({ priceiq: true });
  const navigate = useNavigate();
  const location = useLocation();

  const toggle = (id) => setOpen(p => ({ ...p, [id]: !p[id] }));

  return (
    <div style={{
      width: 220, minWidth: 220, background: "#fff",
      borderRight: "0.5px solid #e2e4e9", display: "flex", flexDirection: "column",
    }}>
      {/* Brand */}
      <div style={{ padding: "16px", borderBottom: "0.5px solid #e2e4e9", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 28, height: 28, background: "#4f46e5", borderRadius: 7, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 13 }}>G</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1d23" }}>Growdhi.ai</div>
          <div style={{ fontSize: 10, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.07em" }}>Decision Intelligence</div>
        </div>
      </div>

      {/* Nav */}
      <div style={{ flex: 1, overflowY: "auto", padding: "10px 8px" }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: "#b0b4bd", textTransform: "uppercase", letterSpacing: "0.08em", padding: "10px 8px 4px" }}>Modules</div>

        {groups.map(g => (
          <div key={g.id} style={{ marginBottom: 2 }}>
            <div onClick={() => toggle(g.id)} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 10px", cursor: "pointer", borderRadius: 8,
              background: open[g.id] ? "#eef2ff" : "transparent",
              color: open[g.id] ? "#4f46e5" : "#374151",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span>{g.icon}</span>
                <div>
                  <div style={{ fontWeight: 500, fontSize: 13 }}>{g.label}</div>
                  <div style={{ fontSize: 10, color: "#9ca3af", fontWeight: 400 }}>{g.meta}</div>
                </div>
              </div>
              <span style={{ fontSize: 11, color: "#9ca3af", transform: open[g.id] ? "rotate(180deg)" : "none", display: "inline-block", transition: "transform 0.18s" }}>▾</span>
            </div>

            {open[g.id] && g.children.map(c => (
              <div key={c.label} onClick={() => c.path && navigate(c.path)}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "7px 10px 7px 32px", borderRadius: 7, margin: "1px 0",
                  cursor: c.path ? "pointer" : "default",
                  background: c.path && location.pathname === c.path ? "#eef2ff" : "transparent",
                  color: c.path && location.pathname === c.path ? "#4f46e5" : "#6b7280",
                  fontWeight: c.path && location.pathname === c.path ? 500 : 400,
                }}>
                <span style={{ fontSize: 12.5 }}>{c.label}</span>
                <span style={{ fontSize: 10, fontWeight: 600, padding: "1px 7px", borderRadius: 10, background: "#f3f4f6", color: "#6b7280" }}>{c.badge}</span>
              </div>
            ))}
          </div>
        ))}

        <hr style={{ border: "none", borderTop: "0.5px solid #e2e4e9", margin: "8px 0" }} />
        <div style={{ fontSize: 10, fontWeight: 600, color: "#b0b4bd", textTransform: "uppercase", letterSpacing: "0.08em", padding: "4px 8px 4px" }}>Tenant Admin</div>
        {["🔌 Data Connections", "👥 User Access", "⚙️ Settings"].map(item => (
          <div key={item} style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 10px", borderRadius: 7, color: "#6b7280", cursor: "pointer", fontSize: 12.5 }}>{item}</div>
        ))}
      </div>
    </div>
  );
}