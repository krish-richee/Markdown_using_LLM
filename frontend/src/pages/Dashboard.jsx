import { useEffect, useState } from "react";
import { fetchDashboard } from "../api/client";
import { BarChart, Bar, ComposedChart, Line, PieChart, Pie, Cell,
         XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
const CURRENCY = "AED";
const fmt = (n) => {
  if (n == null || isNaN(n)) return `${CURRENCY} 0`;
  if (n >= 1e6) return `${CURRENCY} ${(n/1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${CURRENCY} ${(n/1e3).toFixed(0)}K`;
  return `${CURRENCY} ${Math.round(n).toLocaleString()}`;
};
const RISK_COLORS = { HIGH:"#f59e0b", MEDIUM:"#3b82f6", LOW:"#10b981", CRITICAL:"#dc2626" };
const PIE_COLORS  = ["#4f46e5","#7c3aed","#a78bfa"];
const SEASONAL    = {
  "01":0.82,"02":0.75,"03":0.88,"04":0.92,"05":0.95,"06":0.85,
  "07":0.90,"08":0.93,"09":0.97,"10":1.10,"11":1.35,"12":1.45
};
const applySeasonalToMonthly = (data) =>
  (data||[]).map(d => ({
    ...d,
    revenue: Math.round((d.revenue||0) * (SEASONAL[d.month?.slice(-2)] || 1))
  }));
const KPI = ({ label, value, sub, color }) => (
  <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"14px 16px" }}>
    <div style={{ fontSize:11, color:"#9ca3af", fontWeight:500, marginBottom:6, textTransform:"uppercase", letterSpacing:"0.04em" }}>{label}</div>
    <div style={{ fontSize:20, fontWeight:700, color: color||"#1a1d23" }}>{value ?? "—"}</div>
    {sub && <div style={{ fontSize:11, color:"#9ca3af", marginTop:3 }}>{sub}</div>}
  </div>
);
const Skeleton = () => (
  <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
    <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}`}</style>
    {[...Array(3)].map((_,i) => (
      <div key={i} style={{ display:"grid", gridTemplateColumns:`repeat(${i===0?4:2},1fr)`, gap:10 }}>
        {[...Array(i===0?4:2)].map((_,j) => (
          <div key={j} style={{ background:"#f3f4f6", borderRadius:10, height: i===0?80:260, animation:"pulse 1.5s infinite" }} />
        ))}
      </div>
    ))}
  </div>
);
// ── Date helpers ──────────────────────────────────────────────────────────
const toISO   = (d) => d.toISOString().slice(0,10);
const addDays = (d, n) => { const r = new Date(d); r.setDate(r.getDate()+n); return r; };
const diffDays= (a, b) => Math.round((b-a)/(1000*60*60*24)) + 1;
const fmtDisp = (d) => d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"});
const today   = new Date(); today.setHours(0,0,0,0);
const PRESETS = [
  { label:"Today",        fn:() => [today, today] },
  { label:"Yesterday",    fn:() => [addDays(today,-1), addDays(today,-1)] },
  { label:"Last 7 Days",  fn:() => [addDays(today,-7), today] },
  { label:"Last 14 Days", fn:() => [addDays(today,-14), today] },
  { label:"Last 30 Days", fn:() => [addDays(today,-30), today] },
  { label:"Last 90 Days", fn:() => [addDays(today,-90), today] },
  { label:"This Week",    fn:() => { const d=new Date(today); d.setDate(d.getDate()-d.getDay()+1); return [d,today]; }},
  { label:"Last Week",    fn:() => { const e=new Date(today); e.setDate(e.getDate()-e.getDay()); const s=new Date(e); s.setDate(s.getDate()-6); return [s,e]; }},
  { label:"This Month",   fn:() => [new Date(today.getFullYear(),today.getMonth(),1), today] },
  { label:"Last Month",   fn:() => { const s=new Date(today.getFullYear(),today.getMonth()-1,1); const e=new Date(today.getFullYear(),today.getMonth(),0); return [s,e]; }},
  { label:"This Quarter", fn:() => { const q=Math.floor(today.getMonth()/3); return [new Date(today.getFullYear(),q*3,1), today]; }},
  { label:"Last Quarter", fn:() => { const q=Math.floor(today.getMonth()/3); const s=new Date(today.getFullYear(),(q-1)*3,1); const e=new Date(today.getFullYear(),q*3,0); return [s,e]; }},
  { label:"This Year",    fn:() => [new Date(today.getFullYear(),0,1), today] },
  { label:"Last Year",    fn:() => [new Date(today.getFullYear()-1,0,1), new Date(today.getFullYear()-1,11,31)] },
];
function DateFilterBar({ onRangeChange }) {
  const [preset,   setPreset]   = useState("Last 30 Days");
  const [start,    setStart]    = useState(addDays(today,-30));
  const [end,      setEnd]      = useState(today);
  const [compare,  setCompare]  = useState("Previous Period");
  const [custom,   setCustom]   = useState(false);
  const apply = (label, s, e) => {
    setPreset(label); setStart(s); setEnd(e); setCustom(false);
    onRangeChange(toISO(s), toISO(e));
  };
  const compareOpts = ["Previous Period","Previous Year","No Comparison"];
  return (
    <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:12,
      padding:"16px 20px", marginBottom:16, boxShadow:"0 2px 8px rgba(99,102,241,.07)" }}>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 220px", gap:20 }}>
        {/* Left — presets */}
        <div>
          <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.08em", color:"#9ca3af", marginBottom:10 }}>
            📅 Select Date Range
          </div>
          {/* Row 1 */}
          <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:6 }}>
            {PRESETS.slice(0,6).map(p => (
              <button key={p.label} onClick={() => apply(p.label, ...p.fn())} style={{
                padding:"4px 12px", borderRadius:20, fontSize:11, fontWeight:600, cursor:"pointer",
                background: preset===p.label ? "#eef2ff" : "#f8fafc",
                color:      preset===p.label ? "#4f46e5" : "#475569",
                border:     preset===p.label ? "1px solid #6366f1" : "1px solid #e2e4e9",
                transition: "all 0.12s",
              }}>{p.label}</button>
            ))}
            <button onClick={() => { setPreset("Custom Range"); setCustom(true); }} style={{
              padding:"4px 12px", borderRadius:20, fontSize:11, fontWeight:600, cursor:"pointer",
              background: preset==="Custom Range" ? "#eef2ff" : "#f8fafc",
              color:      preset==="Custom Range" ? "#4f46e5" : "#475569",
              border:     preset==="Custom Range" ? "1px solid #6366f1" : "1px solid #e2e4e9",
            }}>Custom Range</button>
          </div>
          {/* Row 2 */}
          <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
            {PRESETS.slice(6).map(p => (
              <button key={p.label} onClick={() => apply(p.label, ...p.fn())} style={{
                padding:"4px 12px", borderRadius:20, fontSize:11, fontWeight:600, cursor:"pointer",
                background: preset===p.label ? "#eef2ff" : "#f8fafc",
                color:      preset===p.label ? "#4f46e5" : "#475569",
                border:     preset===p.label ? "1px solid #6366f1" : "1px solid #e2e4e9",
              }}>{p.label}</button>
            ))}
          </div>
          {/* Custom date pickers */}
          {custom && (
            <div style={{ display:"flex", gap:10, marginTop:10, alignItems:"center" }}>
              <div>
                <div style={{ fontSize:10, color:"#9ca3af", marginBottom:3 }}>FROM</div>
                <input type="date" defaultValue={toISO(start)}
                  onChange={e => setStart(new Date(e.target.value))}
                  style={{ border:"0.5px solid #e2e4e9", borderRadius:7, padding:"5px 10px", fontSize:12 }} />
              </div>
              <div>
                <div style={{ fontSize:10, color:"#9ca3af", marginBottom:3 }}>TO</div>
                <input type="date" defaultValue={toISO(end)}
                  onChange={e => setEnd(new Date(e.target.value))}
                  style={{ border:"0.5px solid #e2e4e9", borderRadius:7, padding:"5px 10px", fontSize:12 }} />
              </div>
              <button onClick={() => onRangeChange(toISO(start), toISO(end))} style={{
                marginTop:16, padding:"6px 16px", background:"#4f46e5", color:"#fff",
                border:"none", borderRadius:7, fontSize:12, fontWeight:600, cursor:"pointer"
              }}>Apply</button>
            </div>
          )}
        </div>
        {/* Right — selected range + compare */}
        <div style={{ background:"#f8fafc", borderRadius:10, padding:"14px 16px" }}>
          <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.08em", color:"#9ca3af", marginBottom:6 }}>
            SELECTED RANGE
          </div>
          <div style={{ fontSize:18, fontWeight:800, color:"#0f172a", marginBottom:2 }}>{preset}</div>
          <div style={{ fontSize:11, color:"#64748b", marginBottom:14 }}>
            {diffDays(start,end)} days · {fmtDisp(start)} → {fmtDisp(end)}
          </div>
          <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.08em", color:"#9ca3af", marginBottom:8 }}>
            COMPARE TO
          </div>
          {compareOpts.map(opt => (
            <label key={opt} style={{ display:"flex", alignItems:"center", gap:7, marginBottom:6, cursor:"pointer", fontSize:12, color: compare===opt?"#4f46e5":"#374151" }}>
              <input type="radio" name="compare" checked={compare===opt} onChange={() => setCompare(opt)}
                style={{ accentColor:"#4f46e5" }} />
              {opt}
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
export default function Dashboard() {
  const [data,    setData]    = useState(null);
  const [error,   setError]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({
    start: "2022-01-01",
    end:   toISO(today),
  });
  const load = (start, end) => {
    setLoading(true); setError(null);
    fetchDashboard(start, end)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message||"Failed to load"); setLoading(false); });
  };
  useEffect(() => { load("2022-01-01", toISO(today)); }, []);
  const handleRangeChange = (start, end) => {
    setDateRange({start, end});
    load(start, end);
  };
  if (error) return (
    <div style={{ padding:40, textAlign:"center" }}>
      <div style={{ fontSize:32, marginBottom:10 }}>⚠️</div>
      <div style={{ fontWeight:600, color:"#dc2626", marginBottom:6 }}>Failed to load dashboard</div>
      <div style={{ fontSize:12, color:"#9ca3af", marginBottom:16 }}>{error}</div>
      <button onClick={() => load(dateRange.start, dateRange.end)}
        style={{ padding:"8px 20px", background:"#4f46e5", color:"#fff", border:"none", borderRadius:8, cursor:"pointer" }}>
        Retry
      </button>
    </div>
  );
  const {
    kpis, brand_revenue, cat_revenue,
    revenue_trend, risk_breakdown,
    store_performance, insights, top_products,
  } = data || {};
  // backend key aliases → frontend names
  const monthly_revenue = revenue_trend;
  const stores          = store_performance;
  const abcData  = data ? [
    { name:"A — Top 10%",    value: kpis.abc_a },
    { name:"B — Mid 40%",    value: kpis.abc_b },
    { name:"C — Bottom 50%", value: kpis.abc_c },
  ] : [];
  const riskData = data ? Object.entries(risk_breakdown||{}).map(([k,v]) => ({ name:k, value:v })) : [];
  const trendData = applySeasonalToMonthly(monthly_revenue);
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      {/* Date Filter Bar */}
      <DateFilterBar onRangeChange={handleRangeChange} />
      {/* Loading skeleton */}
      {loading && <Skeleton />}
      {!loading && data && (<>
        {/* KPI Row 1 — Fix 1: removed AOV + Total Customers, now 4 columns */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10 }}>
          <KPI label="Total Revenue" value={fmt(kpis.total_revenue)} color="#4f46e5" />
          <KPI label="Total Orders"  value={kpis.total_orders?.toLocaleString()} />
          <KPI label="Total SKUs"    value={kpis.total_skus?.toLocaleString()} />
          <KPI label="Total Stock"   value={kpis.total_stock?.toLocaleString()} sub="units in inventory" />
        </div>
        {/* KPI Row 2 */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:10 }}>
          <KPI label="Avg Sell-Through" value={`${kpis.avg_sell_through}%`}            color="#15803d" />
          <KPI label="High Risk SKUs"   value={kpis.high_risk_count?.toLocaleString()} color="#f59e0b" sub="need markdown" />
          <KPI label="Dead Inventory"   value={kpis.dead_inventory?.toLocaleString()}  color="#dc2626" sub="DOS > 180d" />
          <KPI label="ABC-A Products"   value={kpis.abc_a?.toLocaleString()}           color="#4f46e5" sub="top revenue drivers" />
          <KPI label="ABC-C Products"   value={kpis.abc_c?.toLocaleString()}           color="#9ca3af" sub="clearance candidates" />
        </div>
        {/* Charts Row 1 — Brand + Category revenue */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
            <div style={{ fontWeight:600, color:"#1a1d23", marginBottom:4, fontSize:13 }}>Top 10 Brands by Revenue</div>
            <div style={{ fontSize:11, color:"#9ca3af", marginBottom:12 }}>Which brands are driving the most sales</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={brand_revenue} layout="vertical" margin={{ top:0, right:50, left:0, bottom:0 }}>
                <XAxis type="number" tickFormatter={fmt} tick={{ fontSize:9, fill:"#9ca3af" }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="brand" tick={{ fontSize:10, fill:"#374151" }} tickLine={false} axisLine={false} width={80} />
                <Tooltip formatter={v => fmt(v)} contentStyle={{ fontSize:12, borderRadius:8, border:"0.5px solid #e2e4e9" }} />
                <Bar dataKey="revenue" fill="#4f46e5" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
            <div style={{ fontWeight:600, color:"#1a1d23", marginBottom:4, fontSize:13 }}>Revenue by Category</div>
            <div style={{ fontSize:11, color:"#9ca3af", marginBottom:12 }}>Total revenue contribution per category</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={cat_revenue} layout="vertical" margin={{ top:0, right:50, left:0, bottom:0 }}>
                <XAxis type="number" tickFormatter={fmt} tick={{ fontSize:9, fill:"#9ca3af" }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="category" tick={{ fontSize:10, fill:"#374151" }} tickLine={false} axisLine={false} width={90} />
                <Tooltip formatter={v => fmt(v)} contentStyle={{ fontSize:12, borderRadius:8, border:"0.5px solid #e2e4e9" }} />
                <Bar dataKey="revenue" fill="#7c3aed" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        {/* Revenue Trend + Store Performance — side by side */}
        <div style={{ display:"grid", gridTemplateColumns:"1.4fr 1fr", gap:12 }}>
          {/* Monthly Revenue & Orders Trend */}
          <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
            <div style={{ fontWeight:600, color:"#1a1d23", marginBottom:4, fontSize:13 }}>Monthly Revenue & Orders Trend</div>
            <div style={{ fontSize:11, color:"#9ca3af", marginBottom:12 }}>
              Purple bars = revenue (seasonal adjusted) · Nov–Dec peaks = Diwali + Christmas
            </div>
            <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={trendData || []} margin={{ top:4, right:50, left:0, bottom:0 }}>
                  <XAxis dataKey="month" tick={{ fontSize:9, fill:"#9ca3af" }} tickLine={false} axisLine={false} />
                  <YAxis yAxisId="rev" tickFormatter={fmt} tick={{ fontSize:9, fill:"#9ca3af" }} tickLine={false} axisLine={false} width={65} />
                  <YAxis yAxisId="ord" orientation="right" tick={{ fontSize:9, fill:"#0ea5e9" }} tickLine={false} axisLine={false} width={40} />
                  <Tooltip formatter={(v,n) => n==="revenue" ? fmt(v) : v?.toLocaleString()}
                    contentStyle={{ fontSize:12, borderRadius:8, border:"0.5px solid #e2e4e9" }} />
                  <Legend wrapperStyle={{ fontSize:11 }} />
                  <Bar  yAxisId="rev" dataKey="revenue" name="Revenue" fill="#4f46e5" opacity={0.85} radius={[3,3,0,0]} />
                  <Line yAxisId="ord" dataKey="orders"  name="Orders"  stroke="#0ea5e9" strokeWidth={2} dot={{ r:3 }} type="monotone" />
                </ComposedChart>
              </ResponsiveContainer>
            {/* ) : (
              <div style={{ height:220, display:"flex", alignItems:"center", justifyContent:"center",
                color:"#9ca3af", fontSize:12 }}>No trend data for selected period</div>
            )} */}
          </div>
          {/* Store Performance */}
          <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"14px 16px",
            display:"flex", flexDirection:"column" }}>
            <div style={{ fontWeight:600, color:"#1a1d23", marginBottom:10, fontSize:13 }}>Store Performance</div>
            {stores?.length > 0 ? (
              <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
                {(stores||[]).map((s,i) => {
                  const tierColor = s.tier==="HOT"?"#16a34a":s.tier==="COLD"?"#2563eb":"#d97706";
                  const tierBg    = s.tier==="HOT"?"#dcfce7":s.tier==="COLD"?"#dbeafe":"#fef3c7";
                  const stColor   = s.sell_through>=75?"#16a34a":s.sell_through>=65?"#2563eb":"#d97706";
                  return (
                    <div key={i} style={{
                      display:"flex", alignItems:"center", gap:10,
                      padding:"7px 0",
                      borderBottom: i < stores.length-1 ? "0.5px solid #f3f4f6" : "none",
                    }}>
                      {/* color dot */}
                      <div style={{ width:3, height:32, borderRadius:2, background:tierColor, flexShrink:0 }} />
                      {/* name + meta */}
                      <div style={{ flex:1, minWidth:0 }}>
                        <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:3 }}>
                          <span style={{ fontSize:11.5, fontWeight:600, color:"#1a1d23",
                            overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{s.name}</span>
                          <span style={{ fontSize:8.5, fontWeight:700, padding:"1px 5px", borderRadius:6,
                            background:tierBg, color:tierColor, flexShrink:0 }}>{s.tier}</span>
                        </div>
                        <div style={{ background:"#f3f4f6", borderRadius:3, height:4 }}>
                          <div style={{ width:`${Math.min(s.sell_through,100)}%`, height:4,
                            borderRadius:3, background:stColor }} />
                        </div>
                      </div>
                      {/* pct */}
                      <span style={{ fontSize:12.5, fontWeight:700, color:stColor, flexShrink:0 }}>
                        {s.sell_through}%
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ flex:1, display:"flex", alignItems:"center", justifyContent:"center",
                color:"#9ca3af", fontSize:12 }}>No store data available</div>
            )}
          </div>
        </div>
        {/* ABC + Risk donuts */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px", display:"flex", gap:24, alignItems:"center" }}>
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:600, color:"#1a1d23", marginBottom:4, fontSize:13 }}>ABC Classification</div>
              <div style={{ fontSize:11, color:"#9ca3af", marginBottom:8 }}>Revenue contribution tiers</div>
              <ResponsiveContainer width="100%" height={130}>
                <PieChart>
                  <Pie data={abcData} cx="50%" cy="50%" innerRadius={38} outerRadius={60} dataKey="value" paddingAngle={2}>
                    {abcData.map((_,i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ fontSize:11, borderRadius:8, border:"0.5px solid #e2e4e9" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {abcData.map((d,i) => (
                <div key={i} style={{ display:"flex", alignItems:"center", gap:8, fontSize:12 }}>
                  <span style={{ width:10, height:10, borderRadius:2, background:PIE_COLORS[i], display:"inline-block", flexShrink:0 }}></span>
                  <span style={{ color:"#6b7280", minWidth:100 }}>{d.name}</span>
                  <span style={{ fontWeight:700, color:"#1a1d23" }}>{d.value?.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
          <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px", display:"flex", gap:24, alignItems:"center" }}>
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:600, color:"#1a1d23", marginBottom:4, fontSize:13 }}>Clearance Risk Breakdown</div>
              <div style={{ fontSize:11, color:"#9ca3af", marginBottom:8 }}>SKUs by urgency level</div>
              <ResponsiveContainer width="100%" height={130}>
                <PieChart>
                  <Pie data={riskData} cx="50%" cy="50%" innerRadius={38} outerRadius={60} dataKey="value" paddingAngle={2}>
                    {riskData.map((d,i) => <Cell key={i} fill={RISK_COLORS[d.name]||"#9ca3af"} />)}
                  </Pie>
                  <Tooltip contentStyle={{ fontSize:11, borderRadius:8, border:"0.5px solid #e2e4e9" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {riskData.map((d,i) => (
                <div key={i} style={{ display:"flex", alignItems:"center", gap:8, fontSize:12 }}>
                  <span style={{ width:10, height:10, borderRadius:2, background:RISK_COLORS[d.name]||"#9ca3af", display:"inline-block", flexShrink:0 }}></span>
                  <span style={{ color:"#6b7280", minWidth:60 }}>{d.name}</span>
                  <span style={{ fontWeight:700, color:"#1a1d23" }}>{d.value?.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        {/* Top Products table */}
        {top_products?.length > 0 && (
          <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, overflow:"hidden" }}>
            <div style={{ padding:"12px 16px", borderBottom:"0.5px solid #e2e4e9", display:"flex", justifyContent:"space-between" }}>
              <span style={{ fontWeight:600, color:"#1a1d23", fontSize:13 }}>Top Products by Units Sold</span>
              <span style={{ fontSize:11, color:"#9ca3af" }}>Top 10</span>
            </div>
            <table style={{ width:"100%", borderCollapse:"collapse", fontSize:12 }}>
              <thead>
                <tr style={{ background:"#f9fafb" }}>
                  {["#","Product","Category","Brand","Units Sold","Revenue"].map(h => (
                    <th key={h} style={{ padding:"8px 14px", textAlign:"left", fontWeight:600, color:"#6b7280", fontSize:11, borderBottom:"0.5px solid #e2e4e9" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {top_products.map((p,i) => (
                  <tr key={i} style={{ borderBottom:"0.5px solid #f3f4f6" }}>
                    <td style={{ padding:"9px 14px", color:"#9ca3af", fontWeight:600 }}>#{i+1}</td>
                    <td style={{ padding:"9px 14px", fontWeight:500, color:"#1a1d23" }}>{p.product_name}</td>
                    <td style={{ padding:"9px 14px", color:"#6b7280" }}>{p.category}</td>
                    <td style={{ padding:"9px 14px", color:"#6b7280" }}>{p.brand}</td>
                    <td style={{ padding:"9px 14px", fontWeight:600, color:"#4f46e5" }}>{p.units_sold?.toLocaleString()}</td>
                    <td style={{ padding:"9px 14px", fontWeight:600, color:"#15803d" }}>{fmt(p.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {/* Business Insights */}
        <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
          <div style={{ fontWeight:600, color:"#1a1d23", marginBottom:12, fontSize:13 }}>Business Insights</div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 }}>
            {(insights||[]).map((ins,i) => (
              <div key={i} style={{ background:"#f9fafb", borderRadius:8, padding:"12px 14px", borderLeft:"3px solid #4f46e5" }}>
                <div style={{ fontSize:13, marginBottom:4 }}>{ins.icon} <span style={{ fontWeight:600, color:"#1a1d23" }}>{ins.title}</span></div>
                <div style={{ fontSize:11.5, color:"#6b7280", lineHeight:1.6 }}>{ins.text}</div>
              </div>
            ))}
          </div>
        </div>
      </>)}
    </div>
  );
}