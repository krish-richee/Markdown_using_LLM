import { useEffect, useState, useMemo } from "react";
import { fetchPlanner } from "../api/client";

// ── Helpers ────────────────────────────────────────────────────────────────
const fmt = (n) => {
  if (!n || isNaN(n)) return "₹0";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(1)}Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(1)}L`;
  return `₹${Math.round(n).toLocaleString()}`;
};

const RISK_COLOR  = { HIGH: "#f59e0b", CRITICAL: "#dc2626", MEDIUM: "#3b82f6", LOW: "#10b981" };
const RISK_BG     = { HIGH: "#fffbeb", CRITICAL: "#fff1f2", MEDIUM: "#eff6ff", LOW: "#f0fdf4" };
const dosDisplay  = (dos) => {
  if (dos === -1 || dos >= 9999) return ">2yr";
  if (dos > 3650) return `${Math.round(dos/365)}y`;
  return `${dos}d`;
};
const dosColor    = (dos) => (dos === -1 || dos >= 9999) ? "#dc2626" : dos > 365 ? "#f59e0b" : dos > 180 ? "#f59e0b" : "#374151";

// ── Ladder step strip ──────────────────────────────────────────────────────
function LadderSteps({ steps, currentStep }) {
  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
      {steps.map((step, i) => {
        const isActive = i === currentStep;
        const isDone   = i < currentStep;
        return (
          <div key={i} style={{
            flex: 1, padding: "10px 12px", borderRadius: 8, textAlign: "center",
            background: isActive ? "#4f46e5" : isDone ? "#e0e7ff" : "#f3f4f6",
            border: isActive ? "none" : "0.5px solid #e2e4e9",
            transition: "background 0.2s",
          }}>
            <div style={{
              fontSize: 18, fontWeight: 700,
              color: isActive ? "#fff" : isDone ? "#4f46e5" : "#9ca3af",
            }}>
              -{step.pct}%
            </div>
            <div style={{
              fontSize: 10, marginTop: 2,
              color: isActive ? "#c7d2fe" : "#9ca3af",
            }}>
              {step.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Single ladder card ─────────────────────────────────────────────────────
function LadderCard({ ladder, onApprove, onReject, approved, rejected }) {
  const [expanded, setExpanded] = useState(false);

  const capitalTied = (ladder.qty || 0) * (ladder.price || 0);
  const stColor = ladder.sell_through < 30 ? "#dc2626"
                : ladder.sell_through < 60 ? "#f59e0b" : "#15803d";
  const _dosLabel = dosDisplay(ladder.dos);
  const _dosColor = dosColor(ladder.dos);
  const riskC     = RISK_COLOR[ladder.risk] || "#9ca3af";
  const riskBg    = RISK_BG[ladder.risk]    || "#f3f4f6";

  const actionState = approved ? "approved" : rejected ? "rejected" : null;

  return (
    <div style={{
      background: "#fff",
      border: actionState === "approved" ? "1.5px solid #10b981"
            : actionState === "rejected" ? "1.5px solid #ef4444"
            : "0.5px solid #e2e4e9",
      borderRadius: 12,
      padding: "16px 20px",
      marginBottom: 10,
      boxShadow: "0 1px 6px rgba(0,0,0,0.05)",
      transition: "box-shadow 0.2s",
      position: "relative",
      overflow: "hidden",
    }}>

      {/* Approved / rejected banner */}
      {actionState && (
        <div style={{
          position: "absolute", top: 0, right: 0,
          background: actionState === "approved" ? "#10b981" : "#ef4444",
          color: "#fff", fontSize: 10, fontWeight: 700,
          padding: "3px 12px", borderBottomLeftRadius: 8,
          letterSpacing: "0.06em",
        }}>
          {actionState === "approved" ? "✓ APPROVED" : "✕ REJECTED"}
        </div>
      )}

      {/* ── Header ── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#1a1d23" }}>{ladder.product_name}</span>
          {/* Risk badge */}
          <span style={{
            fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 10,
            background: riskBg, color: riskC, border: `1px solid ${riskC}44`,
          }}>
            {ladder.risk}
          </span>
          {/* ABC badge */}
          <span style={{
            fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 10,
            background: "#f3f4f6", color: "#6b7280",
          }}>
            {ladder.abc} Class
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 11, color: "#9ca3af" }}>
            Step {ladder.current_step + 1}/{ladder.total_steps}
          </span>
          {/* expand toggle */}
          <button onClick={() => setExpanded(e => !e)} style={{
            background: "none", border: "0.5px solid #e2e4e9", borderRadius: 6,
            padding: "3px 8px", cursor: "pointer", fontSize: 11, color: "#6b7280",
          }}>
            {expanded ? "▲ Less" : "▼ More"}
          </button>
        </div>
      </div>

      {/* ── Ladder steps ── */}
      <LadderSteps steps={ladder.steps} currentStep={ladder.current_step} />

      {/* ── Meta row ── */}
      <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 12, display: "flex", flexWrap: "wrap", gap: "4px 14px" }}>
        <span>{ladder.product_id} · {ladder.category} · {ladder.brand}</span>
        <span>
          ₹{ladder.curr_price?.toLocaleString()}{" "}
          <span style={{ textDecoration: "line-through", color: "#9ca3af" }}>
            (was ₹{ladder.was_price?.toLocaleString()})
          </span>
        </span>
        <span>Margin: {ladder.margin_pct}%</span>
        <span style={{ color: _dosColor, fontWeight: 600 }}>DOS: {_dosLabel}</span>
      </div>

      {/* ── Stats row ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 6, marginBottom: 12 }}>
        {[
          { label: "Stock on Hand", value: (ladder.qty || 0).toLocaleString(),   color: null       },
          { label: "Capital Tied",  value: fmt(capitalTied),                      color: "#dc2626"  },
          { label: "Sell-Through",  value: `${ladder.sell_through}%`,            color: stColor    },
          { label: "Current Step",  value: `${ladder.current_step+1}/${ladder.total_steps}`, color: null },
          { label: "DOS",           value: _dosLabel,                             color: _dosColor  },
        ].map((s, i) => (
          <div key={i} style={{
            background: "#f9fafb", borderRadius: 8,
            padding: "8px 10px", textAlign: "center",
            border: "0.5px solid #f1f3f5",
          }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: s.color || "#1a1d23" }}>{s.value}</div>
            <div style={{ fontSize: 10, color: "#9ca3af", marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Expanded detail ── */}
      {expanded && (
        <div style={{
          background: "#f9fafb", borderRadius: 8, padding: "12px 14px",
          marginBottom: 12, border: "0.5px solid #e2e4e9",
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "#374151", marginBottom: 8 }}>
            📋 Markdown Ladder Rationale
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8 }}>
            {ladder.steps.map((step, i) => (
              <div key={i} style={{
                background: "#fff", borderRadius: 6, padding: "8px 10px",
                border: i === ladder.current_step ? "1.5px solid #4f46e5" : "0.5px solid #e2e4e9",
              }}>
                <div style={{ fontSize: 13, fontWeight: 700,
                              color: i === ladder.current_step ? "#4f46e5" : "#374151" }}>
                  Step {i + 1} — -{step.pct}%
                </div>
                <div style={{ fontSize: 10, color: "#6b7280", marginTop: 3 }}>{step.label}</div>
                <div style={{ fontSize: 11, color: "#374151", marginTop: 4 }}>
                  Price → ₹{(ladder.price * (1 - step.pct / 100)).toFixed(0).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Action buttons ── */}
      {!actionState && (
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={() => onReject(ladder.product_id)} style={{
            padding: "6px 16px", borderRadius: 7, fontSize: 12, fontWeight: 600,
            border: "1px solid #fca5a5", background: "#fff5f5", color: "#dc2626", cursor: "pointer",
          }}>
            ✕ Reject
          </button>
          <button onClick={() => onApprove(ladder.product_id)} style={{
            padding: "6px 16px", borderRadius: 7, fontSize: 12, fontWeight: 600,
            border: "none", background: "#4f46e5", color: "#fff", cursor: "pointer",
            boxShadow: "0 2px 6px rgba(79,70,229,0.25)",
          }}>
            ✓ Approve Ladder
          </button>
        </div>
      )}
    </div>
  );
}

// ── Summary KPI bar ────────────────────────────────────────────────────────
function SummaryKPIs({ summary, approved, rejected }) {
  const fmtC = (n) => {
    if (!n || isNaN(n)) return "₹0";
    if (n >= 1e7) return `₹${(n / 1e7).toFixed(1)}Cr`;
    if (n >= 1e5) return `₹${(n / 1e5).toFixed(1)}L`;
    return `₹${Math.round(n).toLocaleString()}`;
  };
  // avg_dos sentinel: 9999 = all infinite; 0 = NaN fallback (treat same as infinite)
  const avgDosLabel = !summary ? "—"
    : (summary.avg_dos >= 9999 || summary.avg_dos === 0) ? ">2yr"
    : summary.avg_dos > 3650 ? `${Math.round(summary.avg_dos/365)}y`
    : `${summary.avg_dos}d`;
  const avgDosColor = !summary ? "#4f46e5"
    : (summary.avg_dos >= 9999 || summary.avg_dos === 0) ? "#dc2626" : "#4f46e5";

  const kpis = [
    { label: "Total Candidates",   value: summary?.total_candidates?.toLocaleString() || "—", color: "#f59e0b", sub: "products needing markdown" },
    { label: "Capital at Risk",    value: summary ? fmtC(summary.capital_at_risk) : "—",       color: "#dc2626", sub: "inventory value at risk"   },
    { label: "Avg Days of Stock",  value: avgDosLabel,                                           color: avgDosColor, sub: "across all candidates"    },
    { label: "Approved",           value: approved.size,                                          color: "#10b981", sub: "ladders approved"           },
    { label: "Pending",            value: (summary?.total_candidates || 0) - approved.size - rejected.size,
                                    color: "#f59e0b", sub: "awaiting review"            },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 10, marginBottom: 16 }}>
      {kpis.map((k, i) => (
        <div key={i} style={{
          background: "#fff", border: "0.5px solid #e2e4e9",
          borderRadius: 10, padding: "14px 16px",
          boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
        }}>
          <div style={{ fontSize: 10, color: "#9ca3af", fontWeight: 600,
                        textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 5 }}>
            {k.label}
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, color: k.color }}>{k.value}</div>
          <div style={{ fontSize: 10, color: "#9ca3af", marginTop: 3 }}>{k.sub}</div>
        </div>
      ))}
    </div>
  );
}

// ── Main Planner page ──────────────────────────────────────────────────────
export default function Planner() {
  const [data,        setData]        = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [approved,    setApproved]    = useState(new Set());
  const [rejected,    setRejected]    = useState(new Set());

  // Filters
  const [filterRisk,  setFilterRisk]  = useState("All");
  const [filterABC,   setFilterABC]   = useState("All");
  const [filterBrand, setFilterBrand] = useState("All");
  const [sortBy,      setSortBy]      = useState("dos_desc");
  const [searchQ,     setSearchQ]     = useState("");
  const [showOnly,    setShowOnly]    = useState("all"); // all | pending | approved | rejected

  useEffect(() => {
    setLoading(true);
    fetchPlanner().then(d => { setData(d); setLoading(false); });
  }, []);

  const ladders = data?.ladders || [];

  // Unique filter options
  const allRisks  = useMemo(() => ["All", ...new Set(ladders.map(l => l.risk).filter(Boolean))], [ladders]);
  const allABCs   = useMemo(() => ["All", ...new Set(ladders.map(l => l.abc).filter(Boolean)).values()].sort(), [ladders]);
  const allBrands = useMemo(() => ["All", ...new Set(ladders.map(l => l.brand).filter(Boolean))].sort(), [ladders]);

  // Filtered + sorted ladders
  const filtered = useMemo(() => {
    let arr = [...ladders];
    if (filterRisk  !== "All") arr = arr.filter(l => l.risk  === filterRisk);
    if (filterABC   !== "All") arr = arr.filter(l => l.abc   === filterABC);
    if (filterBrand !== "All") arr = arr.filter(l => l.brand === filterBrand);
    if (searchQ.trim()) {
      const q = searchQ.trim().toLowerCase();
      arr = arr.filter(l =>
        l.product_name?.toLowerCase().includes(q) ||
        l.product_id?.toLowerCase().includes(q) ||
        l.brand?.toLowerCase().includes(q) ||
        l.category?.toLowerCase().includes(q)
      );
    }
    if (showOnly === "approved") arr = arr.filter(l => approved.has(l.product_id));
    if (showOnly === "rejected") arr = arr.filter(l => rejected.has(l.product_id));
    if (showOnly === "pending")  arr = arr.filter(l => !approved.has(l.product_id) && !rejected.has(l.product_id));

    if (sortBy === "dos_desc")    arr.sort((a, b) => b.dos - a.dos);
    if (sortBy === "dos_asc")     arr.sort((a, b) => a.dos - b.dos);
    if (sortBy === "capital")     arr.sort((a, b) => (b.qty*b.price) - (a.qty*a.price));
    if (sortBy === "sell_through") arr.sort((a, b) => a.sell_through - b.sell_through);
    if (sortBy === "risk")        {
      const o = { CRITICAL:0, HIGH:1, MEDIUM:2, LOW:3 };
      arr.sort((a, b) => (o[a.risk]||4) - (o[b.risk]||4));
    }
    return arr;
  }, [ladders, filterRisk, filterABC, filterBrand, searchQ, sortBy, showOnly, approved, rejected]);

  const handleApprove = (id) => {
    setApproved(prev => new Set([...prev, id]));
    setRejected(prev => { const s = new Set(prev); s.delete(id); return s; });
  };
  const handleReject = (id) => {
    setRejected(prev => new Set([...prev, id]));
    setApproved(prev => { const s = new Set(prev); s.delete(id); return s; });
  };

  const handleBulkApprove = () => {
    const ids = filtered.filter(l => !rejected.has(l.product_id)).map(l => l.product_id);
    setApproved(prev => new Set([...prev, ...ids]));
  };

  // pill button style
  const pill = (active, danger) => ({
    padding: "5px 12px", borderRadius: 20, fontSize: 11, fontWeight: 600,
    border: active ? "none" : "0.5px solid #e2e4e9",
    background: active ? (danger ? "#dc2626" : "#4f46e5") : "#fff",
    color: active ? "#fff" : "#6b7280",
    cursor: "pointer",
  });

  const selectStyle = {
    padding: "5px 10px", borderRadius: 7, fontSize: 11, fontWeight: 500,
    border: "0.5px solid #e2e4e9", background: "#fff", color: "#374151",
    cursor: "pointer",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

      {/* ── Summary KPIs ── */}
      <SummaryKPIs summary={data?.summary} approved={approved} rejected={rejected} />

      {/* ── Filter & control bar ── */}
      <div style={{
        background: "#fff", border: "0.5px solid #e2e4e9", borderRadius: 10,
        padding: "12px 16px", display: "flex", flexWrap: "wrap",
        alignItems: "center", gap: 8,
        boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
      }}>
        {/* Search */}
        <input
          placeholder="🔍 Search product, brand, SKU…"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          style={{
            padding: "5px 10px", borderRadius: 7, fontSize: 11,
            border: "0.5px solid #e2e4e9", width: 200, outline: "none",
          }}
        />

        {/* Risk filter */}
        <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)} style={selectStyle}>
          {allRisks.map(r => <option key={r}>{r}</option>)}
        </select>

        {/* ABC filter */}
        <select value={filterABC} onChange={e => setFilterABC(e.target.value)} style={selectStyle}>
          {allABCs.map(a => <option key={a}>{a === "All" ? "All ABC" : `Class ${a}`}</option>)}
        </select>

        {/* Brand filter */}
        <select value={filterBrand} onChange={e => setFilterBrand(e.target.value)} style={selectStyle}>
          {allBrands.map(b => <option key={b}>{b}</option>)}
        </select>

        {/* Sort */}
        <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={selectStyle}>
          <option value="risk">Sort: By Risk</option>
          <option value="dos_desc">Sort: DOS ↓</option>
          <option value="dos_asc">Sort: DOS ↑</option>
          <option value="capital">Sort: Capital Tied</option>
          <option value="sell_through">Sort: Sell-Through ↑</option>
        </select>

        <div style={{ flex: 1 }} />

        {/* Show only pills */}
        <button onClick={() => setShowOnly("all")}      style={pill(showOnly==="all")}>All</button>
        <button onClick={() => setShowOnly("pending")}  style={pill(showOnly==="pending")}>Pending</button>
        <button onClick={() => setShowOnly("approved")} style={pill(showOnly==="approved")}>✓ Approved</button>
        <button onClick={() => setShowOnly("rejected")} style={pill(showOnly==="rejected", true)}>✕ Rejected</button>

        {/* Bulk approve */}
        <button onClick={handleBulkApprove} style={{
          padding: "5px 14px", borderRadius: 7, fontSize: 11, fontWeight: 700,
          border: "none", background: "#4f46e5", color: "#fff",
          cursor: "pointer", marginLeft: 4,
        }}>
          ✓ Approve All Visible
        </button>
      </div>

      {/* ── Result count ── */}
      <div style={{ fontSize: 12.5, color: "#6b7280" }}>
        Markdown ladders — step-by-step clearance schedules ·{" "}
        showing <strong>{filtered.length}</strong>{" "}
        {filtered.length !== ladders.length && `of ${ladders.length} `}products
        {approved.size > 0 && <span style={{ color: "#10b981", marginLeft: 10 }}>· {approved.size} approved</span>}
        {rejected.size > 0 && <span style={{ color: "#dc2626", marginLeft: 10 }}>· {rejected.size} rejected</span>}
      </div>

      {/* ── Cards ── */}
      {loading && (
        <div style={{ padding: 60, color: "#9ca3af", textAlign: "center" }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
          Loading planner data…
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div style={{
          padding: 40, color: "#9ca3af", textAlign: "center",
          background: "#fff", borderRadius: 12, border: "0.5px solid #e2e4e9",
        }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>🎉</div>
          No products match the current filters.
        </div>
      )}

      {filtered.map(ladder => (
        <LadderCard
          key={ladder.product_id}
          ladder={ladder}
          onApprove={handleApprove}
          onReject={handleReject}
          approved={approved.has(ladder.product_id)}
          rejected={rejected.has(ladder.product_id)}
        />
      ))}
    </div>
  );
}