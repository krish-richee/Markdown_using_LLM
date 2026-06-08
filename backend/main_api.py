# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import pandas as pd
# import json, os
# from datetime import datetime
# from utils.data_loader import (
#     compute_sales_metrics,
#     load_store_performance,
#     load_store_monthly_trends,
#     load_orders,
#     load_order_items,
#     compute_elasticity_data,
# )
# from agents.pricing_agent    import PricingAgent
# from agents.inventory_agent  import InventoryAgent
# from agents.demand_agent     import DemandAgent
# from agents.promotion_agent  import PromotionAgent
# from agents.behavior_agent   import BehaviorAgent
# from agents.competitor_agent import CompetitorAgent
# from agents.coordinator      import CoordinatorAgent
# from agents.critic_agent     import CriticAgent
# from agents.base_agent       import AgentStatus
# from config.settings         import MAX_CRITIC_RETRIES

# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# 
def _recompute_risk(df):
    import numpy as np
    df = df.copy()
    df["clearance_risk"] = np.where(
        (df["days_of_stock"] > 365) & (df["sell_through_rate"] < 20), "CRITICAL",
        np.where(
            (df["days_of_stock"] > 180) & (df["sell_through_rate"] < 40), "HIGH",
            np.where(
                (df["days_of_stock"] > 90) & (df["sell_through_rate"] < 60), "MEDIUM",
                "LOW"
            )
        )
    )
    return df

ACTIONS_LOG = "data/actions_log.jsonl"

# def _load_actions():
#     if not os.path.exists(ACTIONS_LOG):
#         return []
#     with open(ACTIONS_LOG) as f:
#         return [json.loads(l) for l in f if l.strip()]

# def _save_action(action: dict):
#     os.makedirs("data", exist_ok=True)
#     with open(ACTIONS_LOG, "a") as f:
#         f.write(json.dumps(action) + "\n")

# def _run_agent(agent, product):
#     if hasattr(agent, "analyze"):
#         return agent.analyze(product)
#     elif hasattr(agent, "run"):
#         return agent.run(product)
#     return None

# def _recompute_risk(df):
#     import numpy as np
#     df = df.copy()
#     df["clearance_risk"] = np.where(
#         (df["days_of_stock"] > 365) & (df["sell_through_rate"] < 20), "CRITICAL",
#         np.where(
#             (df["days_of_stock"] > 180) & (df["sell_through_rate"] < 40), "HIGH",
#             np.where(
#                 (df["days_of_stock"] > 90) & (df["sell_through_rate"] < 60), "MEDIUM",
#                 "LOW"
#             )
#         )
#     )
#     return df

# @app.get("/api/dashboard")
# def get_dashboard(from_date: str = None, to_date: str = None):
#     metrics     = compute_sales_metrics()
#     stores      = load_store_performance()
#     orders      = load_orders()
#     order_items = load_order_items()

#     _date_col = next((c for c in orders.columns if c in ("order_date", "created_at", "date")), None)
#     if _date_col and (from_date or to_date):
#         orders = orders.copy()
#         orders["_dt"] = pd.to_datetime(orders[_date_col], errors="coerce")
#         if from_date:
#             orders = orders[orders["_dt"] >= pd.Timestamp(from_date)]
#         if to_date:
#             orders = orders[orders["_dt"] <= pd.Timestamp(to_date) + pd.Timedelta(days=1)]

#     completed = orders[orders["state"] == "complete"] if "state" in orders.columns else orders

#     total_skus    = len(metrics)
#     total_revenue = float(completed["net_revenue"].sum()) if "net_revenue" in completed.columns else 0
#     total_orders  = int(len(completed))
#     high_risk     = metrics[metrics["clearance_risk"] == "HIGH"]
#     dead          = metrics[metrics["is_dead_inventory"] == True]
#     avg_st        = round(float(metrics["sell_through_rate"].mean()), 1)
#     total_stock   = int(metrics["quantity"].sum())
#     abc_counts    = metrics["abc_class"].value_counts().to_dict()

#     brand_rev = metrics.groupby("brand")["total_revenue"].sum().sort_values(ascending=False).head(10)
#     brand_revenue = [{"brand": str(k), "revenue": round(float(v), 0)} for k, v in brand_rev.items()]

#     cat_rev = metrics.groupby("main_category")["total_revenue"].sum().sort_values(ascending=False).head(8)
#     cat_revenue = [{"category": k, "revenue": round(float(v), 0)} for k, v in cat_rev.items()]

#     cat_st = metrics.groupby("main_category")["sell_through_rate"].mean().sort_values(ascending=False)
#     cat_sellthrough = [{"category": k, "sell_through": round(float(v), 1)} for k, v in cat_st.items()]

