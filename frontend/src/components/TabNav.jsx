import { useNavigate, useLocation } from "react-router-dom";

const tabs = [
  { label: "Dashboard",      path: "/dashboard" },
  { label: "Planner",        path: "/planner" },
  { label: "Actions",        path: "/actions" },
  { label: "History",        path: "/history" },
  { label: "🔔 Notifications", path: "/notifications" },
];

export default function TabNav() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div style={{ background: "#fff", borderBottom: "0.5px solid #e2e4e9", padding: "0 20px", display: "flex", flexShrink: 0 }}>
      <div style={{ marginBottom: 12, paddingTop: 12 }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: "#1a1d23" }}>Markdown Management</div>
        <div style={{ fontSize: 11, color: "#9ca3af" }}>Agent #5 · Price IQ · Clear inventory profitably</div>
      </div>
      <div style={{ display: "flex", marginLeft: "auto", alignItems: "flex-end" }}>
        {tabs.map(t => (
          <div key={t.path} onClick={() => navigate(t.path)} style={{
            padding: "10px 16px", fontSize: 13, fontWeight: 500, cursor: "pointer",
            color: location.pathname === t.path ? "#4f46e5" : "#6b7280",
            borderBottom: location.pathname === t.path ? "2px solid #4f46e5" : "2px solid transparent",
          }}>{t.label}</div>
        ))}
      </div>
    </div>
  );
}
