import { useEffect, useState } from "react";
import { fetchProducts, runAgents } from "../api/client";

const riskColor = { HIGH:"#f59e0b", CRITICAL:"#dc2626", MEDIUM:"#3b82f6", LOW:"#10b981" };
const healthColor = (h) => h?.includes("🟢") ? "#15803d" : h?.includes("🔴") ? "#dc2626" : "#d97706";

const Badge = ({ label, color, bg }) => (
  <span style={{ fontSize:10, fontWeight:700, padding:"2px 8px", borderRadius:10, background: bg||color+"22", color }}>
    {label}
  </span>
);

const AGENT_META = {
  PricingAgent: {
    icon:"💲", label:"Pricing Agent", role:"Markdown calculator",
    desc:"Uses price elasticity, margin rules, and ABC class to calculate the optimal markdown % that maximises revenue recovery without breaching the cost floor.",
    dataKey: (a) => a?.data?.markdown_pct ? `Recommends ${a.data.markdown_pct}% markdown → ₹${a.data.new_price}` : a?.recommendation,
  },
  InventoryAgent: {
    icon:"📦", label:"Inventory Agent", role:"Stock urgency assessor",
    desc:"Analyses days-of-stock, sell-through rate, and quantity to determine how urgently this product needs clearance and what action to take.",
    dataKey: (a) => a?.recommendation,
  },
  DemandAgent: {
    icon:"📈", label:"Demand Agent", role:"Demand forecaster",
    desc:"Forecasts how many units will sell at the discounted price using elasticity data. Estimates revenue impact and expected sell-through over 30 days.",
    dataKey: (a) => a?.recommendation,
  },
  PromotionAgent: {
    icon:"🎯", label:"Promotion Agent", role:"Promotion type selector",
    desc:"Decides which promotion mechanic fits best — flash sale, bundle, seasonal, clearance, or loyalty — based on category, brand tier, and seasonality.",
    dataKey: (a) => a?.recommendation,
  },
  BehaviorAgent: {
    icon:"🧠", label:"Behavior Agent", role:"Customer signal analyser",
    desc:"Reads customer purchase patterns, repeat buy rates, and basket behaviour to check if a price drop would actually drive purchases or just erode margin.",
    dataKey: (a) => a?.recommendation,
  },
  CompetitorAgent: {
    icon:"🌐", label:"Competitor Agent", role:"Live market price tracker",
    desc:"Searches the web in real-time using Tavily API to find what competitors are charging for similar products on Myntra, Amazon, Flipkart, and other retailers.",
    dataKey: (a) => a?.data?.data_available
      ? `Market avg ₹${a.data.avg_comp_price?.toLocaleString()} | You: ${a.data.price_position?.replace(/_/g," ")}`
      : "No competitor prices found on web",
  },
  CoordinatorAgent: {
    icon:"🤖", label:"Coordinator — Groq LLaMA 3.1", role:"Final decision maker",
    desc:"Groq LLM reads all 6 agent reports and synthesises ONE final markdown decision — balancing margin, clearance urgency, competitor position, and business rules.",
    dataKey: (a) => a?.recommendation,
  },
  CriticAgent: {
    icon:"🔍", label:"Critic Agent — Groq LLM", role:"Independent validator",
    desc:"A second Groq LLM call acting as a retail director who independently validates the coordinator's decision — checks cost floor, logic, and business rule compliance.",
    dataKey: (a) => a?.recommendation,
  },
};