#     cat_stock = metrics.groupby("main_category").agg(
#         stock=("quantity", "sum"),
#         sold=("total_qty_sold", "sum")
#     ).reset_index()
#     stock_vs_sold = [
#         {"category": row["main_category"], "stock": int(row["stock"]), "sold": int(row["sold"])}
#         for _, row in cat_stock.iterrows()
#     ]

#     risk_counts = metrics["clearance_risk"].value_counts().to_dict()

#     revenue_trend = []
#     if _date_col and "net_revenue" in orders.columns:
#         _trend = orders.copy()
#         _trend["_dt"] = pd.to_datetime(_trend[_date_col], errors="coerce")
#         _trend["month"] = _trend["_dt"].dt.strftime("%b %y")
#         _trend = _trend.dropna(subset=["_dt", "month"])
#         _grp_cols = {"revenue": ("net_revenue", "sum"), "_dt": ("_dt", "first")}
#         if "order_id" in _trend.columns:
#             _grp_cols["orders"] = ("order_id", "count")
#         _monthly = _trend.groupby("month").agg(**_grp_cols).reset_index()
#         _monthly = _monthly.sort_values("_dt")
#         revenue_trend = [
#             {
#                 "month":   r["month"],
#                 "revenue": round(float(r["revenue"]), 0),
#                 "orders":  int(r["orders"]) if "orders" in r else 0,
#             }
#             for _, r in _monthly.iterrows()
#         ]

#     store_list = []
#     if not stores.empty:
#         for _, row in stores.head(6).iterrows():
#             st_val = float(row["sell_through_rate"] if "sell_through_rate" in row.index else 0)
#             name   = (row["store_name"] if "store_name" in row.index
#                       else row["store_id"] if "store_id" in row.index else "Store")
#             active = int(row["active_skus"] if "active_skus" in row.index
#                          else row["active_markdowns"] if "active_markdowns" in row.index else 0)
#             depth  = float(row["avg_discount_depth"] if "avg_discount_depth" in row.index else 0)
#             store_list.append({
#                 "name":         str(name),
#                 "sell_through": round(st_val, 1),
#                 "active":       active,
#                 "depth":        round(depth, 1),
#                 "tier":         "HOT" if st_val >= 75 else ("COLD" if st_val < 65 else "AVG"),
#             })

#     top_cat      = cat_rev.idxmax() if not cat_rev.empty else "N/A"
#     worst_st_cat = cat_st.idxmin()  if not cat_st.empty else "N/A"
#     dead_pct     = round(len(dead) / total_skus * 100, 1) if total_skus else 0
#     high_pct     = round(len(high_risk) / total_skus * 100, 1) if total_skus else 0

#     insights = [
#         {"icon":"💰","title":"Top Revenue Category",
#          "text":f"{top_cat} drives the highest revenue. Focus markdown strategy here to recover margin without hurting top-line."},
#         {"icon":"⚠️","title":"High Risk Exposure",
#          "text":f"{len(high_risk):,} SKUs ({high_pct}%) are HIGH clearance risk. Immediate markdown action can recover working capital."},
#         {"icon":"💀","title":"Dead Inventory Alert",
#          "text":f"{len(dead):,} SKUs ({dead_pct}%) have DOS >180 days. These are tying up capital and need aggressive clearance pricing."},
#         {"icon":"📉","title":"Lowest Sell-Through",
#          "text":f"{worst_st_cat} has the lowest avg sell-through ({round(float(cat_st.min()),1)}%). Bundle or flash-sale strategy recommended."},
#         {"icon":"🏪","title":"Store Insight",
#          "text":f"{store_list[0]['name'] if store_list else 'Top store'} leads with {store_list[0]['sell_through'] if store_list else 0}% sell-through. Replicate its markdown timing across other stores."},
#         {"icon":"📦","title":"Stock Health",
#          "text":f"Total stock of {total_stock:,} units across {total_skus:,} SKUs. ABC-C holds {abc_counts.get('C',0):,} SKUs — prime clearance candidates."},
#     ]

#     return {
#         "kpis": {
#             "total_revenue":    total_revenue,
#             "total_orders":     total_orders,
#             "total_skus":       total_skus,
#             "total_stock":      total_stock,
#             "high_risk_count":  len(high_risk),
#             "dead_inventory":   len(dead),
#             "avg_sell_through": avg_st,
#             "abc_a":            abc_counts.get("A", 0),
#             "abc_b":            abc_counts.get("B", 0),
#             "abc_c":            abc_counts.get("C", 0),
#         },
#         "brand_revenue":     brand_revenue,
#         "cat_revenue":       cat_revenue,
#         "cat_sellthrough":   cat_sellthrough,
#         "stock_vs_sold":     stock_vs_sold,
#         "risk_breakdown":    risk_counts,
#         "store_performance": store_list,
#         "revenue_trend":     revenue_trend,
#         "insights":          insights,
#     }

