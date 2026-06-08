import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
from utils.data_loader import compute_sales_metrics, load_store_performance

ACTIONS_LOG  = "data/actions_log.jsonl"
NOTIF_LOG    = "data/notification_log.jsonl"


def _load_jsonl(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def render():
    st.markdown("""
    <div class="page-header">
        <div class="page-title">📈 Reports</div>
        <div class="page-subtitle">
            Price IQ · Performance history · Export · Audit trail
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data ──────────────────────────────────────────────────────────
    metrics  = compute_sales_metrics()
    stores   = load_store_performance()
    actions  = _load_jsonl(ACTIONS_LOG)
    notifs   = _load_jsonl(NOTIF_LOG)

    # ── Summary KPIs ───────────────────────────────────────────────────────
    total_actions  = len(actions)
    approved       = len(actions[actions["action"] == "APPROVED"]) \
                     if not actions.empty and "action" in actions else 0
    rejected       = len(actions[actions["action"] == "REJECTED"]) \
                     if not actions.empty and "action" in actions else 0
    modified       = len(actions[actions["action"] == "MODIFIED"]) \
                     if not actions.empty and "action" in actions else 0
    total_notifs   = len(notifs)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Total Actions",   total_actions)
    c2.metric("✅ Approved",        approved)
    c3.metric("❌ Rejected",        rejected)
    c4.metric("✏️ Modified",        modified)
    c5.metric("📣 Notifications",   total_notifs)

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Action History",
        "🏪 Store Report",
        "📦 Inventory Report",
        "📣 Notification Log",
    ])

    # ── Tab 1 — Action history ─────────────────────────────────────────────
    with tab1:
        st.markdown("#### 📋 All Actions")

        if actions.empty:
            st.info("No actions yet. Approve or reject recommendations in the Actions page.")
        else:
            # Format
            df = actions.copy()
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(
                    df["timestamp"]
                ).dt.strftime("%d %b %Y %H:%M")

            if "markdown_pct" in df.columns:
                df["markdown_pct"] = df["markdown_pct"].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else ""
                )

            if "final_price" in df.columns:
                df["final_price"] = df["final_price"].apply(
                    lambda x: f"₹{x:,.2f}" if pd.notna(x) else ""
                )

            st.dataframe(df, use_container_width=True, hide_index=True)

            # Action breakdown chart
            if not actions.empty and "action" in actions.columns:
                action_counts = actions["action"].value_counts()
                fig = go.Figure(go.Bar(
                    x            = action_counts.index,
                    y            = action_counts.values,
                    marker_color = ["#16a34a","#dc2626","#f59e0b"],
                    text         = action_counts.values,
                    textposition = "outside",
                ))
                fig.update_layout(
                    title        = "Action Distribution",
                    height       = 250,
                    margin       = dict(l=0,r=0,t=40,b=0),
                    plot_bgcolor = "rgba(0,0,0,0)",
                    paper_bgcolor= "rgba(0,0,0,0)",
                    yaxis        = dict(showgrid=True,
                                        gridcolor="#f3f4f6"),
                )
                st.plotly_chart(fig, use_container_width=True)

            # Download
            csv = actions.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Download Actions CSV",
                data      = csv,
                file_name = "retailai_actions.csv",
                mime      = "text/csv",
            )

    # ── Tab 2 — Store report ───────────────────────────────────────────────
    with tab2:
        st.markdown("#### 🏪 Store Performance Report")

        if stores.empty:
            st.info("No store data available.")
        else:
            # Sort by sell-through
            df_stores = stores.sort_values(
                "sell_through_rate", ascending=False
            )

            # Chart
            colors = {
                "HOT":  "#16a34a",
                "AVG":  "#f59e0b",
                "COLD": "#3b82f6",
            }
            bar_colors = [
                colors.get(p, "#6b7280")
                for p in df_stores["performance_label"]
            ]

            fig2 = go.Figure(go.Bar(
                x            = df_stores["store_name"],
                y            = df_stores["sell_through_rate"],
                marker_color = bar_colors,
                text         = df_stores["sell_through_rate"].apply(
                    lambda x: f"{x:.1f}%"
                ),
                textposition = "outside",
            ))
            fig2.add_hline(
                y                  = 70,
                line_dash          = "dot",
                line_color         = "#6b7280",
                annotation_text    = "Target 70%",
                annotation_position= "right",
            )
            fig2.update_layout(
                title        = "Sell-Through Rate by Store",
                height       = 320,
                margin       = dict(l=0,r=60,t=40,b=0),
                plot_bgcolor = "rgba(0,0,0,0)",
                paper_bgcolor= "rgba(0,0,0,0)",
                xaxis        = dict(tickangle=-30,
                                    tickfont=dict(size=9)),
                yaxis        = dict(showgrid=True,
                                    gridcolor="#f3f4f6",
                                    range=[0,110]),
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Table
            display_cols = [
                "store_name","city","performance_label",
                "sell_through_rate","avg_discount_depth",
                "active_skus","monthly_revenue",
                "total_stock_units","units_sold",
            ]
            available = [
                c for c in display_cols if c in df_stores.columns
            ]
            st.dataframe(
                df_stores[available],
                use_container_width=True,
                hide_index=True,
            )

            csv2 = df_stores.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Download Store Report CSV",
                data      = csv2,
                file_name = "retailai_store_report.csv",
                mime      = "text/csv",
            )

    # ── Tab 3 — Inventory report ───────────────────────────────────────────
    with tab3:
        st.markdown("#### 📦 Inventory Intelligence Report")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**HIGH Risk Products**")
            high = metrics[
                metrics["clearance_risk"] == "HIGH"
            ][[
                "product_name","main_category","quantity",
                "days_of_stock","sell_through_rate","abc_class"
            ]].sort_values("days_of_stock", ascending=False).head(15)
            high.columns = ["Product","Category","Stock",
                            "DOS","ST%","ABC"]
            st.dataframe(high, use_container_width=True,
                         hide_index=True)

        with col2:
            st.markdown("**Dead Inventory**")
            dead = metrics[
                metrics["is_dead_inventory"] == True
            ][[
                "product_name","main_category","quantity",
                "days_of_stock","total_revenue"
            ]].sort_values("days_of_stock", ascending=False).head(15)
            dead.columns = ["Product","Category","Stock",
                            "DOS","Revenue"]
            dead["Revenue"] = dead["Revenue"].apply(
                lambda x: f"₹{x:,.0f}"
            )
            st.dataframe(dead, use_container_width=True,
                         hide_index=True)

        # Download full inventory report
        inv_report = metrics[[
            "product_id","product_name","main_category",
            "brand","price","quantity","days_of_stock",
            "sell_through_rate","sales_velocity",
            "abc_class","clearance_risk","is_dead_inventory",
            "total_revenue"
        ]].copy()

        csv3 = inv_report.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Download Full Inventory Report CSV",
            data      = csv3,
            file_name = "retailai_inventory_report.csv",
            mime      = "text/csv",
        )

    # ── Tab 4 — Notification log ───────────────────────────────────────────
    with tab4:
        st.markdown("#### 📣 Notification Log")

        if notifs.empty:
            st.info("No notifications sent yet.")
        else:
            df_notifs = notifs.copy()
            if "timestamp" in df_notifs.columns:
                df_notifs["timestamp"] = pd.to_datetime(
                    df_notifs["timestamp"]
                ).dt.strftime("%d %b %Y %H:%M")

            st.dataframe(
                df_notifs[[
                    c for c in [
                        "timestamp","product_name",
                        "markdown_pct","health",
                        "verdict","alerts_sent"
                    ] if c in df_notifs.columns
                ]],
                use_container_width=True,
                hide_index=True,
            )

            csv4 = df_notifs.to_csv(index=False).encode()
            st.download_button(
                "⬇️ Download Notification Log CSV",
                data      = csv4,
                file_name = "retailai_notifications.csv",
                mime      = "text/csv",
            )