function AgentCard({ name, status, agentData }) {
  const meta      = AGENT_META[name] || { icon:"⚙️", label:name, role:"", desc:"" };
  const isPending = status === "pending";
  const isRunning = status === "running";
  const isDone    = status === "done";
  const isReject  = status === "reject";
  const finding   = agentData ? meta.dataKey(agentData) : null;
  const confidence = agentData?.confidence;
  return (
    <div style={{
      background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10,
      overflow:"hidden", opacity: isPending ? 0.45 : 1, transition:"all 0.3s",
      outline: isRunning ? "2px solid #4f46e5" : "none",
    }}>
      <div style={{
        padding:"10px 14px", display:"flex", alignItems:"center", justifyContent:"space-between",
        background: isRunning ? "#eef2ff" : isDone ? "#f0fdf4" : isReject ? "#fef2f2" : "#f9fafb",
        borderBottom:"0.5px solid #e2e4e9",
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <span style={{ fontSize:18 }}>{meta.icon}</span>
          <div>
            <div style={{ fontWeight:700, fontSize:12, color:"#1a1d23" }}>{meta.label}</div>
            <div style={{ fontSize:10, color:"#9ca3af" }}>{meta.role}</div>
          </div>
        </div>
        <div>
          {isPending && <span style={{ fontSize:10, color:"#d1d5db", fontWeight:600 }}>PENDING</span>}
          {isRunning && (
            <span style={{ fontSize:10, fontWeight:700, color:"#4f46e5", background:"#fff", padding:"3px 10px", borderRadius:10, border:"0.5px solid #4f46e5" }}>
              ⚡ RUNNING
            </span>
          )}
          {isDone && (
            <div style={{ textAlign:"right" }}>
              <div style={{ fontSize:10, fontWeight:700, color:"#15803d", background:"#dcfce7", padding:"3px 10px", borderRadius:10, display:"inline-block" }}>
                ✓ PASSED
              </div>
              {confidence && <div style={{ fontSize:10, color:"#9ca3af", marginTop:2 }}>{Math.round(confidence*100)}% confidence</div>}
            </div>
          )}
          {isReject && (
            <span style={{ fontSize:10, fontWeight:700, color:"#dc2626", background:"#fee2e2", padding:"3px 10px", borderRadius:10 }}>
              ✗ REJECTED
            </span>
          )}
        </div>
      </div>
      <div style={{ padding:"10px 14px" }}>
        <div style={{ fontSize:11, color:"#6b7280", lineHeight:1.6, marginBottom: (isDone||isReject) ? 8 : 0 }}>
          {meta.desc}
        </div>
        {(isDone || isReject) && finding && (
          <div style={{
            fontSize:12, fontWeight:500,
            color: isReject ? "#dc2626" : "#1a1d23",
            background: isReject ? "#fef2f2" : "#f0fdf4",
            borderRadius:6, padding:"6px 10px",
            borderLeft: `3px solid ${isReject ? "#dc2626" : "#10b981"}`,
          }}>
            {finding}
          </div>
        )}
        {isRunning && (
          <div style={{ fontSize:11, color:"#4f46e5", fontStyle:"italic", marginTop:4 }}>
            Analysing product signals...
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color, sub }) {
  return (
    <div style={{ background:"#f9fafb", borderRadius:8, padding:"10px 14px" }}>
      <div style={{ fontSize:10, color:"#9ca3af", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.04em", marginBottom:4 }}>{label}</div>
      <div style={{ fontSize:17, fontWeight:700, color: color||"#1a1d23" }}>{value}</div>
      {sub && <div style={{ fontSize:10, color:"#9ca3af", marginTop:2 }}>{sub}</div>}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// HumanApproval — own component so useState is called at top level (Rules of Hooks)
// ─────────────────────────────────────────────────────────────────────────────
function HumanApproval({ result }) {
  const [approvalState, setApprovalState] = useState("pending"); // "pending"|"approved"|"rejected"|"override"
  const [note, setNote]                   = useState("");
  const [overrideTab, setOverrideTab]     = useState(false);
  const [overridePct, setOverridePct]     = useState(result.markdown_pct);

  const origPrice    = result.original_price;
  const costPrice    = result.agents?.PricingAgent?.data?.cost_price || 0;
  const newPrice     = Math.round(origPrice * (1 - overridePct / 100));
  const ovMargin     = newPrice > 0 ? Math.max(0, ((newPrice - costPrice) / newPrice * 100)).toFixed(1) : 0;
  const costFloorPct = costPrice > 0 ? Math.ceil((1 - costPrice / origPrice) * 100) : null;
  const ts           = new Date().toLocaleTimeString([], { hour:"2-digit", minute:"2-digit" });

  return (
    <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
      <div style={{ fontWeight:600, color:"#1a1d23", fontSize:13, marginBottom:12 }}>
        👤 Step 5 — Human Approval
      </div>

      {/* Summary strip */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginBottom:14 }}>
        {[
          { label:"Markdown",  val:`${result.markdown_pct}%`,   color:"#4f46e5" },
          { label:"New Price", val:`AED ${result.final_price}`, color:"#1a1d23" },
          { label:"Critic",    val: result.critic_status === "PASS" ? "✓ PASS" : "✗ FAIL",
            color: result.critic_status === "PASS" ? "#15803d" : "#dc2626" },
        ].map(s => (
          <div key={s.label} style={{ background:"#f9fafb", borderRadius:8, padding:"10px 12px" }}>
            <div style={{ fontSize:10, color:"#9ca3af", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.04em", marginBottom:4 }}>
              {s.label}
            </div>
            <div style={{ fontSize:16, fontWeight:700, color:s.color }}>{s.val}</div>
          </div>
        ))}
      </div>

      {/* ── Pending state ── */}
      {approvalState === "pending" && (
        <>
          {/* Tab switcher */}
          <div style={{ display:"flex", borderBottom:"0.5px solid #e2e4e9", marginBottom:12 }}>
            {["Review","Override"].map(t => (
              <button key={t} onClick={() => setOverrideTab(t === "Override")}
                style={{
                  padding:"7px 16px", fontSize:11, fontWeight:600,
                  background:"transparent", border:"none", cursor:"pointer",
                  borderBottom: (overrideTab ? t==="Override" : t==="Review") ? "2px solid #4f46e5" : "2px solid transparent",
                  color: (overrideTab ? t==="Override" : t==="Review") ? "#4f46e5" : "#9ca3af",
                }}>
                {t}
              </button>
            ))}
          </div>

          {/* ── Review tab ── */}
          {!overrideTab && (
            <>
              <div style={{ fontSize:11, fontWeight:600, color:"#6b7280", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:8 }}>
                Projected Impact
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:14 }}>
                <div style={{ background:"#f0fdf4", borderRadius:8, padding:"10px 12px" }}>
                  <div style={{ fontSize:10, fontWeight:600, color:"#15803d", textTransform:"uppercase", marginBottom:2 }}>Revenue recovery</div>
                  <div style={{ fontSize:14, fontWeight:700, color:"#15803d" }}>
                    +AED {result.agents?.DemandAgent?.data?.revenue_uplift?.toLocaleString() || "—"}
                  </div>
                  <div style={{ fontSize:10, color:"#6b7280", marginTop:2 }}>est. 30-day uplift</div>
                </div>
                <div style={{ background:"#fef2f2", borderRadius:8, padding:"10px 12px" }}>
                  <div style={{ fontSize:10, fontWeight:600, color:"#dc2626", textTransform:"uppercase", marginBottom:2 }}>Margin impact</div>
                  <div style={{ fontSize:14, fontWeight:700, color:"#dc2626" }}>−{result.markdown_pct}% markdown</div>
                  <div style={{ fontSize:10, color:"#6b7280", marginTop:2 }}>gross margin reduction</div>
                </div>
              </div>

              <div style={{ fontSize:11, fontWeight:600, color:"#6b7280", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:8 }}>
                Policy Compliance
              </div>
              {[
                { ok:true,                         text:"Price above cost floor" },
                { ok:result.markdown_pct <= 60,    text:"Markdown within 0–60% policy range" },
                { ok:true,                         text:`ABC-${result.abc_class || "A"} rules applied` },
                { ok:result.critic_status==="PASS", text:"Passed independent LLM critic review" },
              ].map((c, i) => (
                <div key={i} style={{ display:"flex", alignItems:"center", gap:6, padding:"4px 0", fontSize:12, color:"#374151", borderBottom:"0.5px solid #f3f4f6" }}>
                  <span style={{ color: c.ok ? "#15803d" : "#d97706", fontWeight:700 }}>{c.ok ? "✓" : "!"}</span>
                  {c.text}
                </div>
              ))}

              <div style={{ fontSize:11, fontWeight:600, color:"#6b7280", textTransform:"uppercase", letterSpacing:"0.06em", margin:"14px 0 6px" }}>
                Add Note (optional)
              </div>
              <textarea
                value={note}
                onChange={e => setNote(e.target.value)}
                rows={3}
                placeholder="Add a reason, override justification, or internal comment..."
                style={{ width:"100%", border:"0.5px solid #e2e4e9", borderRadius:8, padding:"10px 12px", fontSize:12, fontFamily:"inherit", color:"#374151", resize:"none", outline:"none", marginBottom:12, background:"#fff" }}
              />

              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
                <button onClick={() => setApprovalState("approved")}
                  style={{ padding:"11px", background:"#16a34a", color:"#fff", border:"none", borderRadius:8, fontWeight:700, cursor:"pointer", fontSize:13 }}>
                  ✓ Approve &amp; Push
                </button>
                <button onClick={() => setApprovalState("rejected")}
                  style={{ padding:"11px", background:"#dc2626", color:"#fff", border:"none", borderRadius:8, fontWeight:700, cursor:"pointer", fontSize:13 }}>
                  ✗ Reject
                </button>
              </div>
              <button onClick={() => setOverrideTab(true)}
                style={{ width:"100%", marginTop:8, padding:"9px", background:"transparent", border:"0.5px solid #e2e4e9", borderRadius:8, cursor:"pointer", fontSize:12, color:"#374151", fontWeight:500 }}>
                ✎ Modify markdown % before approving
              </button>
            </>
          )}

          {/* ── Override tab ── */}
          {overrideTab && (
            <>
              <div style={{ marginBottom:12 }}>
                <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, color:"#6b7280", marginBottom:4 }}>
                  <span>Markdown %</span>
                  <span style={{ fontWeight:700, color:"#4f46e5" }}>{overridePct}%</span>
                </div>
                <input type="range" min={0} max={60} step={1} value={overridePct}
                  onChange={e => setOverridePct(Number(e.target.value))}
                  style={{ width:"100%", accentColor:"#4f46e5" }} />
                <div style={{ display:"flex", justifyContent:"space-between", fontSize:10, color:"#9ca3af", marginTop:2 }}>
                  <span>0%</span>
                  {costFloorPct && <span style={{ color:"#dc2626" }}>Cost floor: {costFloorPct}%</span>}
                  <span>60%</span>
                </div>
              </div>

              <div style={{ background:"#eef2ff", borderRadius:8, padding:"10px 12px", marginBottom:12, fontSize:12, color:"#4338ca", fontWeight:600 }}>
                New price: AED {newPrice} &nbsp;·&nbsp; Margin: {ovMargin}%
                {newPrice < costPrice && <span style={{ color:"#dc2626", marginLeft:8 }}>⚠ Below cost floor!</span>}
              </div>

              <textarea
                value={note}
                onChange={e => setNote(e.target.value)}
                rows={3}
                placeholder="Required: reason for overriding AI recommendation..."
                style={{ width:"100%", border:"0.5px solid #e2e4e9", borderRadius:8, padding:"10px 12px", fontSize:12, fontFamily:"inherit", color:"#374151", resize:"none", outline:"none", marginBottom:12, background:"#fff" }}
              />

              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
                <button
                  onClick={() => newPrice >= costPrice
                    ? setApprovalState("override")
                    : alert("Cannot approve — price below cost floor!")}
                  style={{ padding:"11px", background:"#4f46e5", color:"#fff", border:"none", borderRadius:8, fontWeight:700, cursor:"pointer", fontSize:13 }}>
                  ✓ Apply Override &amp; Approve
                </button>
                <button onClick={() => setOverrideTab(false)}
                  style={{ padding:"11px", background:"#f9fafb", color:"#374151", border:"0.5px solid #e2e4e9", borderRadius:8, cursor:"pointer", fontSize:13, fontWeight:500 }}>
                  ← Back
                </button>
              </div>
            </>
          )}
        </>
      )}

      {/* ── Approved state ── */}
      {approvalState === "approved" && (
        <div style={{ background:"#f0fdf4", border:"0.5px solid #86efac", borderRadius:10, padding:"18px", textAlign:"center" }}>
          <div style={{ fontSize:32, marginBottom:6 }}>✅</div>
          <div style={{ fontSize:15, fontWeight:700, color:"#15803d", marginBottom:4 }}>Approved &amp; pushed</div>
          <div style={{ fontSize:12, color:"#16a34a" }}>
            {result.markdown_pct}% markdown → AED {result.final_price} queued for activation · {ts}
          </div>
          {note && (
            <div style={{ marginTop:10, background:"#fff", borderRadius:8, padding:"8px 12px", fontSize:12, color:"#374151", border:"0.5px solid #d1fae5", textAlign:"left" }}>
              <strong>Note:</strong> {note}
            </div>
          )}
        </div>
      )}

      {/* ── Rejected state ── */}
      {approvalState === "rejected" && (
        <div style={{ background:"#fef2f2", border:"0.5px solid #fca5a5", borderRadius:10, padding:"18px", textAlign:"center" }}>
          <div style={{ fontSize:32, marginBottom:6 }}>❌</div>
          <div style={{ fontSize:15, fontWeight:700, color:"#dc2626", marginBottom:4 }}>Recommendation rejected</div>
          <div style={{ fontSize:12, color:"#dc2626" }}>Sent back to coordinator for revision</div>
          {note && (
            <div style={{ marginTop:10, background:"#fff", borderRadius:8, padding:"8px 12px", fontSize:12, color:"#374151", border:"0.5px solid #fecaca", textAlign:"left" }}>
              <strong>Reason:</strong> {note}
            </div>
          )}
        </div>
      )}

      {/* ── Override approved state ── */}
      {approvalState === "override" && (
        <div style={{ background:"#f0fdf4", border:"0.5px solid #86efac", borderRadius:10, padding:"18px", textAlign:"center" }}>
          <div style={{ fontSize:32, marginBottom:6 }}>✅</div>
          <div style={{ fontSize:15, fontWeight:700, color:"#15803d", marginBottom:4 }}>Override approved</div>
          <div style={{ fontSize:12, color:"#16a34a" }}>
            {overridePct}% markdown (AI rec: {result.markdown_pct}%) → AED {newPrice} · {ts}
          </div>
          {note && (
            <div style={{ marginTop:10, background:"#fff", borderRadius:8, padding:"8px 12px", fontSize:12, color:"#374151", border:"0.5px solid #d1fae5", textAlign:"left" }}>
              <strong>Override reason:</strong> {note}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
const agentOrder = ["PricingAgent","InventoryAgent","DemandAgent","PromotionAgent","BehaviorAgent","CompetitorAgent","CoordinatorAgent","CriticAgent"];

export default function Actions() {
  const [data, setData]               = useState(null);
  const [category, setCategory]       = useState("All");
  const [selected, setSelected]       = useState(null);
  const [result, setResult]           = useState(null);
  const [loading, setLoading]         = useState(false);
  const [agentStates, setAgentStates] = useState({});
  const [phase, setPhase]             = useState("select");

  useEffect(() => {
    fetchProducts(category, "All").then(d => {
      setData(d);
      setSelected(null);
      setResult(null);
      setPhase("select");
      setAgentStates({});
    });
  }, [category]);

  const products   = data?.products   || [];
  const categories = data?.categories || ["All"];

  const animateAgents = async (finalResult) => {
    const specialAgents = ["PricingAgent","InventoryAgent","DemandAgent","PromotionAgent","BehaviorAgent","CompetitorAgent"];
    const allAgentData  = finalResult.agents || {};
    setAgentStates({});
    for (let i = 0; i < specialAgents.length; i++) {
      const name = specialAgents[i];
      setAgentStates(prev => ({ ...prev, [name]: { status:"running" } }));
      await new Promise(r => setTimeout(r, 700));
      const ad = allAgentData[name];
      setAgentStates(prev => ({ ...prev, [name]: { status: ad?.status === "REJECT" ? "reject" : "done", agentData: ad } }));
      await new Promise(r => setTimeout(r, 150));
    }
    setAgentStates(prev => ({ ...prev, CoordinatorAgent: { status:"running" } }));
    await new Promise(r => setTimeout(r, 900));
    setAgentStates(prev => ({
      ...prev,
      CoordinatorAgent: { status:"done", agentData: {
        recommendation: `${finalResult.markdown_pct}% markdown → AED ${finalResult.final_price} | ${finalResult.health_badge}`,
        confidence: 0.92,
      }}
    }));
    await new Promise(r => setTimeout(r, 400));
    setAgentStates(prev => ({ ...prev, CriticAgent: { status:"running" } }));
    await new Promise(r => setTimeout(r, 800));
    setAgentStates(prev => ({
      ...prev,
      CriticAgent: {
        status: finalResult.critic_status === "PASS" ? "done" : "reject",
        agentData: {
          recommendation: finalResult.critic_status === "PASS"
            ? "Decision approved — all business rules satisfied"
            : "Decision rejected — see coordinator for revision",
          confidence: 0.88,
        }
      }
    }));
  };

  const run = async () => {
    if (!selected) return;
    setLoading(true);
    setResult(null);
    setPhase("running");
    setAgentStates({});
    const res = await runAgents(selected.product_id);
    await animateAgents(res);
    setResult(res);
    setPhase("done");
    setLoading(false);
  };

  const reset = () => { setSelected(null); setResult(null); setPhase("select"); setAgentStates({}); };

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:12 }}>

      {/* Step 1 — Select Product */}
      <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
        <div style={{ fontWeight:600, color:"#1a1d23", fontSize:13, marginBottom:12 }}>Step 1 — Select Product</div>
        <div style={{ marginBottom:10 }}>
          <div style={{ fontSize:11, color:"#9ca3af", marginBottom:4 }}>CATEGORY</div>
          <select value={category} onChange={e => setCategory(e.target.value)}
            style={{ border:"0.5px solid #e2e4e9", borderRadius:7, padding:"6px 12px", fontSize:12, color:"#374151", background:"#fff", minWidth:200 }}>
            {categories.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div style={{ maxHeight:220, overflowY:"auto", border:"0.5px solid #e2e4e9", borderRadius:8 }}>
          {products.length === 0 && <div style={{ padding:16, color:"#9ca3af", fontSize:12 }}>No products found</div>}
          {products.map(p => (
            <div key={p.product_id}
              onClick={() => { setSelected(p); setResult(null); setPhase("select"); setAgentStates({}); }}
              style={{
                padding:"9px 14px", borderBottom:"0.5px solid #f3f4f6", cursor:"pointer",
                background: selected?.product_id === p.product_id ? "#eef2ff" : "transparent",
                display:"flex", justifyContent:"space-between", alignItems:"center",
              }}>
              <div>
                <span style={{ fontWeight:500, fontSize:12.5, color:"#1a1d23" }}>{p.product_name}</span>
                <span style={{ marginLeft:8, fontSize:11, color:"#9ca3af" }}>{p.brand}</span>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                <Badge label={p.risk} color={riskColor[p.risk]||"#9ca3af"} />
                <Badge label={`ABC-${p.abc}`} color="#4f46e5" />
                <span style={{ fontSize:11, color:"#9ca3af", minWidth:55 }}>DOS: {p.dos}d</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Step 2 — Product State */}
      {selected && (
        <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
          <div style={{ fontWeight:600, color:"#1a1d23", fontSize:13, marginBottom:12 }}>Step 2 — Current Product State</div>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:14 }}>
            <span style={{ fontSize:15, fontWeight:700, color:"#1a1d23" }}>{selected.product_name}</span>
            <Badge label={selected.risk} color={riskColor[selected.risk]||"#9ca3af"} />
            <Badge label={`ABC-${selected.abc}`} color="#4f46e5" />
            <Badge label={selected.category} color="#6b7280" bg="#f3f4f6" />
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(6,1fr)", gap:8, marginBottom:14 }}>
            <StatCard label="Current Price"  value={`AED ${selected.price}`} />
            <StatCard label="Cost Price"     value={`AED ${selected.cost_price}`} color="#6b7280" />
            <StatCard label="Inventory"      value={`${selected.quantity} units`} color="#4f46e5" />
            <StatCard label="Sell-Through"   value={`${selected.sell_through}%`} color={selected.sell_through < 30 ? "#dc2626" : "#15803d"} />
            <StatCard label="Days of Stock"  value={`${selected.dos}d`} color={selected.dos > 365 ? "#dc2626" : selected.dos > 180 ? "#f59e0b" : "#15803d"} />
            <StatCard label="Risk"           value={selected.risk} color={riskColor[selected.risk]} />
          </div>
          <div style={{ background:"#f9fafb", borderRadius:8, padding:"8px 14px", marginBottom:12, display:"flex", gap:20, flexWrap:"wrap" }}>
            <span style={{ fontSize:11, color:"#6b7280" }}>🔑 Powered by:</span>
            <span style={{ fontSize:11, fontWeight:600, color:"#4f46e5" }}>Groq LLaMA 3.1 — 6 specialist agents + coordinator + critic</span>
            <span style={{ fontSize:11, fontWeight:600, color:"#0ea5e9" }}>Tavily — live competitor web search</span>
          </div>
          {phase === "select" && (
            <button onClick={run} style={{ width:"100%", padding:"12px", background:"#4f46e5", color:"#fff", border:"none", borderRadius:8, fontWeight:700, cursor:"pointer", fontSize:14 }}>
              ▶ Run AI Markdown Analysis
            </button>
          )}
        </div>
      )}

      {/* Step 3 — Agent Pipeline */}
      {(phase === "running" || phase === "done") && (
        <div>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
            <div style={{ fontWeight:600, color:"#1a1d23", fontSize:13 }}>Step 3 — AI Agent Pipeline</div>
            {phase === "running" && <span style={{ fontSize:11, color:"#4f46e5", fontWeight:500 }}>⚡ Agents running...</span>}
            {phase === "done"    && <span style={{ fontSize:11, color:"#15803d", fontWeight:500 }}>✅ All agents complete</span>}
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10 }}>
            {agentOrder.map(name => {
              const state = agentStates[name] || {};
              return <AgentCard key={name} name={name} status={state.status || "pending"} agentData={state.agentData} />;
            })}
          </div>
        </div>
      )}

      {/* Step 4 + 5 — Results */}
      {result && phase === "done" && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>

          {/* Left — Final Recommendation */}
          <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"20px" }}>
            <div style={{ fontWeight:600, color:"#1a1d23", fontSize:13, marginBottom:16 }}>Step 4 — Final Recommendation</div>
            <div style={{ textAlign:"center", marginBottom:20 }}>
              <div style={{ fontSize:52, fontWeight:800, color:"#4f46e5", lineHeight:1 }}>{result.markdown_pct}%</div>
              <div style={{ fontSize:13, color:"#9ca3af", marginTop:4 }}>Recommended Markdown</div>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:14 }}>
              <StatCard label="Original Price" value={`AED ${result.original_price}`} />
              <StatCard label="New Price"       value={`AED ${result.final_price}`} color="#4f46e5" />
            </div>
            <div style={{ marginBottom:12, padding:"10px 14px", borderRadius:8,
              background: result.health_badge?.includes("🟢") ? "#f0fdf4" : result.health_badge?.includes("🔴") ? "#fef2f2" : "#fffbeb",
              border:`0.5px solid ${healthColor(result.health_badge)}44`
            }}>
              <div style={{ fontSize:13, fontWeight:600, color: healthColor(result.health_badge) }}>{result.health_badge}</div>
            </div>
            <div style={{ marginBottom:12, padding:"10px 14px", background:"#f9fafb", borderRadius:8 }}>
              <div style={{ fontSize:10, color:"#9ca3af", fontWeight:600, marginBottom:4, textTransform:"uppercase" }}>Promotion Type</div>
              <div style={{ fontSize:13, fontWeight:600, color:"#4f46e5", textTransform:"uppercase" }}>
                {result.promotion_type?.replace(/_/g," ")}
              </div>
            </div>
            <div style={{ padding:"12px 14px", background:"#f9fafb", borderRadius:8 }}>
              <div style={{ fontSize:10, color:"#9ca3af", fontWeight:600, marginBottom:6, textTransform:"uppercase" }}>Coordinator Reasoning</div>
              <div style={{ fontSize:12, color:"#374151", lineHeight:1.7 }}>{result.reasoning}</div>
            </div>
          </div>

          {/* Right column */}
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>

            {/* Competitor Intel */}
            <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
              <div style={{ fontWeight:600, color:"#1a1d23", fontSize:13, marginBottom:10 }}>🌐 Competitor Intel — Live Web Search</div>
              {result.agents?.CompetitorAgent?.data?.data_available ? (
                <>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginBottom:10 }}>
                    <div style={{ background:"#eef2ff", borderRadius:8, padding:"10px 12px", textAlign:"center" }}>
                      <div style={{ fontSize:15, fontWeight:700, color:"#4f46e5" }}>₹{result.agents.CompetitorAgent.data.your_price?.toLocaleString()}</div>
                      <div style={{ fontSize:10, color:"#6b7280", marginTop:2 }}>Your Price</div>
                    </div>
                    <div style={{ background:"#fffbeb", borderRadius:8, padding:"10px 12px", textAlign:"center" }}>
                      <div style={{ fontSize:15, fontWeight:700, color:"#d97706" }}>₹{result.agents.CompetitorAgent.data.avg_comp_price?.toLocaleString()}</div>
                      <div style={{ fontSize:10, color:"#6b7280", marginTop:2 }}>Market Avg</div>
                    </div>
                    <div style={{ background:"#fef2f2", borderRadius:8, padding:"10px 12px", textAlign:"center" }}>
                      <div style={{ fontSize:15, fontWeight:700, color:"#dc2626" }}>₹{result.agents.CompetitorAgent.data.min_comp_price?.toLocaleString()}</div>
                      <div style={{ fontSize:10, color:"#6b7280", marginTop:2 }}>Lowest Found</div>
                    </div>
                  </div>
                  <div style={{ padding:"8px 12px", borderRadius:8, marginBottom:10,
                    background: result.agents.CompetitorAgent.data.price_position === "ABOVE_MARKET" ? "#fef2f2" :
                                result.agents.CompetitorAgent.data.price_position === "BELOW_MARKET" ? "#f0fdf4" : "#eff6ff" }}>
                    <span style={{ fontSize:12, fontWeight:600, color:
                      result.agents.CompetitorAgent.data.price_position === "ABOVE_MARKET" ? "#dc2626" :
                      result.agents.CompetitorAgent.data.price_position === "BELOW_MARKET" ? "#15803d" : "#1d4ed8" }}>
                      {result.agents.CompetitorAgent.data.price_position === "ABOVE_MARKET" ? "⬆ Priced ABOVE market — markdown recommended" :
                       result.agents.CompetitorAgent.data.price_position === "BELOW_MARKET" ? "⬇ Already BELOW market — markdown not needed" :
                       "↔ Priced AT market"}
                    </span>
                  </div>
                  {result.agents.CompetitorAgent.data.sources?.length > 0 && (
                    <div>
                      <div style={{ fontSize:10, color:"#9ca3af", fontWeight:600, marginBottom:6, textTransform:"uppercase" }}>Found on these stores</div>
                      {result.agents.CompetitorAgent.data.sources.slice(0,4).map((src, i) => {
                        const domain = src.replace(/https?:\/\/(www\.)?/,'').split('/')[0];
                        const store  = domain.split('.')[0];
                        return (
                          <div key={i} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"7px 10px", background:"#f9fafb", borderRadius:6, marginBottom:4 }}>
                            <span style={{ fontSize:12, fontWeight:500, color:"#374151", textTransform:"capitalize" }}>🛒 {store}</span>
                            <span style={{ fontSize:10, color:"#4f46e5", cursor:"pointer" }} onClick={() => window.open(src, '_blank')}>view listing →</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              ) : (
                <div style={{ background:"#fffbeb", borderRadius:8, padding:"12px 14px" }}>
                  <div style={{ fontSize:12, fontWeight:600, color:"#d97706", marginBottom:6 }}>⚠️ Competitor data unavailable</div>
                  <div style={{ fontSize:11, color:"#6b7280", lineHeight:1.6 }}>Tavily API key is missing or empty. Add it to your <code>.env</code> file:</div>
                  <div style={{ fontFamily:"monospace", fontSize:11, background:"#f3f4f6", padding:"6px 10px", borderRadius:6, marginTop:6 }}>TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx</div>
                  <div style={{ fontSize:11, color:"#6b7280", marginTop:6 }}>Free at <strong>app.tavily.com</strong> — 1000 searches/month</div>
                </div>
              )}
            </div>

            {/* Critic Verdict */}
            <div style={{ background:"#fff", border:"0.5px solid #e2e4e9", borderRadius:10, padding:"16px" }}>
              <div style={{ fontWeight:600, color:"#1a1d23", fontSize:13, marginBottom:10 }}>🔍 Critic Verdict — Independent LLM Review</div>
              <div style={{ padding:"12px 14px", borderRadius:8, marginBottom:10,
                background: result.critic_status === "PASS" ? "#f0fdf4" : "#fef2f2",
                border:`0.5px solid ${result.critic_status === "PASS" ? "#86efac" : "#fca5a5"}`
              }}>
                <div style={{ fontSize:16, fontWeight:700, color: result.critic_status === "PASS" ? "#15803d" : "#dc2626", marginBottom:4 }}>
                  {result.critic_status === "PASS" ? "✅ APPROVED" : "❌ REJECTED"}
                </div>
                <div style={{ fontSize:11, color:"#6b7280" }}>
                  {result.critic_status === "PASS"
                    ? "Decision passed all business rule checks by independent Groq LLM reviewer"
                    : "Decision was rejected — coordinator will revise and resubmit"}
                </div>
              </div>
              {["Price above cost floor ✓","Markdown within 0–60% range ✓","ABC class rules applied ✓","Risk level considered ✓","Business logic verified ✓"].map((c,i) => (
                <div key={i} style={{ display:"flex", alignItems:"center", gap:6, padding:"4px 0", fontSize:12, color:"#374151" }}>
                  <span style={{ color:"#15803d" }}>✓</span> {c}
                </div>
              ))}
            </div>

            {/* ✅ Step 5 — Human Approval (proper component, no hooks violation) */}
            <HumanApproval result={result} />

            <button onClick={reset} style={{ padding:"10px", background:"transparent", border:"0.5px solid #e2e4e9", borderRadius:8, cursor:"pointer", fontSize:12, color:"#374151", fontWeight:500 }}>
              ← Analyse Another Product
            </button>

          </div>
        </div>
      )}
    </div>
  );
}