# @app.get("/api/products")
# def get_products(category: str = "All", risk: str = "All", limit: int = 500):
#     metrics = compute_sales_metrics()
#     metrics = _recompute_risk(metrics)
#     df = metrics.copy()
#     if category != "All":
#         df = df[df["main_category"] == category]
#     if risk != "All":
#         df = df[df["clearance_risk"] == risk]
#     risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
#     df["_risk_rank"] = df["clearance_risk"].map(risk_order).fillna(4)
#     df = df.sort_values(["_risk_rank", "days_of_stock"], ascending=[True, False]).head(limit)
#     categories = ["All"] + sorted(metrics["main_category"].dropna().unique().tolist())
#     products = []
#     for _, row in df.iterrows():
#         dos = int(row.get("days_of_stock", 0))
#         dos = dos if dos < 99999 else 9999
#         products.append({
#             "product_id":   str(row["product_id"]),
#             "product_name": str(row.get("product_name", "")),
#             "category":     str(row.get("main_category", "")),
#             "brand":        str(row.get("brand", "")),
#             "price":        float(row.get("price", 0)),
#             "cost_price":   float(row.get("cost_price", 0)),
#             "quantity":     int(row.get("quantity", 0)),
#             "sell_through": float(row.get("sell_through_rate", 0)),
#             "dos":          dos,
#             "risk":         str(row.get("clearance_risk", "")),
#             "abc":          str(row.get("abc_class", "")),
#         })
#     return {"products": products, "categories": categories}

# class RunRequest(BaseModel):
#     product_id: str

# @app.post("/api/run")
# def run_agents(req: RunRequest):
#     metrics       = compute_sales_metrics()
#     elasticity_df = compute_elasticity_data()
#     row = metrics[metrics["product_id"] == req.product_id]
#     if row.empty:
#         raise HTTPException(status_code=404, detail="Product not found")
#     product   = row.iloc[0].to_dict()
#     elast_row = elasticity_df[elasticity_df["product_id"] == req.product_id]
#     product["elasticity"] = float(elast_row["elasticity"].iloc[0]) if not elast_row.empty else -1.2
#     for k, v in product.items():
#         if hasattr(v, 'item'):
#             product[k] = v.item()
#     agents = [
#         PricingAgent(), InventoryAgent(), DemandAgent(),
#         PromotionAgent(), BehaviorAgent(), CompetitorAgent(),
#     ]
#     agent_outputs = {}
#     for agent in agents:
#         try:
#             out = _run_agent(agent, product)
#             if out:
#                 agent_outputs[out.agent_name] = out
#         except Exception as e:
#             print(f"Agent {agent.name} error: {e}")
#     coordinator = CoordinatorAgent()
#     critic      = CriticAgent()
#     decision = coordinator.synthesise(product, agent_outputs)
#     for attempt in range(MAX_CRITIC_RETRIES):
#         verdict = critic.review(product, decision)
#         decision.critic_verdict = verdict
#         if verdict.status == AgentStatus.PASS:
#             break
#         decision = coordinator.synthesise(product, agent_outputs, attempt + 1, verdict.reason)
#     result = {
#         "product_id":     str(decision.product_id),
#         "product_name":   str(decision.product_name),
#         "markdown_pct":   float(decision.recommended_markdown_pct),
#         "final_price":    float(decision.final_price),
#         "original_price": float(product.get("price", 0)),
#         "health_badge":   str(decision.health_badge),
#         "promotion_type": str(decision.promotion_type),
#         "reasoning":      str(decision.coordinator_reasoning),
#         "critic_status":  str(decision.critic_verdict.status.value),
#         "timestamp":      datetime.now().isoformat(),
#         "agents": {
#             name: {
#                 "recommendation": str(o.recommendation),
#                 "confidence":     float(o.confidence),
#                 "reasoning":      str(o.reasoning),
#                 "status":         str(o.status.value),
#                 "data":           o.data if isinstance(o.data, dict) else {},
#             }
#             for name, o in agent_outputs.items()
#         },
#     }
#     _save_action({
#         "type":      "EXEC",
#         "summary":   f"{decision.product_name} — {decision.recommended_markdown_pct}% markdown recommended",
#         "timestamp": result["timestamp"],
#         "data":      result,
#     })
#     return result

