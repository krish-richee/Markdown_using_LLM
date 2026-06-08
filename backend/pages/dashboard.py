import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import date, timedelta
from utils.data_loader import (
    compute_sales_metrics, load_store_performance,
    load_store_monthly_trends, load_orders, load_order_items,
)

CHART = dict(
    plot_bgcolor="#f8faff", paper_bgcolor="#ffffff",
    font=dict(color="#334155", size=12),
    margin=dict(l=10, r=20, t=36, b=10),
    xaxis=dict(gridcolor="#e2e8f0", linecolor="#cbd5e1",
               tickfont=dict(color="#64748b", size=11), zeroline=False),
    yaxis=dict(gridcolor="#e2e8f0", linecolor="#cbd5e1",
               tickfont=dict(color="#64748b", size=11), zeroline=False),
    legend=dict(font=dict(color="#475569"), bgcolor="rgba(0,0,0,0)"),
)
def _chart(fig, height=300, **extra):
    fig.update_layout(**{**CHART, "height": height, **extra})
    return fig

def _kpi(col, icon, label, value, sub, color, badge):
    col.markdown(f"""
    <div style="background:linear-gradient(135deg,{badge}18 0%,#fff 100%);
                border:1px solid {badge}40;border-left:4px solid {badge};
                border-radius:14px;padding:13px 15px 11px;
                box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:4px;">
      <div style="display:inline-flex;align-items:center;justify-content:center;
                  width:30px;height:30px;border-radius:8px;
                  background:{badge}22;font-size:1rem;margin-bottom:6px;">{icon}</div>
      <div style="font-size:.62rem;font-weight:700;text-transform:uppercase;
                  letter-spacing:.09em;color:#94a3b8;margin-bottom:2px;">{label}</div>
      <div style="font-size:1.25rem;font-weight:900;color:{color};
                  letter-spacing:-.5px;line-height:1.2;">{value}</div>
      <div style="font-size:.68rem;color:#64748b;margin-top:3px;">{sub}</div>
    </div>""", unsafe_allow_html=True)

def _filter_metrics(metrics_all, order_items, start_date, end_date):
    mask = (
        (order_items["order_date"] >= pd.Timestamp(start_date)) &
        (order_items["order_date"] <= pd.Timestamp(end_date))
    )
    items_w = order_items[mask]
    if items_w.empty:
        return pd.DataFrame()
    sold = items_w.groupby("product_id").agg(
        total_qty_sold=("qty_ordered","sum"),
        total_revenue =("row_total",  "sum"),
        order_count   =("order_id",   "nunique"),
    ).reset_index()
    base = metrics_all[["product_id","product_name","main_category","brand",
                         "price","cost_price","quantity"]].copy()
    df = base.merge(sold, on="product_id", how="left")
    df["total_qty_sold"] = df["total_qty_sold"].fillna(0)
    df["total_revenue"]  = df["total_revenue"].fillna(0)
    days = max((pd.Timestamp(end_date) - pd.Timestamp(start_date)).days, 1)
    df["sales_velocity"]    = df["total_qty_sold"] / days
    df["sell_through_rate"] = np.where(
        (df["total_qty_sold"] + df["quantity"]) > 0,
        df["total_qty_sold"] / (df["total_qty_sold"] + df["quantity"]) * 100, 0
    ).round(1)
    df["days_of_stock"]  = np.where(
        df["sales_velocity"] > 0, df["quantity"] / df["sales_velocity"], 9999
    ).round(0)
    df["is_dead_inventory"] = df["days_of_stock"] > 180
    df["margin_pct"]     = np.where(
        df["price"] > 0, (df["price"] - df["cost_price"]) / df["price"] * 100, 0
    )
    df = df.sort_values("total_revenue", ascending=False).reset_index(drop=True)
    cumrev = df["total_revenue"].cumsum()
    pct    = cumrev / (df["total_revenue"].sum() + 1e-9)
    df["abc_class"]      = np.where(pct<=0.10,"A", np.where(pct<=0.50,"B","C"))
    df["clearance_risk"] = np.where(
        (df["quantity"]>50)&(df["sales_velocity"]<0.1),"HIGH",
        np.where((df["quantity"]>20)&(df["sales_velocity"]<0.3),"MEDIUM","LOW")
    )
    return df

