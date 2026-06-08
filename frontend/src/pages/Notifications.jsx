
import { useEffect, useState } from "react";

const BASE = "https://markdownusingllm-production.up.railway.app";

const SEV = {
  HIGH:   { bg:"#fee2e2", color:"#dc2626", dot:"#dc2626", label:"🚨 HIGH" },
  MEDIUM: { bg:"#fff7ed", color:"#c2410c", dot:"#f59e0b", label:"⚠️ MEDIUM" },
  LOW:    { bg:"#f0fdf4", color:"#15803d", dot:"#10b981", label:"ℹ️ LOW" },
};

const TYPE_ICONS = {
  RED_HEALTH:               "🔴",
  HIGH_RISK_APPROVED:       "✅",
  MAX_RETRIES:              "🔄",
  ABC_A_DEEP_DISCOUNT:      "⚠️",
  DEAD_INVENTORY_CLEARANCE: "🗑️",
};

export default function Notifications() {
  const [data,       setData]       = useState(null);
  const [filter,     setFilter]     = useState("All");
  const [testing,    setTesting]    = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [loading,    setLoading]    = useState(true);

  const load = () => {
    setLoading(true);
    fetch(`${BASE}/api/notifications`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const sendTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${BASE}/api/test-notify`, { method: "POST" });
      const d   = await res.json();
      setTestResult(d);
      load();
    } catch(e) {
      setTestResult({ error: e.message });
    }
    setTesting(false);
  };

  const notifications = data?.notifications || [];
  const filtered = filter === "All"
    ? notifications
    : notifications.filter(n => n.severity === filter);

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:12 }}>

      {/* Header */}
      <div style={{
        background:"#fff", border:"0.5px solid #e2e4e9",
        borderRadius:10, padding:16,
        display:"flex", justifyContent:"space-between", alignItems:"center"
      }}>
        <div>
          <div style={{ fontSize:15, fontWeight:700, color:"#1a1d23" }}>
            🔔 Notification Center
          </div>
          <div style={{ fontSize:11, color:"#9ca3af", marginTop:2 }}>
            AI agent alert log · auto-generated on every pipeline run
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <button onClick={load} style={{
            padding:"7px 14px", background:"#f9fafb",
            border:"0.5px solid #e2e4e9", borderRadius:7,
            fontSize:12, cursor:"pointer", color:"#374151"
          }}>🔄 Refresh</button>
          <button onClick={sendTest} disabled={testing} style={{
            padding:"7px 14px", background:"#4f46e5", color:"#fff",
            border:"none", borderRadius:7, fontSize:12,
            cursor:"pointer", fontWeight:600,
            opacity: testing ? 0.6 : 1
          }}>
            {testing ? "Sending..." : "🧪 Send Test Alert"}
          </button>
        </div>
      </div>

      {/* Test result banner */}
      {testResult && (
        <div style={{
          background: testResult.error ? "#fef2f2" : "#f0fdf4",
          border:`0.5px solid ${testResult.error ? "#fca5a5" : "#86efac"}`,
          borderRadius:8, padding:"10px 14px", fontSize:12,
          color: testResult.error ? "#dc2626" : "#15803d"
        }}>
          {testResult.error
            ? `❌ Test failed: ${testResult.error}`
            : `✅ Test sent — ${testResult.alerts} alerts fired`
          }
        </div>
      )}

      {/* KPI cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10 }}>
        {[
          { label:"Total Alerts", value:data?.total  || 0, color:"#4f46e5" },
          { label:"🚨 HIGH",      value:data?.high   || 0, color:"#dc2626" },
          { label:"⚠️ MEDIUM",    value:data?.medium || 0, color:"#f59e0b" },
          { label:"ℹ️ LOW",       value:data?.low    || 0, color:"#10b981" },
        ].map((k,i) => (
          <div key={i} style={{
            background:"#fff", border:"0.5px solid #e2e4e9",
            borderRadius:10, padding:"13px 15px"
          }}>
            <div style={{ fontSize:11, color:"#9ca3af", fontWeight:500, marginBottom:6 }}>
              {k.label}
            </div>
            <div style={{ fontSize:28, fontWeight:700, color:k.color }}>
              {k.value}
            </div>
          </div>
        ))}
      </div>

      {/* Channel status */}
      <div style={{
        background:"#fff", border:"0.5px solid #e2e4e9",
        borderRadius:10, padding:16
      }}>
        <div style={{ fontSize:13, fontWeight:600, color:"#1a1d23", marginBottom:12 }}>
          📡 Notification Channels
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 }}>
          {[
            {
              icon:"📋", label:"File Log",
              sub:"data/notification_log.jsonl",
              status:"active",
              note:"Always on — logs every alert automatically"
            },
            {
              icon:"💬", label:"Slack",
              sub:"SLACK_WEBHOOK_URL",
              status:"active",
              note:"Add webhook URL to .env to enable"
            },
            {
              icon:"📧", label:"AWS SNS",
              sub:"SNS_TOPIC_ARN",
              status:"active",
              note:"Add SNS ARN to .env to enable email"
            },
          ].map((c,i) => (
            <div key={i} style={{
              background:"#f9fafb", borderRadius:8,
              padding:"12px 14px", border:"0.5px solid #e2e4e9"
            }}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:6 }}>
                <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                  <span style={{ fontSize:18 }}>{c.icon}</span>
                  <span style={{ fontSize:13, fontWeight:600, color:"#1a1d23" }}>{c.label}</span>
                </div>
                <span style={{
                  fontSize:10, fontWeight:700, padding:"2px 8px", borderRadius:8,
                  background: c.status==="active" ? "#dcfce7" : "#f3f4f6",
                  color:      c.status==="active" ? "#15803d" : "#9ca3af",
                }}>
                  {c.status==="active" ? "● ACTIVE" : "○ OFF"}
                </span>
              </div>
              <div style={{ fontSize:10, color:"#9ca3af", fontFamily:"monospace", marginBottom:4 }}>
                {c.sub}
              </div>
              <div style={{ fontSize:11, color:"#6b7280" }}>{c.note}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Alert feed */}
      <div style={{
        background:"#fff", border:"0.5px solid #e2e4e9",
        borderRadius:10, overflow:"hidden"
      }}>
        {/* Filter bar */}
        <div style={{
          padding:"11px 16px", borderBottom:"0.5px solid #e2e4e9",
          display:"flex", alignItems:"center", justifyContent:"space-between"
        }}>
          <div style={{ fontSize:13, fontWeight:600, color:"#1a1d23" }}>
            Alert Feed
            <span style={{ fontSize:11, color:"#9ca3af", marginLeft:8, fontWeight:400 }}>
              {filtered.length} alerts
            </span>
          </div>
          <div style={{ display:"flex", gap:6 }}>
            {["All","HIGH","MEDIUM","LOW"].map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                padding:"4px 12px", borderRadius:6, fontSize:11,
                fontWeight:500, cursor:"pointer", border:"none",
                background: filter===f ? "#4f46e5" : "#f3f4f6",
                color:      filter===f ? "#fff"    : "#6b7280",
              }}>{f}</button>
            ))}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div style={{ padding:32, textAlign:"center", color:"#9ca3af", fontSize:13 }}>
            Loading alerts...
          </div>
        )}

        {/* Empty state */}
        {!loading && filtered.length === 0 && (
          <div style={{ padding:32, textAlign:"center" }}>
            <div style={{ fontSize:32, marginBottom:8 }}>🔕</div>
            <div style={{ fontSize:13, fontWeight:600, color:"#374151", marginBottom:4 }}>
              No alerts yet
            </div>
            <div style={{ fontSize:11, color:"#9ca3af" }}>
              Run the AI pipeline on a product in Actions tab to generate alerts
            </div>
          </div>
        )}

        {/* Alert rows */}
        {!loading && filtered.map((n, i) => {
          const s    = SEV[n.severity] || SEV.LOW;
          const icon = TYPE_ICONS[n.type] || "📢";
          const time = n.timestamp
            ? new Date(n.timestamp).toLocaleString("en-IN", {
                day:"numeric", month:"short",
                hour:"2-digit", minute:"2-digit"
              })
            : "";

          return (
            <div key={i} style={{
              padding:"12px 16px",
              borderBottom:"0.5px solid #f3f4f6",
              display:"flex", gap:12, alignItems:"flex-start",
              transition:"background 0.1s",
            }}
            onMouseEnter={e => e.currentTarget.style.background="#fafbff"}
            onMouseLeave={e => e.currentTarget.style.background=""}
            >
              {/* Severity dot */}
              <div style={{
                width:8, height:8, borderRadius:"50%",
                background:s.dot, marginTop:6, flexShrink:0
              }}/>

              <div style={{ flex:1 }}>
                {/* Top row */}
                <div style={{
                  display:"flex", justifyContent:"space-between",
                  alignItems:"flex-start", marginBottom:4
                }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                    <span style={{ fontSize:15 }}>{icon}</span>
                    <span style={{ fontSize:12, fontWeight:600, color:"#1a1d23" }}>
                      {n.type?.replace(/_/g," ")}
                    </span>
                    <span style={{
                      fontSize:9, fontWeight:700, padding:"2px 7px",
                      borderRadius:8, background:s.bg, color:s.color
                    }}>{s.label}</span>
                  </div>
                  <span style={{ fontSize:10, color:"#9ca3af", whiteSpace:"nowrap" }}>
                    {time}
                  </span>
                </div>

                {/* Message */}
                <div style={{ fontSize:12, color:"#374151", lineHeight:1.6, marginBottom:6 }}>
                  {n.message}
                </div>

                {/* Meta row */}
                <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
                  {n.product_name && (
                    <span style={{
                      fontSize:10, color:"#6b7280",
                      background:"#f3f4f6", padding:"2px 8px", borderRadius:6
                    }}>
                      📦 {n.product_name}
                    </span>
                  )}
                  {n.markdown_pct > 0 && (
                    <span style={{
                      fontSize:10, color:"#4f46e5", fontWeight:600,
                      background:"#eef2ff", padding:"2px 8px", borderRadius:6
                    }}>
                      {n.markdown_pct}% markdown
                    </span>
                  )}
                  {n.verdict && (
                    <span style={{
                      fontSize:10, fontWeight:600,
                      color: n.verdict==="PASS" ? "#15803d" : "#dc2626",
                      background: n.verdict==="PASS" ? "#f0fdf4" : "#fef2f2",
                      padding:"2px 8px", borderRadius:6
                    }}>
                      Critic: {n.verdict}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Setup guide
      <div style={{
        background:"#fffbeb", border:"0.5px solid #fde68a",
        borderRadius:10, padding:16
      }}>
        <div style={{ fontSize:13, fontWeight:600, color:"#92400e", marginBottom:8 }}>
          🔧 Enable real Slack + Email notifications
        </div>
        <div style={{
          fontFamily:"monospace", fontSize:11, background:"#fff",
          border:"0.5px solid #fde68a", borderRadius:6,
          padding:"10px 14px", lineHeight:2.2, color:"#374151"
        }}>
          <span style={{ color:"#9ca3af" }}># Add to Markdown_using_LLM/.env</span><br/>
          <span style={{ color:"#15803d" }}>SLACK_WEBHOOK_URL</span>=https://hooks.slack.com/services/YOUR/WEBHOOK<br/>
          <span style={{ color:"#15803d" }}>SNS_TOPIC_ARN</span>=arn:aws:sns:ap-south-1:123456789:retailai-alerts
        </div>
        <div style={{ fontSize:11, color:"#92400e", marginTop:8, lineHeight:1.8 }}>
          <strong>Slack (free):</strong> api.slack.com → Your Apps → Create App → Incoming Webhooks<br/>
          <strong>SNS (AWS):</strong> AWS Console → SNS → Topics → Create → Add email subscription
        </div>
      </div> */}

    </div>
  );
}