# @app.get("/api/history")
# def get_history():
#     return {"history": _load_actions()[::-1]}

# @app.get("/api/planner")
# def get_planner():
#     import math
#     metrics    = compute_sales_metrics()
#     candidates = metrics[metrics["clearance_risk"].isin(["HIGH", "CRITICAL"])].copy()
#     candidates = candidates.sort_values("days_of_stock", ascending=False)

#     total_candidates = len(candidates)
#     capital_at_risk  = float(
#         (candidates["quantity"].fillna(0) * candidates["price"].fillna(0)).sum()
#     )

#     _finite_dos = candidates[candidates["days_of_stock"] < 99999]["days_of_stock"]
#     if len(_finite_dos) == 0:
#         avg_dos = 9999
#     else:
#         _mean = _finite_dos.mean()
#         avg_dos = 9999 if (math.isnan(_mean) or _mean >= 9999) else int(_mean)

#     ladders = []
#     for _, row in candidates.head(100).iterrows():
#         price = float(row.get("price", 0))
#         cost  = float(row.get("cost_price", 0))
#         qty   = int(row.get("quantity", 0))
#         st    = float(row.get("sell_through_rate", 0))
#         risk  = str(row.get("clearance_risk", "HIGH"))

#         dos_raw = row.get("days_of_stock", 0)
#         try:
#             dos_raw = float(dos_raw)
#         except:
#             dos_raw = 99999
#         if math.isnan(dos_raw) or math.isinf(dos_raw):
#             dos = -1
#         else:
#             dos = int(min(dos_raw, 99999))

#         if dos >= 99999 and st > 0:
#             sold_est = qty * (st / 100) / max(1 - st / 100, 0.001)
#             if sold_est > 0:
#                 daily_rate = sold_est / 365
#                 estimated  = int(qty / daily_rate)
#                 dos = estimated if estimated < 99999 else -1

#         if dos == -1 or dos >= 9999 or risk == "CRITICAL":
#             steps = [
#                 {"pct":20,"label":"2wk · time"},
#                 {"pct":35,"label":"2wk · velocity"},
#                 {"pct":50,"label":"2wk · time"},
#                 {"pct":65,"label":"Final · clearance"},
#             ]
#         elif dos > 180:
#             steps = [
#                 {"pct":15,"label":"2wk · time"},
#                 {"pct":30,"label":"2wk · velocity"},
#                 {"pct":50,"label":"2wk · time"},
#             ]
#         else:
#             steps = [
#                 {"pct":10,"label":"2wk · time"},
#                 {"pct":20,"label":"2wk · velocity"},
#                 {"pct":35,"label":"2wk · time"},
#             ]

#         margin_pct = round((price - cost) / price * 100, 1) if price > 0 else 0
#         curr_price = round(price * (1 - steps[0]["pct"] / 100), 2)

#         ladders.append({
#             "product_id":   str(row["product_id"]),
#             "product_name": str(row.get("product_name", "")),
#             "category":     str(row.get("main_category", "")),
#             "brand":        str(row.get("brand", "")),
#             "risk":         risk,
#             "abc":          str(row.get("abc_class", "")),
#             "price":        price,
#             "cost_price":   cost,
#             "curr_price":   curr_price,
#             "was_price":    price,
#             "qty":          qty,
#             "dos":          dos,
#             "sell_through": round(st, 1),
#             "margin_pct":   margin_pct,
#             "steps":        steps,
#             "current_step": 0,
#             "total_steps":  len(steps),
#         })

#     return {
#         "summary": {
#             "total_candidates": total_candidates,
#             "capital_at_risk":  round(capital_at_risk, 0),
#             "avg_dos":          avg_dos,
#         },
#         "ladders": ladders,
#     }
    
    
    
# # ── Notifications ──────────────────────────────────────────────────────────
# NOTIF_FILE = "data/notification_log.jsonl"

# @app.get("/api/notifications")
# def get_notifications():
#     if not os.path.exists(NOTIF_FILE):
#         return {"notifications": [], "total": 0, "high": 0, "medium": 0, "low": 0}
#     rows = []
#     with open(NOTIF_FILE) as f:
#         for line in f:
#             line = line.strip()
#             if line:
#                 try:
#                     rows.append(json.loads(line))
#                 except:
#                     pass
#     rows = list(reversed(rows))
#     all_alerts = []
#     for r in rows:
#         for a in r.get("alerts", []):
#             all_alerts.append({
#                 "timestamp":    r.get("timestamp", ""),
#                 "product_id":   r.get("product_id", ""),
#                 "product_name": r.get("product_name", ""),
#                 "markdown_pct": r.get("markdown_pct", 0),
#                 "health":       r.get("health", ""),
#                 "verdict":      r.get("verdict", ""),
#                 "type":         a.get("type", ""),
#                 "severity":     a.get("severity", ""),
#                 "message":      a.get("message", ""),
#             })
#     return {
#         "notifications": all_alerts,
#         "total":  len(all_alerts),
#         "high":   len([a for a in all_alerts if a["severity"] == "HIGH"]),
#         "medium": len([a for a in all_alerts if a["severity"] == "MEDIUM"]),
#         "low":    len([a for a in all_alerts if a["severity"] == "LOW"]),
#     }