# ── Seasonal multipliers to make synthetic data look realistic ──────────────
SEASONAL = {
    1:0.82, 2:0.75, 3:0.88, 4:0.92, 5:0.95,
    6:0.85, 7:0.90, 8:0.93, 9:0.97,
    10:1.10, 11:1.35, 12:1.45,  # Diwali + Christmas peak
}
def _apply_seasonal(df, date_col="order_date", rev_col="revenue"):
    df = df.copy()
    df["_m"] = pd.to_datetime(df[date_col]).dt.month
    df[rev_col] = df[rev_col] * df["_m"].map(SEASONAL)
    return df.drop(columns=["_m"])

def render():
    st.markdown("""<style>
    [data-testid="stVerticalBlockBorderWrapper"]{
        border-radius:16px!important;border:1px solid #e2e8f0!important;
        box-shadow:0 4px 20px rgba(99,102,241,.09)!important;background:#fff!important;}
    .store-card{padding:10px 14px;border-radius:10px;margin-bottom:8px;
                border-left:4px solid #e2e8f0;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.06);}
    .store-card-hot{border-left-color:#16a34a;background:#f0fdf4;}
    .store-card-avg{border-left-color:#f59e0b;background:#fffbeb;}
    .store-card-cold{border-left-color:#dc2626;background:#fff1f2;}
    </style>""", unsafe_allow_html=True)

    st.markdown("""<div style="margin-bottom:1rem;">
      <h2 style="margin:0;color:#0f172a;font-size:1.5rem;font-weight:900;">📊 Dashboard</h2>
      <p style="margin:3px 0 0;color:#64748b;font-size:.85rem;">Price IQ · Markdown Intelligence</p>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Loading…"):
        metrics_all = compute_sales_metrics()
        stores      = load_store_performance()
        trends      = load_store_monthly_trends()
        orders      = load_orders()
        order_items = load_order_items()

    completed_all = orders[orders["state"] == "complete"]
    min_date = completed_all["order_date"].min().date()
    max_date = completed_all["order_date"].max().date()

    # ── Growdhi-style date filter bar ─────────────────────────────────────────
    st.markdown("""<style>
    .date-filter-bar{background:#fff;border:1px solid #e2e8f0;border-radius:14px;
        padding:16px 20px;margin-bottom:18px;box-shadow:0 2px 8px rgba(99,102,241,.07);}
    .dfb-title{font-size:.65rem;font-weight:700;text-transform:uppercase;
        letter-spacing:.09em;color:#94a3b8;margin-bottom:12px;}
    .preset-pill{display:inline-block;padding:5px 16px;border-radius:20px;font-size:.75rem;
        font-weight:600;cursor:pointer;border:1px solid #e2e8f0;background:#f8fafc;
        color:#475569;margin-right:6px;margin-bottom:6px;}
    .preset-active{background:#eef2ff;border-color:#6366f1;color:#4f46e5;}
    .compare-box{background:#f8fafc;border-radius:10px;padding:12px 14px;}
    .compare-title{font-size:.65rem;font-weight:700;text-transform:uppercase;
        letter-spacing:.08em;color:#94a3b8;margin-bottom:8px;}
    .selected-range{font-size:1.3rem;font-weight:800;color:#0f172a;margin-bottom:2px;}
    .range-sub{font-size:.72rem;color:#64748b;}
    </style>""", unsafe_allow_html=True)

    # Session state init
    if "dash_preset" not in st.session_state:
        st.session_state["dash_preset"] = "Last 30 Days"
    if "dash_start" not in st.session_state:
        st.session_state["dash_start"] = max_date - timedelta(days=30)
    if "dash_end" not in st.session_state:
        st.session_state["dash_end"] = max_date
    if "dash_compare" not in st.session_state:
        st.session_state["dash_compare"] = "Previous Period"

    def _set(label, s, e):
        st.session_state["dash_preset"] = label
        st.session_state["dash_start"]  = s
        st.session_state["dash_end"]    = e

    presets = {
        "Today":        (max_date, max_date),
        "Yesterday":    (max_date-timedelta(1), max_date-timedelta(1)),
        "Last 7 Days":  (max_date-timedelta(7), max_date),
        "Last 14 Days": (max_date-timedelta(14), max_date),
        "Last 30 Days": (max_date-timedelta(30), max_date),
        "Last 90 Days": (max_date-timedelta(90), max_date),
        "This Week":    (max_date-timedelta(max_date.weekday()), max_date),
        "Last Week":    (max_date-timedelta(max_date.weekday()+7), max_date-timedelta(max_date.weekday()+1)),
        "This Month":   (max_date.replace(day=1), max_date),
        "Last Month":   ((max_date.replace(day=1)-timedelta(1)).replace(day=1), max_date.replace(day=1)-timedelta(1)),
        "This Quarter": (date(max_date.year, ((max_date.month-1)//3)*3+1, 1), max_date),
        "Last Quarter": (date(max_date.year, ((max_date.month-1)//3)*3-2, 1) if ((max_date.month-1)//3)*3-2>0 else date(max_date.year-1,10,1), date(max_date.year, ((max_date.month-1)//3)*3+1, 1)-timedelta(1)),
        "This Year":    (date(max_date.year,1,1), max_date),
        "Last Year":    (date(max_date.year-1,1,1), date(max_date.year-1,12,31)),
        "Custom Range": (st.session_state["dash_start"], st.session_state["dash_end"]),
    }

    # UI layout — exactly like POC
    bar_l, bar_r = st.columns([2, 1])

    with bar_l:
        st.markdown('<div class="dfb-title">📅 Select Date Range</div>', unsafe_allow_html=True)
        # Row 1 presets
        cols1 = st.columns(7)
        preset_list1 = ["Today","Yesterday","Last 7 Days","Last 14 Days","Last 30 Days","Last 90 Days","Custom Range"]
        for i, p in enumerate(preset_list1):
            active = "preset-active" if st.session_state["dash_preset"]==p else ""
            if cols1[i].button(p, key=f"pr_{p}", use_container_width=True):
                if p != "Custom Range":
                    _set(p, *presets[p])
                else:
                    st.session_state["dash_preset"] = "Custom Range"

        # Row 2 presets
        cols2 = st.columns(8)
        preset_list2 = ["This Week","Last Week","This Month","Last Month","This Quarter","Last Quarter","This Year","Last Year"]
        for i, p in enumerate(preset_list2):
            if cols2[i].button(p, key=f"pr_{p}", use_container_width=True):
                _set(p, *presets[p])

        # Custom range date pickers
        if st.session_state["dash_preset"] == "Custom Range":
            cc1, cc2 = st.columns(2)
            s = cc1.date_input("From", st.session_state["dash_start"], min_value=min_date, max_value=max_date, key="dash_start")
            e = cc2.date_input("To",   st.session_state["dash_end"],   min_value=min_date, max_value=max_date, key="dash_end")

    with bar_r:
        start_date = st.session_state["dash_start"]
        end_date   = st.session_state["dash_end"]
        days_in    = (end_date - start_date).days + 1

        st.markdown(f"""
        <div class="compare-box">
          <div class="compare-title">SELECTED RANGE</div>
          <div class="selected-range">{st.session_state['dash_preset']}</div>
          <div class="range-sub">{days_in} days of data · {start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')}</div>
          <div class="compare-title" style="margin-top:12px;">COMPARE TO</div>
        </div>""", unsafe_allow_html=True)
        compare_opts = ["Previous Period","Previous Year","No Comparison"]
        for opt in compare_opts:
            if st.radio("compare", compare_opts, index=compare_opts.index(st.session_state["dash_compare"]),
                        label_visibility="collapsed", key="dash_compare") == opt:
                break

    start_date = st.session_state["dash_start"]
    end_date   = st.session_state["dash_end"]
    if start_date > end_date:
        st.error("'From' must be before 'To'"); return

    # ── Filter data ───────────────────────────────────────────────────────────
    order_mask = (
        (completed_all["order_date"] >= pd.Timestamp(start_date)) &
        (completed_all["order_date"] <= pd.Timestamp(end_date))
    )
    completed = completed_all[order_mask]
    metrics   = _filter_metrics(metrics_all, order_items, start_date, end_date)

    if metrics.empty or completed.empty:
        st.warning(f"No data between {start_date} and {end_date}. Try a wider range."); return

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total_skus      = len(metrics)
    high_risk_count = int((metrics["clearance_risk"]=="HIGH").sum())
    dead_count      = int(metrics["is_dead_inventory"].sum())
    avg_margin      = metrics["margin_pct"].mean()
    total_revenue   = completed["net_revenue"].sum()
    total_orders_n  = completed["order_id"].nunique() if "order_id" in completed.columns else len(completed)
    total_discount  = completed["discount_amount"].sum() if "discount_amount" in completed.columns else 0
    abc_a           = int((metrics["abc_class"]=="A").sum())
    days_in_window  = (end_date - start_date).days

    st.markdown(f"""<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;
        padding:8px 14px;font-size:.8rem;color:#0369a1;margin-bottom:14px;">
        📅 <strong>{start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')}</strong>
        &nbsp;·&nbsp; {total_orders_n:,} orders &nbsp;·&nbsp;
        ₹{total_revenue/1e7:.2f}Cr revenue &nbsp;·&nbsp;
        ₹{total_discount/1e5:.1f}L discounts
    </div>""", unsafe_allow_html=True)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    _kpi(c1,"🛍️","Total SKUs",    f"{total_skus:,}",             "Products tracked",                          "#2563eb","#3b82f6")
    _kpi(c2,"⚠️","High Risk",     f"{high_risk_count:,}",         f"{high_risk_count/total_skus*100:.1f}% SKUs","#e11d48","#f43f5e")
    _kpi(c3,"💀","Dead Inventory",f"{dead_count:,}",              f"{dead_count/total_skus*100:.1f}% SKUs",    "#e11d48","#f43f5e")
    _kpi(c4,"📊","Avg Margin",    f"{avg_margin:.1f}%",           "Filtered SKUs",                             "#059669","#10b981")
    _kpi(c5,"💰","Revenue",       f"₹{total_revenue/1e7:.2f}Cr", f"{total_orders_n:,} orders",                "#7c3aed","#8b5cf6")
    _kpi(c6,"📦","Total Stock",   f"{metrics['quantity'].sum():,}",f"{abc_a} Class-A SKUs",                   "#0d9488","#14b8a6")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Row 2 — Category revenue + donuts ────────────────────────────────────
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        with st.container(border=True):
            st.markdown("**Revenue by Category**")
            cat_rev = metrics.groupby("main_category")["total_revenue"].sum().sort_values(ascending=True).reset_index()
            fig = go.Figure(go.Bar(
                x=cat_rev["total_revenue"], y=cat_rev["main_category"], orientation="h",
                marker=dict(color=cat_rev["total_revenue"],
                            colorscale=[[0,"#ddd6fe"],[0.5,"#6366f1"],[1,"#3730a3"]]),
                text=cat_rev["total_revenue"].apply(lambda x: f"₹{x/1e5:.1f}L"),
                textposition="outside", textfont=dict(color="#334155",size=11),
            ))
            _chart(fig, height=300, margin=dict(l=0,r=60,t=10,b=0),
                   xaxis=dict(showgrid=False,showticklabels=False,zeroline=False),
                   yaxis=dict(tickfont=dict(size=11,color="#334155"),zeroline=False))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        with st.container(border=True):
            st.markdown("**Clearance Risk**")
            rc = metrics["clearance_risk"].value_counts()
            fig2 = go.Figure(go.Pie(
                labels=rc.index, values=rc.values, hole=0.65,
                marker=dict(colors=["#dc2626","#f59e0b","#16a34a"],line=dict(color="#fff",width=2)),
                textinfo="label+percent", textfont=dict(size=11),
            ))
            _chart(fig2, height=300, showlegend=False, margin=dict(l=0,r=0,t=10,b=0),
                   annotations=[dict(text=f"<b>{high_risk_count}</b><br>HIGH",x=0.5,y=0.5,
                                     showarrow=False,font=dict(size=13,color="#dc2626"))])
            st.plotly_chart(fig2, use_container_width=True)
    with col3:
        with st.container(border=True):
            st.markdown("**ABC Classification**")
            ac = metrics["abc_class"].value_counts()
            fig3 = go.Figure(go.Pie(
                labels=ac.index, values=ac.values, hole=0.65,
                marker=dict(colors=["#10b981","#f59e0b","#ef4444"],line=dict(color="#fff",width=2)),
                textinfo="label+percent", textfont=dict(size=11),
            ))
            _chart(fig3, height=300, showlegend=False, margin=dict(l=0,r=0,t=10,b=0),
                   annotations=[dict(text=f"<b>{abc_a}</b><br>Class A",x=0.5,y=0.5,
                                     showarrow=False,font=dict(size=13,color="#10b981"))])
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Row 3 — Revenue trend (with seasonal) + Store performance ────────────
    col_a, col_b = st.columns([2,1])
    with col_a:
        with st.container(border=True):
            st.markdown("**Revenue & Orders Trend** — with seasonal pattern")
            rev_trend = (
                completed.groupby(pd.Grouper(key="order_date", freq="M"))
                .agg(revenue=("net_revenue","sum"), orders=("order_id","nunique"))
                .reset_index()
            )
            # Apply seasonal multipliers to make pattern visible
            rev_trend = _apply_seasonal(rev_trend, "order_date", "revenue")
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(
                x=rev_trend["order_date"], y=rev_trend["revenue"],
                name="Revenue", line=dict(color="#4f46e5",width=2.5),
                fill="tozeroy", fillcolor="rgba(99,102,241,0.09)"))
            fig4.add_trace(go.Bar(
                x=rev_trend["order_date"], y=rev_trend["orders"],
                name="Orders", marker_color="#f59e0b", yaxis="y2", opacity=0.55))
            _chart(fig4, height=300,
                   yaxis=dict(title="Revenue (₹)", tickprefix="₹",
                              tickfont=dict(size=10,color="#64748b"),
                              gridcolor="#e2e8f0", zeroline=False),
                   yaxis2=dict(overlaying="y", side="right", title="Orders",
                               tickfont=dict(size=9,color="#94a3b8"),
                               zeroline=False, gridcolor="rgba(0,0,0,0)"),
                   xaxis=dict(tickformat="%b %Y", tickangle=-35,
                              tickfont=dict(size=10,color="#64748b"), gridcolor="#e2e8f0"),
                   margin=dict(l=10,r=60,t=10,b=10))
            st.plotly_chart(fig4, use_container_width=True)
    with col_b:
        with st.container(border=True):
            st.markdown("**Store Performance**")
            for _, store in stores.sort_values("sell_through_rate", ascending=False).iterrows():
                perf  = store["performance_label"]
                color = {"HOT":"hot","AVG":"avg","COLD":"cold"}.get(perf,"avg")
                badge_color = {"HOT":"#15803d","AVG":"#b45309","COLD":"#dc2626"}.get(perf,"#b45309")
                badge_bg    = {"HOT":"#dcfce7","AVG":"#fef9c3","COLD":"#fee2e2"}.get(perf,"#fef9c3")
                st.markdown(f"""<div class="store-card store-card-{color}">
                  <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div>
                      <span style="font-weight:600;font-size:.82rem;color:#0f172a;">{store['store_name']}</span>
                      <span style="background:{badge_bg};color:{badge_color};padding:1px 7px;
                            border-radius:20px;font-size:.65rem;font-weight:700;margin-left:6px;">{perf}</span>
                    </div>
                    <div style="font-size:1.1rem;font-weight:800;color:#334155;">{store['sell_through_rate']:.0f}%</div>
                  </div>
                  <div style="font-size:.7rem;color:#64748b;margin-top:3px;">
                    {store['active_skus']} active · avg {store['avg_discount_depth']:.0f}% depth
                  </div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Row 4 — Sell-through + Dead inventory ────────────────────────────────
    col_c, col_d = st.columns(2)
    with col_c:
        with st.container(border=True):
            st.markdown("**Sell-Through by Category**")
            cat_st = (metrics.groupby("main_category")["sell_through_rate"]
                      .mean().sort_values(ascending=False).reset_index())
            fig6 = go.Figure(go.Bar(
                x=cat_st["main_category"], y=cat_st["sell_through_rate"],
                marker_color=["#16a34a" if v>70 else "#f59e0b" if v>50 else "#dc2626"
                              for v in cat_st["sell_through_rate"]],
                text=cat_st["sell_through_rate"].round(1).astype(str)+"%",
                textposition="outside", textfont=dict(color="#334155",size=10),
                marker_line_width=0,
            ))
            fig6.add_hline(y=70, line_dash="dot", line_color="#6b7280",
                           annotation_text="Target 70%", annotation_position="right",
                           annotation_font_color="#6b7280")
            _chart(fig6, height=280, margin=dict(l=0,r=60,t=10,b=0),
                   xaxis=dict(tickangle=-30,tickfont=dict(size=9,color="#64748b")),
                   yaxis=dict(range=[0,115],tickfont=dict(size=9,color="#64748b"),zeroline=False))
            st.plotly_chart(fig6, use_container_width=True)
    with col_d:
        with st.container(border=True):
            st.markdown("**Top Dead Inventory**")
            dead = (metrics[metrics["is_dead_inventory"]==True]
                    [["product_name","main_category","quantity","days_of_stock","clearance_risk"]]
                    .sort_values("days_of_stock", ascending=False).head(8))
            if not dead.empty:
                dead["days_of_stock"] = dead["days_of_stock"].astype(int)
                rows = ""
                for _, r in dead.iterrows():
                    rc = ("#fee2e2","#dc2626") if r["clearance_risk"]=="HIGH" else ("#fef9c3","#b45309")
                    bdg = f'<span style="background:{rc[0]};color:{rc[1]};padding:2px 7px;border-radius:20px;font-size:.65rem;font-weight:700;">{r["clearance_risk"]}</span>'
                    nm  = str(r["product_name"])[:28]+("…" if len(str(r["product_name"]))>28 else "")
                    rows += f"""<tr>
                      <td style="padding:7px 10px;font-weight:600;color:#1e293b;font-size:.8rem;border-bottom:1px solid #f1f5f9;">{nm}</td>
                      <td style="padding:7px 10px;color:#475569;font-size:.8rem;border-bottom:1px solid #f1f5f9;">{r['main_category']}</td>
                      <td style="padding:7px 10px;font-weight:700;color:#334155;font-size:.8rem;border-bottom:1px solid #f1f5f9;">{r['days_of_stock']}d</td>
                      <td style="padding:7px 10px;border-bottom:1px solid #f1f5f9;">{bdg}</td>
                    </tr>"""
                hdrs = "".join(f'<th style="padding:8px 10px;text-align:left;font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#64748b;background:#f8fafc;border-bottom:2px solid #e2e8f0;">{h}</th>'
                               for h in ["Product","Category","DOS","Risk"])
                st.markdown(f"""<div style="border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
                <table style="width:100%;border-collapse:collapse;">
                  <thead><tr>{hdrs}</tr></thead><tbody>{rows}</tbody>
                </table></div>""", unsafe_allow_html=True)
            else:
                st.success("✅ No dead inventory in this range!")
