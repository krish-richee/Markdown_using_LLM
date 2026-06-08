import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from utils.data_loader import compute_sales_metrics, compute_elasticity_data, compute_event_metrics
from agents.pricing_agent import PricingAgent
from agents.inventory_agent import InventoryAgent
from agents.demand_agent import DemandAgent
from agents.promotion_agent import PromotionAgent
from agents.behavior_agent import BehaviorAgent
from agents.competitor_agent import CompetitorAgent
from agents.coordinator import CoordinatorAgent
from agents.critic_agent import CriticAgent
from agents.notification_agent import NotificationAgent
from agents.base_agent import AgentStatus
from config.settings import MAX_CRITIC_RETRIES

ACTIONS_LOG = "data/actions_log.jsonl"


def _save_action(action: dict):
    os.makedirs("data", exist_ok=True)
    with open(ACTIONS_LOG, "a") as f:
        f.write(json.dumps(action) + "\n")


def _load_actions() -> list:
    if not os.path.exists(ACTIONS_LOG):
        return []
    with open(ACTIONS_LOG) as f:
        return [json.loads(l) for l in f if l.strip()]


def render():
    st.markdown("""
    <div class="page-header">
        <div class="page-title">✅ Actions</div>
        <div class="page-subtitle">
            Price IQ · Review and approve AI markdown recommendations
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data ──────────────────────────────────────────────────────────
    with st.spinner("Loading products..."):
        metrics       = compute_sales_metrics()
        elasticity_df = compute_elasticity_data()
        event_metrics = compute_event_metrics()

    # ── Product selector ───────────────────────────────────────────────────
    st.markdown("### 🛍️ Select Product to Analyse")

    col1, col2 = st.columns([1, 2])
    with col1:
        cat_options = ["All"] + sorted(
            metrics["main_category"].unique().tolist()
        )
        selected_cat = st.selectbox("Category", cat_options)

    filtered = metrics[metrics["clearance_risk"].isin(["HIGH", "MEDIUM"])]
    if selected_cat != "All":
        filtered = filtered[filtered["main_category"] == selected_cat]

    with col2:
        product_options = filtered["product_name"].tolist()
        selected_name   = st.selectbox(
            f"Product ({len(product_options)} available)",
            product_options,
        )

    if not selected_name:
        st.info("Select a product to generate an AI recommendation.")
        return

    row = filtered[filtered["product_name"] == selected_name].iloc[0]
    pid = row["product_id"]

    elast_row  = elasticity_df[elasticity_df["product_id"] == pid]
    elasticity = float(elast_row["elasticity"].mean()) \
                 if not elast_row.empty else -1.2

    product = row.to_dict()
    product["elasticity"]               = elasticity
    product["recommended_markdown_pct"] = 20
    product["forecast_days"]            = 30

    # ── Product info ───────────────────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Price",      f"₹{row['price']:,.2f}")
    c2.metric("💲 Cost",       f"₹{row.get('cost_price', row['price']*0.55):,.2f}")
    c3.metric("📦 Stock",      f"{int(row['quantity'])} units")
    c4.metric("⚠️ Risk",       row["clearance_risk"])
    c5.metric("🏷️ ABC Class",  row["abc_class"])

    st.caption(
        f"DOS: **{int(row.get('days_of_stock',0))}d** · "
        f"Velocity: **{row.get('sales_velocity',0):.3f} u/day** · "
        f"Sell-through: **{row.get('sell_through_rate',0):.1f}%** · "
        f"Category: **{row['main_category']}**"
    )

    st.divider()

    # ── Run pipeline button ────────────────────────────────────────────────
    if st.button(
        "🤖 Run AI Pipeline — Generate Recommendation",
        type="primary",
        use_container_width=True,
    ):
        with st.status(
            "🤖 Running AI agents...", expanded=True
        ) as status:

            # Run all agents
            st.write("💰 Pricing Agent (Groq)...")
            pricing_out = PricingAgent().analyze(product)

            st.write("📦 Inventory Agent (Groq)...")
            inventory_out = InventoryAgent().analyze(product)

            st.write("📈 Demand Agent (Groq)...")
            demand_out = DemandAgent().analyze(product)

            st.write("🎯 Promotion Agent...")
            promo_out = PromotionAgent().analyze(product)

            st.write("👥 Behavior Agent...")
            behavior_out = BehaviorAgent().analyze(product, event_metrics)

            st.write("🔍 Competitor Agent (Tavily)...")
            comp_out = CompetitorAgent().analyze(product)

            agent_outputs = {
                "PricingAgent":    pricing_out,
                "InventoryAgent":  inventory_out,
                "DemandAgent":     demand_out,
                "PromotionAgent":  promo_out,
                "BehaviorAgent":   behavior_out,
                "CompetitorAgent": comp_out,
            }

            # Coordinator + Critic loop
            st.write("🧠 Coordinator synthesising (Groq)...")
            coordinator     = CoordinatorAgent()
            critic          = CriticAgent()
            retry_count     = 0
            critic_feedback = ""
            decision        = None

            while retry_count <= MAX_CRITIC_RETRIES:
                decision = coordinator.synthesise(
                    product, agent_outputs,
                    retry_count=retry_count,
                    critic_feedback=critic_feedback,
                )
                st.write(
                    f"🔍 Critic reviewing "
                    f"(attempt {retry_count+1})..."
                )
                verdict = critic.review(product, decision)

                if verdict.status == AgentStatus.PASS:
                    st.write("✅ Critic approved!")
                    break
                else:
                    critic_feedback = verdict.reason
                    retry_count    += 1
                    if retry_count > MAX_CRITIC_RETRIES:
                        st.write("⚠️ Max retries — forcing approval")
                        decision.critic_verdict.status = AgentStatus.PASS
                        break

            status.update(
                label="✅ AI Pipeline complete!", state="complete"
            )

        # Store in session
        st.session_state["last_decision"]      = decision
        st.session_state["last_agent_outputs"] = agent_outputs
        st.session_state["last_product"]       = product

    # ── Show decision if available ─────────────────────────────────────────
    if "last_decision" in st.session_state:
        decision      = st.session_state["last_decision"]
        agent_outputs = st.session_state["last_agent_outputs"]

        st.markdown("### 📊 AI Recommendation")

        # Health badge
        health = decision.health_badge
        if "🟢" in health:
            badge_css = "health-green"
        elif "🔴" in health:
            badge_css = "health-red"
        else:
            badge_css = "health-yellow"

        st.markdown(
            f'<div class="{badge_css}" '
            f'style="margin-bottom:1rem">{health}</div>',
            unsafe_allow_html=True,
        )

        # Decision metrics
        d1, d2, d3, d4 = st.columns(4)
        d1.metric(
            "📉 Recommended Markdown",
            f"{decision.recommended_markdown_pct}%",
        )
        d2.metric(
            "💰 New Price",
            f"₹{decision.final_price:,.2f}",
            f"-₹{row['price']-decision.final_price:,.2f}",
        )
        d3.metric(
            "🎯 Promotion",
            decision.promotion_type.upper(),
        )
        d4.metric(
            "🔄 Critic Retries",
            str(retry_count if "retry_count" in dir() else 0),
        )

        # Reasoning
        st.info(f"**AI Reasoning:** {decision.coordinator_reasoning}")

        # Agent summary
        with st.expander("📋 View all agent outputs"):
            for name, out in agent_outputs.items():
                conf_pct = int(out.confidence * 100)
                st.markdown(f"""
                <div class="agent-card">
                    <div class="agent-card-name">{name}</div>
                    <div class="agent-card-rec">{out.recommendation}</div>
                    <div class="agent-card-reasoning">{out.reasoning}</div>
                    <div class="confidence-bar-wrap">
                        <div class="confidence-bar"
                             style="width:{conf_pct}%"></div>
                    </div>
                    <div style="font-size:0.7rem;color:#9ca3af;
                                margin-top:2px;">
                        Confidence: {out.confidence:.0%}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # ── Approve / Reject / Modify ──────────────────────────────────
        st.markdown("### 🎯 Your Decision")
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            if st.button(
                "✅ Approve",
                type="primary",
                use_container_width=True,
            ):
                _save_action({
                    "timestamp":   datetime.now().isoformat(),
                    "product_id":  pid,
                    "product_name":selected_name,
                    "action":      "APPROVED",
                    "markdown_pct":decision.recommended_markdown_pct,
                    "final_price": decision.final_price,
                    "health":      decision.health_badge,
                    "promo":       decision.promotion_type,
                })
                # Send notifications
                NotificationAgent().notify(product, decision)
                st.success(
                    f"✅ Approved! {decision.recommended_markdown_pct}% "
                    f"markdown on {selected_name}"
                )

        with col_b:
            if st.button(
                "❌ Reject",
                use_container_width=True,
            ):
                _save_action({
                    "timestamp":   datetime.now().isoformat(),
                    "product_id":  pid,
                    "product_name":selected_name,
                    "action":      "REJECTED",
                    "markdown_pct":decision.recommended_markdown_pct,
                    "reason":      "Manual rejection",
                })
                st.error("❌ Recommendation rejected.")

        with col_c:
            custom_pct = st.number_input(
                "✏️ Custom markdown %",
                min_value  = 0,
                max_value  = 60,
                value      = int(decision.recommended_markdown_pct),
                step       = 5,
            )
            if st.button("💾 Save Custom", use_container_width=True):
                _save_action({
                    "timestamp":   datetime.now().isoformat(),
                    "product_id":  pid,
                    "product_name":selected_name,
                    "action":      "MODIFIED",
                    "markdown_pct":custom_pct,
                    "final_price": row["price"] * (1 - custom_pct/100),
                    "original_pct":decision.recommended_markdown_pct,
                })
                st.success(f"💾 Saved custom {custom_pct}% markdown.")

    # ── Action history ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📜 Recent Actions")
    actions = _load_actions()
    if actions:
        df = pd.DataFrame(actions[-20:]).iloc[::-1]
        df["timestamp"] = pd.to_datetime(
            df["timestamp"]
        ).dt.strftime("%d %b %H:%M")
        st.dataframe(
            df[["timestamp","product_name","action",
                "markdown_pct","final_price"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No actions yet — approve or reject a recommendation above.")