# @app.post("/api/test-notify")
# def test_notification():
#     from agents.notification_agent import NotificationAgent
#     from agents.base_agent import CriticVerdict, FinalDecision
#     test_product = {
#         "product_id":      "TEST_001",
#         "product_name":    "Test Product",
#         "clearance_risk":  "HIGH",
#         "abc_class":       "C",
#         "is_dead_inventory": True,
#         "days_of_stock":   200,
#         "price":           999,
#     }
#     test_decision = FinalDecision(
#         product_id="TEST_001",
#         product_name="Test Product",
#         recommended_markdown_pct=30,
#         final_price=699,
#         health_badge="🟡 Caution",
#         coordinator_reasoning="Test notification",
#         critic_verdict=CriticVerdict(
#             status=AgentStatus.PASS,
#             reason="Test",
#             retry_count=0,
#         ),
#     )
#     result = NotificationAgent().notify(test_product, test_decision)
#     return {"status": "sent", "alerts": result["alerts_sent"]}


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import json, os
from datetime import datetime
from utils.data_loader import (
    compute_sales_metrics,
    load_store_performance,
    load_store_monthly_trends,
    load_order_items,
    compute_elasticity_data,
)
from agents.pricing_agent    import PricingAgent
from agents.inventory_agent  import InventoryAgent
from agents.demand_agent     import DemandAgent
from agents.promotion_agent  import PromotionAgent
from agents.behavior_agent   import BehaviorAgent
from agents.competitor_agent import CompetitorAgent
from agents.coordinator      import CoordinatorAgent
from agents.critic_agent     import CriticAgent
from agents.base_agent       import AgentStatus
from config.settings         import MAX_CRITIC_RETRIES
from utils.dynamodb          import scan_monthly_revenue

app = FastAPI()

@app.get("/health")
def health(): return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
def _recompute_risk(df):
    import numpy as np
    df = df.copy()
    df["clearance_risk"] = np.where(
        (df["days_of_stock"] > 365) & (df["sell_through_rate"] < 20), "CRITICAL",
        np.where(
            (df["days_of_stock"] > 180) & (df["sell_through_rate"] < 40), "HIGH",
            np.where(
                (df["days_of_stock"] > 90) & (df["sell_through_rate"] < 60), "MEDIUM",
                "LOW"
            )
        )
    )
    return df
