import { useEffect, useState } from "react";
import { fetchHistory } from "../api/client";

export default function History() {
  const [data, setData] = useState(null);
  useEffect(() => { fetchHistory().then(setData); }, []);

  const items = data?.history || [];

  return (
    <div style={{ background: "#fff", border: "0.5px solid #e2e4e9", borderRadius: 10, overflow: "hidden" }}>
      <div style={{ padding: "12px 16px", borderBottom: "0.5px solid #e2e4e9", fontWeight: 600, color: "#1a1d23" }}>
        Markdown History
      </div>
      {items.length === 0 && <div style={{ padding: 20, color: "#9ca3af", fontSize: 12 }}>No markdowns run yet. Go to Actions to analyse a product.</div>}
      {items.map((item, i) => (
        <div key={i} style={{ padding: "14px 16px", borderBottom: "0.5px solid #f3f4f6" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontWeight: 600, fontSize: 13, color: "#1a1d23" }}>{item.data?.product_name || item.summary}</span>
            <span style={{ fontSize: 11, color: "#9ca3af" }}>{new Date(item.timestamp).toLocaleString()}</span>
          </div>
          {item.data && (
            <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#6b7280" }}>
              <span>Markdown: <strong style={{ color: "#4f46e5" }}>{item.data.markdown_pct}%</strong></span>
              <span>Price: AED {item.data.original_price} → <strong>AED {item.data.final_price}</strong></span>
              <span>{item.data.health_badge}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}