@app.get("/api/dashboard")
def get_dashboard(from_date: str = None, to_date: str = None):
    metrics     = compute_sales_metrics()
    stores      = load_store_performance()

    # Load precomputed monthly revenue (39 rows, instant)
    monthly_rows  = scan_monthly_revenue()
    total_revenue = sum(float(r.get("revenue", 0)) for r in monthly_rows)
    total_orders  = sum(int(r.get("order_count", 0)) for r in monthly_rows)

    total_skus    = len(metrics)
    high_risk     = metrics[metrics["clearance_risk"] == "HIGH"]
    dead          = metrics[metrics["is_dead_inventory"] == True]
    avg_st        = round(float(metrics["sell_through_rate"].mean()), 1)
    total_stock   = int(metrics["quantity"].sum())
    abc_counts    = metrics["abc_class"].value_counts().to_dict()

    brand_rev = metrics.groupby("brand")["total_revenue"].sum().sort_values(ascending=False).head(10)
    brand_revenue = [{"brand": str(k), "revenue": round(float(v), 0)} for k, v in brand_rev.items()]

    cat_rev = metrics.groupby("main_category")["total_revenue"].sum().sort_values(ascending=False).head(8)
    cat_revenue = [{"category": k, "revenue": round(float(v), 0)} for k, v in cat_rev.items()]

    cat_st = metrics.groupby("main_category")["sell_through_rate"].mean().sort_values(ascending=False)
    cat_sellthrough = [{"category": k, "sell_through": round(float(v), 1)} for k, v in cat_st.items()]

    cat_stock = metrics.groupby("main_category").agg(
        stock=("quantity", "sum"),
        sold=("total_qty_sold", "sum")
    ).reset_index()
    stock_vs_sold = [
        {"category": row["main_category"], "stock": int(row["stock"]), "sold": int(row["sold"])}
        for _, row in cat_stock.iterrows()
    ]

    risk_counts = metrics["clearance_risk"].value_counts().to_dict()

    # Revenue trend from precomputed table — instant, no 80k scan
    revenue_trend = sorted(
        [{"month": r["month_label"], "revenue": round(float(r.get("revenue", 0)), 0), "orders": int(r.get("order_count", 0))}
         for r in monthly_rows],
        key=lambda x: x["month"]
    )

    store_list = []
    if not stores.empty:
        for _, row in stores.head(6).iterrows():
            st_val = float(row["sell_through_rate"] if "sell_through_rate" in row.index else 0)
            name   = (row["store_name"] if "store_name" in row.index
                      else row["store_id"] if "store_id" in row.index else "Store")
            active = int(row["active_skus"] if "active_skus" in row.index
                         else row["active_markdowns"] if "active_markdowns" in row.index else 0)
            depth  = float(row["avg_discount_depth"] if "avg_discount_depth" in row.index else 0)
            store_list.append({
                "name":         str(name),
                "sell_through": round(st_val, 1),
                "active":       active,
                "depth":        round(depth, 1),
                "tier":         "HOT" if st_val >= 75 else ("COLD" if st_val < 65 else "AVG"),
            })

    top_cat      = cat_rev.idxmax() if not cat_rev.empty else "N/A"
    worst_st_cat = cat_st.idxmin()  if not cat_st.empty else "N/A"
    dead_pct     = round(len(dead) / total_skus * 100, 1) if total_skus else 0
    high_pct     = round(len(high_risk) / total_skus * 100, 1) if total_skus else 0

    insights = [
        {"icon":"💰","title":"Top Revenue Category",
         "text":f"{top_cat} drives the highest revenue. Focus markdown strategy here to recover margin without hurting top-line."},
        {"icon":"⚠️","title":"High Risk Exposure",
         "text":f"{len(high_risk):,} SKUs ({high_pct}%) are HIGH clearance risk. Immediate markdown action can recover working capital."},
        {"icon":"💀","title":"Dead Inventory Alert",
         "text":f"{len(dead):,} SKUs ({dead_pct}%) have DOS >180 days. These are tying up capital and need aggressive clearance pricing."},
        {"icon":"📉","title":"Lowest Sell-Through",
         "text":f"{worst_st_cat} has the lowest avg sell-through ({round(float(cat_st.min()),1)}%). Bundle or flash-sale strategy recommended."},
        {"icon":"🏪","title":"Store Insight",
         "text":f"{store_list[0]['name'] if store_list else 'Top store'} leads with {store_list[0]['sell_through'] if store_list else 0}% sell-through. Replicate its markdown timing across other stores."},
        {"icon":"📦","title":"Stock Health",
         "text":f"Total stock of {total_stock:,} units across {total_skus:,} SKUs. ABC-C holds {abc_counts.get('C',0):,} SKUs — prime clearance candidates."},
    ]

    return {
        "kpis": {
            "total_revenue":    total_revenue,
            "total_orders":     total_orders,
            "total_skus":       total_skus,
            "total_stock":      total_stock,
            "high_risk_count":  len(high_risk),
            "dead_inventory":   len(dead),
            "avg_sell_through": avg_st,
            "abc_a":            abc_counts.get("A", 0),
            "abc_b":            abc_counts.get("B", 0),
            "abc_c":            abc_counts.get("C", 0),
        },
        "brand_revenue":     brand_revenue,
        "cat_revenue":       cat_revenue,
        "cat_sellthrough":   cat_sellthrough,
        "stock_vs_sold":     stock_vs_sold,
        "risk_breakdown":    risk_counts,
        "store_performance": store_list,
        "revenue_trend":     revenue_trend,
        "insights":          insights,
    }

@app.get("/api/products")
def get_products(category: str = "All", risk: str = "All", limit: int = 500):
    metrics = compute_sales_metrics()
    metrics = _recompute_risk(metrics)
    df = metrics.copy()
    if category != "All":
        df = df[df["main_category"] == category]
    if risk != "All":
        df = df[df["clearance_risk"] == risk]
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    df["_risk_rank"] = df["clearance_risk"].map(risk_order).fillna(4)
    df = df.sort_values(["_risk_rank", "days_of_stock"], ascending=[True, False]).head(limit)
    categories = ["All"] + sorted(metrics["main_category"].dropna().unique().tolist())
    products = []
    for _, row in df.iterrows():
        dos = int(row.get("days_of_stock", 0))
        dos = dos if dos < 99999 else 9999
        products.append({
            "product_id":   str(row["product_id"]),
            "product_name": str(row.get("product_name", "")),
            "category":     str(row.get("main_category", "")),
            "brand":        str(row.get("brand", "")),
            "price":        float(row.get("price", 0)),
            "cost_price":   float(row.get("cost_price", 0)),
            "quantity":     int(row.get("quantity", 0)),
            "sell_through": float(row.get("sell_through_rate", 0)),
            "dos":          dos,
            "risk":         str(row.get("clearance_risk", "")),
            "abc":          str(row.get("abc_class", "")),
        })
    return {"products": products, "categories": categories}

class RunRequest(BaseModel):
    product_id: str

@app.post("/api/run")
def run_agents(req: RunRequest):
    metrics       = compute_sales_metrics()
    elasticity_df = compute_elasticity_data()
    row = metrics[metrics["product_id"] == req.product_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Product not found")
    product   = row.iloc[0].to_dict()
    elast_row = elasticity_df[elasticity_df["product_id"] == req.product_id]
    product["elasticity"] = float(elast_row["elasticity"].iloc[0]) if not elast_row.empty else -1.2
    for k, v in product.items():
        if hasattr(v, 'item'):
            product[k] = v.item()
    agents = [
        PricingAgent(), InventoryAgent(), DemandAgent(),
        PromotionAgent(), BehaviorAgent(), CompetitorAgent(),
    ]
    agent_outputs = {}
    for agent in agents:
        try:
            out = _run_agent(agent, product)
            if out:
                agent_outputs[out.agent_name] = out
        except Exception as e:
            print(f"Agent {agent.name} error: {e}")
    coordinator = CoordinatorAgent()
    critic      = CriticAgent()
    decision = coordinator.synthesise(product, agent_outputs)
    for attempt in range(MAX_CRITIC_RETRIES):
        verdict = critic.review(product, decision)
        decision.critic_verdict = verdict
        if verdict.status == AgentStatus.PASS:
            break
        decision = coordinator.synthesise(product, agent_outputs, attempt + 1, verdict.reason)
    result = {
        "product_id":     str(decision.product_id),
        "product_name":   str(decision.product_name),
        "markdown_pct":   float(decision.recommended_markdown_pct),
        "final_price":    float(decision.final_price),
        "original_price": float(product.get("price", 0)),
        "health_badge":   str(decision.health_badge),
        "promotion_type": str(decision.promotion_type),
        "reasoning":      str(decision.coordinator_reasoning),
        "critic_status":  str(decision.critic_verdict.status.value),
        "timestamp":      datetime.now().isoformat(),
        "agents": {
            name: {
                "recommendation": str(o.recommendation),
                "confidence":     float(o.confidence),
                "reasoning":      str(o.reasoning),
                "status":         str(o.status.value),
                "data":           o.data if isinstance(o.data, dict) else {},
            }
            for name, o in agent_outputs.items()
        },
    }
    _save_action({
        "type":      "EXEC",
        "summary":   f"{decision.product_name} — {decision.recommended_markdown_pct}% markdown recommended",
        "timestamp": result["timestamp"],
        "data":      result,
    })

    # Fire notifications automatically after every agent run
    try:
        from agents.notification_agent import NotificationAgent
        NotificationAgent().notify(product, decision)
    except Exception as e:
        print(f"Notification error: {e}")

    return result

@app.get("/api/history")
def get_history():
    return {"history": _load_actions()[::-1]}

@app.get("/api/planner")
def get_planner():
    import math
    metrics    = compute_sales_metrics()
    candidates = metrics[metrics["clearance_risk"].isin(["HIGH", "CRITICAL"])].copy()
    candidates = candidates.sort_values("days_of_stock", ascending=False)

    total_candidates = len(candidates)
    capital_at_risk  = float(
        (candidates["quantity"].fillna(0) * candidates["price"].fillna(0)).sum()
    )

    _finite_dos = candidates[candidates["days_of_stock"] < 99999]["days_of_stock"]
    if len(_finite_dos) == 0:
        avg_dos = 9999
    else:
        _mean = _finite_dos.mean()
        avg_dos = 9999 if (math.isnan(_mean) or _mean >= 9999) else int(_mean)

    ladders = []
    for _, row in candidates.head(100).iterrows():
        price = float(row.get("price", 0))
        cost  = float(row.get("cost_price", 0))
        qty   = int(row.get("quantity", 0))
        st    = float(row.get("sell_through_rate", 0))
        risk  = str(row.get("clearance_risk", "HIGH"))

        dos_raw = row.get("days_of_stock", 0)
        try:
            dos_raw = float(dos_raw)
        except:
            dos_raw = 99999
        if math.isnan(dos_raw) or math.isinf(dos_raw):
            dos = -1
        else:
            dos = int(min(dos_raw, 99999))

        if dos >= 99999 and st > 0:
            sold_est = qty * (st / 100) / max(1 - st / 100, 0.001)
            if sold_est > 0:
                daily_rate = sold_est / 365
                estimated  = int(qty / daily_rate)
                dos = estimated if estimated < 99999 else -1

        if dos == -1 or dos >= 9999 or risk == "CRITICAL":
            steps = [
                {"pct":20,"label":"2wk · time"},
                {"pct":35,"label":"2wk · velocity"},
                {"pct":50,"label":"2wk · time"},
                {"pct":65,"label":"Final · clearance"},
            ]
        elif dos > 180:
            steps = [
                {"pct":15,"label":"2wk · time"},
                {"pct":30,"label":"2wk · velocity"},
                {"pct":50,"label":"2wk · time"},
            ]
        else:
            steps = [
                {"pct":10,"label":"2wk · time"},
                {"pct":20,"label":"2wk · velocity"},
                {"pct":35,"label":"2wk · time"},
            ]

        margin_pct = round((price - cost) / price * 100, 1) if price > 0 else 0
        curr_price = round(price * (1 - steps[0]["pct"] / 100), 2)

        ladders.append({
            "product_id":   str(row["product_id"]),
            "product_name": str(row.get("product_name", "")),
            "category":     str(row.get("main_category", "")),
            "brand":        str(row.get("brand", "")),
            "risk":         risk,
            "abc":          str(row.get("abc_class", "")),
            "price":        price,
            "cost_price":   cost,
            "curr_price":   curr_price,
            "was_price":    price,
            "qty":          qty,
            "dos":          dos,
            "sell_through": round(st, 1),
            "margin_pct":   margin_pct,
            "steps":        steps,
            "current_step": 0,
            "total_steps":  len(steps),
        })

    return {
        "summary": {
            "total_candidates": total_candidates,
            "capital_at_risk":  round(capital_at_risk, 0),
            "avg_dos":          avg_dos,
        },
        "ladders": ladders,
    }
    
    
    
# ── Notifications ──────────────────────────────────────────────────────────
NOTIF_FILE = "data/notification_log.jsonl"

NOTIF_FILE = "data/notification_log.jsonl"

@app.get("/api/notifications")
def get_notifications():
    if not os.path.exists(NOTIF_FILE):
        return {"notifications": [], "total": 0, "high": 0, "medium": 0, "low": 0}
    rows = []
    with open(NOTIF_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except:
                    pass
    rows = list(reversed(rows))
    all_alerts = []
    for r in rows:
        for a in r.get("alerts", []):
            all_alerts.append({
                "timestamp":    r.get("timestamp", ""),
                "product_id":   r.get("product_id", ""),
                "product_name": r.get("product_name", ""),
                "markdown_pct": r.get("markdown_pct", 0),
                "health":       r.get("health", ""),
                "verdict":      r.get("verdict", ""),
                "type":         a.get("type", ""),
                "severity":     a.get("severity", ""),
                "message":      a.get("message", ""),
            })
    return {
        "notifications": all_alerts,
        "total":  len(all_alerts),
        "high":   len([a for a in all_alerts if a["severity"] == "HIGH"]),
        "medium": len([a for a in all_alerts if a["severity"] == "MEDIUM"]),
        "low":    len([a for a in all_alerts if a["severity"] == "LOW"]),
    }

@app.post("/api/test-notify")
def test_notification():
    from agents.notification_agent import NotificationAgent
    from agents.base_agent import CriticVerdict, FinalDecision
    test_product = {
        "product_id":        "TEST_001",
        "product_name":      "Test Product",
        "clearance_risk":    "HIGH",
        "abc_class":         "C",
        "is_dead_inventory": True,
        "days_of_stock":     200,
        "price":             999,
    }
    test_decision = FinalDecision(
        product_id="TEST_001",
        product_name="Test Product",
        recommended_markdown_pct=30,
        final_price=699,
        health_badge="🟡 Caution",
        coordinator_reasoning="Test notification",
        critic_verdict=CriticVerdict(
            status=AgentStatus.PASS,
            reason="Test",
            retry_count=0,
        ),
    )
    result = NotificationAgent().notify(test_product, test_decision)
    return {"status": "sent", "alerts": result["alerts_sent"]}
